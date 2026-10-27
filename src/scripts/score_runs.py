#!/usr/bin/env python3
"""Score several agent runs of the same drive, to see how much the answers vary from run to run.

    python src/scripts/score_runs.py data/eval/events_gt_<session>.csv runs/<s>/agent/events.json runs/<s>/agent_repeats/run*/events.json [--json out.json]

Even at temperature 0 the model's answers differ between runs, so one run's score is one sample.
For each run: precision and recall as score.py computes them. Over the runs: the range of each,
and per candidate how many runs reached the same decision (verdict, type and side), which shows
where the agent is unsure.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
import score  # noqa: E402
from label_events import read_rows  # noqa: E402


def decision(ev):
    if ev["verdict"] == "rejected":
        return "rejected"
    return " ".join(x for x in (ev["type"], ev.get("side") or "") if x)


def summarize(runs, gt):
    """runs: {name: [event]} -> per-run scores, ranges and per-candidate agreement."""
    per_run = {}
    for name, events in runs.items():
        o = score.score(events, gt)["overall"]
        per_run[name] = {k: o[k] for k in ("tp", "fp", "fn", "precision", "recall")}
        per_run[name]["flagged"] = o["tp"] + o["fp"]
        per_run[name]["unverified"] = sum(e["verdict"] == "unverified" for e in events)
    ids = sorted({e["id"] for events in runs.values() for e in events})
    agreement = {}
    for cid in ids:
        votes = Counter(decision(e) for events in runs.values() for e in events if e["id"] == cid)
        top, n = votes.most_common(1)[0]
        agreement[cid] = {"majority": top, "agree": n, "of": sum(votes.values()), "votes": dict(votes)}
    span = lambda k: [min(r[k] for r in per_run.values()), max(r[k] for r in per_run.values())]  # noqa: E731
    return {"runs": per_run, "range": {k: span(k) for k in ("precision", "recall", "flagged", "tp")},
            "unanimous": sum(a["agree"] == a["of"] for a in agreement.values()), "candidates": len(ids),
            "agreement": agreement}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("gt", help="data/eval/events_gt_<session>.csv")
    p.add_argument("runs", nargs="+", help="events.json of each run")
    p.add_argument("--json", help="also write the full result here")
    args = p.parse_args(argv)
    gt = score.ground_truth(read_rows(Path(args.gt)))
    runs = {str(Path(r).parent): json.loads(Path(r).read_text()) for r in args.runs}
    result = summarize(runs, gt)
    print(f"{'run':<44}{'flagged':>8}{'right':>6}{'prec':>7}{'found':>6}{'recall':>7}{'unverif':>8}")
    for name, r in result["runs"].items():
        print(f"{name:<44}{r['flagged']:>8}{r['tp']:>6}{r['precision']:>7.2f}{r['tp']:>6}{r['recall']:>7.2f}"
              f"{r['unverified']:>8}")
    rg = result["range"]
    print(f"precision {rg['precision'][0]:.2f}-{rg['precision'][1]:.2f}, recall {rg['recall'][0]:.2f}-{rg['recall'][1]:.2f} "
          f"over {len(runs)} runs ({len(gt)} labelled events)")
    print(f"same decision in every run: {result['unanimous']} of {result['candidates']} candidates; the others:")
    for cid, a in result["agreement"].items():
        if a["agree"] < a["of"]:
            print(f"  {cid}: " + ", ".join(f"{k} x{v}" for k, v in sorted(a["votes"].items(), key=lambda kv: -kv[1])))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
