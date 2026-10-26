"""Tests for src/scripts/label_events.py: the pre-filled moments and the format check."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import label_events  # noqa: E402


def timeline(n, at=None):
    """n rows at 1 s apart, driving straight at 10 m/s; at = {t: {can or vision overrides}}."""
    at = at or {}
    rows = []
    for t in range(n):
        can = {"speed_mps": 10.0, "speed_mph": 22.4, "steering_deg": 0.0, "blinker": None, "standstill": False, "gear": "D"}
        vision = {"signs": [], "departure": None}
        for key, value in at.get(t, {}).items():
            (vision if key in vision else can)[key] = value
        rows.append({"t_s": float(t), "can": can, "vision": vision})
    return rows


class RunsTest(unittest.TestCase):
    def test_merges_short_gaps(self):
        rows = [{"t_s": float(t)} for t in range(10)]
        on = {1, 2, 4, 8}
        self.assertEqual(label_events.runs(rows, lambda r: r["t_s"] in on, gap_s=2), [(1.0, 4.0), (8.0, 8.0)])


class PrefillTest(unittest.TestCase):
    def kinds(self, rows):
        return [(r["type"], r["side"], r["detail"]) for r in label_events.prefill_rows(rows)]

    def test_stop_after_stop_sign(self):
        stop = {"type": "stop", "value": None, "score": 0.5, "text": "stop", "box": [0, 0, 1, 1]}
        rows = timeline(20, {3: {"signs": [stop]}, 6: {"standstill": True, "speed_mps": 0.0}})
        self.assertEqual(self.kinds(rows), [("stop_sign", "", "full_stop")])

    def test_stop_without_sign(self):
        rows = timeline(20, {6: {"standstill": True, "speed_mps": 0.0}})
        self.assertEqual(self.kinds(rows), [("other_stop", "", "")])

    def test_turn_blinker_before_late_and_none(self):
        rows = timeline(60, {2: {"blinker": "left"}, 4: {"steering_deg": 200.0},
                               20: {"steering_deg": -200.0}, 21: {"blinker": "right", "steering_deg": -200.0},
                               40: {"steering_deg": 200.0}})
        self.assertEqual(self.kinds(rows), [("turn", "left", "blinker"), ("turn", "right", "late_blinker"),
                                            ("turn", "left", "no_blinker")])

    def test_blinker_without_turn_is_a_lane_change(self):
        rows = timeline(20, {5: {"blinker": "right"}, 6: {"blinker": "right"}})
        self.assertEqual(self.kinds(rows), [("lane_change", "right", "blinker")])

    def test_curve_needs_duration_and_speed(self):
        bend = {"steering_deg": -45.0}
        rows = timeline(30, {**{t: bend for t in range(5, 9)}, 20: bend})  # 3 s bend, then a 0 s one
        self.assertEqual(self.kinds(rows), [("curve", "right", "")])

    def test_departure_needs_two_frames(self):
        rows = timeline(20, {3: {"departure": "LEFT"}, 4: {"departure": "LEFT"}, 10: {"departure": "RIGHT"}})
        self.assertEqual(self.kinds(rows), [("lane_departure", "left", "")])

    def test_rows_are_numbered_and_unreviewed(self):
        rows = label_events.prefill_rows(timeline(20, {6: {"standstill": True, "speed_mps": 0.0}}))
        self.assertEqual((rows[0]["id"], rows[0]["status"], rows[0]["source"]), (1, "?", "prefill"))
        self.assertIn("max 22 mph, gear D", rows[0]["hint"])


class CheckTest(unittest.TestCase):
    def row(self, **kw):
        r = {c: "" for c in label_events.COLUMNS}
        r.update(id="1", status="yes", source="prefill", type="turn", t_start="10", t_end="12", side="left",
                 detail="blinker")
        r.update(kw)
        return r

    def test_valid_rows(self):
        self.assertEqual(label_events.check_rows([self.row(), self.row(id="2", type="stop_sign", side="",
                                                                       detail="rolling_stop", confidence="unsure")]), [])

    def test_unreviewed_and_rejected_rows_are_not_checked_further(self):
        self.assertEqual(label_events.check_rows([self.row(status="no", type="whatever"), self.row(id="2", status="?")]), [])

    def test_problems(self):
        problems = label_events.check_rows([
            self.row(type="turnn"),
            self.row(id="2", side=""),
            self.row(id="3", detail="full_stop"),
            self.row(id="4", t_end="9"),
            self.row(id="5", type="stop_sign", side="left", detail="full_stop"),
            self.row(id="5", status="maybe", source="me"),
        ])
        text = "\n".join(problems)
        for needle in ("is not one of", "needs side", "detail for turn", "t_end before", "has no side",
                       "duplicate id", "status must be", "source must be"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
