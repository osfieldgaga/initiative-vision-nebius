# Initiative Vision: verified driving scenarios from a real car

A camera and the CAN bus of a real car record a drive. OpenCV finds the lanes and the stop signs,
simple rules propose moments worth a look (stops, turns, curves, lane departures), and an agent on
**Nebius Token Factory** (NVIDIA **Nemotron 3 Super**, with **Nemotron VL** to look at frames) checks
each one against the data and confirms, corrects or rejects it. A validator checks every claim the
agent makes against the source frames and CAN samples, so nothing reaches the output on the model's
word alone. The events that the agent and a human labeller agree on become **MATLAB
`drivingScenario` test cases** that replay the car's real speed and path.

Entry for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com), Physical AI track.
Technical report: [docs/nebius-technical-report.pdf](docs/nebius-technical-report.pdf). Video: *link to come*.

> Not a safety system: it never controls the vehicle. The drive was recorded with a camera and a CAN
> logger on a Raspberry Pi in a normal car.

## Results on the shared drive (7.7 min, 15 hand-labelled events)

| | flagged | right | precision | found of 15 | recall |
|---|---|---|---|---|---|
| Rules alone | 37 | 12 | 0.32 | 12 | 0.80 |
| Rules + agent, final run | 21 | 9 | 0.43 | 9 | 0.60 |
| Rules + agent, 4 runs (final code) | 20-25 | 9-10 | 0.36-0.48 | 9-10 | 0.60-0.67 |

- **Precision** = how many of the events a method reports are real; **recall** = how many of the
  real events it finds. Matching: same type and side, overlapping time (±1 s), one to one.
- The agent cuts the rules' false alarms roughly in half, at the cost of some real events. Every event
  it keeps carries claims that a validator checked against the data; 0 of 37 candidates in the final
  run ended unverified.
- **MATLAB:** 8 scenarios (events the agent and the labels agree on) plus the whole drive; all 9
  replay the CAN speed within 0.05 m/s rms in MATLAB R2025a.
- Small numbers: one event moves recall by 7 points. Failure cases and limits are in the report.

## For judges: no car, no cloud account, no cost

Everything below runs on a laptop (Linux, macOS or Windows, Python 3.12 or 3.13). The agent's calls
to Token Factory were recorded, and `--replay` answers from those recordings, so it needs no API key.

1. **Get the code and the drive** (503 MB: 7.7 minutes, privacy-processed: faces and plates blurred,
   no GPS, no VIN; see `PRIVACY.md` inside):
   ```bash
   git clone https://github.com/osfieldgaga/initiative-vision-nebius.git && cd initiative-vision-nebius
   python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
   curl -L -O https://github.com/osfieldgaga/initiative-vision-aws/releases/download/v1.0/ivision-drive-20261022.zip
   python3 -m zipfile -e ivision-drive-20261022.zip test_sessions/
   D=test_sessions/20261022T164127Z-084b
   ```
2. **Replay the agent** over the 37 candidates (a few seconds). It rebuilds every request from the data and
   the code and checks it against the recording, then writes `runs/20261022T164127Z-084b/agent/events.json`;
   `git diff` shows it is identical to the committed run.
   ```bash
   .venv/bin/python src/scripts/agent.py $D --replay
   ```
3. **Score it** against the hand labels:
   ```bash
   .venv/bin/python src/scripts/score.py runs/20261022T164127Z-084b/agent/events.json data/eval/events_gt_20261022T164127Z-084b.csv
   ```
4. **Trace an event to its source.** In `events.json`, every claim names its frame file and CAN row,
   for example the full stop at the stop sign at 296 s (`c23`):
   ```json
   {"seq": 4592, "field": "mph", "value": "0.0", "frame": "00004592_4851274309000.jpg", "can_row": 4851272192169}
   ```
   The frame is in `$D/`, the CAN row is the `timestamp_ns` in `$D/decoded.csv`. The whole conversation
   with the model, tool calls included, is in `runs/20261022T164127Z-084b/agent/transcripts/c23.json`.
5. **Watch the drive with the labels** (optional): `.venv/bin/python src/scripts/label_tool.py $D`
   (space pause, a / d seek, q quit).
6. **MATLAB** (optional, needs the Automated Driving Toolbox): in `scenarios/20261022T164127Z-084b/`,
   run `full_drive` to play the whole drive or `ev_c23_stop_sign` for one event. `full_drive(4)`
   plays faster. Each file's header lists the event, the agent's verdict, the validated claims and the
   hand label that agrees.

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

### Live run with your own key (optional)

With a Token Factory key in `NEBIUS_API_KEY`, the agent calls the models for real. `--max-usd` stops it
past an estimated spend (a full run was about $0.17). `--agent-dir` keeps the committed run untouched:

```bash
export NEBIUS_API_KEY=...        # or put it on the first line of apikey.md (git-ignored)
.venv/bin/python src/scripts/agent.py $D --agent-dir runs/mine --max-usd 0.50
.venv/bin/python src/scripts/score.py runs/mine/events.json data/eval/events_gt_20261022T164127Z-084b.csv
```

Answers can differ from run to run, even at temperature 0 (measured above).

## How it works

