"""Tests for src/scripts/agent.py (the validator) and src/scripts/tokenfactory.py (record / replay). No network."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import agent  # noqa: E402
import tokenfactory as tf  # noqa: E402

DRIVE = ROOT / "test_sessions" / "private-640" / "20261022T164127Z-084b"
RUN = ROOT / "runs" / DRIVE.name


def answer(text):
    return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 1000, "completion_tokens": 100}}


class ClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "t.json"

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, bodies, meter=None):
        client = tf.Client(self.path, meter=meter)
        client._post = lambda body: answer(body["messages"][0]["content"].upper())
        return [client.chat(b) for b in bodies]

    def test_replay_returns_the_recorded_answers(self):
        bodies = [{"model": tf.SUPER, "messages": [{"role": "user", "content": m}]} for m in ("a", "b")]
        live = self.record(bodies)
        replay = tf.Client(self.path, replay=True)
        self.assertEqual([replay.chat(b) for b in bodies], live)

    def test_replay_stops_when_the_request_changed(self):
        self.record([{"model": tf.SUPER, "messages": [{"role": "user", "content": "a"}]}])
        replay = tf.Client(self.path, replay=True)
        with self.assertRaises(tf.ReplayMismatch):
            replay.chat({"model": tf.SUPER, "messages": [{"role": "user", "content": "changed"}]})

    def test_replay_allows_other_image_bytes_but_not_other_text(self):
        img = lambda data, text="is there a stop sign?": {"model": tf.VL, "messages": [{"role": "user", "content": [  # noqa: E731
            {"type": "text", "text": text}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}]}]}
        client = tf.Client(self.path)
        client._post = lambda body: answer("No.")
        client.chat(img("AAAA"))
        client.chat(img("AAAA"))
        replay = tf.Client(self.path, replay=True)
        replay.chat(img("BBBB"))  # same frame, encoded by another OpenCV build
        self.assertEqual(replay.image_mismatches, 1)
        with self.assertRaises(tf.ReplayMismatch):
            replay.chat(img("AAAA", text="is there a yield sign?"))

    def test_images_are_not_stored_but_are_hashed(self):
        body = {"model": tf.VL, "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}}]}]}
        stored = tf.summary(body)["messages"][0]["content"][0]
        self.assertNotIn("image_url", stored)
        self.assertEqual(len(stored["sha256"]), 64)

    def test_budget(self):
        meter = tf.Meter(max_usd=0.0004)  # one call = 1000 * 0.30e-6 + 100 * 0.90e-6 = $0.00039
        self.record([{"model": tf.SUPER, "messages": [{"role": "user", "content": "a"}]}], meter)
        with self.assertRaises(tf.BudgetExceeded):
            self.record([{"model": tf.SUPER, "messages": [{"role": "user", "content": "b"}]}] * 2, meter)


class TableTest(unittest.TestCase):
    def test_norm(self):
        self.assertEqual([agent.norm(x) for x in ("null", " Left ", "true", 3.5, None)], [None, "left", True, 3.5, None])


@unittest.skipUnless((RUN / "timeline.jsonl").exists() and (DRIVE / "decoded.csv").exists(),
                     "needs the 2026-10-22 drive and its timeline (vision_batch.py, fuse.py)")
class ValidateTest(unittest.TestCase):
    """The validator against the real drive: the claims and details below were checked by hand."""

    @classmethod
    def setUpClass(cls):
        cls.sess = agent.Session(DRIVE, RUN)

    def stop(self, **kw):
        ev = {"verdict": "confirmed", "type": "stop_sign", "t_start": 170.7, "t_end": 176.1, "side": "",
              "detail": "rolling_stop", "reason": "",
              "claims": [{"seq": 2720, "field": "mph", "value": "1.1"},
                         {"seq": 2652, "field": "vision_stop_sign", "value": "true"},
                         {"seq": 2652, "field": "frame_check", "value": "yes"}]}
        ev.update(kw)
        return ev

    def test_true_event_passes(self):
        self.assertEqual(agent.validate(self.stop(), self.sess, {(2652,): "Yes."}), [])

    def test_claims_must_match_the_data(self):
        errors = agent.validate(self.stop(claims=[{"seq": 2720, "field": "mph", "value": "0.0"},
                                                  {"seq": 99999, "field": "mph", "value": "1"}]), self.sess)
        self.assertTrue(any("mph is 1.1 in the data" in e for e in errors))
        self.assertTrue(any("no data for that frame" in e for e in errors))

    def test_stop_detail_comes_from_the_can_log(self):
        # the Standstill flag was on here, but the car never stopped (slowest 0.54 m/s = 1.2 mph)
        errors = agent.validate(self.stop(detail="full_stop"), self.sess, {(2652,): "Yes."})
        self.assertEqual(errors, ["slowest speed in 170.7-176.1 s is 1.2 mph (CAN log), so detail is rolling_stop"])

    def test_vision_events_need_a_look_and_a_real_quote(self):
        no_quote = self.stop(claims=self.stop()["claims"][:2])
        self.assertIn("look_at_frames at frames of this event first", agent.validate(no_quote, self.sess, {})[0])
        errors = agent.validate(self.stop(), self.sess, {(2652,): "No."})
        self.assertTrue(any("frame_check must quote" in e for e in errors))

    def test_frame_check_quotes_the_answer_about_that_frame(self):
        both = {(2652, 2660): "Frame 2652: Yes, a stop sign on the right.\nFrame 2660: No sign visible."}
        self.assertEqual(agent.validate(self.stop(), self.sess, both), [])
        wrong = self.stop(claims=self.stop()["claims"][:2] + [{"seq": 2652, "field": "frame_check", "value": "No sign"}])
        self.assertTrue(any("frame_check must quote" in e for e in agent.validate(wrong, self.sess, both)))

    def test_turn_blinker_and_side(self):
        turn = {"verdict": "confirmed", "type": "turn", "t_start": 93.25, "t_end": 98.0, "side": "left",
                "detail": "blinker", "reason": "", "claims": [{"seq": 1451, "field": "steer", "value": "90.1"}]}
        self.assertEqual(agent.validate(turn, self.sess), [])
        self.assertIn("so detail is blinker", agent.validate({**turn, "detail": "no_blinker"}, self.sess)[0])
        self.assertIn("never reaches 45 deg to the right",
                      agent.validate({**turn, "side": "right", "detail": "no_blinker"}, self.sess)[0])

    def test_claim_count(self):
        many = [{"seq": 2720, "field": "mph", "value": "1.1"}] * (agent.MAX_CLAIMS + 1)
        self.assertTrue(any("(you gave 7)" in e for e in agent.validate(self.stop(claims=many), self.sess)))

    def test_rejection_only_needs_true_claims(self):
        ev = self.stop(verdict="rejected", detail="whatever", t_start=251.4, t_end=257.4,
                       claims=[{"seq": 3856, "field": "mph", "value": "13.1"}])
        self.assertEqual(agent.validate(ev, self.sess, {}), [])

    def test_table_has_the_view_values(self):
        t = agent.table([self.sess.rows[2720]])
        self.assertEqual(dict(zip(t["columns"], t["rows"][0]))["mph"], 1.1)


if __name__ == "__main__":
    unittest.main()
