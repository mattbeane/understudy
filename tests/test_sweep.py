"""sweep.py: the temporal guard is the whole point. An echo written after the send
matches better than the true draft; the guard must pick the pre-send turn anyway."""
import json
import os
import subprocess
import sys

import pytest

import sweep

DRAFT = ("Sam - confirming the round at four million on a twenty pre. One board seat "
         "for you, one independent we name together. Docs go out this week and we "
         "close at the end of the month. Anything you want to push on before I send "
         "the papers across? I want this wrapped before the offsite.")
SENT = ("Sam - $4M at 20 pre, confirmed. One board seat for you, one independent "
        "(vacant, fills only with my sign-off). Docs out this week, close end of "
        "month. Anything feel off? Happy to talk it through before the offsite.")
ECHO = SENT + " (that is the note I sent Sam this morning, quoted back while we review it)"
PAD = " Context filler so the turn clears the minimum turn length gate." * 12


def _mk_transcripts(tmp_path, turns):
    d = tmp_path / "sessions"
    d.mkdir()
    f = d / "abc123.jsonl"
    lines = [json.dumps({"timestamp": ts, "message": {"role": "assistant",
             "content": [{"type": "text", "text": text}]}}) for ts, text in turns]
    f.write_text("\n".join(lines) + "\n")
    return d


def _mk_sends(tmp_path, rows):
    f = tmp_path / "sends.jsonl"
    f.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return f


def _send(ts="2026-06-25T16:00:00Z", **kw):
    base = {"message_id": "m1", "recipient": "Sam (investor)", "sent": SENT, "sent_ts": ts}
    base.update(kw)
    return base


def test_temporal_guard_prefers_presend_draft(tmp_path):
    turns = [("2026-06-25T15:00:00Z", DRAFT + PAD),          # true draft, before send
             ("2026-06-26T09:00:00Z", ECHO + PAD)]           # echo, after send, better match
    tr = _mk_transcripts(tmp_path, turns)
    turns_loaded, _ = sweep.load_turns(tr, min_len=100)
    found, why = sweep.find_draft(_send(), turns_loaded)
    assert found, why
    assert found["draft_ts"].startswith("2026-06-25T15")
    assert "confirming the round at four million" in found["draft"]


def test_only_postsend_match_means_no_pair(tmp_path):
    tr = _mk_transcripts(tmp_path, [("2026-06-26T09:00:00Z", ECHO + PAD)])
    turns_loaded, _ = sweep.load_turns(tr, min_len=100)
    found, why = sweep.find_draft(_send(), turns_loaded)
    assert found is None
    assert "human-authored" in why


def test_missing_sent_ts_fails_closed(tmp_path):
    tr = _mk_transcripts(tmp_path, [("2026-06-25T15:00:00Z", DRAFT + PAD)])
    turns_loaded, _ = sweep.load_turns(tr, min_len=100)
    found, why = sweep.find_draft(_send(ts=None), turns_loaded)
    assert found is None
    assert "temporal guard" in why


def test_unstamped_turns_are_excluded(tmp_path):
    d = tmp_path / "s"
    d.mkdir()
    (d / "x.jsonl").write_text(json.dumps({"message": {"role": "assistant",
        "content": [{"type": "text", "text": DRAFT + PAD}]}}) + "\n")
    turns_loaded, n_unstamped = sweep.load_turns(d, min_len=100)
    assert turns_loaded == []
    assert n_unstamped == 1


def test_end_to_end_apply_reaches_helper(tmp_path):
    tr = _mk_transcripts(tmp_path, [("2026-06-25T15:00:00Z", DRAFT + PAD)])
    sends = _mk_sends(tmp_path, [_send()])
    pairs = tmp_path / "pairs.jsonl"
    env = dict(os.environ, UNDERSTUDY_PAIRS=str(pairs))
    res = subprocess.run([sys.executable, str(sweep.pathlib.Path(sweep.__file__)),
                          "--sends", str(sends), "--transcripts", str(tr),
                          "--min-turn", "100", "--apply"],
                         capture_output=True, text=True, env=env)
    assert "KEPT" in res.stderr, res.stderr
    row = json.loads(pairs.read_text().strip())
    assert row["message_id"] == "m1"
    assert row["sent_ts"] == "2026-06-25T16:00:00Z"


def test_short_send_skipped(tmp_path):
    tr = _mk_transcripts(tmp_path, [("2026-06-25T15:00:00Z", DRAFT + PAD)])
    sends = _mk_sends(tmp_path, [_send(sent="thanks, works for me")])
    res = subprocess.run([sys.executable, str(sweep.pathlib.Path(sweep.__file__)),
                          "--sends", str(sends), "--transcripts", str(tr), "--min-turn", "100"],
                         capture_output=True, text=True)
    assert "too short" in res.stderr
    assert res.stdout.strip() == ""


def test_aligned_region_strips_chat_framing():
    turn = "Here is my take on the situation, and then the note.\n\n" + DRAFT + "\n\nWant me to stage it?"
    region = sweep.aligned_region(turn, SENT)
    assert "Here is my take" not in region
    assert "Want me to stage it" not in region
    assert "board seat" in region
