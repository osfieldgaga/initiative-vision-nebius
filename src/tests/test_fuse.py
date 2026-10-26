"""Tests for src/scripts/fuse.py: joining frames with CAN, and the signals' meaning on the real drive."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import fuse  # noqa: E402

DRIVE = ROOT / "test_sessions" / "private-640" / "20261022T164127Z-084b"


def write_session(d, can_rows):
    """A session with one frame at t0 = 1 s and decoded.csv rows (t_s, speed, blinker, standstill)."""
    (d / "frames.csv").write_text("seq,filename,timestamp_ns\n0,frames/a.jpg,1000000000\n")
    lines = ["timestamp_ns,seq,message,EBCMWheelSpdFront.vehicle_speed_mps,TurnSignals,Standstill,PRNDL2"]
    for k, (t, v, blink, still) in enumerate(can_rows):
        lines.append(f"{1_000_000_000 + round(t * 1e9)},{k},X,{v},{blink},{still},D")
    (d / "decoded.csv").write_text("\n".join(lines) + "\n")


class FuseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        write_session(self.dir, [(0, 0.0, 0, 1), (1, 2.0, 1, 0), (2, 4.0, 1, 0), (3, 4.0, 2, 0)])
        self.track = fuse.load_track(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def test_state_is_last_row_at_or_before_t(self):
        [row] = fuse.fuse([{"seq": 7, "frame": "f.jpg", "timestamp_ns": 2_500_000_000, "t_s": 1.5,
                            "lane_valid": True}], self.track)
        can = row["can"]
        self.assertEqual(can["speed_mps"], 2.0)
        self.assertEqual(can["blinker"], "left")
        self.assertIs(can["standstill"], False)
        self.assertEqual(can["gear"], "D")
        self.assertEqual(can["row_ts_ns"], 2_000_000_000)
        self.assertEqual(row["vision"], {"lane_valid": True})
        self.assertEqual((row["seq"], row["t_s"]), (7, 1.5))

    def test_accel_and_odometer(self):
        odo = fuse.odometer(self.track)
        self.assertEqual(list(odo), [0.0, 1.0, 4.0, 8.0])  # trapezoids: 1, 3, 4 m
        can = fuse.can_at(self.track, odo, 1.5)
        self.assertAlmostEqual(can["accel_mps2"], 2.0)  # (speed at 2 s - speed at 1 s) / 1 s
        self.assertAlmostEqual(can["odo_m"], 2.5)

    def test_right_blinker_and_before_first_row(self):
        odo = fuse.odometer(self.track)
        self.assertEqual(fuse.can_at(self.track, odo, 3.0)["blinker"], "right")
        self.assertIsNone(fuse.can_at(self.track, odo, -0.5))
        self.assertEqual(fuse.can_at(self.track, odo, -0.05)["row_ts_ns"], 1_000_000_000)  # within CAN_LEAD_S

    def test_rows_sorted_by_time(self):
        rows = [{"seq": s, "frame": "", "timestamp_ns": 0, "t_s": t} for s, t in ((2, 2.0), (1, 1.0))]
        self.assertEqual([r["seq"] for r in fuse.fuse(rows, self.track)], [1, 2])


@unittest.skipUnless((DRIVE / "decoded.csv").exists(), "needs the 2026-10-22 drive (see README)")
class RealDriveTest(unittest.TestCase):
    """What the docstring claims about the signals, checked on the shared drive."""

    @classmethod
    def setUpClass(cls):
        with open(DRIVE / "frames.csv", newline="") as f:
            frames = list(csv.DictReader(f))
        t0 = int(frames[0]["timestamp_ns"])
        rows = [{"seq": int(r["seq"]), "frame": Path(r["filename"]).name, "timestamp_ns": int(r["timestamp_ns"]),
                 "t_s": (int(r["timestamp_ns"]) - t0) / 1e9} for r in frames[::5]]  # ~3 fps
        cls.timeline = fuse.fuse(rows, fuse.load_track(DRIVE))
        cls.t_of = {int(r["seq"]): (int(r["timestamp_ns"]) - t0) / 1e9 for r in frames}

    def window(self, t0, t1):
        return [r["can"] for r in self.timeline if t0 <= r["t_s"] <= t1]

    def test_car_stops_after_the_confirmed_stop_signs(self):
        # last frame each sign was seen in, checked by eye (data/eval/README.md)
        for seq in (2676, 4512):
            t = self.t_of[seq]
            self.assertTrue(any(c["standstill"] for c in self.window(t, t + 3)), f"no stop after seq {seq}")

    def test_blinker_is_followed_by_steering_the_same_way(self):
        # an episode = consecutive frames with the same blinker on; the turn can come after a wait
        # (at 290 s the blinker goes on before a stop sign and the car turns after stopping)
        episodes, prev = [], None
        for r in self.timeline:
            side = r["can"]["blinker"]
            if side is not None and side == prev:
                episodes[-1][2] = r["t_s"]
            elif side is not None:
                episodes.append([side, r["t_s"], r["t_s"]])
            prev = side
        for side, start, end in episodes:
            steer = [c["steering_deg"] for c in self.window(start - 2, end + 8)]
            turned = max(steer) > 90 if side == "left" else min(steer) < -90
            self.assertTrue(turned, f"{side} blinker at {start:.1f}-{end:.1f} s without a {side} turn")
        self.assertEqual(len(episodes), 7)

    def test_speed_units(self):
        cans = [r["can"] for r in self.timeline if r["can"]["speed_mps"] > 3]
        ratio = sorted(c["speed_mph"] / c["speed_mps"] for c in cans)[len(cans) // 2]
        self.assertAlmostEqual(ratio, 2.237, delta=0.1)  # mph per m/s

    def test_odometer_grows(self):
        odo = [r["can"]["odo_m"] for r in self.timeline]
        self.assertEqual(odo, sorted(odo))
        self.assertGreater(odo[-1], 1000)


if __name__ == "__main__":
    unittest.main()