```
Raspberry Pi in the car: camera (15 fps) + CAN logger
   │  recorded drive: frames + decoded.csv (speed, steering, yaw, blinker, brake, gear, standstill)
   ▼
1 vision_batch.py   OpenCV pipeline (lld.py, signs.py, unchanged from the OpenCV entry) at 3 fps
                    lanes, lane offset, departure, stop signs                       → vision.jsonl
2 fuse.py           each frame + the car's CAN state at that instant, with the CAN row → timeline.jsonl
3 candidates.py     rules propose moments (standstill, steering, blinker, signs, departures),
                    each with its evidence: frames, key frames, CAN rows, stats     → candidates.json
4 agent.py          one conversation per candidate with Nemotron 3 Super on Token Factory
                      tools: get_window (the data), look_at_frames (Nemotron VL), rerun_vision
                             (OpenCV at 15 fps), emit_event (the answer, with claims)
                      validator: every claim against the data; stop, blinker and side details
                             recomputed from the full CAN log; vision events need a frame check
                      errors go back to the model (4 tries), else "unverified"     → events.json
5 score.py          against hand labels (label_events.py, label_tool.py)
6 export_matlab.py  events the agent and the labels agree on → drivingScenario .m files
  verify_matlab.py  runs them in MATLAB and checks they replay the CAN data
```

Every Token Factory call goes through `tokenfactory.py`, which records the request's sha256 and the
full response. On replay, a request that differs from the recording stops the run (`ReplayMismatch`),
so a replay reproduces the recorded run or fails loudly. The one allowance: frame images are JPEGs
this code encodes, and another OpenCV build may produce different bytes for the same frame; if every
text in the request still matches, the call is replayed and counted.

## Repository layout

| Path | What |
|---|---|
| `src/scripts/vision_batch.py`, `fuse.py` | Steps 1-2: vision over a recorded drive, joined with CAN |
| `src/scripts/candidates.py` | Step 3: rule candidates with evidence |
| `src/scripts/agent.py`, `tokenfactory.py` | Step 4: the agent, its tools and validator; the recording Token Factory client |
| `src/scripts/score.py` | Step 5: precision, recall and detail accuracy against hand labels |
| `src/scripts/label_events.py`, `label_tool.py` | Pre-filled label list and format check; the labelling window |
| `src/scripts/export_matlab.py`, `verify_matlab.py` | Step 6: MATLAB scenarios and their check |
| `src/scripts/eval_vl_lanes.py` | How reliable the VL model is at seeing lane lines (95 labelled frames) |
| `data/eval/` | Hand labels, labelling guide (`LABELLING.md`), label schema |
| `runs/20261022T164127Z-084b/` | Every intermediate output of the shared drive, the agent's recordings, repeat runs |
| `scenarios/20261022T164127Z-084b/` | The MATLAB scenarios, `expected.json`, `verify.json` |
| `lld.py`, `signs.py` | The OpenCV perception pipeline, imported unchanged from the OpenCV entry |
| `lld_aws.py`, `live_view.py`, `src/lambda/`, `phase2/`, `infra/` | The live AWS pipeline of the OpenCV entry (history, not used here) |

`src/tests/` has the unit tests: `for t in src/tests/test_*.py; do .venv/bin/python -m unittest "$t"; done`.

## Built on the OpenCV entry

This project starts from [Initiative Vision](https://github.com/osfieldgaga/initiative-vision-aws), our
OpenCV AI Competition 2026 entry: a Pi in a car streams frames to AWS, where OpenCV 5 finds lanes,
vehicles and signs live. That entry stays as it was (it is being judged separately). New here, all
written during the hackathon:

- The offline pipeline over a recorded drive (vision batch, CAN fusion, rule candidates).
- The agent on Token Factory with Nemotron 3 Super and Nemotron VL, its tools and the validator.
- Record and replay of every model call, with a spend cap.
- Hand labels with a labelling tool, the scorer, and a measured evaluation (including run-to-run noise
  and how far the VL model can be trusted on lane lines).
- The MATLAB scenario export and its check in MATLAB, with the yaw-rate calibration it needed.

Reused unchanged: `lld.py` and `signs.py` (the OpenCV vision), the recorded drive and its privacy copy.

## Running the vision from scratch (optional)

The outputs of steps 1-3 are committed, so nothing above needs the vision models. To recompute them,
get the weights as in the OpenCV entry's README (YOLOPv2 converted to ONNX, the OpenCV zoo CRNN text
recognizer), then:

```bash
.venv/bin/python src/scripts/vision_batch.py $D --fps 3
.venv/bin/python src/scripts/fuse.py $D
.venv/bin/python src/scripts/candidates.py $D
```

## Privacy

The shared drive is a privacy copy: faces and plate areas blurred, GPS columns removed, and the raw
CAN log (which holds the VIN) left out. The yaw-rate calibration used the original drive's GPS on the
recording laptop only; just the two calibration numbers are published. Model calls send frames of the
privacy copy only.

## Limitations

- One drive, 15 labelled events: the numbers are indicative, not a benchmark.
- The agent's answers vary from run to run; it sometimes trusts a "no" from the VL model that it
  shouldn't (a turn rejected because "no intersection is visible" mid-turn), and once ignored one it
  should have heeded. Details in the report.
- Scenarios hold only the ego car: no other road users, signs or real lane geometry. The path comes
  from the yaw rate, so over a whole drive it drifts; it is right locally, not a map.
- Lane departures depend on vision that misses faded lines; both labelled departures were missed.
