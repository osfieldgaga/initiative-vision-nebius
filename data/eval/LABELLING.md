# Labelling driving events (ground truth)

The scenario-mining evaluation compares what the rules and the agent find against what really
happened in the drive. "What really happened" is this file: `events_gt_20261022T164127Z-084b.csv`.
Budget: about 1.5 h, 2 h at most.

## Setup

```bash
.venv/bin/python src/scripts/virtual_pi.py test_sessions/private-640/20261022T164127Z-084b --no-upload
.venv/bin/python src/scripts/virtual_pi.py test_sessions/private-640/20261022T164127Z-084b --no-upload --start 165 --speed 0.5
```

- The overlay's **`drive 171.3s`** is the clock to use for every time in the file (same clock as the pipeline).
- Keys: space pause, a / d jump 10 s, click the timeline to seek, q quit. `--start` opens at a time,
  `--speed 0.5` plays at half speed.
- The CAN panel shows speed, steering, gear and the blinker arrows: use them.
- Open the CSV in LibreOffice Calc (keep **CSV format**, comma separator, when saving) or a text editor.
- Use only the virtual Pi (raw camera + CAN) while labelling, not the overlay videos or the results page, so the
  pipeline's output can't steer your answers.

## Steps

1. **Watch the whole drive once at normal speed** (8 min) with the CSV open. Note anything that happens that
   isn't in the list.
2. **Go through the rows in order.** Jump to `t_start` (seek, or restart with `--start`), watch, then set:
   - `status`: `yes` = this event happened, `no` = it didn't (or it's a duplicate, or parking-lot manoeuvring).
   - For `yes`: fix `type`, `t_start`, `t_end`, `side`, `detail` to what really happened (the pre-filled values
     are guesses), and optionally `confidence` = `sure` / `unsure`.
   - `hint` is why the row was suggested. Leave it as is. `notes` is free text.
3. **Add every event the list missed** as a new row: next free `id`, `status` = `yes`, `source` = `added`.
4. **Check the file:** `.venv/bin/python src/scripts/label_events.py check data/eval/events_gt_20261022T164127Z-084b.csv`.
   It prints problems by line, then `OK`.

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
