#!/usr/bin/env python3
"""Label tool: replay a drive like the virtual Pi, with a panel to label what happens, saved to a CSV.

    python src/scripts/label_tool.py <session_dir> [--schema data/eval/schemas/driving_events.json]
                                     [--csv path.csv] [--start 165] [--speed 0.5]

The window is the virtual Pi's (camera undistorted and upright, CAN panel, timeline), plus a label
panel on the right. What can be labelled comes from a schema JSON file, so another labelling task
only needs another schema (see data/eval/schemas/driving_events.json):

    columns       the CSV's columns, in order
    id_column     unique row id (new rows get the next integer)
    time_columns  [start, end] in drive seconds: set with the "= now" buttons
    fields        what the panel edits: {"name", "options": [...]}, or "options_by": {other field:
                  {value: [...], "*": default}} for options that depend on another field, or
                  "text": true for typed text. "" in a list shows as "-" (empty).
    show          columns shown read-only (e.g. the pre-fill's hint)
    new_row       values for rows added here
    csv           default CSV path, "{session}" = the session folder's name
    check         "label_events": also run label_events.check_rows before saving
    color_by      the field that colours each row's span on the timeline

The panel follows the playback: it shows the row whose [start, end] holds the current time (pre-filled
from the CSV), Tab cycles if several do. Edits stay in the panel until Save (Enter), which writes
the whole CSV at once (the first save of a run keeps a .bak of the file as it was). Rows are never
deleted here: set status to "no".

Keys: space pause, a / d seek 10 s, , / . one frame back / forward (pauses), [ / ] slower / faster,
s / e set start / end to now, n new row here, Tab next row here, Enter save, r revert, q / Esc quit.
Click the timeline to seek; coloured marks under it are the CSV's rows (grey = no, amber = ?).
While the notes field is active, keys type into it; Enter or Esc leaves it.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import sys
import time
from pathlib import Path

import cv2 as cv
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
from virtual_pi import (TIMELINE_H, CanTrack, display_frame, draw_can_panel, draw_overlay,  # noqa: E402
                        draw_timeline, first_timestamp_ns, load_frames)

LABEL_W = 400
SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
PALETTE = [(255, 170, 60), (90, 200, 90), (60, 120, 255), (230, 120, 230), (60, 220, 220), (200, 200, 90),
           (150, 110, 255), (120, 180, 255)]
GREY, WHITE, ACCENT, DIM = (150, 150, 150), (240, 240, 240), (60, 170, 255), (70, 70, 70)
OK_GREEN, ERR_RED, AMBER = (90, 210, 90), (80, 80, 240), (40, 180, 230)


class Schema:
    def __init__(self, spec):
        self.name = spec.get("name", "labels")
        self.columns = spec["columns"]
        self.id = spec.get("id_column", "id")
        self.start, self.end = spec["time_columns"]
        self.fields = spec["fields"]
        self.show = spec.get("show", [])
        self.new_row = spec.get("new_row", {})
        self.csv = spec.get("csv")
        self.check = spec.get("check")
        self.color_by = spec.get("color_by")
        for f in self.fields:
            if f["name"] not in self.columns:
                raise SystemExit(f"schema field {f['name']!r} is not one of the columns")

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def options(self, field, row):
        """Allowed values of field (a fields entry) for this row; None for a text field."""
        if "options" in field:
            return field["options"]
        if "options_by" in field:
            (other, table), = field["options_by"].items()
            return table.get(row.get(other, ""), table.get("*", []))
        return None


def parse_t(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


class Store:
    """The CSV's rows, and the rules for editing and saving them."""

    def __init__(self, schema, path):
        self.schema, self.path = schema, Path(path)
        self.rows, self.backed_up = [], False
        if self.path.exists():
            with open(self.path, newline="") as f:
                reader = csv.DictReader(f)
                missing = set(schema.columns) - set(reader.fieldnames or [])
                if missing:
                    raise SystemExit(f"{self.path} has no column(s) {', '.join(sorted(missing))} from the schema")
                self.extra = [c for c in reader.fieldnames if c not in schema.columns]  # kept as they are
                self.rows = [{k: (v or "") for k, v in r.items()} for r in reader]
        else:
            self.extra = []

    def span(self, row):
        return parse_t(row.get(self.schema.start)), parse_t(row.get(self.schema.end))

    def covering(self, t):
        """Rows whose [start, end] holds t, earliest start first."""
        out = []
        for r in self.rows:
            t0, t1 = self.span(r)
            if t0 is not None and t1 is not None and t0 <= t <= t1:
                out.append(r)
        return sorted(out, key=lambda r: self.span(r)[0])

    def nearest(self, t, n=3):
        timed = [r for r in self.rows if self.span(r)[0] is not None]
        return sorted(timed, key=lambda r: abs(self.span(r)[0] - t))[:n]

    def next_id(self):
        ids = [int(r[self.schema.id]) for r in self.rows if str(r.get(self.schema.id, "")).isdigit()]
        return str(max(ids, default=0) + 1)

    def new(self, t):
        row = {c: "" for c in self.schema.columns + self.extra}
        row.update(self.schema.new_row)
        row[self.schema.id] = self.next_id()
        row[self.schema.start] = row[self.schema.end] = f"{t:.1f}"
        return self.fit(row)

    def fit(self, row):
        """Reset option fields whose value isn't allowed any more (e.g. detail after type changed)."""
        for f in self.schema.fields:
            opts = self.schema.options(f, row)
            if opts is not None and row.get(f["name"], "") not in opts:
                row[f["name"]] = opts[0] if opts else ""
        return row

    def set(self, row, name, value):
        row[name] = value
        return self.fit(row)

    def problems(self, row):
        """[problem] that stop this row being saved."""
        out = []
        t0, t1 = self.span(row)
        if t0 is None or t1 is None:
            out.append("start and end must be set")
        elif t1 < t0:
            out.append("end is before start")
        for f in self.schema.fields:
            opts = self.schema.options(f, row)
            if opts is not None and row.get(f["name"], "") not in opts:
                out.append(f"{f['name']} must be one of {opts}")
        if self.schema.check == "label_events":
            from label_events import check_rows
            out += [p.split(": ", 1)[-1] for p in check_rows([{c: row.get(c, "") for c in self.schema.columns}])]
        return out

    def save(self, row):
        """Write row (replacing the one with its id, or appended) and the rest of the CSV; returns problems."""
        problems = self.problems(row)
        if problems:
            return problems
        key = self.schema.id
        for k, r in enumerate(self.rows):
            if r.get(key) == row[key]:
                self.rows[k] = dict(row)
                break
        else:
            self.rows.append(dict(row))
        if self.path.exists() and not self.backed_up:
            self.path.with_suffix(self.path.suffix + ".bak").write_bytes(self.path.read_bytes())
            self.backed_up = True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, self.schema.columns + self.extra, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.rows)
        os.replace(tmp, self.path)  # a crash mid-write never leaves a half-written CSV
        return []


