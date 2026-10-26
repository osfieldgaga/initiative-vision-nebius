#!/usr/bin/env python3
"""Score detected driving events against the hand-labelled ground truth.

    python src/scripts/score.py runs/<session>/candidates.json data/eval/events_gt_<session>.csv [--sure-only] [--json out.json]

Works for any event list with type, t_start, t_end, side, detail: the rule candidates (step 4) and
the agent's events (step 5). Events with "verdict": "rejected" are skipped (the agent said no).

Ground truth = the CSV's status "yes" rows (LABELLING.md). A detection matches a true event of
the same type and side whose time span overlaps it, padded by MATCH_PAD_S; each true event and
each detection is used at most once, largest overlap first. Reported per type and overall:
precision, recall, and detail accuracy (full_stop / rolling_stop / blinker / ...) on the matches.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "scripts"))
from label_events import TYPES, read_rows  # noqa: E402

MATCH_PAD_S = 1.0


def overlap(a, b):
    """Seconds of overlap between a and b after padding both by MATCH_PAD_S (> 0 = they match)."""
    return min(a["t_end"], b["t_end"]) - max(a["t_start"], b["t_start"]) + 2 * MATCH_PAD_S


def ground_truth(rows, sure_only=False):
    return [{"id": r["id"], "type": r["type"], "t_start": float(r["t_start"]), "t_end": float(r["t_end"]),
             "side": r["side"], "detail": r["detail"], "source": r["source"]}
            for r in rows if r["status"] == "yes" and not (sure_only and r["confidence"] == "unsure")]


def match(pred, gt):
    """[(pred index, gt index)], one-to-one, same type and side, largest overlap first."""
    pairs = sorted(((overlap(p, g), i, j) for i, p in enumerate(pred) for j, g in enumerate(gt)
                    if p["type"] == g["type"] and (p.get("side") or "") == g["side"] and overlap(p, g) > 0),
                   reverse=True)
    used_p, used_g, out = set(), set(), []
    for _, i, j in pairs:
        if i not in used_p and j not in used_g:
            used_p.add(i)
            used_g.add(j)
            out.append((i, j))
    return sorted(out)


def ratio(a, b):
    return round(a / b, 3) if b else None


def score(pred, gt):
    pred = [p for p in pred if p.get("verdict") != "rejected"]
    pairs = match(pred, gt)
    matched_p, matched_g = {i for i, _ in pairs}, {j for _, j in pairs}

    def summary(types):
        tp = sum(pred[i]["type"] in types for i, _ in pairs)
        n_pred = sum(p["type"] in types for p in pred)
        n_gt = sum(g["type"] in types for g in gt)
        detail_ok = sum(pred[i]["type"] in types and (pred[i].get("detail") or "") == gt[j]["detail"] for i, j in pairs)
        return {"tp": tp, "fp": n_pred - tp, "fn": n_gt - tp, "precision": ratio(tp, n_pred), "recall": ratio(tp, n_gt),
                "detail_accuracy": ratio(detail_ok, tp)}

    added = [j for j, g in enumerate(gt) if g["source"] == "added"]
    return {
        "per_type": {t: summary({t}) for t in TYPES if any(x["type"] == t for x in pred + gt)},
        "overall": summary(set(TYPES)),
        "recall_on_added": ratio(sum(j in matched_g for j in added), len(added)),
        "matches": [{"pred": pred[i].get("id"), "gt": gt[j]["id"], "type": gt[j]["type"],
                     "detail": [pred[i].get("detail") or "", gt[j]["detail"]]} for i, j in pairs],
        "false_positives": [{"pred": p.get("id"), "type": p["type"], "t_start": p["t_start"]}
                            for i, p in enumerate(pred) if i not in matched_p],
        "missed": [{"gt": g["id"], "type": g["type"], "t_start": g["t_start"], "source": g["source"]}
                   for j, g in enumerate(gt) if j not in matched_g],
    }


def table(result):
    lines = [f"{'type':<16}{'TP':>4}{'FP':>4}{'FN':>4}{'prec':>7}{'recall':>8}{'detail':>8}"]
    fmt = lambda x: "-" if x is None else f"{x:.2f}"  # noqa: E731
    for name, s in [*result["per_type"].items(), ("overall", result["overall"])]:
        lines.append(f"{name:<16}{s['tp']:>4}{s['fp']:>4}{s['fn']:>4}{fmt(s['precision']):>7}{fmt(s['recall']):>8}"
                     f"{fmt(s['detail_accuracy']):>8}")
    lines.append(f"recall on events the pre-fill missed (source added): {fmt(result['recall_on_added'])}")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("pred", help="candidates.json or events.json")
    p.add_argument("gt", help="data/eval/events_gt_<session>.csv")
    p.add_argument("--sure-only", action="store_true", help="leave out ground-truth rows marked unsure")
    p.add_argument("--json", help="also write the full result here")
    args = p.parse_args(argv)

    rows = read_rows(args.gt)
    if any(r["status"] == "?" for r in rows):
        print(f"warning: {sum(r['status'] == '?' for r in rows)} ground-truth rows still unreviewed (status ?)")
    result = score(json.load(open(args.pred)), ground_truth(rows, args.sure_only))
    print(table(result))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=1) + "\n")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
