#!/usr/bin/env python3
"""Agent that checks each rule candidate against the drive's data and cites the samples it used.

    python src/scripts/agent.py <session_dir> [--only c11,c15] [--max-usd 0.25] [--no-vl]
    python src/scripts/agent.py <session_dir> --replay      # no key: answers come from the recordings

Steps 5-6 of scenario mining. One short conversation per candidate (runs/<session>/candidates.json)
with Nemotron 3 Super on Nebius Token Factory, temperature 0, and four tools:

    get_window(t_start, t_end)        the fused timeline (~3 frames/s): CAN state + vision per frame
    look_at_frames(seqs, question)    Nemotron 3.5 Super VL looks at up to 4 camera frames
    rerun_vision(t_start, t_end)      the OpenCV pipeline on every frame (15 fps) of a short window
    emit_event(...)                   the answer: confirmed / corrected / rejected, with claims

Nothing the model says is taken on trust. emit_event goes through validate(): every claim
(seq, field, value) must equal the source data for that frame, and the event's stop detail,
blinker detail and steering side are recomputed from the full-rate CAN log, and a stop sign or
lane departure can only be confirmed after looking at its frames. A failed check goes
back to the model as the tool result (MAX_EMITS tries); after that the candidate is kept as the
rules found it, marked "unverified".

Output in runs/<session>/agent/: events.json (one per candidate, with the claims resolved to frame
file and CAN row), transcripts/<id>.json (every request's sha256 and the full response), and
vision_full.jsonl (rerun_vision's frames, reused on replay).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import fuse  # noqa: E402
import tokenfactory as tf  # noqa: E402
from label_events import SIDED, TYPES  # noqa: E402

MAX_TURNS = 8
MAX_EMITS = 4
MAX_WINDOW_S = 60
MAX_ROWS = 60
MAX_RERUN_S = 3.0
MAX_FRAMES = 4
MAX_CLAIMS = 6
MPH_PER_MPS = 2.23694
STOPPED_MPH = 0.3
ROLLING_MPH = 5.0
BLINKER_BEFORE_S = 8.0
TURN_MIN_DEG, CURVE_MIN_DEG = 45.0, 10.0
CLAIM_PAD_S = 15.0
LOOK_BEFORE_S = 10.0  # a stop sign is seen up to this long before the event's frames
VISION_TYPES = ("stop_sign", "lane_departure")  # events that rest on vision: frames must be looked at
# field -> tolerance for numbers (None = must be equal)
FIELDS = {"mph": 0.6, "steer": 2.0, "accel": 0.1, "offset_m": 0.05, "blinker": None, "standstill": None,
          "brake": None, "gear": None, "lane_valid": None, "departure": None, "vision_stop_sign": None,
          "frame_check": None}
DETAILS = sorted({d for ds in TYPES.values() for d in ds})


def definitions():
    """The event definitions table, as the human labeller read it in data/eval/LABELLING.md."""
    text = (ROOT / "data" / "eval" / "LABELLING.md").read_text()
    return text.split("## Event definitions", 1)[1].split("Tricky cases:", 1)[0].strip()


SYSTEM = """You review candidate driving events that simple rules found in a recorded drive (front camera and \
CAN bus of a car in the US). For each candidate, decide whether it really happened as described: confirm it, \
correct it (type, times, side or detail), or reject it. Cite the samples that prove your answer.

Data. Times are seconds since the first frame. get_window returns a table, about 3 frames per second:
seq = frame number, t = time, can_row = timestamp_ns of the CAN row used, mph = vehicle speed,
steer = steering wheel angle in degrees (positive = left, a turn at an intersection is 150-450),
blinker = left / right / null, standstill = the car's Standstill flag (NOT proof the car stopped: it can be on
at 4 mph; use mph, 0.0 means stopped), brake = brake pedal pressed, gear = P/R/N/D, accel = m/s2,
lane_valid = vision found both lane lines, offset_m = car offset from the lane centre (positive = right of it),
departure = vision says the car is drifting out of its lane (left / right / null), signs = signs vision read
("stop:-3.79" = stop sign, detector score).

Event definitions (the same ones the human labeller used):

{definitions}

How to decide:
- Reject only what did not happen as an event of any type (no stop sign there, parking-lot manoeuvring, a
  departure with no line). If it happened differently, correct it: a stop sign the car did not stop at is a
  stop_sign with detail no_stop, not a rejection.
