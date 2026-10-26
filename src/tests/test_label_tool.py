"""Tests for src/scripts/label_tool.py: schema, pre-filled rows, editing rules and saving (no window)."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import label_tool as lt  # noqa: E402

SCHEMA = ROOT / "data" / "eval" / "schemas" / "driving_events.json"
HEADER = "id,status,source,type,t_start,t_end,side,detail,confidence,hint,notes,extra\n"


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "gt.csv"
        self.path.write_text(HEADER +
                             "1,?,prefill,turn,10.0,14.0,left,blinker,,steering past 90 deg,,x1\n"
                             "2,?,prefill,curve,12.0,13.0,right,,,,,x2\n"
                             "7,no,prefill,other_stop,30.0,35.0,,,,,,x3\n")
        self.schema = lt.Schema.load(SCHEMA)
        self.store = lt.Store(self.schema, self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self):
        with open(self.path, newline="") as f:
            return list(csv.DictReader(f))

    def test_rows_at_a_time(self):
        self.assertEqual([r["id"] for r in self.store.covering(12.5)], ["1", "2"])
        self.assertEqual(self.store.covering(20), [])
        self.assertEqual([r["id"] for r in self.store.nearest(29, n=2)], ["7", "2"])

    def test_dependent_options(self):
        row = dict(self.store.rows[0])
        self.store.set(row, "type", "stop_sign")
        self.assertEqual((row["side"], row["detail"]), ("", "full_stop"))  # stop signs have no side
        self.store.set(row, "type", "lane_change")
        self.assertEqual((row["side"], row["detail"]), ("left", "blinker"))

    def test_save_edits_one_row_and_keeps_the_rest(self):
        row = dict(self.store.rows[0])
        self.store.set(row, "status", "yes")
        self.store.set(row, "detail", "late_blinker")
        self.assertEqual(self.store.save(row), [])
        rows = self.read()
        self.assertEqual([r["id"] for r in rows], ["1", "2", "7"])
        self.assertEqual((rows[0]["status"], rows[0]["detail"], rows[0]["hint"], rows[0]["extra"]),
                         ("yes", "late_blinker", "steering past 90 deg", "x1"))  # untouched columns kept
        self.assertEqual(rows[1], {**rows[1], "status": "?", "extra": "x2"})
        self.assertTrue(self.path.with_suffix(".csv.bak").exists())

    def test_new_row(self):
        row = self.store.new(42.34)
        self.assertEqual((row["id"], row["status"], row["source"], row["t_start"], row["t_end"]),
                         ("8", "yes", "added", "42.3", "42.3"))
        row["t_end"] = "45.0"
        self.store.set(row, "type", "curve")
        self.assertEqual(self.store.save(row), [])
        self.assertEqual(self.read()[-1]["type"], "curve")

    def test_save_refuses_bad_rows(self):
        row = dict(self.store.rows[0], status="yes", t_end="9.0")
        self.assertIn("end is before start", self.store.save(row))
        self.assertEqual(self.read()[0]["t_end"], "14.0")  # file unchanged

    def test_label_events_check_runs(self):
        row = dict(self.store.rows[0], status="yes", side="")  # bypassing set(): a turn needs a side
        self.assertTrue(any("needs side" in p for p in self.store.problems(row)))

    def test_new_file(self):
        store = lt.Store(self.schema, Path(self.tmp.name) / "sub" / "new.csv")
        row = store.new(5.0)
        row["t_end"] = "6.0"
        self.assertEqual(store.save(row), [])
        self.assertEqual(len(store.rows), 1)

    def test_schema_from_another_task(self):
        spec = {"name": "weather", "columns": ["id", "from", "to", "sky"], "time_columns": ["from", "to"],
                "fields": [{"name": "sky", "options": ["sun", "rain"]}], "new_row": {}}
        path = Path(self.tmp.name) / "weather.csv"
        store = lt.Store(lt.Schema(spec), path)
        row = store.new(1.0)
        self.assertEqual(row["sky"], "sun")
        self.assertEqual(store.save(store.set(row, "sky", "rain")), [])
        self.assertEqual(path.read_text().splitlines(), ["id,from,to,sky", "1,1.0,1.0,rain"])

    def test_schema_field_must_be_a_column(self):
        with self.assertRaises(SystemExit):
            lt.Schema({"columns": ["id", "a", "b"], "time_columns": ["a", "b"], "fields": [{"name": "zzz", "text": True}]})


class UITest(unittest.TestCase):
    """Panel behaviour without a window: frames are just times."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "gt.csv"
        path.write_text(HEADER + "1,?,prefill,turn,10.0,14.0,left,blinker,,,,\n2,?,prefill,curve,12.0,13.0,right,,,,,\n")
        self.store = lt.Store(lt.Schema.load(SCHEMA), path)
        frames = [(k, None, k / 10) for k in range(300)]  # 30 s at 10 fps
        self.ui = lt.UI(self.store.schema, self.store, frames, 11.0)

    def tearDown(self):
        self.tmp.cleanup()

    def test_panel_follows_time_until_edited(self):
        self.assertEqual(self.ui.row["id"], "1")
        self.ui.seek(12.5)  # rows 1 and 2 both hold this time
        self.ui.key(9)  # Tab: the other row here
        self.assertEqual(self.ui.row["id"], "2")
        self.ui.act(("set", "status", "yes"))
        self.assertTrue(self.ui.paused and self.ui.dirty)
        self.ui.seek(25)
        self.assertEqual(self.ui.row["id"], "2")  # unsaved edits stay in the panel
        self.ui.act(("revert",))
        self.assertIsNone(self.ui.row)  # nothing at 25 s

    def test_keys_set_times_and_save(self):
        self.ui.seek(11.5)
        self.ui.key(ord("s"))
        self.ui.seek(13.9)
        self.ui.key(ord("e"))
        self.ui.act(("set", "status", "yes"))
        self.ui.key(13)  # Enter
        self.assertFalse(self.ui.dirty)
        saved = self.store.rows[0]
        self.assertEqual((saved["t_start"], saved["t_end"], saved["status"]), ("11.5", "13.9", "yes"))

    def test_typing_notes(self):
        self.ui.act(("type", "notes"))
        for ch in "dup of 2":
            self.ui.key(ord(ch))
        self.ui.key(8)  # backspace
        self.ui.key(13)  # leaves the field, doesn't save
        self.assertEqual(self.ui.row["notes"], "dup of ")
        self.assertTrue(self.ui.dirty)

    def test_quit_asks_twice_with_unsaved_edits(self):
        self.ui.act(("set", "status", "no"))
        self.assertTrue(self.ui.key(ord("q")))
        self.assertFalse(self.ui.key(ord("q")))

    def test_new_row_at_current_time(self):
        self.ui.seek(20.0)
        self.ui.key(ord("n"))
        self.assertEqual((self.ui.row["id"], self.ui.row["t_start"]), ("3", "20.0"))


if __name__ == "__main__":
    unittest.main()
