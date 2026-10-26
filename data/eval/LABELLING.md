# Labelling driving events (ground truth)

The scenario-mining evaluation compares what the rules and the agent find against what really
happened in the drive. "What really happened" is this file: `events_gt_20261022T164127Z-084b.csv`.
Budget: about 1.5 h, 2 h at most.

## Setup

```bash
.venv/bin/python src/scripts/label_tool.py test_sessions/private-640/20261022T164127Z-084b
.venv/bin/python src/scripts/label_tool.py test_sessions/private-640/20261022T164127Z-084b --start 165 --speed 0.5
```

The label tool is the virtual Pi (camera, CAN panel, timeline) with a label panel on the right, reading
and writing the CSV directly. What it labels comes from `data/eval/schemas/driving_events.json`.

- The overlay's **`drive 171.3s`** is the clock for every time (same clock as the pipeline).
- The panel shows the row whose time span holds the current moment, pre-filled from the CSV (Tab if
  several). Click an option to change it, `= now` (or `s` / `e`) to set start / end to the current
  frame, then **Save (Enter)**: it writes the CSV at once (a `.bak` of the file is kept on the first save).
- Keys: space pause, a / d jump 10 s, `,` / `.` one frame back / forward, `[` / `]` slower / faster,
  n new row, r revert, q quit. Click the timeline to seek. The marks under it are the rows:
  amber = still `?`, grey = `no`, coloured by type = `yes`.
- Use only the tool (raw camera + CAN) while labelling, not the overlay videos or the results page, so the
  pipeline's output can't steer your answers.

## Steps

1. **Watch the whole drive once at normal speed** (8 min). Pause on anything the list doesn't have
   (no row in the panel) and press n to add it right away.
2. **Go through the rows in order** (the amber marks): for each, check it at half speed, then set:
   - `status`: `yes` = this event happened, `no` = it didn't (or it's a duplicate, or parking-lot manoeuvring).
   - For `yes`: fix `type`, start / end, `side`, `detail` to what really happened (the pre-filled values
     are guesses), and optionally `confidence` = `sure` / `unsure`.
   - `hint` (shown under the times) is why the row was suggested. `notes` is free text.
   - Save.
3. **Check the file:** `.venv/bin/python src/scripts/label_events.py check data/eval/events_gt_20261022T164127Z-084b.csv`.
   It prints problems by line, then `OK` (the tool already refuses to save a row that fails it).

A new drive: run `vision_batch.py`, `fuse.py` and `label_events.py prefill` on it for a pre-filled list,
or open it in the label tool straight away and add every event by hand (the CSV is created on the first save).

## Event definitions

Only label **driving on roads**. Anything inside a parking lot or driveway (slow manoeuvring, reversing,
parked) is `no`. Turning from the road into a parking lot, or out of it onto the road, is a `turn`.

| type | what | t_start → t_end | side | detail |
|---|---|---|---|---|
| `stop_sign` | approaching a stop sign | first moment the sign is readable on screen → car moving again past the line | (empty) | `full_stop` (speed reached 0), `rolling_stop` (slowed, never 0), `no_stop` |
| `other_stop` | stopping for anything else: traffic, light, pedestrian, yielding | start of braking for it → moving again | (empty) | (empty) |
| `turn` | changing road at an intersection, or road ↔ driveway / parking entrance | steering starts → wheel straight on the new road | `left` / `right` | `blinker` (on before steering started), `late_blinker` (only after), `no_blinker` |
| `lane_change` | moving to the next lane on the same road | starts drifting → settled in the new lane | `left` / `right` | as for `turn` |
| `curve` | the road bends and you follow it (no intersection), clearly noticeable | steering starts → straight again | `left` / `right` | (empty) |
| `lane_departure` | a wheel touches or crosses a lane line or the road edge **without** meaning to change lane | wheel reaches the line → back in the lane | `left` / `right` | (empty) |

Tricky cases:

- **No line visible** (unmarked residential road): it can't be a `lane_departure`, mark `no`. The vision-flagged
  departure rows are often false alarms of exactly this kind.
- **Two rows, one event** (e.g. two short "turn" rows inside one real turn): one `yes` with the full times, the
  other `no` with notes `dup of <id>`.
- **One row, two events**: fix the row for the first, add a row (`source` = `added`) for the second.
- **Stop sign + turn** at the same intersection: two events, a `stop_sign` and a `turn`.
- **Times** within about 0.5 s are fine: events are matched by overlapping time, not exact values.
- **Can't tell from the video**: label your best guess with `confidence` = `unsure`. The evaluation reports
  results with and without unsure rows.

## When done

Run the check, then commit the CSV. The pre-filled version is in git history, so the evaluation can also report
how many events the pre-fill missed (`source` = `added`).

Regenerating the pre-fill (it refuses to overwrite a labelled file):
`.venv/bin/python src/scripts/label_events.py prefill test_sessions/private-640/20261022T164127Z-084b`
