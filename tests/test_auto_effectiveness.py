"""auto_effectiveness.py: tag-free win-rate, scored against the real send."""
import auto_effectiveness as ae


def test_pipeline_closer_to_sent_wins():
    recs = [{"id": "1", "cold": "totally different wording here", "pipeline": "the exact sent text",
             "sent": "the exact sent text"}]
    out = ae.score(recs)
    assert out["items"][0]["winner"] == "pipeline"
    assert out["pipeline_win_rate"] == 1.0
    assert out["mean_lift"] > 0


def test_cold_closer_to_sent_wins():
    recs = [{"id": "1", "cold": "the exact sent text", "pipeline": "nothing like it at all",
             "sent": "the exact sent text"}]
    out = ae.score(recs)
    assert out["items"][0]["winner"] == "cold"
    assert out["pipeline_win_rate"] == 0.0


def test_dead_band_is_a_tie():
    recs = [{"id": "1", "cold": "same same same", "pipeline": "same same same", "sent": "same same same"}]
    out = ae.score(recs, epsilon=0.02)
    assert out["items"][0]["winner"] == "tie"
    assert out["ties"] == 1
    assert out["pipeline_win_rate"] is None  # no decided items


def test_aggregate_excludes_ties_from_rate():
    recs = [
        {"id": "1", "cold": "x", "pipeline": "the sent", "sent": "the sent"},   # pipeline
        {"id": "2", "cold": "the sent", "pipeline": "y", "sent": "the sent"},   # cold
        {"id": "3", "cold": "tie text", "pipeline": "tie text", "sent": "tie text"},  # tie
    ]
    out = ae.score(recs)
    assert out["n"] == 3
    assert out["ties"] == 1
    assert out["pipeline_wins"] == 1
    assert out["cold_wins"] == 1
    assert out["pipeline_win_rate"] == 0.5  # 1 of 2 decided


def test_load_counts_bad(tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text('{"id":"1","cold":"a","pipeline":"b","sent":"c"}\nbroken\n')
    rows, bad = ae.load(f)
    assert len(rows) == 1
    assert bad == 1
