#!/usr/bin/env python3
"""Ground-truth driving events for a drive: a pre-filled list to review, and a format check.

    python src/scripts/label_events.py prefill <session_dir> [--timeline runs/<session>/timeline.jsonl]
    python src/scripts/label_events.py check data/eval/events_gt_<session>.csv

How to label: data/eval/LABELLING.md.

prefill writes data/eval/events_gt_<session>.csv (never overwrites it): one row per moment worth
a look, with a suggested type and times, status "?" for you to set to yes / no. The moments come
from CAN (standstill, steering, blinker) and only two from vision (stop signs seen, departures
flagged), so most of the list doesn't depend on the vision the evaluation is scoring. It will
still miss things: watch the whole drive and add what's missing, source "added", so the
evaluation can report how much the pre-fill missed.

check validates the file (types, times, side and detail values) and prints a summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

COLUMNS = ["id", "status", "source", "type", "t_start", "t_end", "side", "detail", "confidence", "hint", "notes"]
# type -> allowed detail values ("" = none needed); see LABELLING.md for the definitions
TYPES = {
    "stop_sign": {"full_stop", "rolling_stop", "no_stop"},
    "other_stop": {""},
    "turn": {"blinker", "no_blinker", "late_blinker"},
    "lane_change": {"blinker", "no_blinker", "late_blinker"},
    "curve": {""},
    "lane_departure": {""},
}
SIDED = {"turn", "lane_change", "curve", "lane_departure"}

TURN_DEG = 90           # |steering wheel angle| of a turn at an intersection (this drive's turns: 194-429)
CURVE_DEG = 20          # ... of a bend in the road
CURVE_MIN_S = 2.0
CURVE_MIN_MPS = 4.0
MERGE_GAP_S = 2.0       # runs closer than this are one episode
BLINKER_BEFORE_S = 8.0  # a blinker this long before a turn (or during it) counts for it
SIGN_BEFORE_S = 10.0    # a stop sign seen this long before a standstill makes it a stop_sign suggestion


def runs(rows, test, gap_s=MERGE_GAP_S):
    """[(t_start, t_end)] of consecutive rows where test(row) holds, merging gaps shorter than gap_s."""
    out = []
    for r in rows:
        if not test(r):
            continue
        if out and r["t_s"] - out[-1][1] <= gap_s:
            out[-1][1] = r["t_s"]
        else:
            out.append([r["t_s"], r["t_s"]])
    return [tuple(x) for x in out]


def overlaps(a, b, pad=0.0):
    return a[0] - pad <= b[1] and b[0] - pad <= a[1]


def context(timeline, t0, t1):
    """'max 12 mph, gear D/R' over [t0, t1]: parking-lot manoeuvres are slow and often in reverse."""
    cans = [r["can"] for r in timeline if r["can"] and t0 <= r["t_s"] <= t1]
    if not cans:
        return ""
    gears = sorted({c["gear"] for c in cans if c["gear"]}, key="PRNDL".find)
    return f"max {max(c['speed_mph'] or 0 for c in cans):.0f} mph, gear {'/'.join(gears) or '?'}"


def prefill_rows(timeline):
    can = lambda r: r["can"] or {}  # noqa: E731
    sign_runs = runs(timeline, lambda r: any(s["type"] == "stop" for s in r["vision"]["signs"]), gap_s=3)
    blinker = {side: runs(timeline, lambda r, s=side: can(r).get("blinker") == s, gap_s=1) for side in ("left", "right")}
    rows = []

    for start, end in runs(timeline, lambda r: can(r).get("standstill"), gap_s=1):
        signs = [s for s in sign_runs if start - SIGN_BEFORE_S <= s[1] <= end]
        if signs:
            rows.append(("stop_sign", min(s[0] for s in signs), end, "", "full_stop",
                         f"standstill {start:.1f}-{end:.1f} s; stop sign seen by vision {signs[0][0]:.1f}-{signs[-1][1]:.1f} s"))
        else:
            rows.append(("other_stop", max(start - 5, 0), end, "", "", f"standstill {start:.1f}-{end:.1f} s"))

    turns = []
    for side, sign in (("left", 1), ("right", -1)):
        for start, end in runs(timeline, lambda r, s=sign: (can(r).get("steering_deg") or 0) * s > TURN_DEG):
            turns.append((start, end))
            used = [b for b in blinker[side] if overlaps((start - BLINKER_BEFORE_S, end), b)]
            detail = "no_blinker" if not used else "late_blinker" if min(b[0] for b in used) > start else "blinker"
            rows.append(("turn", start, end, side, detail,
                         f"steering past {TURN_DEG} deg; {side} blinker " +
                         (", ".join(f"{b[0]:.1f}-{b[1]:.1f} s" for b in used) or "not on")))

    for side, sign in (("left", 1), ("right", -1)):
        bends = runs(timeline, lambda r, s=sign: CURVE_DEG < (can(r).get("steering_deg") or 0) * s <= TURN_DEG
                     and (can(r).get("speed_mps") or 0) > CURVE_MIN_MPS)
        for start, end in bends:
            if end - start >= CURVE_MIN_S and not any(overlaps((start, end), t, pad=1) for t in turns):
                rows.append(("curve", start, end, side, "", f"steering {CURVE_DEG}-{TURN_DEG} deg for {end - start:.1f} s"))

    for side in ("left", "right"):
        for b in blinker[side]:
            if not any(overlaps(b, (t[0] - BLINKER_BEFORE_S, t[1])) for t in turns):
                rows.append(("lane_change", b[0], b[1] + 3, side, "blinker", f"{side} blinker {b[0]:.1f}-{b[1]:.1f} s, no turn"))

    for side in ("LEFT", "RIGHT"):
        for start, end in runs(timeline, lambda r, s=side: r["vision"]["departure"] == s, gap_s=1):
            if end > start:  # at least two frames
                rows.append(("lane_departure", start, end, side.lower(), "",
                             f"vision flagged departing {side.lower()} {start:.1f}-{end:.1f} s"))

    rows.sort(key=lambda r: r[1])
    rows = [(typ, t0, t1, side, detail, f"{hint}; {context(timeline, t0, t1)}") for typ, t0, t1, side, detail, hint in rows]
    return [{"id": k, "status": "?", "source": "prefill", "type": typ, "t_start": f"{t0:.1f}", "t_end": f"{t1:.1f}",
             "side": side, "detail": detail, "confidence": "", "hint": hint, "notes": ""}
            for k, (typ, t0, t1, side, detail, hint) in enumerate(rows, 1)]


def check_rows(rows):
    """[problem] for a labelled file's rows (empty = fine)."""
    problems, ids = [], set()
    for n, r in enumerate(rows, 2):  # line numbers, after the header
        where = f"line {n} (id {r.get('id') or '?'})"
        if r["id"] in ids:
            problems.append(f"{where}: duplicate id")
        ids.add(r["id"])
        if r["status"] not in ("yes", "no", "?"):
            problems.append(f"{where}: status must be yes, no or ?")
        if r["source"] not in ("prefill", "added"):
            problems.append(f"{where}: source must be prefill or added")
        if r["status"] != "yes":
            continue
        if r["type"] not in TYPES:
            problems.append(f"{where}: type {r['type']!r} is not one of {', '.join(TYPES)}")
            continue
        try:
            t0, t1 = float(r["t_start"]), float(r["t_end"])
            if t1 < t0:
                problems.append(f"{where}: t_end before t_start")
        except ValueError:
            problems.append(f"{where}: t_start / t_end must be seconds, e.g. 171.5")
        if r["type"] in SIDED and r["side"] not in ("left", "right"):
            problems.append(f"{where}: {r['type']} needs side left or right")
        if r["type"] not in SIDED and r["side"]:
            problems.append(f"{where}: {r['type']} has no side, leave it empty")
        if r["detail"] not in TYPES[r["type"]]:
            allowed = sorted(TYPES[r["type"]] - {""}) or ["(empty)"]
            problems.append(f"{where}: detail for {r['type']} must be {' / '.join(allowed)}")
        if r["confidence"] not in ("", "sure", "unsure"):
            problems.append(f"{where}: confidence must be sure, unsure or empty")
    return problems