def _text(img, text, org, scale=0.45, color=WHITE, thick=1):
    cv.putText(img, text, org, cv.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv.LINE_AA)


def text_w(text, scale=0.45):
    return cv.getTextSize(text, cv.FONT_HERSHEY_SIMPLEX, scale, 1)[0][0]


def wrap(text, width, scale=0.4):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and text_w(trial, scale) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


class Panel:
    """Draws the label panel and remembers where its buttons are."""

    def __init__(self, height):
        self.height = height
        self.hits = []  # (x0, y0, x1, y1, action)

    def button(self, img, x, y, label, action, on=False, color=ACCENT, enabled=True):
        w = text_w(label) + 16
        if on:
            cv.rectangle(img, (x, y), (x + w, y + 22), color, -1)
        cv.rectangle(img, (x, y), (x + w, y + 22), color if (on or enabled) else DIM, 1)
        _text(img, label, (x + 8, y + 16), 0.45, (20, 20, 20) if on else (WHITE if enabled else DIM))
        if enabled:
            self.hits.append((x, y, x + w, y + 22, action))
        return x + w + 6

    def chips(self, img, x, y, values, current, name, color=ACCENT):
        """Option buttons for field name, wrapping; returns the y below them."""
        x0 = x
        for v in values:
            label = v or "-"
            if x + text_w(label) + 16 > LABEL_W - 10:
                x, y = x0, y + 28
            x = self.button(img, x, y, label, ("set", name, v), on=(v == current), color=color)
        return y + 30

    def draw(self, ui):
        self.hits = []
        img = np.full((self.height, LABEL_W, 3), 24, np.uint8)
        s, store, row = ui.schema, ui.store, ui.row
        _text(img, s.name.upper(), (14, 24), 0.5, GREY)
        _text(img, store.path.name, (14, 42), 0.38, GREY)
        y = 62
        here = store.covering(ui.t)
        if row is None:
            _text(img, f"no row at {ui.t:.1f} s", (14, y + 14), 0.5)
            self.button(img, 14, y + 26, "+ new row here (n)", ("new",))
            y += 64
            near = store.nearest(ui.t)
            if near:
                _text(img, "nearest rows (click to jump):", (14, y), 0.4, GREY)
                y += 10
                for r in near:
                    label = f"{r[s.id]}: {r.get(s.color_by, '') if s.color_by else ''} {store.span(r)[0]:.1f} s"
                    self.button(img, 14, y, label, ("goto_row", r[s.id]))
                    y += 28
            self.footer(img, ui)
            return img

        title = f"row {row[s.id]}" + ("  (new)" if not any(r[s.id] == row[s.id] for r in store.rows) else "")
        _text(img, title, (14, y + 12), 0.55, WHITE, 1)
        if ui.dirty:
            _text(img, "unsaved", (LABEL_W - 80, y + 12), 0.45, AMBER)
        if len(here) > 1:
            _text(img, f"{len(here)} rows here, Tab = next", (150, y + 12), 0.38, GREY)
        y += 26
        for f in s.fields:
            _text(img, f["name"], (14, y + 4), 0.38, GREY)
            y += 10
            opts = s.options(f, row)
            if opts is None:  # text field
                active = ui.typing == f["name"]
                value = row.get(f["name"], "")
                shown = value[-44:] + ("_" if active and int(time.time() * 2) % 2 else "")
                cv.rectangle(img, (14, y), (LABEL_W - 14, y + 22), ACCENT if active else DIM, 1)
                _text(img, shown or ("type, then Enter" if active else "click to type"), (20, y + 16), 0.42,
                      WHITE if shown else GREY)
                self.hits.append((14, y, LABEL_W - 14, y + 22, ("type", f["name"])))
                y += 30
            else:
                y = self.chips(img, 14, y, opts, row.get(f["name"], ""), f["name"])

        for col, label, key in ((s.start, "start", "s"), (s.end, "end", "e")):
            _text(img, f"{label} {row.get(col) or '--'} s", (14, y + 16), 0.48)
            x = self.button(img, 150, y, f"= now ({key})", ("time", col))
            self.button(img, x, y, "go", ("go", col))
            y += 28
        for col in s.show:
            for k, line in enumerate(wrap(f"{col}: {row.get(col, '')}", LABEL_W - 28)[:3]):
                _text(img, line, (14, y + 14 + 15 * k), 0.38, GREY)
            y += 14 + 15 * min(len(wrap(f"{col}: {row.get(col, '')}", LABEL_W - 28)), 3)
        self.footer(img, ui)
        return img

    def footer(self, img, ui):
        y = self.height - 76
        for k, line in enumerate(wrap(ui.message, LABEL_W - 28)[:2]):
            _text(img, line, (14, y + 15 * k), 0.4, ui.message_color)
        y = self.height - 40
        x = 14
        if ui.row is not None:
            x = self.button(img, x, y, "Save (Enter)", ("save",), color=OK_GREEN, enabled=ui.dirty)
            x = self.button(img, x, y, "Revert (r)", ("revert",), enabled=ui.dirty)
        self.button(img, x, y, "New (n)", ("new",))
        _text(img, f"speed {ui.speed:g}x   space pause   [ ] speed   , . frame", (14, self.height - 8), 0.36, GREY)


