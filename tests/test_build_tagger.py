"""build_tagger.py: builds a self-contained tagger from the shipped example eval dir."""
import json

import build_tagger


def test_builds_from_example(tmp_path):
    out = tmp_path / "tagger.html"
    items = build_tagger.main([str(build_tagger.EXAMPLE_DIR), str(out)])
    assert out.exists()
    assert len(items) == 3
    html = out.read_text(encoding="utf-8")
    assert "UNDERSTUDY TAGGER" in html
    # the A/B texts are embedded for the blind choice
    assert "token refresh path" in html


def test_items_carry_blind_sources_and_meta(tmp_path):
    items = build_tagger.main([str(build_tagger.EXAMPLE_DIR), str(tmp_path / "t.html")])
    by_id = {it["id"]: it for it in items}
    ex1 = by_id["ex-1"]
    # panel-key.json says ex-1 is A=revised, B=draft
    assert ex1["A"]["source"] == "revised"
    assert ex1["B"]["source"] == "draft"
    assert ex1["A"]["text"] and ex1["B"]["text"]
    assert ex1["recipient"] == "Sam (investor)"
    # the reference 'sent' is carried but is not an A/B option
    assert ex1["real_send"]


def test_load_jsonl_counts_bad(tmp_path):
    f = tmp_path / "x.jsonl"
    f.write_text('{"id":"a","text":"ok"}\nbroken\n{"no_id":true}\n')
    d, n_bad = build_tagger.load_jsonl(f)
    assert "a" in d
    assert n_bad == 2  # malformed JSON + missing id key


def test_script_breakout_is_neutralized(tmp_path):
    ed = tmp_path / "ev"
    ed.mkdir()
    (ed / "draft.jsonl").write_text('{"id":"x","text":"</script><script>alert(1)</script>"}\n')
    (ed / "revised.jsonl").write_text('{"id":"x","text":"safe"}\n')
    (ed / "panel-key.json").write_text('{"x":{"A":"draft","B":"revised"}}')
    out = tmp_path / "t.html"
    build_tagger.main([str(ed), str(out)])
    h = out.read_text(encoding="utf-8")
    # the file must contain exactly one real </script> (the template's own close tag)
    assert h.count("</script>") == 1
    # the injected one is escaped instead
    assert "\\u003c/script\\u003e" in h


def test_label_quote_does_not_break_js(tmp_path):
    out = tmp_path / "t.html"
    build_tagger.main([str(build_tagger.EXAMPLE_DIR), str(out), "--label", 'x"; alert(1);//'])
    h = out.read_text(encoding="utf-8")
    # the raw, un-escaped break-out form must not appear
    assert 'BATCH = "x"; alert' not in h
    # the label is embedded as a proper JSON string literal
    assert 'const BATCH = "x\\"; alert(1);//"' in h
