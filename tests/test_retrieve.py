"""retrieve.py: corpus resolution/fallback, bucketing, and honest bad-row counting."""
import retrieve


def test_bucket_of_known_recipients():
    assert retrieve.bucket_of("Sam (investor)") == "Investors / board"
    assert retrieve.bucket_of("Priya (team, eng)") == "Team"
    assert retrieve.bucket_of("Dana (customer)") == "Customers / external"
    assert retrieve.bucket_of("Prof Lee (.edu)") == "Academic / personal"


def test_bucket_of_unknown_is_none():
    assert retrieve.bucket_of("somebody random") is None
    assert retrieve.bucket_of("") is None


def test_resolve_falls_back_to_example(tmp_path, monkeypatch):
    monkeypatch.delenv("UNDERSTUDY_PAIRS", raising=False)
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus/pairs.example.jsonl").write_text("{}\n")
    path, used_fallback = retrieve.resolve_pairs_path(None, root=tmp_path)
    assert used_fallback is True
    assert path.name == "pairs.example.jsonl"


def test_resolve_prefers_real_corpus(tmp_path, monkeypatch):
    monkeypatch.delenv("UNDERSTUDY_PAIRS", raising=False)
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus/pairs.jsonl").write_text("{}\n")
    (tmp_path / "corpus/pairs.example.jsonl").write_text("{}\n")
    path, used_fallback = retrieve.resolve_pairs_path(None, root=tmp_path)
    assert used_fallback is False
    assert path.name == "pairs.jsonl"


def test_resolve_explicit_wins(monkeypatch):
    monkeypatch.setenv("UNDERSTUDY_PAIRS", "/from/env.jsonl")
    path, used_fallback = retrieve.resolve_pairs_path("/explicit/x.jsonl")
    assert used_fallback is False
    assert str(path) == "/explicit/x.jsonl"


def test_resolve_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERSTUDY_PAIRS", "/from/env.jsonl")
    path, used_fallback = retrieve.resolve_pairs_path(None, root=tmp_path)
    assert used_fallback is False
    assert str(path) == "/from/env.jsonl"


def test_load_pairs_counts_bad_rows(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text('{"ep_id":"a","draft":"d","sent":"s"}\nNOT JSON\n\n{"ep_id":"b"}\n')
    rows, n_bad = retrieve.load_pairs(f)
    assert len(rows) == 2
    assert n_bad == 1


def test_shipped_example_corpus_is_clean():
    rows, n_bad = retrieve.load_pairs(retrieve.ROOT / "corpus/pairs.example.jsonl")
    assert n_bad == 0
    assert len(rows) >= 3