def timeline_marks(bar, store, current_id, total_t):
    """The CSV's rows as coloured marks under the timeline, the current row outlined."""
    s = store.schema
    x0, x1 = 90, bar.shape[1] - 16
    values = sorted({r.get(s.color_by, "") for r in store.rows}) if s.color_by else [""]
    for r in store.rows:
        t0, t1 = store.span(r)
        if t0 is None or t1 is None or not total_t:
            continue
        a, b = x0 + int((x1 - x0) * t0 / total_t), x0 + int((x1 - x0) * t1 / total_t)
        status = r.get("status", "yes")
        color = (GREY if status == "no" else AMBER if status == "?" else
                 PALETTE[values.index(r.get(s.color_by, "")) % len(PALETTE)] if s.color_by else ACCENT)
        cv.rectangle(bar, (a, 25), (max(b, a + 2), 31), color, -1)
        if r.get(s.id) == current_id:
            cv.rectangle(bar, (a - 1, 23), (max(b, a + 2) + 1, 33), WHITE, 1)
    return bar


class UI:
    """Playback, the row being edited, and what the panel's buttons do."""

    def __init__(self, schema, store, frames, t):
        self.schema, self.store, self.frames = schema, store, frames
        self.times = [f[2] for f in frames]
        self.total_t = frames[-1][2]
        self.speed = 1.0
        self.row, self.dirty, self.typing = None, False, None
        self.message, self.message_color = "", GREY
        self.i = max(0, bisect.bisect_right(self.times, t) - 1)
        self.drive_t0, self.wall_t0, self.paused = self.times[self.i], time.monotonic(), False
        self.follow()

    @property
    def t(self):
        return self.times[self.i]

    def tick(self):
        if not self.paused:
            target = self.drive_t0 + (time.monotonic() - self.wall_t0) * self.speed
            while self.i + 1 < len(self.frames) and self.times[self.i + 1] <= target:
                self.i += 1
            self.follow()

    def seek(self, t):
        t = min(max(t, 0.0), self.total_t)
        self.i = max(0, bisect.bisect_right(self.times, t) - 1)
        self.drive_t0, self.wall_t0 = self.times[self.i], time.monotonic()
        self.follow()

    def set_paused(self, paused):
        if self.paused and not paused:
            self.drive_t0, self.wall_t0 = self.t, time.monotonic()
        self.paused = paused

    def set_speed(self, step):
        k = min(max(SPEEDS.index(self.speed) + step, 0), len(SPEEDS) - 1)
        self.drive_t0, self.wall_t0, self.speed = self.t, time.monotonic(), SPEEDS[k]

    def follow(self):
        """Show the row at the current time, unless the one in the panel has unsaved edits."""
        if self.dirty:
            return
        here = self.store.covering(self.t)
        ids = [r[self.schema.id] for r in here]
        if self.row is not None and self.row[self.schema.id] in ids:
            return
        self.row = dict(here[0]) if here else None

    def say(self, text, color=GREY):
        self.message, self.message_color = text, color

    def act(self, action):
        s = self.schema
        kind = action[0]
        if kind == "goto_row":
            r = next(r for r in self.store.rows if r[s.id] == action[1])
            self.set_paused(True)
            self.seek(self.store.span(r)[0])
            return
        if kind == "new":
            self.set_paused(True)
            self.row, self.dirty = self.store.new(self.t), True
            self.say(f"new row at {self.t:.1f} s: set the fields, then end (e) and Save", GREY)
            return
        if self.row is None:
            return
        self.set_paused(True)  # editing: hold the frame still
        if kind == "set":
            self.store.set(self.row, action[1], action[2])
            self.dirty = True
        elif kind == "type":
            self.typing = action[1]
        elif kind == "time":
            self.row[action[1]] = f"{self.t:.1f}"
            self.dirty = True
        elif kind == "go":
            t = parse_t(self.row.get(action[1]))
            if t is not None:
                self.seek(t)
        elif kind == "next":
            here = self.store.covering(self.t)
            if len(here) > 1 and not self.dirty:
                ids = [r[s.id] for r in here]
                k = (ids.index(self.row[s.id]) + 1) % len(ids) if self.row[s.id] in ids else 0
                self.row = dict(here[k])
        elif kind == "revert":
            saved = next((r for r in self.store.rows if r[s.id] == self.row[s.id]), None)
            self.row, self.dirty, self.typing = (dict(saved) if saved else None), False, None
            self.say("reverted")
            self.follow()
        elif kind == "save":
            self.typing = None
            problems = self.store.save(self.row)
            if problems:
                self.say("not saved: " + "; ".join(problems), ERR_RED)
            else:
                self.dirty = False
                self.say(f"saved row {self.row[s.id]} to {self.store.path.name}", OK_GREEN)

    def key(self, key):
        """Returns False to quit."""
        if self.typing:
            name = self.typing
            if key in (13, 10, 27):
                self.typing = None
            elif key in (8, 65288, 127):
                self.row[name] = self.row.get(name, "")[:-1]
                self.dirty = True
            elif 32 <= key < 127 and key != ord(","):  # commas are fine in CSV, but keep notes simple
                self.row[name] = self.row.get(name, "") + chr(key)
                self.dirty = True
            return True
        if key in (ord("q"), 27):
            if self.dirty and self.message != "unsaved changes: q again to quit without saving":
                self.say("unsaved changes: q again to quit without saving", AMBER)
                return True
            return False
        if key == ord(" "):
            self.set_paused(not self.paused)
        elif key in (ord("a"), 65361, 2424832):
            self.seek(self.t - 10)
        elif key in (ord("d"), 65363, 2555904):
            self.seek(self.t + 10)
        elif key in (ord(","), ord(".")):
            self.set_paused(True)
            self.i = min(max(self.i + (1 if key == ord(".") else -1), 0), len(self.frames) - 1)
            self.follow()
        elif key in (ord("["), ord("]")):
            self.set_speed(1 if key == ord("]") else -1)
        elif key == ord("s"):
            self.act(("time", self.schema.start))
        elif key == ord("e"):
            self.act(("time", self.schema.end))
        elif key == ord("n"):
            self.act(("new",))
        elif key == 9:
            self.act(("next",))
        elif key in (13, 10):
            if self.dirty:
                self.act(("save",))
        elif key == ord("r"):
            self.act(("revert",))
        return True


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--schema", default=str(ROOT / "data" / "eval" / "schemas" / "driving_events.json"))
    p.add_argument("--csv", help="default: the schema's csv, {session} = the session folder name")
    p.add_argument("--start", type=float, default=0.0)
    p.add_argument("--speed", type=float, default=1.0, choices=SPEEDS)
    args = p.parse_args(argv)

    session = Path(args.session_dir)
    schema = Schema.load(args.schema)
    if not args.csv and not schema.csv:
        p.error("the schema has no default csv: pass --csv")
    path = Path(args.csv) if args.csv else ROOT / schema.csv.format(session=session.name)
    store = Store(schema, path)
    frames = load_frames(session)
    print("loading CAN (decoded.csv) ...")
    can = CanTrack(session / "decoded.csv", first_timestamp_ns(session))
    print(f"{len(frames)} frames; {len(store.rows)} rows in {path}" + ("" if path.exists() else " (new file)"))

    ui = UI(schema, store, frames, args.start)
    ui.speed = args.speed
    window = "label tool"
    cv.namedWindow(window, cv.WINDOW_AUTOSIZE | cv.WINDOW_GUI_NORMAL)
    clicks = []
    cv.setMouseCallback(window, lambda ev, x, y, *_: clicks.append((x, y)) if ev == cv.EVENT_LBUTTONDOWN else None)
    panel, layout = None, {}
    shown, view_seq, view = None, None, None
    try:
        while True:
            ui.tick()
            seq, fpath, drive_t = frames[ui.i]
            if seq != view_seq:
                frame = cv.imread(str(fpath))
                if frame is not None:
                    view, view_seq = display_frame(frame), seq
            if view is None:
                continue
            img = view.copy()
            draw_overlay(img, seq, drive_t, f"speed {ui.speed:g}x", ui.paused)
            can_panel = draw_can_panel(img.shape[0], can.at(drive_t), can.available, drive_t)
            panel = panel or Panel(img.shape[0])
            label_panel = panel.draw(ui)
            screen = np.hstack([img, can_panel, label_panel])
            bar = draw_timeline(screen.shape[1], drive_t, ui.total_t)
            timeline_marks(bar, store, ui.row[schema.id] if ui.row else None, ui.total_t)
            screen = np.vstack([screen, bar])
            layout = {"h": img.shape[0], "w": screen.shape[1], "panel_x": img.shape[1] + can_panel.shape[1]}
            cv.imshow(window, screen)

            key = cv.waitKeyEx(15)
            while clicks:
                x, y = clicks.pop(0)
                if y >= layout["h"]:  # timeline
                    ui.seek(min(max((x - 90) / (layout["w"] - 106), 0.0), 1.0) * ui.total_t)
                    continue
                px = x - layout["panel_x"]
                if px < 0:
                    ui.typing = None
                    continue
                for x0, y0, x1, y1, action in panel.hits:
                    if x0 <= px <= x1 and y0 <= y <= y1:
                        if action[0] != "type":
                            ui.typing = None
                        ui.act(action)
                        break
            if key != -1 and not ui.key(key & 0xFFFF if key < 0x10000 else key):
                break
            if cv.getWindowProperty(window, cv.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cv.destroyAllWindows()
    if ui.dirty:
        print(f"quit with unsaved changes to row {ui.row[schema.id]}")
    print(f"{len(store.rows)} rows in {path}")


if __name__ == "__main__":
    main()