- Reject manoeuvring inside a parking lot or driveway: walking pace, back-and-forth steering, gear changes to R
  or P. Speed alone is not enough: turns at intersections are often 5-12 mph, especially after a stop.
- Vision can be wrong (false stop signs, lane lines found where there are none). When a candidate depends on
  vision (a stop sign, a lane departure), check the frames with look_at_frames before confirming. Ask a
  specific question and pass the frames that matter (e.g. where the sign was detected, or where departure
  was flagged). rerun_vision gives every frame of a short window if the 3 fps rows are not enough.
- A lane_departure needs a visible lane line or road edge that a wheel touches or crosses.
- look_at_frames is conservative about lane lines (measured on 95 hand-labelled frames of this drive): when
  it says lines are visible it was always right, but it missed three quarters of the lines that were there.
  So "no lines" from it is weak evidence; ask a specific question (where is the car relative to the line?).
- Usually: get_window once, then look_at_frames if vision is involved, then emit_event.

emit_event: give the event as it really happened, per the definitions. claims = 2 to 6 samples from the tool
outputs that support it: {{"seq": frame, "field": one of the row fields above or "vision_stop_sign", "value":
exactly as the tool showed it, as text}}. Two extra fields: "vision_stop_sign" (did the sign reader read a stop
sign in that frame: "true" / "false") and "frame_check" (value = a quote from look_at_frames' answer about that
frame). A validator checks every claim against the source data, and checks the
stop detail, blinker detail and side against the CAN log. If it returns errors, fix the event and call
emit_event again."""


def tool(name, description, properties, required):
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties, "required": required}}}


SPAN = {"t_start": {"type": "number"}, "t_end": {"type": "number"}}
TOOLS = {
    "get_window": tool("get_window", f"Fused timeline rows between two drive times (max {MAX_WINDOW_S} s; long windows "
                       f"are thinned to {MAX_ROWS} rows).", SPAN, ["t_start", "t_end"]),
    "look_at_frames": tool("look_at_frames", f"Ask a vision-language model a question about up to {MAX_FRAMES} camera "
                           "frames, given by seq.", {"seqs": {"type": "array", "items": {"type": "integer"}},
                                                     "question": {"type": "string"}}, ["seqs", "question"]),
    "rerun_vision": tool("rerun_vision", f"Run the lane and sign pipeline on every frame (15 fps) between two drive "
                         f"times (max {MAX_RERUN_S} s). Rows as in get_window.", SPAN, ["t_start", "t_end"]),
    "emit_event": tool("emit_event", "Your final answer for this candidate.", {
        "verdict": {"type": "string", "enum": ["confirmed", "corrected", "rejected"]},
        "type": {"type": "string", "enum": list(TYPES)},
        **SPAN,
        "side": {"type": "string", "enum": ["left", "right", ""]},
        "detail": {"type": "string", "enum": DETAILS},
        "claims": {"type": "array", "items": {"type": "object", "properties": {
            "seq": {"type": "integer"}, "field": {"type": "string", "enum": list(FIELDS)},
            "value": {"type": "string", "description": "as the tool showed it, written as text: \"5.2\", \"left\", \"true\", \"null\""}},
            "required": ["seq", "field", "value"]}},
        "reason": {"type": "string", "description": "one or two sentences, no numbers (the claims carry them)"},
    }, ["verdict", "type", "t_start", "t_end", "side", "detail", "claims", "reason"]),
}

VL_PROMPT = ("Dashcam frames from a car driving in the US (camera behind the windshield, the car's hood at the "
             "bottom). Answer briefly and factually; say so if you can't tell. Answer for each frame separately, "
             "one line per frame starting with its label, e.g. \"Frame 2720: ...\".\n\nQuestion: ")


def upright_jpeg(path):
    """A raw frame as the human labeller saw it: undistorted and rotated upright (the camera is mounted
    sideways), via lld.undistort_frame."""
    import cv2 as cv
    import lld
    ok, buf = cv.imencode(".jpg", lld.undistort_frame(cv.imread(str(path))), [cv.IMWRITE_JPEG_QUALITY, 90])
    return buf.tobytes()


def view(r):
    """A timeline row as the model sees it (and as claims are checked)."""
    c, v = r["can"] or {}, r["vision"]
    rnd = lambda x, n: None if x is None else round(x, n)  # noqa: E731
    return {"seq": r["seq"], "t": round(r["t_s"], 2), "can_row": c.get("row_ts_ns"), "mph": rnd(c.get("speed_mph"), 1),
            "steer": rnd(c.get("steering_deg"), 1), "blinker": c.get("blinker"), "standstill": c.get("standstill"),
            "brake": c.get("brake"), "gear": c.get("gear"), "accel": rnd(c.get("accel_mps2"), 2),
            "lane_valid": v.get("lane_valid"), "offset_m": rnd(v.get("offset_m"), 2),
            "departure": (v.get("departure") or "").lower() or None,
            "signs": [f"{s['type']}{s['value'] or ''}:{s['score']:.2f}" for s in v.get("signs") or []]}


class Session:
    """The drive's data the tools read and the validator checks against."""

    def __init__(self, session_dir, run_dir):
        self.dir, self.run_dir = Path(session_dir), Path(run_dir)
        self.timeline = [json.loads(line) for line in open(self.run_dir / "timeline.jsonl")]
        with open(self.dir / "frames.csv", newline="") as f:
            rows = list(csv.DictReader(f))
        t0 = int(rows[0]["timestamp_ns"])
        self.frames = {int(r["seq"]): (r["filename"], int(r["timestamp_ns"]), (int(r["timestamp_ns"]) - t0) / 1e9)
                       for r in rows}
        self.track = fuse.load_track(self.dir)
        self.rows = {r["seq"]: r for r in self.timeline}
        self.full_path = self.run_dir / "agent" / "vision_full.jsonl"
        if self.full_path.exists():
            for line in open(self.full_path):
                r = json.loads(line)
                self.rows.setdefault(r["seq"], r)
        self._models = None

    def window(self, t0, t1):
        return [r for r in self.timeline if t0 <= r["t_s"] <= t1]

    def can_series(self, name, t0, t1):
        i0 = max(int(np.searchsorted(self.track.t, t0, side="right")) - 1, 0)  # state at t0 = last row before it
        i1 = int(np.searchsorted(self.track.t, t1, side="right"))
        return np.asarray(self.track.values[name][i0:i1], dtype=float)

    def rerun(self, t0, t1):
        """Timeline rows for every frame in [t0, t1], running the pipeline on frames not yet processed."""
        seqs = [s for s, (_, _, t) in self.frames.items() if t0 <= t <= t1]
        todo = [s for s in seqs if s not in self.rows]
        if todo:
            import cv2 as cv
            import lld
            import signs
            if self._models is None:
                self._models = (*lld.load_model(), signs.SignReader())
            model, device, reader = self._models
            self.full_path.parent.mkdir(parents=True, exist_ok=True)
            vision = []
            for s in todo:
                name, ts_ns, t = self.frames[s]
                metrics, _, _ = lld.process_frame(cv.imread(str(self.dir / name)), model, device, reader)
                vision.append({"seq": s, "frame": Path(name).name, "timestamp_ns": ts_ns, "t_s": round(t, 3), **metrics})
            fused = fuse.fuse(vision, self.track)
            with open(self.full_path, "a") as f:
                for r in fused:
                    f.write(json.dumps(r) + "\n")
                    self.rows[r["seq"]] = r
        return [self.rows[s] for s in seqs]


