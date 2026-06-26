#!/usr/bin/env python3
"""
auto_effectiveness.py - measure the drafting pipeline WITHOUT human tagging.

The blind A/B tagger needs a human to pick which draft is "more you." That human
label is the ground truth that calibrates the judge, and the model must never fake
it: a model labeling its own A/B set is the judge grading the judge, which makes the
numbers fiction. (See docs/automation.md, "The line you can't automate.")

But there is another ground truth that costs nothing and is already on hand: what you
ACTUALLY SENT, which reconcile fetches with provenance. So for each situation, compare
a cold draft (no pipeline) and the pipeline draft against the real send. Whichever
lands closer to what you sent wins. That is a continuous, automatic effectiveness
signal, measured against reality instead of a forced preference, and it needs no taps.

Input: jsonl, one object per line: {id, cold, pipeline, sent}
Output: aggregate pipeline win-rate + mean lift (and per-item detail in the return value).

Usage: python3 auto_effectiveness.py records.jsonl [--epsilon 0.02]
"""
import argparse
import difflib
import json
import pathlib
import sys


def sim(a, b):
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def score(records, epsilon=0.02):
    """Per-item winner against the real send, plus the aggregate. epsilon is the
    dead-band within which the two drafts count as a tie."""
    rows, wins, ties, lifts = [], 0, 0, []
    for r in records:
        sc = sim(r.get("cold", ""), r.get("sent", ""))
        sp = sim(r.get("pipeline", ""), r.get("sent", ""))
        lift = sp - sc
        if abs(lift) <= epsilon:
            verdict, ties = "tie", ties + 1
        elif lift > 0:
            verdict, wins = "pipeline", wins + 1
        else:
            verdict = "cold"
        lifts.append(lift)
        rows.append({"id": r.get("id"), "sim_cold": round(sc, 4), "sim_pipeline": round(sp, 4),
                     "lift": round(lift, 4), "winner": verdict})
    n = len(rows)
    decided = n - ties
    return {
        "n": n,
        "ties": ties,
        "pipeline_wins": wins,
        "cold_wins": decided - wins,
        "pipeline_win_rate": round(wins / decided, 4) if decided else None,
        "mean_lift": round(sum(lifts) / n, 4) if n else None,
        "items": rows,
    }


def load(p):
    rows, bad = [], 0
    for ln in pathlib.Path(p).read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tag-free effectiveness: cold vs pipeline draft, scored against the real send.")
    ap.add_argument("records", help="jsonl of {id, cold, pipeline, sent}")
    ap.add_argument("--epsilon", type=float, default=0.02, help="tie dead-band on the similarity lift")
    a = ap.parse_args(argv)
    rows, bad = load(a.records)
    if bad:
        print(f"warning: skipped {bad} malformed line(s)", file=sys.stderr)
    out = score(rows, a.epsilon)
    print(json.dumps({k: v for k, v in out.items() if k != "items"}, indent=2))
    return out


if __name__ == "__main__":
    main()
