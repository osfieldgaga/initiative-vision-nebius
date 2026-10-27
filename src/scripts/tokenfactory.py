"""Nebius Token Factory chat client that records every exchange, so a run can be replayed without a key.

Live: each request goes to Token Factory (OpenAI-compatible) and the request's sha256 and the full
response are appended to a transcript file. Replay: requests are answered from the transcript in
order; a request whose sha256 differs from the recorded one stops the replay (the code or inputs
changed), so a replay reproduces the recorded run exactly or fails loudly. One allowance: images are
JPEGs this code encodes (agent.upright_jpeg), and another OpenCV build may encode the same frame with
different bytes. If only image bytes differ and every text in the request matches the recording, the
call is replayed and counted in Client.image_mismatches, which the agent reports.

Key: $NEBIUS_API_KEY, else the first line of apikey.md at the repo root (git-excluded). It is
only ever sent in the Authorization header.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_URL = "https://api.tokenfactory.nebius.com/v1"
SUPER = "nvidia/nemotron-3-super-120b-a12b"
VL = "nvidia/Nemotron-3.5-Super-VL"
# USD per million (input, output) tokens. Super from the public price list (2026-10); VL not
# listed there, so priced high on purpose: the cap must not underestimate.
PRICES = {SUPER: (0.30, 0.90), VL: (1.00, 3.00)}


class BudgetExceeded(RuntimeError):
    pass


class ReplayMismatch(RuntimeError):
    pass


def api_key():
    key = os.environ.get("NEBIUS_API_KEY")
    if not key and (ROOT / "apikey.md").exists():
        key = (ROOT / "apikey.md").read_text().strip().splitlines()[0].strip()
    if not key:
        raise SystemExit("no Token Factory key: set NEBIUS_API_KEY (or use --replay)")
    return key


def image_part(jpeg):
    """An image message part from JPEG bytes (or a path to a JPEG file)."""
    data = base64.b64encode(jpeg if isinstance(jpeg, bytes) else Path(jpeg).read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}


def sha(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


def summary(body):
    """The request as stored in the transcript: images replaced by their sha256 (the request
    sha256 still covers them)."""
    def strip(x):
        if isinstance(x, dict):
            if x.get("type") == "image_url":
                return {"type": "image_url", "sha256": hashlib.sha256(x["image_url"]["url"].encode()).hexdigest()}
            return {k: strip(v) for k, v in x.items()}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    return strip(body)


def text_only(request):
    """A stored request summary without the images' hashes: what must match on replay."""
    def strip(x):
        if isinstance(x, dict):
            return {"type": "image_url"} if x.get("type") == "image_url" else {k: strip(v) for k, v in x.items()}
        if isinstance(x, list):
            return [strip(v) for v in x]
        return x
    return json.dumps(strip(json.loads(json.dumps(request))), sort_keys=True)


class Meter:
    """Running cost over every Client that shares it; raises BudgetExceeded past max_usd."""

    def __init__(self, max_usd=None):
        self.max_usd, self.usd, self.tokens_in, self.tokens_out, self.calls = max_usd, 0.0, 0, 0, 0

    def add(self, model, usage):
        p_in, p_out = PRICES.get(model, (1.0, 3.0))
        self.tokens_in += usage.get("prompt_tokens", 0)
        self.tokens_out += usage.get("completion_tokens", 0)
        self.usd += (usage.get("prompt_tokens", 0) * p_in + usage.get("completion_tokens", 0) * p_out) / 1e6
        self.calls += 1

    def check(self):
        if self.max_usd is not None and self.usd >= self.max_usd:
            raise BudgetExceeded(f"spent ~${self.usd:.4f} of the ${self.max_usd} cap")

    def __str__(self):
        return f"{self.calls} calls, {self.tokens_in} in / {self.tokens_out} out tokens, ~${self.usd:.4f}"


class Client:
    """chat(body) -> response dict, recorded to (or replayed from) transcript_path."""

    def __init__(self, transcript_path, replay=False, meter=None, base_url=BASE_URL):
        self.path, self.replay, self.meter, self.base_url = Path(transcript_path), replay, meter or Meter(), base_url
        if replay:
            if not self.path.exists():
                raise ReplayMismatch(f"no recording at {self.path}")
            self.recorded = json.loads(self.path.read_text())["calls"]
        self.calls, self.image_mismatches = [], 0

    def chat(self, body):
        k = len(self.calls)
        if self.replay:
            if k >= len(self.recorded):
                raise ReplayMismatch(f"{self.path.name}: call {k} isn't in the recording")
            if self.recorded[k]["sha256"] != sha(body):
                if text_only(summary(body)) != text_only(self.recorded[k]["request"]):
                    raise ReplayMismatch(f"{self.path.name}: call {k} differs from the recording")
                self.image_mismatches += 1  # same text, image bytes encoded differently
            response = self.recorded[k]["response"]
        else:
            self.meter.check()
            response = self._post(body)
        self.meter.add(body["model"], response.get("usage") or {})
        self.calls.append({"sha256": sha(body), "request": summary(body), "response": response})
        if not self.replay:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"calls": self.calls}, indent=1) + "\n")
        return response

    def _post(self, body, tries=4):
        req = urllib.request.Request(f"{self.base_url}/chat/completions", json.dumps(body).encode(),
                                     {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"})
        for attempt in range(tries):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                    raise RuntimeError(f"Token Factory HTTP {e.code}: {e.read()[:300]!r}") from None
            except (urllib.error.URLError, TimeoutError):
                if attempt == tries - 1:
                    raise
            time.sleep(2 ** attempt * 2)
