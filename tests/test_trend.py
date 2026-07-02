"""trend.py: baseline vs dated cohorts, mean sim and heavy rate."""
import json

import trend


def test_groups_baseline_and_months(tmp_path):
    rows = [
        {"sim": 0.4, "edit_weight": "heavy"},                                   # baseline (no sent_ts)
        {"sim": 0.6, "edit_weight": "heavy"},                                   # baseline
        {"sim": 0.7, "edit_weight": "heavy", "sent_ts": "2026-06-25T15:57:02Z"},
        {"sim": 0.9, "edit_weight": "light", "sent_ts": "2026-07-02T10:00:00Z"},
    ]
    f = tmp_path / "p.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    loaded, bad = trend.load(f)
    assert bad == 0
    out = trend.compute(loaded)
    by = {g["group"]: g for g in out}
    assert out[0]["group"] == "baseline"          # baseline sorts first
    assert by["baseline"]["n"] == 2
    assert by["baseline"]["mean_sim"] == 0.5
    assert by["baseline"]["heavy_rate"] == 1.0
    assert by["2026-06"]["n"] == 1
    assert by["2026-07"]["heavy_rate"] == 0.0


def test_load_counts_bad(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"sim":0.5,"edit_weight":"light"}\nnot json\n')
    rows, bad = trend.load(f)
    assert len(rows) == 1
    assert bad == 1


def test_shipped_example_runs():
    rows, bad = trend.load(trend.ROOT / "corpus/pairs.example.jsonl")
    assert bad == 0
    out = trend.compute(rows)
    assert out and out[0]["group"] == "baseline"