def table(rows):
    """Rows as {"columns": [...], "rows": [[...]]}: the same values as view(), a third of the tokens."""
    views = [view(r) for r in rows]
    cols = list(views[0]) if views else []
    return {"columns": cols, "rows": [[v[c] for c in cols] for v in views]}


def thin(rows, n):
    if len(rows) <= n:
        return rows
    return [rows[i] for i in np.linspace(0, len(rows) - 1, n).round().astype(int)]


def norm(x):
    if isinstance(x, str):
        x = x.strip().lower()
        return {"none": None, "null": None, "": None, "true": True, "false": False}.get(x, x)
    return x


def claim_value(row, field):
    if field == "vision_stop_sign":  # what the OpenCV sign reader read in this frame
        return any(s["type"] == "stop" for s in row["vision"].get("signs") or [])
    return view(row)[field]


def validate(ev, sess, answers=None):
    """[problem] with an emitted event; empty = every claim and derived detail matches the source.
    answers = {tuple of seqs: answer} from look_at_frames (None = the tool isn't available)."""
    errors = []
    typ, side, detail, verdict = ev.get("type"), ev.get("side") or "", ev.get("detail") or "", ev.get("verdict")
    if verdict not in ("confirmed", "corrected", "rejected"):
        return ["verdict must be confirmed, corrected or rejected"]
    if typ not in TYPES:
        return [f"type must be one of {', '.join(TYPES)}"]
    try:
        t0, t1 = float(ev["t_start"]), float(ev["t_end"])
    except (KeyError, TypeError, ValueError):
        return ["t_start and t_end must be numbers (seconds)"]
    end = max(t for _, _, t in sess.frames.values())
    if not 0 <= t0 <= t1 <= end + 1:
        errors.append(f"need 0 <= t_start <= t_end <= {end:.1f}")
    claims = ev.get("claims") or []
    if not 1 <= len(claims) <= MAX_CLAIMS:
        errors.append(f"cite 1 to {MAX_CLAIMS} claims, the ones that decide the event (you gave {len(claims)})")
    for c in claims:
        seq, field = c.get("seq"), c.get("field")
        row = sess.rows.get(seq)
        if row is None:
            errors.append(f"claim seq {seq}: no data for that frame (cite seqs from get_window or rerun_vision)")
            continue
        if field not in FIELDS:
            errors.append(f"claim seq {seq}: unknown field {field!r}")
            continue
        if field == "frame_check":  # must be an answer look_at_frames gave about this frame
            said = [about(a, seq) for q, a in (answers or {}).items() if seq in q]
            if not any(norm(str(c.get("value"))) and norm(str(c.get("value"))) in norm(a) for a in said):
                errors.append(f"claim seq {seq}: frame_check must quote an answer look_at_frames gave for that frame")
            continue
        if not t0 - CLAIM_PAD_S <= row["t_s"] <= t1 + CLAIM_PAD_S:
            errors.append(f"claim seq {seq} (t={row['t_s']:.1f}) is far from the event {t0:.1f}-{t1:.1f}")
        got, want = norm(c.get("value")), norm(claim_value(row, field))
        tol = FIELDS[field]
        if tol is not None:
            try:
                got = float(got)
            except (TypeError, ValueError):
                pass
            ok = isinstance(got, (int, float)) and not isinstance(got, bool) and want is not None and abs(got - want) <= tol
        else:
            ok = got == want
        if not ok:
            errors.append(f"claim seq {seq}: {field} is {want!r} in the data, not {c.get('value')!r}")
    if verdict == "rejected":
        return errors
    if not any(t0 - 1 <= sess.rows[c["seq"]]["t_s"] <= t1 + 1 for c in claims if c.get("seq") in sess.rows):
        errors.append("cite at least one sample inside the event's time span")
    if typ in SIDED and side not in ("left", "right"):
        errors.append(f"{typ} needs side left or right")
    if typ not in SIDED and side:
        errors.append(f"{typ} has no side")
    if detail not in TYPES[typ]:
        errors.append(f"detail for {typ} must be {' / '.join(sorted(TYPES[typ] - {''})) or '(empty)'}")
    if errors:
        return errors

    if answers is not None and typ in VISION_TYPES:
        times = [sess.frames[q][2] for seqs in answers for q in seqs]
        if not any(t0 - LOOK_BEFORE_S <= t <= t1 for t in times):
            errors.append(f"a {typ} rests on vision, which can be wrong: look_at_frames at frames of this event first")
    if typ == "stop_sign":
        v = np.nanmin(sess.can_series("speed_mps", t0, t1)) * MPH_PER_MPS
        want = "full_stop" if v <= STOPPED_MPH else "rolling_stop" if v < ROLLING_MPH else "no_stop"
        if detail != want:
            errors.append(f"slowest speed in {t0:.1f}-{t1:.1f} s is {v:.1f} mph (CAN log), so detail is {want}")
    if typ in ("turn", "lane_change"):
        code = {"left": 1, "right": 2}[side]
        before = np.any(sess.can_series("blinker", t0 - BLINKER_BEFORE_S, t0 + 0.5) == code)
        during = np.any(sess.can_series("blinker", t0, t1) == code)
        want = "blinker" if before else "late_blinker" if during else "no_blinker"
        if detail != want:
            errors.append(f"{side} blinker in the CAN log: {'on' if before else 'off'} in the {BLINKER_BEFORE_S:.0f} s "
                          f"before t_start, {'on' if during else 'off'} during, so detail is {want}")
    if typ in ("turn", "curve"):
        steer = sess.can_series("steering_deg", t0, t1) * (1 if side == "left" else -1)
        need = TURN_MIN_DEG if typ == "turn" else CURVE_MIN_DEG
        if not np.nanmax(steer, initial=-np.inf) >= need:
            errors.append(f"steering never reaches {need:.0f} deg to the {side} in {t0:.1f}-{t1:.1f} s (CAN log)")
    return errors


