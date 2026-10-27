"""Tests for src/scripts/export_matlab.py: path from CAN, waypoints for MATLAB's trajectory(), file contents."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import export_matlab as em  # noqa: E402


def track(speed, yaw_deg_s, dur=10.0):
    """A CAN track at 100 Hz with constant speed (m/s) and yaw rate (deg/s, converted to raw units)."""
    t = np.arange(0, dur, 0.01)
    raw = em.YAW_BIAS_RAW + yaw_deg_s / em.YAW_DEG_S_PER_RAW
    return SimpleNamespace(t=t, values={"speed_mps": np.full_like(t, speed), "yaw_rate_raw": np.full_like(t, raw)})


class ProfileTest(unittest.TestCase):
    def test_straight(self):
        t, v, x, y, h = em.profile(track(5.0, 0.0), 0, 4)
        self.assertAlmostEqual(x[-1], 20.0, places=6)
        self.assertAlmostEqual(y[-1], 0.0, places=6)

    def test_left_turn_quarter_circle(self):
        # 9 deg/s for 10 s = 90 deg to the left; radius v / omega
        t, v, x, y, h = em.profile(track(5.0, 9.0, dur=11), 0, 10)
        r = 5.0 / np.radians(9.0)
        self.assertAlmostEqual(np.degrees(h[-1]), 90.0, places=3)
        self.assertAlmostEqual(x[-1], r, delta=0.05)
        self.assertAlmostEqual(y[-1], r, delta=0.05)

    def test_parked_car_does_not_turn(self):
        t, v, x, y, h = em.profile(track(0.0, 5.0), 0, 5)  # yaw noise while stopped
        self.assertEqual(float(np.abs(h).max()), 0.0)


class WaypointsTest(unittest.TestCase):
    def test_standstill_becomes_one_wait(self):
        t = np.arange(0, 6.01, 0.1)
        v = np.where((t >= 2) & (t < 4), 0.0, 2.0)
        x = np.cumsum(v * 0.1) - v[0] * 0.1
        wps = em.waypoints(t, v, x, np.zeros_like(x))
        stops = [w for w in wps if w[2] == 0.0]
        self.assertEqual(len(stops), 1)
        # MATLAB's time to each waypoint (even speed change per leg, plus waits) lands on the car's time
        # right after the stop, so a delay can't build up over a drive
        clock, after = wps[0][4], wps.index(stops[0]) + 1
        for a, b in zip(wps[:after], wps[1:after + 1]):
            clock += a[3] + 2 * np.hypot(b[0] - a[0], b[1] - a[1]) / (a[2] + b[2])
        self.assertAlmostEqual(clock, wps[after][4], places=6)
        self.assertLess(stops[0][3], 2.0)  # shorter than the 2 s stop: the slow-down and start take longer
        for a, b in zip(wps, wps[1:]):
            self.assertGreater(np.hypot(b[0] - a[0], b[1] - a[1]), 0.04)  # trajectory() rejects repeated points
        self.assertTrue(all(w[3] == 0.0 for w in wps if w[2] > 0))  # waits only where stopped

    def test_road_is_left_of_the_path_and_long_enough(self):
        x = np.linspace(0, 30, 301)
        pts = em.road_centers(x, np.zeros_like(x), np.zeros_like(x))
        self.assertTrue(all(abs(p[1] - em.LANE_W_M / 2) < 1e-9 for p in pts))
        self.assertGreater(pts[-1][0], 30)  # extends past the end
        short = em.road_centers(np.zeros(5), np.zeros(5), np.zeros(5))
        self.assertAlmostEqual(short[-1][0] - short[0][0], em.MIN_ROAD_M)


class FileTest(unittest.TestCase):
    def test_header_traces_the_event(self):
        ev = {"id": "c11", "type": "stop_sign", "side": "", "detail": "rolling_stop", "t_start": 170.71,
              "t_end": 176.07, "verdict": "confirmed", "validation": "passed", "reason": "x",
              "claims": [{"seq": 2720, "field": "mph", "value": "1.1", "frame": "00002720_1.jpg", "can_row": 4725}]}
        text = em.matlab_file("ev_c11_stop_sign", ev, "S", 167.7, 179.1, [(0, 0, 5.0, 0.0), (5, 0, 0.0, 2.0)],
                              [(0, 1.75), (20, 1.75)])
        self.assertTrue(text.startswith("function [scenario, egoVehicle] = ev_c11_stop_sign(speedup)"))
        self.assertIn("seq 2720 mph = 1.1  (frame 00002720_1.jpg, CAN row 4725)", text)
        self.assertIn("waittime = [0.000; 2.000];", text)
        self.assertNotIn("%%", text)  # a cell break would split MATLAB's help text
        self.assertIn("if nargout == 0", text)  # plays itself when run on its own
        self.assertIn("eventNames = {'c11 stop_sign rolling_stop'};", text)

    def test_full_drive_lists_every_event(self):
        evs = [{"id": "c11", "type": "stop_sign", "side": "", "detail": "rolling_stop", "t_start": 170.7, "t_end": 176.1},
               {"id": "c29", "type": "turn", "side": "left", "detail": "blinker", "t_start": 376.0, "t_end": 381.0}]
        text = em.drive_file("full_drive", "S", 0.0, 459.3, [(0, 0, 5.0, 0.0), (5, 0, 0.0, 2.0)],
                             [(0, 1.75), (20, 1.75)], evs)
        self.assertTrue(text.startswith("function [scenario, egoVehicle] = full_drive(speedup)"))
        self.assertIn("ev_c29_turn.m", text)
        self.assertIn("eventTimes = [170.70 176.10; 376.00 381.00];", text)
        self.assertIn("'Waypoints', 'off'", text)


class AgreedTest(unittest.TestCase):
    def test_only_events_the_labels_agree_with(self):
        ev = lambda i, typ, t0, side="", detail="", verdict="confirmed": {  # noqa: E731
            "id": i, "type": typ, "t_start": t0, "t_end": t0 + 4, "side": side, "detail": detail, "verdict": verdict}
        events = [ev("c1", "turn", 10, "left", "blinker"), ev("c2", "turn", 30, "left", "no_blinker"),
                  ev("c3", "stop_sign", 50, detail="rolling_stop"), ev("c4", "turn", 70, "right", verdict="rejected")]
        row = lambda i, typ, t0, side="", detail="", status="yes": {  # noqa: E731
            "id": i, "status": status, "source": "prefill", "type": typ, "t_start": str(t0), "t_end": str(t0 + 3),
            "side": side, "detail": detail, "confidence": ""}
        labels = [row("1", "turn", 10.5, "left", "blinker"), row("2", "turn", 30, "right", "no_blinker"),
                  row("3", "stop_sign", 50, detail="full_stop"), row("4", "turn", 70, "right", status="yes")]
        got = em.agreed(events, labels)
        self.assertEqual([(e["id"], e["label"]) for e in got], [("c1", "1")])  # c2 wrong side, c3 detail, c4 rejected


if __name__ == "__main__":
    unittest.main()
