#!/usr/bin/env python3
"""Join every processed frame with what the car was doing at that moment, from its CAN bus.

    python src/scripts/fuse.py <session_dir> [--vision runs/<session>/vision.jsonl] [--out runs/<session>/timeline.jsonl]
    python src/scripts/fuse.py test_sessions/private-640/20261022T164127Z-084b

Step 2 of scenario mining. Input: vision_batch.py's vision.jsonl and the session's decoded.csv
(same monotonic clock as the frames, rows forward-filled, so the state at t is the last row at or
before t). Output: one JSON object per frame, in drive order:

    seq, frame, timestamp_ns, t_s     the frame (t_s = seconds since the first frame)
    can                               SIGNALS at t_s, plus
                                        accel_mps2  from speed over +-ACCEL_DT_S (the EBCM
                                                    longitudinal accel signal is too noisy)
                                        odo_m       distance driven since the start of the recording
                                        row_ts_ns   timestamp_ns of the decoded.csv row used, so any
                                                    claim made from this frame cites an exact CAN row
    vision                            everything vision_batch.py wrote for the frame

Signal meanings, checked on the 2026-10-22 drive: speed_mps is the EBCM front wheel speed (max 12.3
m/s where VehicleSpeed says 28.6, so VehicleSpeed is mph); steering_deg is positive to the left;
every one of the 7 blinker episodes was followed by steering the same way (1 = left, 2 = right);
at both stop signs, standstill came on about 1 s after the last frame the sign was seen in.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
from virtual_pi import CanTrack, first_timestamp_ns  # noqa: E402

SIGNALS = {
    "speed_mps": (("EBCMWheelSpdFront.vehicle_speed_mps",), 1.0),
    "speed_mph": (("VehicleSpeed",), 1.0),
    "steering_deg": (("SteeringWheelAngle",), 1.0),  # positive = left
    # unit not verified: tracks steering_deg (r = 0.99); ~0.22 deg/s per unit against lateral
    # acceleration / speed, but that fit is loose (r = 0.77). Calibrate before integrating it.
    "yaw_rate_raw": (("YawRate",), 1.0),
    "lat_accel_mps2": (("LateralAcceleration",), 1.0),
    "accel_pct": (("AcceleratorPedal2", "AcceleratorPedal"), 100 / 254),
    "brake": (("EBCMBrakePedalPosition.BrakePressed",), 1.0),
    "brake_pressure": (("UserBrakePressure",), 1.0),
    "blinker": (("TurnSignals",), 1.0),
    "standstill": (("Standstill",), 1.0),
    "gear": (("PRNDL2", "PRNDL"), None),
}
BLINKER = {1.0: "left", 2.0: "right"}
ACCEL_DT_S = 0.5
CAN_LEAD_S = 0.1  # a frame this close before the first CAN row uses that row (the log starts ~0.3 ms late)
FRAME_KEYS = ("seq", "frame", "timestamp_ns", "t_s")


def odometer(track):
    """Distance driven (m) at each CAN row: speed integrated with the trapezoid rule."""
    v = np.nan_to_num(track.values["speed_mps"])
    steps = np.diff(track.t) * (v[1:] + v[:-1]) / 2
    return np.concatenate([[0.0], np.cumsum(steps)])


def speed_at(track, t):
    return track.at(min(max(t, track.t[0]), track.t[-1]))["speed_mps"]


def can_at(track, odo, t):
    """The CAN state at drive time t (see the module docstring), or None before the first row."""
    i = int(np.searchsorted(track.t, t, side="right")) - 1
    if i < 0:
        if track.t[0] - t > CAN_LEAD_S:
            return None
        i, t = 0, track.t[0]
    can = track.at(t)
    can["blinker"] = BLINKER.get(can["blinker"])
    for flag in ("brake", "standstill"):
        can[flag] = None if can[flag] is None else bool(can[flag])
    before, after = speed_at(track, t - ACCEL_DT_S), speed_at(track, t + ACCEL_DT_S)
    if before is not None and after is not None:
        can["accel_mps2"] = (after - before) / (2 * ACCEL_DT_S)
    else:
        can["accel_mps2"] = None
    can["odo_m"] = float(np.interp(t, track.t, odo))
    can = {k: round(v, 4) if isinstance(v, float) else v for k, v in can.items()}
    can["row_ts_ns"] = int(track.ts_ns[i])
    return can


def fuse(vision_rows, track):
    """[timeline row] for vision_rows (vision.jsonl objects), sorted by drive time."""
    odo = odometer(track)
    out = []
    for row in sorted(vision_rows, key=lambda r: r["t_s"]):
        out.append({**{k: row[k] for k in FRAME_KEYS},
                    "can": can_at(track, odo, row["t_s"]),
                    "vision": {k: v for k, v in row.items() if k not in FRAME_KEYS}})
    return out


def load_track(session_dir):
    session = Path(session_dir)
    track = CanTrack(session / "decoded.csv", first_timestamp_ns(session), SIGNALS)
    if not track.available:
        raise SystemExit(f"{session / 'decoded.csv'} not found: decode the CAN log first (see virtual_pi.py)")
    return track


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--vision", help="default runs/<session>/vision.jsonl")
    p.add_argument("--out", help="default runs/<session>/timeline.jsonl")
    args = p.parse_args(argv)

    session = Path(args.session_dir)
    run_dir = ROOT / "runs" / session.name
    vision_path = Path(args.vision) if args.vision else run_dir / "vision.jsonl"
    out = Path(args.out) if args.out else run_dir / "timeline.jsonl"

    vision_rows = [json.loads(line) for line in open(vision_path)]
    timeline = fuse(vision_rows, load_track(session))
    out.write_text("".join(json.dumps(r) + "\n" for r in timeline))

    cans = [r["can"] for r in timeline if r["can"]]
    print(f"{len(timeline)} frames, {len(cans)} with CAN; {cans[-1]['odo_m']:.0f} m driven; "
          f"moving in {sum(c['speed_mps'] > 0.5 for c in cans)}, standstill in {sum(bool(c['standstill']) for c in cans)}, "
          f"blinker on in {sum(c['blinker'] is not None for c in cans)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