def read_rows(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path}: missing columns {', '.join(sorted(missing))}")
        return [{k: (v or "").strip() for k, v in r.items()} for r in reader]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pf = sub.add_parser("prefill")
    pf.add_argument("session_dir")
    pf.add_argument("--timeline", help="default runs/<session>/timeline.jsonl")
    pf.add_argument("--out", help="default data/eval/events_gt_<session>.csv")
    ck = sub.add_parser("check")
    ck.add_argument("csv")
    args = p.parse_args(argv)

    if args.cmd == "prefill":
        session = Path(args.session_dir).name
        timeline_path = Path(args.timeline) if args.timeline else ROOT / "runs" / session / "timeline.jsonl"
        out = Path(args.out) if args.out else ROOT / "data" / "eval" / f"events_gt_{session}.csv"
        if out.exists():
            raise SystemExit(f"{out} exists (it may hold your labels): move it away first")
        rows = prefill_rows([json.loads(line) for line in open(timeline_path)])
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, COLUMNS)
            w.writeheader()
            w.writerows(rows)
        counts = {}
        for r in rows:
            counts[r["type"]] = counts.get(r["type"], 0) + 1
        print(f"wrote {out}: {len(rows)} moments to review ({', '.join(f'{v} {k}' for k, v in counts.items())})")
        return

    rows = read_rows(args.csv)
    problems = check_rows(rows)
    for line in problems:
        print(line)
    status = {s: sum(r["status"] == s for r in rows) for s in ("yes", "no", "?")}
    events = {}
    for r in rows:
        if r["status"] == "yes":
            events[r["type"]] = events.get(r["type"], 0) + 1
    print(f"{len(rows)} rows: {status['yes']} yes, {status['no']} no, {status['?']} still to review; "
          f"{sum(r['source'] == 'added' for r in rows)} added by hand")
    print("events: " + (", ".join(f"{v} {k}" for k, v in sorted(events.items())) or "none yet"))
    print("OK" if not problems else f"{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
