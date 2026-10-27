"""Tests for src/scripts/score_runs.py: scores and agreement over several runs."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import score_runs  # noqa: E402


def ev(cid, verdict, typ="turn", side="left", t0=10.0):
    return {"id": cid, "verdict": verdict, "type": typ, "side": side, "detail": "", "t_start": t0, "t_end": t0 + 3}


class SummarizeTest(unittest.TestCase):
    def test_ranges_and_agreement(self):
        gt = [{"id": "1", "type": "turn", "side": "left", "detail": "", "t_start": 10.0, "t_end": 13.0, "source": "prefill"}]
        runs = {"a": [ev("c1", "confirmed"), ev("c2", "confirmed", t0=50)],
                "b": [ev("c1", "confirmed"), ev("c2", "rejected", t0=50)]}
        r = score_runs.summarize(runs, gt)
        self.assertEqual(r["runs"]["a"]["precision"], 0.5)
        self.assertEqual(r["runs"]["b"]["precision"], 1.0)
        self.assertEqual(r["range"]["precision"], [0.5, 1.0])
        self.assertEqual((r["unanimous"], r["candidates"]), (1, 2))
        self.assertEqual(r["agreement"]["c2"]["votes"], {"turn left": 1, "rejected": 1})


if __name__ == "__main__":
    unittest.main()
