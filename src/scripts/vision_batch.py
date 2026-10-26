#!/usr/bin/env python3
"""Run the perception pipeline over a recorded drive, offline, and save every frame's metrics.

    python src/scripts/vision_batch.py <session_dir> [--fps 3] [--also <session_dir>/lane_labels.csv]
    python src/scripts/vision_batch.py test_sessions/private-640/20261022T164127Z-084b --fps 3

This is step 1 of scenario mining: the same lld.process_frame (and signs.SignReader) as the live
service, but on a local session folder instead of S3 + SQS, and at any rate. Frames are sampled
by time: the first frame at or after each 1/fps tick of the drive (the camera records ~15 fps
with jitter, so a fixed stride would drift). --also adds named frames on top of the sample,
e.g. the hand-labelled ones, so the result can be scored against lane_labels.csv.

Output: <out> (default runs/<session>/vision.jsonl), one JSON object per frame, in drive order:

    seq, frame, timestamp_ns, t_s     where in the drive (t_s = seconds since the first frame,
                                      the same clock as virtual_pi.py and decoded.csv)
    input_size                        [w, h] of the frame as read
    ...                               everything lld.process_frame returns (offset_m, lane_valid,
                                      departure, objects, signs, ...)

Lines are written as they're computed; re-running skips frames already in the file, so an
interrupted run resumes. Delete the file to start over.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import cv2 as cv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import lld  # noqa: E402
import signs  # noqa: E402
from virtual_pi import load_frames  # noqa: E402


def sample_by_time(frames, fps):
    """Indices into frames ([(seq, path, t_s)], t_s ascending) of the first frame at or after each
    1/fps tick. A gap longer than a tick yields one frame, not duplicates."""
    picked, next_t = [], 0.0
    for i, (_, _, t) in enumerate(frames):
        if t >= next_t - 1e-9:
            picked.append(i)
            next_t = (int(t * fps + 1e-9) + 1) / fps
    return picked


def frames_named(frames, names):
    """Indices of the frames whose file name is in names."""
    names = set(names)
    return [i for i, (_, path, _) in enumerate(frames) if Path(path).name in names]


def read_done(out):
    """seqs already in an earlier run's output (a torn last line is dropped and redone)."""
    done = set()
    if not out.exists():
        return done
    lines = out.read_text().splitlines()
    good = []
    for line in lines:
        try:
            done.add(json.loads(line)["seq"])
            good.append(line)
        except (json.JSONDecodeError, KeyError):
            pass
    if len(good) != len(lines):
        out.write_text("".join(l + "\n" for l in good))
    return done


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("session_dir")
    p.add_argument("--fps", type=float, default=3.0, help="frames per second of drive to process")
    p.add_argument("--also", help="CSV with a 'frame' column (e.g. lane_labels.csv): process those frames too")
    p.add_argument("--out", help="default runs/<session>/vision.jsonl")
    p.add_argument("--no-signs", action="store_true", help="skip the sign reader")
    p.add_argument("--limit", type=int, help="stop after this many new frames (for a quick test)")
    args = p.parse_args(argv)

    session = Path(args.session_dir)
    out = Path(args.out) if args.out else ROOT / "runs" / session.name / "vision.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)

    frames = load_frames(session)
    picked = set(sample_by_time(frames, args.fps))
    if args.also:
        with open(args.also, newline="") as f:
            picked |= set(frames_named(frames, (r["frame"] for r in csv.DictReader(f))))
    done = read_done(out)
    todo = [i for i in sorted(picked) if frames[i][0] not in done]
    print(f"{session.name}: {len(frames)} frames, {len(picked)} picked at {args.fps:g} fps"
          f"{' + --also' if args.also else ''}, {len(picked) - len(todo)} already done, {len(todo)} to go")
    if args.limit is not None:
        todo = todo[:args.limit]

    model, device = lld.load_model()
    sign_reader = None if args.no_signs else signs.SignReader()
    with open(session / "frames.csv", newline="") as f:
        ts_ns = {int(r["seq"]): int(r["timestamp_ns"]) for r in csv.DictReader(f)}

    started = time.perf_counter()
    with open(out, "a") as f:
        for n, i in enumerate(todo, 1):
            seq, path, t = frames[i]
            frame = cv.imread(str(path))
            if frame is None:
                print(f"seq {seq}: could not read {path}, skipping")
                continue
            metrics, _, _ = lld.process_frame(frame, model, device, sign_reader)
            row = {"seq": seq, "frame": Path(path).name, "timestamp_ns": ts_ns[seq],
                   "t_s": round(t, 3), "input_size": [frame.shape[1], frame.shape[0]], **metrics}
            f.write(json.dumps(row) + "\n")
            f.flush()
            if n % 50 == 0 or n == len(todo):
                rate = (time.perf_counter() - started) / n
                print(f"{n}/{len(todo)}  t={t:6.1f} s  {rate:.2f} s/frame  ~{rate * (len(todo) - n) / 60:.0f} min left")

    print(f"wrote {out}")


if __name__ == "__main__":
    main()
