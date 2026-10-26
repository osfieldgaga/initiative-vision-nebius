"""Tests for src/scripts/candidates.py (rule candidates) and src/scripts/score.py (scoring them)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
sys.path.insert(0, str(ROOT / "src" / "tests"))
import candidates  # noqa: E402
import score  # noqa: E402
from test_label_events import timeline  # noqa: E402

STOP = {"type": "stop", "value": None, "score": 0.5, "text": "stop", "box": [0, 0, 1, 1]}


def with_seq_and_rows(rows):
    for k, r in enumerate(rows):
        r["seq"] = k * 5
        r["can"]["row_ts_ns"] = 1000 + k
    return rows


class CandidatesTest(unittest.TestCase):
    def detect(self, at, n=30):
        return candidates.detect(with_seq_and_rows(timeline(n, at)))

    def test_stop_sign_detail_from_wheel_speed_not_the_flag(self):
        full = self.detect({3: {"signs": [STOP]}, 6: {"standstill": True, "speed_mps": 0.0}})
        rolling = self.detect({3: {"signs": [STOP]}, 6: {"standstill": True, "speed_mps": 0.5}})
        self.assertEqual([(c["type"], c["detail"]) for c in full], [("stop_sign", "full_stop")])
        self.assertEqual([(c["type"], c["detail"]) for c in rolling], [("stop_sign", "rolling_stop")])

    def test_stop_sign_without_standstill(self):
        rolling = self.detect({3: {"signs": [STOP]}, 5: {"speed_mps": 1.5}})
        ignored = self.detect({3: {"signs": [STOP]}})
        self.assertEqual([(c["type"], c["detail"]) for c in rolling], [("stop_sign", "rolling_stop")])
        self.assertEqual([(c["type"], c["detail"]) for c in ignored], [("stop_sign", "no_stop")])
        self.assertEqual(rolling[0]["evidence"]["key_seqs"], [15])

    def test_evidence_cites_frames_and_can_rows(self):
        [c] = self.detect({4: {"steering_deg": 150.0}, 5: {"steering_deg": 200.0}, 6: {"steering_deg": 120.0}})
        self.assertEqual((c["id"], c["type"], c["side"], c["detail"]), ("c01", "turn", "left", "no_blinker"))
        ev = c["evidence"]
        self.assertEqual(ev["seqs"], [20, 30])
        self.assertEqual(ev["key_seqs"], [25])  # peak steering
        self.assertEqual(ev["can_rows"], [1004, 1005, 1006])
        self.assertEqual(ev["stats"]["max_left_steer_deg"], 200.0)
        self.assertEqual(ev["stats"]["gear"], ["D"])


def ev(typ, t0, t1, side="", detail="", **kw):
    return {"type": typ, "t_start": t0, "t_end": t1, "side": side, "detail": detail, **kw}


def gt_row(id, typ, t0, t1, side="", detail="", source="prefill"):
    return {**ev(typ, t0, t1, side, detail), "id": id, "source": source}


class ScoreTest(unittest.TestCase):
    def test_match_needs_type_side_and_overlap(self):
        gt = [gt_row("1", "turn", 10, 12, "left", "blinker")]
        self.assertEqual(score.match([ev("turn", 12.5, 14, "left")], gt), [(0, 0)])  # within the 1 s pad
        self.assertEqual(score.match([ev("turn", 14.5, 16, "left")], gt), [])
        self.assertEqual(score.match([ev("turn", 10, 12, "right")], gt), [])
        self.assertEqual(score.match([ev("curve", 10, 12, "left")], gt), [])

    def test_one_to_one_largest_overlap_first(self):
        gt = [gt_row("1", "other_stop", 10, 20), gt_row("2", "other_stop", 21, 30)]
        self.assertEqual(score.match([ev("other_stop", 18, 29)], gt), [(0, 1)])

    def test_counts_detail_and_rejected(self):
        gt = [gt_row("1", "stop_sign", 10, 15, detail="rolling_stop"), gt_row("2", "turn", 30, 33, "left", "blinker"),
              gt_row("3", "curve", 50, 54, "right", source="added")]
        pred = [ev("stop_sign", 10, 16, detail="full_stop", id="c1"), ev("turn", 30, 32, "left", "blinker", id="c2"),
                ev("lane_departure", 40, 41, "left", id="c3"), ev("curve", 70, 72, "left", id="c4", verdict="rejected")]
        r = score.score(pred, score.ground_truth([{**g, "status": "yes", "confidence": "", "t_start": str(g["t_start"]),
                                                   "t_end": str(g["t_end"])} for g in gt]))
        self.assertEqual({k: r["overall"][k] for k in ("tp", "fp", "fn")}, {"tp": 2, "fp": 1, "fn": 1})
        self.assertEqual(r["overall"]["detail_accuracy"], 0.5)
        self.assertEqual(r["per_type"]["stop_sign"]["detail_accuracy"], 0.0)
        self.assertEqual(r["recall_on_added"], 0.0)
        self.assertEqual([m["pred"] for m in r["matches"]], ["c1", "c2"])
        self.assertEqual(r["false_positives"], [{"pred": "c3", "type": "lane_departure", "t_start": 40}])
        self.assertIn("overall", score.table(r))

    def test_sure_only_and_unreviewed(self):
        rows = [{"id": "1", "status": "yes", "source": "prefill", "type": "curve", "t_start": "1", "t_end": "2",
                 "side": "left", "detail": "", "confidence": "unsure"},
                {"id": "2", "status": "?", "source": "prefill", "type": "curve", "t_start": "1", "t_end": "2",
                 "side": "left", "detail": "", "confidence": ""}]
        self.assertEqual(len(score.ground_truth(rows)), 1)
        self.assertEqual(score.ground_truth(rows, sure_only=True), [])


if __name__ == "__main__":
    unittest.main()