def about(answer, seq):
    """The part of a look_at_frames answer about one frame: its "Frame <seq>:" line, or the whole answer
    if the model didn't answer frame by frame."""
    lines = [ln for ln in answer.splitlines() if re.match(rf"\W*frame\s+{seq}\b", ln.strip(), re.I)]
    return "\n".join(lines) if lines else answer


def look(sess, client, seqs, question):
    seqs = [int(s) for s in seqs][:MAX_FRAMES]
    missing = [s for s in seqs if s not in sess.frames]
    if missing or not seqs:
        return {"error": f"no such frame(s): {missing}" if missing else "give at least one seq"}
    content = [{"type": "text", "text": VL_PROMPT + question}]
    for s in seqs:
        name, _, t = sess.frames[s]
        content += [{"type": "text", "text": f"Frame {s} (t = {t:.2f} s):"}, tf.image_part(upright_jpeg(sess.dir / name))]
    body = {"model": tf.VL, "temperature": 0, "max_tokens": 400, "messages": [{"role": "user", "content": content}],
            "chat_template_kwargs": {"enable_thinking": False}}
    answer = client.chat(body)["choices"][0]["message"].get("content") or ""
    return {"seqs": seqs, "answer": answer.strip()}


def run_tool(name, args, sess, client):
    if name == "get_window":
        t0, t1 = float(args["t_start"]), float(args["t_end"])
        t1 = min(t1, t0 + MAX_WINDOW_S)
        return table(thin(sess.window(t0, t1), MAX_ROWS))
    if name == "rerun_vision":
        t0, t1 = float(args["t_start"]), float(args["t_end"])
        t1 = min(t1, t0 + MAX_RERUN_S)
        return table(sess.rerun(t0, t1))
    if name == "look_at_frames":
        return look(sess, client, args.get("seqs") or [], str(args.get("question", "")))
    return {"error": f"unknown tool {name}"}


