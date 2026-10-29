# Devpost submission text (draft)

**Project name:** Initiative Vision: verified driving scenarios from a real car
**Track:** Physical AI
**Tagline (one line):** An agent on Nebius Token Factory turns a real car's camera and CAN log into verified,
traceable driving events and MATLAB test scenarios.

**Links**
- Code: https://github.com/osfieldgaga/initiative-vision-nebius (MIT)
- Video: https://youtu.be/PSb4bcy_xpE
- Technical report: https://github.com/osfieldgaga/initiative-vision-nebius/blob/main/docs/nebius-technical-report.pdf
- Built on (OpenCV AI Competition 2026 entry): https://github.com/osfieldgaga/initiative-vision-aws

**Built with:** Nebius Token Factory, NVIDIA Nemotron 3 Super, NVIDIA Nemotron 3.5 Super VL, OpenCV 5, YOLOPv2,
Python, MATLAB Automated Driving Toolbox, Raspberry Pi, CAN bus

---

## Inspiration

Engineers who test driver-assistance software need lists of real moments: "rolled through the stop sign",
"turned left without a blinker". Today someone scrubs through hours of video to find them. I already had a
Raspberry Pi in my car recording the camera and the CAN bus, and an OpenCV pipeline that finds lanes and stop
signs. The question for this hackathon: can an agent go through a recorded drive and produce those events, in a
way an engineer could actually trust?

"Trust" became the design rule: every event the agent outputs must be traceable to the exact frames and CAN
samples behind it, with an evaluation showing how often it is right.

## What it does

1. **OpenCV** (my existing pipeline, unchanged) finds the lanes, the car's position in its lane and stop signs in
   each frame of a recorded drive, and each frame is joined with the car's CAN state at that instant: speed,
   steering, yaw rate, blinker, brake, gear.
2. **Simple rules** propose moments worth a look: stops, stop signs, turns, curves, lane departures. They are
   tuned to miss nothing, so they over-detect: 37 candidates on a 7.7-minute drive.
3. **An agent on Nebius Token Factory** reviews each candidate in its own short conversation with
   **Nemotron 3 Super**. It reads the data around the moment, can ask **Nemotron 3.5 Super VL** about specific
   frames ("is there a stop sign in frame 4507?"), can re-run the OpenCV pipeline at full frame rate, and then
   confirms, corrects or rejects the event, citing the samples that prove it.
4. **A validator** (plain code) checks every citation against the source data and recomputes the key facts
   from the full-rate CAN log: was it a full or rolling stop, was the blinker on before the turn, which way did
   the car steer. A stop sign or lane departure can only be confirmed after the agent has looked at the frames.
   If anything is wrong, the errors go back to the model to fix; after 4 tries the candidate is marked
   unverified. Nothing reaches the output on the model's word alone.
5. **Every model call is recorded**, so anyone can replay the whole run without an API key, and the replay fails
   loudly if anything differs from the recording.
6. **Evaluation:** I labelled the drive by hand with a labelling tool I built for it, and a scorer compares the
   rules and the agent with my labels.
7. **MATLAB:** events that both the agent and my labels confirm become `drivingScenario` files that replay the
   car's real speed and path, plus one file with the whole drive. A script runs them all in MATLAB and checks
   they match the CAN data.

## How I built it

- **Data:** one real drive (Oct 22, 2026), 6998 frames at 15 fps plus the CAN log, recorded by a Raspberry Pi 3B in
  my car. The shared copy is privacy-processed (faces and plates blurred, no GPS, no VIN).
- **Vision:** `lld.py` and `signs.py` from my OpenCV entry, imported unchanged (YOLOPv2 on `cv.dnn`, bird's-eye
  lane geometry, a classical stop-sign reader with OCR).
- **Agent:** Python, no framework. Four tools (`get_window`, `look_at_frames`, `rerun_vision`, `emit_event`), one
  conversation per candidate, temperature 0. Nemotron 3 Super handles the reasoning and tool calls; Nemotron VL
  only answers questions about frames, with thinking off.
- **Token Factory client:** about 150 lines of standard-library Python on the OpenAI-compatible API, with
  recording, replay (requests matched by SHA-256) and a spend cap. A full run over the drive is 127 calls and
  about $0.17.
- **Validator:** checks claim values within tolerances (0.6 mph, 2 degrees of steering), requires `frame_check`
  claims to quote a real VL answer about that frame, recomputes stop, blinker and side details from the raw CAN
  log.
- **Evaluation:** a pre-filled label list from CAN, a labelling window (the virtual Pi from my OpenCV entry plus a
  panel that edits the CSV), written event definitions that the agent reads too, and a one-to-one scorer.
