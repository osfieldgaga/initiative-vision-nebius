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
| 4 | Rule candidates | `candidates.json` + baseline score vs ground truth | high recall | Tue |
| 5 | Agent v1 (Nemotron 3 Super + tools + validator, `--replay` from recorded responses) | `events.json` | every event passes the validator; replay is identical | Tue |
| 6 | Agent v2: VL frame checks (Nemotron 3.5 Super VL), re-run vision at 1280 px | rules vs rules + agent table | table exists | Tue-Wed |
| 7 | MATLAB export, simplest `drivingScenario` per event | `scenarios/*.m` | one runs in MATLAB | Wed |
| 8 | Results page + Token Factory proxy with spend cap | demo URL | a judge can open it and re-run an event | Wed |
| | **Cut line: steps 1-8 = minimum submittable** | | | **end of Wed** |
| 9 | Optional: steps 1-6 as a Nebius Serverless Job | | | Wed if ahead |
| 10 | README, Devpost text, what's new, feedback, video < 3 min (>= 1 min of the car) | submitted | | Thu |
| | Stretch: end-of-drive report from validated events only | | | if ahead |

Models (checked live 2026-10-25): `nvidia/nemotron-3-super-120b-a12b` (tool calling works),
`nvidia/Nemotron-3.5-Super-VL` (images work; send `chat_template_kwargs: {"enable_thinking": false}`
or it spends the whole budget reasoning).