def resolve(claims, sess):
    """Claims with the frame file and CAN row behind each one, for tracing back to the source."""
    out = []
    for c in claims:
        r = sess.rows[c["seq"]]
        out.append({**c, "t_s": r["t_s"], "frame": r["frame"], "can_row": (r["can"] or {}).get("row_ts_ns")})
    return out


def review(cand, sess, client, tools):
    """One candidate -> event dict (see the module docstring)."""
    brief = {k: cand[k] for k in ("id", "type", "t_start", "t_end", "side", "detail", "rule")}
    brief["stats"] = cand["evidence"]["stats"]
    brief["key_seqs"] = cand["evidence"]["key_seqs"]
    messages = [{"role": "system", "content": SYSTEM.format(definitions=definitions())},
                {"role": "user", "content": "Candidate:\n" + json.dumps(brief)}]
    emits, errors, frames_checked = 0, [], []
    for turn in range(1, MAX_TURNS + 1):
        body = {"model": tf.SUPER, "temperature": 0, "max_tokens": 4096, "messages": messages,
                "tools": [TOOLS[t] for t in tools]}
        msg = client.chat(body)["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        messages.append({"role": "assistant", "content": msg.get("content") or "",
                         **({"tool_calls": [{"id": c["id"], "type": "function", "function": c["function"]}
                                            for c in calls]} if calls else {})})
        if not calls:
            messages.append({"role": "user", "content": "Finish by calling emit_event."})
            continue
        final = None
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError as e:
                args, result = None, {"error": f"arguments are not valid JSON: {e}"}
            if args is not None and name == "emit_event":
                emits += 1
                answers = ({tuple(f["seqs"]): f["answer"] for f in frames_checked}
                           if "look_at_frames" in tools else None)
                errors = validate(args, sess, answers)
                result = {"ok": not errors, "errors": errors}
                if not errors:
                    final = args
            elif args is not None and name in tools:
                try:
                    result = run_tool(name, args, sess, client)
                except (KeyError, TypeError, ValueError) as e:
                    result = {"error": f"bad arguments: {e}"}
                if name == "look_at_frames" and "seqs" in result:
                    frames_checked.append({"seqs": result["seqs"], "question": args.get("question"),
                                           "answer": result["answer"]})
            elif args is not None:
                result = {"error": f"unknown tool {name}"}
            messages.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(result)})
        if final:
            return {"id": cand["id"], "verdict": final["verdict"],
                    **{k: final[k] for k in ("type", "t_start", "t_end", "side", "detail")},
                    "reason": final.get("reason", ""), "claims": resolve(final["claims"], sess),
                    "frames_checked": frames_checked, "validation": "passed", "turns": turn,
                    "candidate": brief}
        if emits >= MAX_EMITS:
            break
    return unverified(cand, brief, f"no valid emit_event after {emits} tries" + (f": {errors}" if errors else ""),
                      frames_checked)