- **MATLAB:** ego speed from the wheel-speed signal, path integrated from the yaw rate (calibrated against the
  original drive's GPS, offline), road along the path. `verify_matlab.py` simulates every file and compares it
  with the CAN data.

## Results (one drive, 15 labelled events)

| | flagged | right | precision | found of 15 | recall |
|---|---|---|---|---|---|
| Rules alone | 37 | 12 | 0.32 | 12 | 0.80 |
| Rules + agent, final run | 21 | 9 | 0.43 | 9 | 0.60 |
| Rules + agent, 4 runs (final code) | 20-25 | 9-10 | 0.36-0.48 | 9-10 | 0.60-0.67 |

The agent cuts the rules' false alarms roughly in half and every event it keeps carries validated evidence, but
it also drops some real events. The 8 events that the agent and my labels agree on became MATLAB scenarios; all
8, and the whole drive, replay the CAN speed within 0.05 m/s in MATLAB.

## Challenges I ran into

- **The car's own signals lie a little.** The `Standstill` flag was on at a stop sign while the car was still
  rolling at 1.2 mph, so a rolling stop looked like a full stop. Stop details now come from wheel speed. The yaw
  rate had no documented unit; I calibrated it against GPS.
- **Models state plausible things that aren't in the data.** The validator caught wrong values and frames with no
  data, and refused a "stop sign" the model hadn't looked at, which turned out to be red autumn leaves. In the walkthrough in the report, the model claims
  the car had started moving at a frame where the data says it was still stopped, gets the error back, and fixes
  it.
- **The VL model is a reliable confirmer but a weak denier.** On 95 hand-labelled frames, when it said "lane
  lines visible" it was always right, but it missed three quarters of them. The agent still sometimes trusts its
  "no" too much: a real turn into a parking entrance was rejected because "no intersection is visible".
- **Run-to-run variation.** Even at temperature 0, only 20 of 37 candidates got the same decision in all 4 runs of
  the final code. I report the spread (precision 0.36-0.48) and the run I named final in advance, not the best run.
- **Honest evaluation with one drive.** I fixed only what I had planned before labelling, so the score isn't tuned
  on the answers. I also found my own labels contradicted my written definitions (parking-lot moves) and fixed
  them before the final scoring.

## Accomplishments that I'm proud of

- Every number and citation in the output can be traced to a frame file and a CAN row, and a replay proves the
  run is genuine.
- An evaluation that reports where it fails (with the frames) instead of only where it works.
- MATLAB scenarios that come from a real car and are checked in MATLAB, not just generated.

## What I learned

- Let rules find and the model judge; never let the model compute what code can compute.
- Put checks in code, not in the prompt: the model skipped a visual check the prompt asked for, until the
  validator required it.
- Measure the tools you give an agent; the VL model's weaknesses explained most of the agent's mistakes.

## What's next for it

- More drives, and fixing the two failure modes on one drive while scoring on another.
- A general road-object detector on every frame (pedestrians, traffic lights, vehicles, signs), in OpenCV with a
  permissive license (e.g. the OpenCV model zoo's YOLOX or NanoDet on `cv.dnn`): new event types such as running a
  red light or yielding to a pedestrian, a trained stop-sign check (it would have removed the red-leaves false alarm),
  parked-car density as a hint that the car is in a parking lot (the biggest source of false alarms), and other road
  users as actors in the MATLAB scenarios. Scored on a new labelled drive, not this one.
- Running the batch steps as a Nebius Serverless Job over a fleet of drives.

## What was significantly updated during the hackathon

The project builds on my OpenCV AI Competition 2026 entry (a Pi in the car streams frames to AWS, where OpenCV
finds lanes, vehicles and signs live). That entry is unchanged and is being judged separately. Everything below
was written during this hackathon, in a new repository:

- The offline pipeline over a recorded drive: vision batch, CAN fusion, rule candidates.
- The agent on Nebius Token Factory with Nemotron 3 Super and Nemotron VL, its tools and the validator.
- Record and replay of every model call, and the spend cap.
- The labelling tool, the hand labels, the scorer and the evaluation (including run-to-run noise and how far the VL
  model can be trusted).
- The MATLAB scenario export, its check in MATLAB, and the yaw-rate calibration it needed.

Reused unchanged: `lld.py` and `signs.py` (the OpenCV vision) and the recorded drive.

## Feedback on Nebius Token Factory (for the organisers)

- **Worked well:** the OpenAI-compatible API meant a 150-line client with no SDK; tool calling with Nemotron 3
  Super was reliable across hundreds of calls; per-call `usage` made an exact spend cap easy.
- **Would help:** published per-token prices for the VL model (I had to assume a high price for the cap); a note
  in the VL model's docs that `chat_template_kwargs: {"enable_thinking": false}` is needed for short answers
  (without it the model spent the whole token budget reasoning); a note on how deterministic
  temperature 0 is (and whether a seed is honoured), since repeat runs differed.
