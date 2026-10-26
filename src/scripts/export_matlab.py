#!/usr/bin/env python3
"""Export each verified driving event as a MATLAB drivingScenario (Automated Driving Toolbox).

    python src/scripts/export_matlab.py <session_dir> [--events runs/<session>/agent/events.json] [--out scenarios/<session>]

Step 7 of scenario mining. For every event the agent confirmed or corrected (validator passed),
writes ev_<id>_<type>.m, a MATLAB function returning [scenario, egoVehicle]:

    scenario = ev_c11_stop_sign();  plot(scenario);  while advance(scenario), pause(0.05), end
    drivingScenarioDesigner(ev_c11_stop_sign())

The simplest scenario that keeps what made the event: the ego vehicle replays the car's real speed
profile (front wheel speed from the CAN log, standstills included) along its real path, on a
two-lane road (3.5 m lanes) that follows the path, ego in the right lane. The window is the event
plus PAD_S either side.

The path comes from the CAN log only: heading = integral of the yaw rate, position = integral of
speed along the heading, starting at the origin facing +x. YawRate's unit isn't documented; it was
calibrated against the GPS of the original (unshared) recording: (raw - 2.5) * 0.112 = deg/s,
positive = left (167 windows of 3-6 s while moving, r = 0.96, 2.7 deg rms over a window). Only these
two numbers are used; no position from the GPS is exported. Checked against the GPS heading change
of the 9 exported events where GPS heading is usable (moving >= 6 m around the window): median
error 11.5 deg, worst 30 deg (the GPS gives ~1 fix/s, itself rough at low speed). Good for "a turn
of about 90 deg to the left", not for lane-level geometry.

Each file's header traces the event to its source: drive, times, the agent's verdict and the
validated claims (frame file, CAN row). verify_matlab.py simulates every file in MATLAB and checks
the replayed speed against the CAN log.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import fuse  # noqa: E402

YAW_BIAS_RAW = 2.5        # YawRate reading at standstill (median over 54,913 standstill rows)
YAW_DEG_S_PER_RAW = 0.112  # calibrated against GPS heading, see the module docstring
PAD_S = 3.0
DT_S = 0.1
STOPPED_MPS = 0.05         # wheel speed reads 0.0 when stopped
WAYPOINT_EVERY_M = 0.5
ROAD_EVERY_M = 4.0
LANE_W_M = 3.5
MIN_ROAD_M = 20.0
VERIFIED = ("confirmed", "corrected")


def profile(track, t0, t1):
    """(t, speed m/s, x, y, heading rad) every DT_S over [t0, t1] from the CAN log."""
    t = np.arange(t0, t1 + DT_S / 2, DT_S)
    v = np.nan_to_num(np.interp(t, track.t, np.nan_to_num(track.values["speed_mps"])))
    yaw = np.interp(t, track.t, np.nan_to_num(track.values["yaw_rate_raw"], nan=YAW_BIAS_RAW))
    rate = np.radians((yaw - YAW_BIAS_RAW) * YAW_DEG_S_PER_RAW)
    rate[v < STOPPED_MPS] = 0.0  # a parked car doesn't turn; keeps sensor noise out of the path
    heading = np.concatenate([[0.0], np.cumsum((rate[1:] + rate[:-1]) / 2 * DT_S)])
    step = (v[1:] + v[:-1]) / 2 * DT_S
    mid = (heading[1:] + heading[:-1]) / 2
    x = np.concatenate([[0.0], np.cumsum(step * np.cos(mid))])
    y = np.concatenate([[0.0], np.cumsum(step * np.sin(mid))])
    return t, v, x, y, heading


def waypoints(t, v, x, y):
    """[(x, y, speed, wait_s)] for MATLAB's trajectory(): a point every WAYPOINT_EVERY_M while moving,
    one point with speed 0 and the stop's duration as wait time for each standstill."""
    out, k, n = [], 0, len(t)
    last_xy = None
    while k < n:
        if v[k] < STOPPED_MPS:
            j = k
            while j + 1 < n and v[j + 1] < STOPPED_MPS:
                j += 1
            wait = max(t[j] - t[k], DT_S)
            if last_xy is not None and np.hypot(x[k] - last_xy[0], y[k] - last_xy[1]) < 0.05:
                out[-1] = (out[-1][0], out[-1][1], 0.0, out[-1][3] + wait)  # stopped where the last point is
            else:
                out.append((x[k], y[k], 0.0, wait))
                last_xy = (x[k], y[k])
            k = j + 1
            continue
        if last_xy is None or np.hypot(x[k] - last_xy[0], y[k] - last_xy[1]) >= WAYPOINT_EVERY_M or k == n - 1:
            if last_xy is None or np.hypot(x[k] - last_xy[0], y[k] - last_xy[1]) >= 0.05:
                out.append((x[k], y[k], float(v[k]), 0.0))
                last_xy = (x[k], y[k])
        k += 1
    return out