def unverified(cand, brief, why, frames_checked=()):
    return {"id": cand["id"], "verdict": "unverified", **{k: cand[k] for k in ("type", "t_start", "t_end", "side", "detail")},
            "reason": why, "claims": [], "frames_checked": list(frames_checked), "validation": "failed",
            "candidate": brief}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--run-dir", help="default runs/<session>")
    p.add_argument("--only", help="comma-separated candidate ids, e.g. c11,c15")
    p.add_argument("--replay", action="store_true", help="answer from the recorded transcripts (no key, no cost)")
    p.add_argument("--max-usd", type=float, default=0.25, help="stop calling the API past this estimated spend")
    p.add_argument("--no-vl", action="store_true", help="without look_at_frames (the step 5 agent)")
    p.add_argument("--agent-dir", help="where transcripts and events.json go (default <run-dir>/agent); "
                   "e.g. a repeat run that leaves the final one alone")
    p.add_argument("--out", help="default <agent-dir>/events.json")
    args = p.parse_args(argv)

    run_dir = Path(args.run_dir) if args.run_dir else ROOT / "runs" / Path(args.session_dir).name
    agent_dir = (Path(args.agent_dir) if args.agent_dir else
                 run_dir / "agent" if not args.no_vl else run_dir / "agent_no_vl")
    out = Path(args.out) if args.out else agent_dir / "events.json"
    sess = Session(args.session_dir, run_dir)
    cands = json.loads((run_dir / "candidates.json").read_text())
    if args.only:
        wanted = set(args.only.split(","))
        cands = [c for c in cands if c["id"] in wanted]
    tools = ["get_window", "rerun_vision", "emit_event"] + ([] if args.no_vl else ["look_at_frames"])
    meter = tf.Meter(None if args.replay else args.max_usd)

    events = []
    for cand in cands:
        brief = {k: cand[k] for k in ("id", "type", "t_start", "t_end", "side", "detail", "rule")}
        client = tf.Client(agent_dir / "transcripts" / f"{cand['id']}.json", replay=args.replay, meter=meter)
        try:
            ev = review(cand, sess, client, tools)
        except tf.BudgetExceeded as e:
            ev = unverified(cand, brief, f"not reviewed: {e}")
        events.append(ev)
        changed = "" if ev["verdict"] != "corrected" else " -> " + " ".join(
            str(ev[k]) for k in ("type", "side", "detail", "t_start", "t_end") if ev[k] != cand[k])
        print(f"{cand['id']} {cand['type']:<14} {cand['t_start']:7.1f} s  {ev['verdict']:<11}{changed}"
              f"  [{meter}]", flush=True)

    if args.only and out.exists():  # merge into an earlier full run
        old = {e["id"]: e for e in json.loads(out.read_text())}
        old.update({e["id"]: e for e in events})
        events = sorted(old.values(), key=lambda e: e["id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(events, indent=1) + "\n")
    counts = {}
    for e in events:
        counts[e["verdict"]] = counts.get(e["verdict"], 0) + 1
    print(f"{len(events)} events: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) + f"; {meter}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
