#!/usr/bin/env python3
"""
trend.py - the effectiveness curve, no tagging required.

If the loop is learning, your edits shrink: mean draft->sent similarity rises
and the heavy-edit rate falls, over time. Every reconciled pair already carries
the measurement (sim, edit_weight, sent_ts), so the signal is free; it is
scored against what you actually sent, not against a forced preference.

Pairs without sent_ts (a bootstrap harvest) form the "baseline" cohort; dated
pairs group by month. Read newer months against baseline: sim up and heavy-rate
down means the drafts are landing closer to what you really send.

Usage: python3 bin/trend.py [--pairs corpus/pairs.jsonl] [--json]
"""
import argparse
import json
import os
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent


def resolve_pairs(explicit=None):
    if explicit:
        return pathlib.Path(explicit)
    env = os.environ.get("UNDERSTUDY_PAIRS")
    if env:
        return pathlib.Path(env)
    real = ROOT / "corpus/pairs.jsonl"
    return real if real.exists() else ROOT / "corpus/pairs.example.jsonl"


def load(p):
    rows, bad = [], 0
    p = pathlib.Path(p)
    if not p.exists():
        return rows, bad
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def compute(rows):
    """Group pairs into baseline (no sent_ts) + calendar months; mean sim + heavy rate per group."""
    groups = defaultdict(list)
    for r in rows:
        ts = r.get("sent_ts") or ""
        groups[ts[:7] if ts else "baseline"].append(r)
    out = []
    for g in sorted(groups, key=lambda k: ("0" if k == "baseline" else "1") + k):
        rs = groups[g]
        sims = [r["sim"] for r in rs if isinstance(r.get("sim"), (int, float))]
        heavy = sum(1 for r in rs if r.get("edit_weight") == "heavy")
        out.append({"group": g, "n": len(rs),
                    "mean_sim": round(sum(sims) / len(sims), 3) if sims else None,
                    "heavy_rate": round(heavy / len(rs), 3)})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Edit-shrinkage trend from the pairs corpus.")
    ap.add_argument("--pairs", default="", help="path to a pairs.jsonl; overrides auto-resolution")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    a = ap.parse_args(argv)
    path = resolve_pairs(a.pairs or None)
    rows, bad = load(path)
    if bad:
        print(f"warning: skipped {bad} malformed line(s) in {path.name}", file=sys.stderr)
    groups = compute(rows)
    if a.json:
        print(json.dumps(groups, indent=2))
        return groups
    print(f"edit-shrinkage trend ({path.name}, {len(rows)} pairs)")
    print(f"{'cohort':<12} {'n':>4} {'mean sim':>9} {'heavy rate':>11}")
    for g in groups:
        ms = f"{g['mean_sim']:.3f}" if g["mean_sim"] is not None else "-"
        print(f"{g['group']:<12} {g['n']:>4} {ms:>9} {g['heavy_rate']:>11.0%}")
    print("watch for: mean sim rising, heavy rate falling. That is the loop working.")
    return groups


if __name__ == "__main__":
    main()
