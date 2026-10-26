"""Tests for src/scripts/vision_batch.py: time-based sampling and resuming."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import vision_batch  # noqa: E402


def frames_at(times):
    return [(k, Path(f"frames/{k:08d}.jpg"), t) for k, t in enumerate(times)]


class SampleByTimeTest(unittest.TestCase):
    def test_first_frame_at_or_after_each_tick(self):
        # ~15 fps with jitter, 3 fps wanted: ticks at 0, 1/3, 2/3, 1
        times = [0.0, 0.07, 0.13, 0.2, 0.27, 0.33, 0.4, 0.47, 0.53, 0.6, 0.67, 0.73, 0.8, 0.87, 0.93, 1.0]
        picked = vision_batch.sample_by_time(frames_at(times), 3)
        self.assertEqual([times[i] for i in picked], [0.0, 0.4, 0.67, 1.0])

    def test_gap_gives_one_frame_not_duplicates(self):
        picked = vision_batch.sample_by_time(frames_at([0.0, 0.1, 2.05, 2.1, 2.4]), 3)
        self.assertEqual(picked, [0, 2, 4])

    def test_every_frame_when_fps_exceeds_recording(self):
        self.assertEqual(vision_batch.sample_by_time(frames_at([0.0, 0.5, 1.0]), 30), [0, 1, 2])


class HelpersTest(unittest.TestCase):
    def test_frames_named(self):
        frames = frames_at([0.0, 0.1, 0.2])
        self.assertEqual(vision_batch.frames_named(frames, ["00000002.jpg", "nope.jpg"]), [2])

    def test_read_done_drops_torn_last_line(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "vision.jsonl"
            out.write_text(json.dumps({"seq": 4}) + "\n" + json.dumps({"seq": 9}) + "\n" + '{"seq": 1')
            self.assertEqual(vision_batch.read_done(out), {4, 9})
            self.assertEqual(len(out.read_text().splitlines()), 2)

    def test_read_done_missing_file(self):
        self.assertEqual(vision_batch.read_done(Path("/nonexistent/vision.jsonl")), set())


if __name__ == "__main__":
    unittest.main()
