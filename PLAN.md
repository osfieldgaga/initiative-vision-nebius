# Nebius x NVIDIA hackathon plan (Physical AI track)

Deadline: Fri 2026-10-30 10:00 PT. Target: submitted Thu 10-29. Each step ends runnable and committed.

Goal: an agent on Nebius Token Factory (Nemotron) that turns a recorded drive (camera + CAN) into
verified driving events, each traceable to its frames and CAN samples, and exports them as MATLAB
`drivingScenario` test cases. The OpenCV pipeline (`lld.py`, `signs.py`) is reused unchanged.
The AWS pipeline is untouched; it stays the OpenCV competition entry (`upstream`).

| # | Step | Output | Done when | When |
|---|---|---|---|---|
| ✅ 0 | Setup: repo, license, Token Factory key, model spike | | done | Sun |
| ✅ 1 | Vision batch `src/scripts/vision_batch.py`: `lld.process_frame` over the drive at 3 fps | `runs/<session>/vision.jsonl` | lane_valid on the 95 labelled frames matches `lane_eval/results.json` | Sun |
| ✅ 2 | Fusion `src/scripts/fuse.py`: vision + CAN (speed, steering, yaw, blinker, standstill, brake) on timestamp | `timeline.jsonl` | tests: stopped at the known stop signs, blinker at known lane changes | Mon |
| 3 | Ground truth (2 h max): review `data/eval/events_gt_<session>.csv`, how-to in `data/eval/LABELLING.md` | labelled CSV | `label_events.py check` says OK | Mon |
| ✅ 4 | Rule candidates `src/scripts/candidates.py` (with evidence: seqs, CAN rows, stats); scorer `src/scripts/score.py` | `candidates.json` + baseline score vs ground truth | code done; score once labels are in | Sun |
| ✅ 5 | Agent `src/scripts/agent.py` (Nemotron 3 Super + tools + validator), client `tokenfactory.py` (record / `--replay`, spend cap) | `runs/<s>/agent/events.json` | every event passes the validator or is marked unverified; replay is identical (checked) | Sun |
| ✅ 6 | VL frame checks (`look_at_frames`), `rerun_vision` at 15 fps (1280 px originals aren't shareable); VL vs 95 lane labels `eval_vl_lanes.py` | rules vs rules + agent table | VL eval done; table once labels are in | Sun |
| 7 | MATLAB export, simplest `drivingScenario` per event | `scenarios/*.m` | one runs in MATLAB | Wed |
| 8 | Results page + Token Factory proxy with spend cap | demo URL | a judge can open it and re-run an event | Wed |
| | **Cut line: steps 1-8 = minimum submittable** | | | **end of Wed** |
| 9 | Optional: steps 1-6 as a Nebius Serverless Job | | | Wed if ahead |
| 10 | README, Devpost text, what's new, feedback, video < 3 min (>= 1 min of the car) | submitted | | Thu |
| | Stretch: end-of-drive report from validated events only | | | if ahead |

Models (checked live 2026-10-25): `nvidia/nemotron-3-super-120b-a12b` (tool calling works),
`nvidia/Nemotron-3.5-Super-VL` (images work; send `chat_template_kwargs: {"enable_thinking": false}`
or it spends the whole budget reasoning).

Evaluation caveat: the ground-truth list was pre-filled by the same rules, so the rules' recall is
inflated by construction. The honest numbers are precision (after the `no` rows), detail accuracy,
and recall on `source = added` rows, which the pre-fill missed.

CAN finding (2026-10-25): the car's `Standstill` flag is not "speed = 0". At the 171 s stop sign it
was on from 4.3 mph down to 1.1 mph and the car never stopped; every other standstill reads 0.0.
Stop details use wheel speed.

First full agent run (2026-10-26, ~$0.18, 133 calls): 37 candidates -> 16 confirmed, 4 corrected,
14 rejected, 3 unverified (validator refused every attempt; kept as the rules found them).
VL vs 95 hand-labelled lane frames (upright, undistorted): "both lines visible" precision 1.00,
recall 0.25; the OpenCV pipeline 0.98 / 0.73. VL is a reliable confirmer, a weak denier.

For the final run, after the labels are in (each change invalidates the recordings, so batch them):
- look_at_frames: ask the VL for one answer per frame (a single "Yes" for 4 frames is ambiguous).
- Validator error for too many claims: say how many were given; MAX_EMITS 3 -> 4.
- Lane departures were rejected on VL "no lines visible" despite the prompt warning: check against labels.
