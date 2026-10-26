#!/usr/bin/env python3
"""Rule-based candidate driving events from a fused timeline: the baseline the agent must beat.

    python src/scripts/candidates.py <session_dir> [--timeline runs/<session>/timeline.jsonl] [--out runs/<session>/candidates.json]

Step 4 of scenario mining. Tuned for recall: the agent (step 5) confirms, corrects or rejects
each candidate, so a missed event here is lost but a false one only costs the agent a look.

The rules are label_events.py's pre-fill (same thresholds, so the two stay comparable), plus one
case the pre-fill can't suggest: a stop sign seen with no standstill after it becomes a
stop_sign candidate too. A stop sign's detail comes from the slowest wheel speed, not the car's
Standstill flag: at the 171 s stop sign of the 2026-10-22 drive the flag was on from 4.3 mph
down to 1.1 mph and the car never reached 0 (every other standstill episode reads 0.0).

Every candidate carries its evidence, so each claim can be traced to source samples:
    seqs         [first, last] frame seq inside [t_start, t_end]
    key_seqs     frames that triggered the rule (sign seen, departure flagged, peak steering, ...)
    can_rows     decoded.csv timestamp_ns of the rows at t_start, t_end and the key moment
    stats        numbers computed from those rows (min / max speed, max steering, gear, blinker)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
from label_events import (BLINKER_BEFORE_S, CURVE_DEG, CURVE_MIN_MPS, CURVE_MIN_S, MERGE_GAP_S,  # noqa: E402
                          SIGN_BEFORE_S, TURN_DEG, overlaps, runs)

SIGN_AFTER_S = 6.0   # a stop sign with no standstill within this long after it was last seen
STOPPED_MPS = 0.1    # wheel speed reads exactly 0.0 when stopped
ROLLING_MPS = 2.2    # 5 mph: slower than this at a stop sign is a rolling stop


def can(r):
    return r["can"] or {}


def window(timeline, t0, t1):
    return [r for r in timeline if t0 <= r["t_s"] <= t1]


def evidence(timeline, t0, t1, key_seqs=(), key_t=None):
    rows = window(timeline, t0, t1) or [min(timeline, key=lambda r: abs(r["t_s"] - t0))]
    cans = [can(r) for r in rows if r["can"]]
    speeds = [c["speed_mps"] for c in cans if c.get("speed_mps") is not None]
    steers = [c["steering_deg"] for c in cans if c.get("steering_deg") is not None]
    blinks = sorted({c["blinker"] for c in cans if c.get("blinker")})
    gears = sorted({c["gear"] for c in cans if c.get("gear")}, key="PRNDL".find)
    key_rows = [rows[0], rows[-1]]
    if key_t is not None:
        key_rows.append(min(rows, key=lambda r: abs(r["t_s"] - key_t)))
    return {
        "seqs": [rows[0]["seq"], rows[-1]["seq"]],
        "key_seqs": list(key_seqs),
        "can_rows": sorted({can(r)["row_ts_ns"] for r in key_rows if r["can"]}),
        "stats": {
            "min_speed_mps": round(min(speeds), 2) if speeds else None,
            "max_speed_mps": round(max(speeds), 2) if speeds else None,
            "max_left_steer_deg": round(max(steers), 1) if steers else None,
            "max_right_steer_deg": round(-min(steers), 1) if steers else None,
            "blinker": blinks,
            "gear": gears,
        },
    }


def stop_detail(timeline, t0, t1):
    """(full_stop / rolling_stop / no_stop, the slowest row) over [t0, t1]."""
    slowest = min(window(timeline, t0, t1), key=lambda r: can(r).get("speed_mps", 99))
    v = can(slowest).get("speed_mps")
    detail = "no_stop" if v is None or v >= ROLLING_MPS else "rolling_stop" if v >= STOPPED_MPS else "full_stop"
    return detail, slowest


def seqs_where(timeline, t0, t1, test):
    return [r["seq"] for r in window(timeline, t0, t1) if test(r)]


def detect(timeline):
    """[candidate] in time order; see the module docstring for the fields."""
    stop_seen = lambda r: any(s["type"] == "stop" for s in r["vision"]["signs"])  # noqa: E731
    sign_runs = runs(timeline, stop_seen, gap_s=3)
    blinker = {side: runs(timeline, lambda r, s=side: can(r).get("blinker") == s, gap_s=1) for side in ("left", "right")}
    stops = runs(timeline, lambda r: can(r).get("standstill"), gap_s=1)
    out = []

    def add(typ, t0, t1, side, detail, rule, key_seqs=(), key_t=None):
        out.append({"type": typ, "t_start": round(t0, 2), "t_end": round(t1, 2), "side": side, "detail": detail,
                    "rule": rule, "evidence": evidence(timeline, t0, t1, key_seqs, key_t)})

    for start, end in stops:
        signs = [s for s in sign_runs if start - SIGN_BEFORE_S <= s[1] <= end]
        if signs:
            t0 = min(s[0] for s in signs)
            detail, slowest = stop_detail(timeline, t0, end)
            add("stop_sign", t0, end, "", detail,
                f"stop sign seen {t0:.1f}-{signs[-1][1]:.1f} s, Standstill flag {start:.1f}-{end:.1f} s; "
                f"slowest {can(slowest)['speed_mps']} m/s at {slowest['t_s']:.1f} s",
                seqs_where(timeline, t0, signs[-1][1], stop_seen), slowest["t_s"])
        else:
            add("other_stop", max(start - 5, 0), end, "", "", f"Standstill flag {start:.1f}-{end:.1f} s, no stop sign seen",
                key_t=start)

    for s0, s1 in sign_runs:
        if any(s0 - SIGN_BEFORE_S <= s1 <= st[1] and st[0] <= s1 + SIGN_AFTER_S for st in stops):
            continue  # the stop_sign / full_stop case above
        detail, slowest = stop_detail(timeline, s0, s1 + SIGN_AFTER_S)
        add("stop_sign", s0, s1 + SIGN_AFTER_S, "", detail,
            f"stop sign seen {s0:.1f}-{s1:.1f} s, no Standstill flag; "
            f"slowest {can(slowest)['speed_mps']} m/s at {slowest['t_s']:.1f} s",
            seqs_where(timeline, s0, s1, stop_seen), slowest["t_s"])

    turns = []
    for side, sign in (("left", 1), ("right", -1)):
        for start, end in runs(timeline, lambda r, s=sign: (can(r).get("steering_deg") or 0) * s > TURN_DEG):
            turns.append((start, end))
            used = [b for b in blinker[side] if overlaps((start - BLINKER_BEFORE_S, end), b)]
            detail = "no_blinker" if not used else "late_blinker" if min(b[0] for b in used) > start else "blinker"
            peak = max(window(timeline, start, end), key=lambda r: (can(r).get("steering_deg") or 0) * sign)
            add("turn", start, end, side, detail,
                f"steering past {TURN_DEG} deg {start:.1f}-{end:.1f} s; {side} blinker " +
                (", ".join(f"{b[0]:.1f}-{b[1]:.1f} s" for b in used) or "not on"),
                [peak["seq"]], peak["t_s"])

    for side, sign in (("left", 1), ("right", -1)):
        bends = runs(timeline, lambda r, s=sign: CURVE_DEG < (can(r).get("steering_deg") or 0) * s <= TURN_DEG
                     and (can(r).get("speed_mps") or 0) > CURVE_MIN_MPS, gap_s=MERGE_GAP_S)
        for start, end in bends:
            if end - start >= CURVE_MIN_S and not any(overlaps((start, end), t, pad=1) for t in turns):
                add("curve", start, end, side, "", f"steering {CURVE_DEG}-{TURN_DEG} deg for {end - start:.1f} s")

    for side in ("left", "right"):
        for b in blinker[side]:
            if not any(overlaps(b, (t[0] - BLINKER_BEFORE_S, t[1])) for t in turns):
                add("lane_change", b[0], b[1] + 3, side, "blinker", f"{side} blinker {b[0]:.1f}-{b[1]:.1f} s, no turn",
                    key_t=b[0])

    for side in ("LEFT", "RIGHT"):
        for start, end in runs(timeline, lambda r, s=side: r["vision"]["departure"] == s, gap_s=1):
            if end > start:  # at least two frames
                add("lane_departure", start, end, side.lower(), "",
                    f"vision flagged departing {side.lower()} {start:.1f}-{end:.1f} s",
                    seqs_where(timeline, start, end, lambda r, s=side: r["vision"]["departure"] == s))

    out.sort(key=lambda c: (c["t_start"], c["type"]))
    for k, c in enumerate(out, 1):
        c["id"] = f"c{k:02d}"
    return [{"id": c.pop("id"), **c} for c in out]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--timeline", help="default runs/<session>/timeline.jsonl")
    p.add_argument("--out", help="default runs/<session>/candidates.json")
    args = p.parse_args(argv)

    run_dir = ROOT / "runs" / Path(args.session_dir).name
    timeline_path = Path(args.timeline) if args.timeline else run_dir / "timeline.jsonl"
    out = Path(args.out) if args.out else run_dir / "candidates.json"

    cands = detect([json.loads(line) for line in open(timeline_path)])
    out.write_text(json.dumps(cands, indent=1) + "\n")
    counts = {}
    for c in cands:
        key = c["type"] + (f" ({c['detail']})" if c["type"] == "stop_sign" else "")
        counts[key] = counts.get(key, 0) + 1
    print(f"{len(cands)} candidates: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
