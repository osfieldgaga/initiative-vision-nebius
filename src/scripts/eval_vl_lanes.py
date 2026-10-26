#!/usr/bin/env python3
"""How far can the agent trust Nemotron VL about lane lines? Score it, and the OpenCV pipeline, on hand labels.

    python src/scripts/eval_vl_lanes.py <session_dir> [--labels data/eval/lane_labels_<session>.csv] [--replay]

Labels: label_lanes.py's lane_labels.csv (copied to data/eval/ so it ships with the repo; frame names
and labels only). centred / left / right = both lane lines visible, one_line, no_lines; skip is left
out. Nemotron 3.5 Super VL gets each labelled frame alone, upright and undistorted as the labeller
saw it, and answers in JSON; the pipeline's
lane_valid comes from vision_batch.py's vision.jsonl (run with --also on the labels). Both are scored
on "both lines visible or not", the question lane_valid answers.

Writes runs/<session>/vl_lanes/: transcript.json (replayable) and results.json.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import tokenfactory as tf  # noqa: E402
from agent import upright_jpeg  # noqa: E402

PROMPT = ("Dashcam frame from a car driving in the US (camera behind the windshield, the car's hood at the bottom). "
          "Look at the road directly ahead. Reply with JSON only: {\"lane_lines\": \"both\" | \"one\" | \"none\"} "
          "where both = painted lines (or a clear painted road edge) visible on both sides of the car's lane, "
          "one = only one side, none = no painted lines.")
TRUTH = {"centred": "both", "left": "both", "right": "both", "one_line": "one", "no_lines": "none"}


def parse(text):
    m = re.search(r'"lane_lines"\s*:\s*"(both|one|none)"', text or "")
    return m.group(1) if m else None


def binary(pairs):
    """precision / recall / accuracy of 'both visible' over [(truth, predicted)]."""
    tp = sum(t and p for t, p in pairs)
    fp = sum(p and not t for t, p in pairs)
    fn = sum(t and not p for t, p in pairs)
    tn = len(pairs) - tp - fp - fn
    r = lambda a, b: round(a / b, 3) if b else None  # noqa: E731
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": r(tp, tp + fp), "recall": r(tp, tp + fn),
            "accuracy": r(tp + tn, len(pairs))}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--labels", help="default data/eval/lane_labels_<session>.csv")
    p.add_argument("--replay", action="store_true")
    p.add_argument("--max-usd", type=float, default=0.15)
    args = p.parse_args(argv)

    session = Path(args.session_dir)
    labels_path = Path(args.labels) if args.labels else ROOT / "data" / "eval" / f"lane_labels_{session.name}.csv"
    with open(labels_path, newline="") as f:
        labels = {r["frame"]: TRUTH[r["label"]] for r in csv.DictReader(f) if r["label"] in TRUTH}
    run_dir = ROOT / "runs" / session.name
    pipeline = {}
    for line in open(run_dir / "vision.jsonl"):
        r = json.loads(line)
        pipeline[r["frame"]] = r["lane_valid"]
    out_dir = run_dir / "vl_lanes"
    client = tf.Client(out_dir / "transcript.json", replay=args.replay, meter=tf.Meter(None if args.replay else args.max_usd))

    rows = []
    for name in sorted(labels):
        body = {"model": tf.VL, "temperature": 0, "max_tokens": 50, "chat_template_kwargs": {"enable_thinking": False},
                "messages": [{"role": "user", "content": [{"type": "text", "text": PROMPT},
                                                          tf.image_part(upright_jpeg(session / "frames" / name))]}]}
        text = client.chat(body)["choices"][0]["message"].get("content")
        rows.append({"frame": name, "truth": labels[name], "vl": parse(text), "vl_raw": text,
                     "pipeline_lane_valid": pipeline.get(name)})

    scored = [r for r in rows if r["pipeline_lane_valid"] is not None]
    confusion = {}
    for r in rows:
        key = f"{r['truth']} -> {r['vl']}"
        confusion[key] = confusion.get(key, 0) + 1
    results = {
        "session": session.name, "frames": len(rows), "model": tf.VL,
        "vl_unparsed": sum(r["vl"] is None for r in rows),
        "both_visible": {
            "vl": binary([(r["truth"] == "both", r["vl"] == "both") for r in scored]),
            "pipeline": binary([(r["truth"] == "both", bool(r["pipeline_lane_valid"])) for r in scored]),
        },
        "vl_3class_accuracy": round(sum(r["truth"] == r["vl"] for r in rows) / len(rows), 3),
        "vl_confusion": dict(sorted(confusion.items())),
        "cost": str(client.meter),
        "rows": rows,
    }
    (out_dir / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    print(f"{len(rows)} labelled frames ({len(scored)} also in vision.jsonl); {client.meter}")
    for who in ("vl", "pipeline"):
        s = results["both_visible"][who]
        print(f"  {who:<9} both lines visible: precision {s['precision']}, recall {s['recall']}, accuracy {s['accuracy']}"
              f"  (TP {s['tp']} FP {s['fp']} FN {s['fn']} TN {s['tn']})")
    print(f"  vl both / one / none accuracy {results['vl_3class_accuracy']}; confusion {results['vl_confusion']}")
    print(f"wrote {out_dir / 'results.json'}")


if __name__ == "__main__":
    main()
