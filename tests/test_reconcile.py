"""reconcile_helper.py: field aliases, provenance, authorship, dedup. Run as a subprocess (it reads stdin)."""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELPER = ROOT / "bin/reconcile_helper.py"


def run(obj, pairs_path):
    env = dict(os.environ, UNDERSTUDY_PAIRS=str(pairs_path))
    p = subprocess.run([sys.executable, str(HELPER)], input=json.dumps(obj),
                       capture_output=True, text=True, env=env)
    return p.stdout.strip()


def test_legacy_aliases_are_accepted(tmp_path):
    """The documented claude_draft/matt_sent input must work, not SKIP empty."""
    pp = tmp_path / "p.jsonl"
    out = run({"recipient": "Sam (investor)", "claude_draft": "hi there",
               "matt_sent": "Sam - yes.", "message_id": "m1"}, pp)
    assert out.startswith("KEPT"), out
    row = json.loads(pp.read_text().strip())
    assert row["draft"] == "hi there"
    assert row["sent"] == "Sam - yes."


def test_canonical_fields_are_accepted(tmp_path):
    pp = tmp_path / "p.jsonl"
    out = run({"recipient": "Sam", "draft": "d", "sent": "s", "message_id": "m1"}, pp)
    assert out.startswith("KEPT"), out


def test_provenance_required(tmp_path):
    out = run({"recipient": "Sam", "draft": "d", "sent": "s"}, tmp_path / "p.jsonl")
    assert "provenance" in out, out


def test_empty_send_skipped(tmp_path):
    out = run({"recipient": "Sam", "draft": "d", "sent": "", "message_id": "m1"}, tmp_path / "p.jsonl")
    assert "empty" in out, out


def test_authorship_filter_drops_bot(tmp_path):
    out = run({"recipient": "scheduled-task feed", "draft": "d", "sent": "s",
               "message_id": "m1"}, tmp_path / "p.jsonl")
    assert "authorship" in out, out


def test_dedup_on_message_id(tmp_path):
    pp = tmp_path / "p.jsonl"
    run({"recipient": "Sam", "draft": "d", "sent": "s", "message_id": "m1"}, pp)
    out = run({"recipient": "Sam", "draft": "d2", "sent": "s2", "message_id": "m1"}, pp)
    assert out.startswith("SKIP: dup"), out
    assert len(pp.read_text().strip().splitlines()) == 1


def test_sim_and_weight_computed(tmp_path):
    pp = tmp_path / "p.jsonl"
    run({"recipient": "Sam", "draft": "the quick brown fox",
         "sent": "a totally different sentence", "message_id": "m1"}, pp)
    row = json.loads(pp.read_text().strip())
    assert 0.0 <= row["sim"] <= 1.0
    assert row["edit_weight"] == "heavy"


def test_reformatting_is_not_editing(tmp_path):
    """Bullets/quote-markers/markdown must not count as edits: sim stays high."""
    pp = tmp_path / "p.jsonl"
    run({"recipient": "Sam", "message_id": "m1",
         "draft": "> **Plan:**\n> - ship friday\n> - close monday",
         "sent": "Plan:\n• ship friday\n• close monday"}, pp)
    row = json.loads(pp.read_text().strip())
    assert row["sim"] >= 0.9
    assert row["edit_weight"] == "light"


def test_sensitive_flag_on_personal_comp(tmp_path):
    pp = tmp_path / "p.jsonl"
    out = run({"recipient": "Ops (payroll)", "message_id": "m1",
               "draft": "here is my salary model from my latest paystub",
               "sent": "attached my comp model, W-2 gross-up as discussed, $26,877 / mo"}, pp)
    assert "[sensitive]" in out
    assert json.loads(pp.read_text().strip())["sensitive"] is True


def test_deal_size_is_not_sensitive(tmp_path):
    """Round sizes and valuations are normal comms; only personal comp/medical flags."""
    pp = tmp_path / "p.jsonl"
    run({"recipient": "Sam (investor)", "message_id": "m1",
         "draft": "confirming the $4M round at a $20M pre",
         "sent": "confirmed: $4M at 20 pre, docs this week"}, pp)
    assert "sensitive" not in json.loads(pp.read_text().strip())


def test_sent_ts_preserved(tmp_path):
    pp = tmp_path / "p.jsonl"
    run({"recipient": "Sam", "draft": "d", "sent": "s", "message_id": "m1",
         "sent_ts": "2026-06-25T15:57:02Z"}, pp)
    assert json.loads(pp.read_text().strip())["sent_ts"] == "2026-06-25T15:57:02Z"
