#!/usr/bin/env python3
"""Simulate every exported scenario in MATLAB and check it replays the car's CAN data.

    python src/scripts/verify_matlab.py [scenarios/<session>] [--matlab matlab]

Runs each ev_*.m listed in expected.json (written by export_matlab.py) with advance() until the
scenario ends, recording the ego vehicle's speed and position every sample, then compares with the
CAN profile the file was made from:

    speed_rms      RMS difference between the replayed and the CAN speed (m/s), at the CAN samples
                   the simulation covers
    duration_err   when the simulation ends (the ego reaches its last waypoint) vs the window's end (s)
    end_err        distance between the ego's final position and the CAN path's end (m)

A scenario passes if it builds and runs in MATLAB and stays within the TOLERANCES. Writes
verify.json next to the scenarios.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TOLERANCES = {"speed_rms": 0.5, "duration_err": 1.0, "end_err": 2.0}  # set before the first run

SCRIPT = """
names = jsondecode(fileread('{expected}'));
out = struct();
for k = 1:numel(names)
    n = names(k).name;
    try
        [s, ego] = feval(n);
        t = []; v = []; xy = [];
        while advance(s)
            t(end+1) = s.SimulationTime; v(end+1) = norm(ego.Velocity); xy(end+1, :) = ego.Position(1:2);
        end
        out.(n) = struct('ok', true, 't', t, 'v', v, 'xy', xy);
    catch e
        out.(n) = struct('ok', false, 'error', e.message);
    end
end
fid = fopen('{result}', 'w'); fprintf(fid, '%s', jsonencode(out)); fclose(fid);
"""


def compare(exp, sim):
    if not sim.get("ok"):
        return {"ok": False, "error": sim.get("error")}
    t, v = np.asarray(sim["t"], float), np.asarray(sim["v"], float)
    xy = np.asarray(sim["xy"], float).reshape(-1, 2)
    want_t, want_v = np.asarray(exp["t"]), np.asarray(exp["speed"])
    covered = want_t <= t[-1] + 1e-6
    got_v = np.interp(want_t[covered], t, v)
    r = {"ok": True,
         "speed_rms": round(float(np.sqrt(np.mean((got_v - want_v[covered]) ** 2))), 3),
         "duration_err": round(float(t[-1] - want_t[-1]), 2),
         "end_err": round(float(np.hypot(*(xy[-1] - np.asarray(exp["end_xy"])))), 2)}
    r["pass"] = all(abs(r[k]) <= tol for k, tol in TOLERANCES.items())
    return r


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("scenarios", nargs="?", default=str(ROOT / "scenarios" / "20261022T164127Z-084b"))
    p.add_argument("--matlab", default="matlab")
    args = p.parse_args(argv)
    d = Path(args.scenarios).resolve()
    expected = json.loads((d / "expected.json").read_text())
    names = d / "names.json"
    names.write_text(json.dumps([{"name": e["name"]} for e in expected]))
    result = d / "matlab_result.json"
    runner = d / "verify_run_tmp.m"
    runner.write_text(SCRIPT.format(expected=names, result=result))
    try:
        proc = subprocess.run([args.matlab, "-batch", f"cd('{d}'); verify_run_tmp"],
                              capture_output=True, text=True, timeout=1200)
    finally:
        names.unlink()
        runner.unlink()
    if proc.returncode != 0 or not result.exists():
        sys.exit(f"MATLAB failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    sims = json.loads(result.read_text())
    result.unlink()
    report = {e["name"]: compare(e, sims.get(e["name"], {"ok": False, "error": "not run"})) for e in expected}
    (d / "verify.json").write_text(json.dumps({"tolerances": TOLERANCES, "scenarios": report}, indent=1) + "\n")
    for n, r in report.items():
        if r["ok"]:
            print(f"{n:<28} {'PASS' if r['pass'] else 'FAIL'}  speed rms {r['speed_rms']:.2f} m/s  "
                  f"duration {r['duration_err']:+.2f} s  end {r['end_err']:.2f} m")
        else:
            print(f"{n:<28} ERROR {r['error']}")
    passed = sum(r.get("pass", False) for r in report.values())
    print(f"{passed} of {len(report)} scenarios pass; wrote {d / 'verify.json'}")
    sys.exit(0 if passed == len(report) else 1)


if __name__ == "__main__":
    main()