def road_centers(x, y, heading):
    """Road centre line: the path shifted half a lane to the left (ego drives in the right lane),
    a point every ROAD_EVERY_M, extended straight to at least MIN_ROAD_M."""
    cx, cy = x - np.sin(heading) * LANE_W_M / 2, y + np.cos(heading) * LANE_W_M / 2
    pts, travelled, last = [(cx[0], cy[0])], 0.0, (x[0], y[0])
    for k in range(1, len(x)):
        travelled += np.hypot(x[k] - last[0], y[k] - last[1])
        last = (x[k], y[k])
        if travelled >= ROAD_EVERY_M:
            pts.append((cx[k], cy[k]))
            travelled = 0.0
    length = sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
    if length < MIN_ROAD_M:  # (nearly) standing still: a short straight road ahead
        h = heading[-1]
        pts = [pts[0], (pts[0][0] + MIN_ROAD_M * np.cos(h), pts[0][1] + MIN_ROAD_M * np.sin(h))]
    else:  # a little road past the end, so the car doesn't drive off its edge
        a, b = pts[-2], pts[-1]
        d = np.hypot(b[0] - a[0], b[1] - a[1])
        pts.append((b[0] + (b[0] - a[0]) / d * 5, b[1] + (b[1] - a[1]) / d * 5))
    return pts


def mat(rows, fmt="%.3f"):
    return "[" + "; ".join(" ".join(fmt % v for v in r) for r in rows) + "]"


def matlab_file(name, ev, session, t0, t1, wps, road):
    claims = "\n".join(f"%   seq {c['seq']} {c['field']} = {c['value']}  (frame {c['frame']}, CAN row {c['can_row']})"
                       for c in ev.get("claims", []))
    reason = ev.get("reason", "").replace("\n", " ")
    xy = [(w[0], w[1], 0.0) for w in wps]
    speeds = [w[2] for w in wps]
    waits = [w[3] for w in wps]
    return f"""function [scenario, egoVehicle] = {name}()
%{name.upper()} {ev['type']} {ev['side']} {ev['detail']} at {ev['t_start']:.1f}-{ev['t_end']:.1f} s, from a real drive.
%   scenario = {name}(); plot(scenario); while advance(scenario), pause(0.05), end
%   drivingScenarioDesigner({name}())
%
%   Drive {session}, drive time {t0:.1f}-{t1:.1f} s (the event +/- {PAD_S:g} s).
%   Event (agent verdict: {ev['verdict']}, validator: {ev.get('validation', '')}): type {ev['type']}, side {ev['side'] or '-'},
%   detail {ev['detail'] or '-'}, {ev['t_start']:.2f}-{ev['t_end']:.2f} s. Agent's reason (not validated): {reason}
%   Validated claims:
{claims or '%   (none)'}
%
%   Ego: the car's speed profile (CAN front wheel speed) along its path (CAN yaw rate, calibrated
%   (raw - {YAW_BIAS_RAW}) * {YAW_DEG_S_PER_RAW} deg/s), starting at the origin facing +x. Road: two {LANE_W_M} m
%   lanes along the path, ego in the right lane. Made by src/scripts/export_matlab.py.

scenario = drivingScenario('SampleTime', {DT_S});  % runs until the ego's trajectory ends ({t1 - t0:.1f} s of drive)

roadCenters = {mat([(p[0], p[1], 0.0) for p in road])};
road(scenario, roadCenters, 'Lanes', lanespec([1 1], 'Width', {LANE_W_M}), 'Name', 'Road');

egoVehicle = vehicle(scenario, 'ClassID', 1, 'Position', [{wps[0][0]:.3f} {wps[0][1]:.3f} 0], 'Name', 'Ego');
waypoints = {mat(xy)};
speed = {mat([[s] for s in speeds])};
waittime = {mat([[w] for w in waits])};
trajectory(egoVehicle, waypoints, speed, waittime);
end
"""


def event_name(ev):
    return f"ev_{ev['id']}_{ev['type']}"


def export(session_dir, events, out_dir):
    """Writes one .m per verified event; returns [(name, t0, t1, can speed profile)] for checking."""
    track = fuse.load_track(session_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    end_t = float(track.t[-1])
    for ev in events:
        if ev.get("verdict") not in VERIFIED:
            continue
        t0, t1 = max(ev["t_start"] - PAD_S, 0.0), min(ev["t_end"] + PAD_S, end_t)
        t, v, x, y, heading = profile(track, t0, t1)
        wps = waypoints(t, v, x, y)
        if len(wps) < 2:  # parked the whole window: nothing to drive
            continue
        name = event_name(ev)
        (out_dir / f"{name}.m").write_text(matlab_file(name, ev, Path(session_dir).name, t0, t1, wps,
                                                       road_centers(x, y, heading)))
        written.append({"name": name, "t0": round(t0, 2), "t1": round(t1, 2), "t": [round(a - t0, 2) for a in t],
                        "speed": [round(float(a), 3) for a in v],
                        "distance_m": round(float(np.sum((v[1:] + v[:-1]) / 2 * DT_S)), 2),
                        "end_xy": [round(float(x[-1]), 2), round(float(y[-1]), 2)],
                        "turned_deg": round(float(np.degrees(heading[-1])), 1)})
    (out_dir / "expected.json").write_text(json.dumps(written, indent=1) + "\n")
    return written


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--events", help="default runs/<session>/agent/events.json")
    p.add_argument("--out", help="default scenarios/<session>")
    args = p.parse_args(argv)
    session = Path(args.session_dir).name
    events_path = Path(args.events) if args.events else ROOT / "runs" / session / "agent" / "events.json"
    out = Path(args.out) if args.out else ROOT / "scenarios" / session
    written = export(args.session_dir, json.loads(events_path.read_text()), out)
    for w in written:
        print(f"{w['name']:<28} {w['t1'] - w['t0']:5.1f} s  {w['distance_m']:6.1f} m  turned {w['turned_deg']:6.1f} deg")
    print(f"wrote {len(written)} scenarios to {out}")


if __name__ == "__main__":
    main()
