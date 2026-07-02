#!/usr/bin/env python3
"""
sweep.py - the sends-first reconcile core, frozen into code.

Given the messages you ACTUALLY SENT (fetched with provenance by whatever has
mailbox access) and a directory of assistant session transcripts, find the
draft behind each send and emit verified candidate pairs.

Two rules make the output trustworthy, both learned from live failures:

  1. SENDS-FIRST. Start from the mailbox, never from staged drafts. A draft you
     staged is not a draft you sent; a "shipped it" in chat is not provenance.
  2. THE DRAFT MUST PRECEDE THE SEND. Only assistant turns timestamped before
     the send time are candidates. A restatement written after the send usually
     matches better than the true draft (people write cleaner once the answer
     exists); without the clock, the match pairs a message with its own echo and
     the edit delta reads backwards. The guard also stops a reconcile session,
     which quotes fetched sends, from matching its own quotes. Fail-closed:
     turns without timestamps are excluded, and a send without sent_ts is
     skipped outright.

A send with no adequate pre-send match is human-authored: skipped, no pair.

Input (--sends): jsonl, one send per line (see docs/schemas.md):
  {message_id, sent, sent_ts, recipient, [thread_id], [channel], [context], [ep_id]}

Transcripts (--transcripts): a directory of session .jsonl files.
  --format claude-code (default): lines carrying {timestamp, message: {role:
    "assistant", content: [{type: "text", text: ...}]}} (or top-level type).
  --format simple: lines of {ts, role, text}.

Output: one candidate pair per line on stdout, ready for reconcile_helper.py.
With --apply, each candidate is piped through the helper for you (provenance,
authorship, dedup, sensitive-flagging all enforced there). Diagnostics on stderr.

Usage:
  python3 bin/sweep.py --sends sends.jsonl --transcripts ~/sessions [--apply]
"""
import argparse
import difflib
import glob
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

HELPER = pathlib.Path(__file__).resolve().parent / "reconcile_helper.py"
STOP = set("about after all also because before could every from have here just like more most "
           "other should since some their there these they this that what when where which while "
           "will would your".split())


def parse_ts(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _turns_claude_code(path):
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        m = o.get("message", o)
        if (m.get("role") or o.get("type")) != "assistant":
            continue
        c = m.get("content", "")
        if isinstance(c, list):
            c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
        if isinstance(c, str) and c.strip():
            yield parse_ts(o.get("timestamp")), c


def _turns_simple(path):
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if o.get("role") == "assistant" and isinstance(o.get("text"), str) and o["text"].strip():
            yield parse_ts(o.get("ts")), o["text"]


def load_turns(root, fmt="claude-code", skip_prefixes=("agent-", "journal"), min_len=400):
    """Return (turns, n_unstamped). Unstamped turns are EXCLUDED, not guessed at."""
    reader = _turns_claude_code if fmt == "claude-code" else _turns_simple
    turns, n_unstamped = [], 0
    for f in sorted(glob.glob(os.path.join(str(root), "*.jsonl"))):
        base = os.path.basename(f)
        if any(base.startswith(p) for p in skip_prefixes):
            continue
        try:
            for ts, text in reader(f):
                if len(text) < min_len:
                    continue
                if ts is None:
                    n_unstamped += 1
                    continue
                turns.append((base[:12], ts, text))
        except OSError:
            continue
    return turns, n_unstamped


def norm(s):
    """Formatting-normalize for similarity: strip quote markers, bullets, markdown,
    collapse whitespace. Re-formatting is not editing."""
    s = re.sub(r"^\s*>\s?", "", s, flags=re.M)
    s = re.sub(r"^\s*[-*•]\s+", "", s, flags=re.M)
    s = re.sub(r"[*_#`]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def anchors(sent, k=12):
    """A few rare-ish tokens from the send, used as a cheap prefilter."""
    toks = []
    for w in re.findall(r"[a-z][a-z'-]{6,}", sent.lower()):
        if w not in STOP and w not in toks:
            toks.append(w)
    return set(toks[:k])


def aligned_region(turn_text, sent_text, min_block=13):
    """The span of the turn that lines up with the send: the draft, minus chat framing.
    autojunk=False is required: difflib's default marks common characters as junk on
    prose-length strings and fragments the blocks. The span is widened to paragraph
    boundaries so the draft keeps its own opening and close."""
    sm = difflib.SequenceMatcher(None, turn_text, sent_text, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= min_block]
    if not blocks:
        return turn_text.strip()
    start = blocks[0].a
    end = blocks[-1].a + blocks[-1].size
    pstart = turn_text.rfind("\n\n", 0, start)
    start = pstart + 2 if pstart != -1 else 0
    pend = turn_text.find("\n\n", end)
    end = pend if pend != -1 else len(turn_text)
    region = turn_text[start:end]
    return re.sub(r"^\s*>\s?", "", region, flags=re.M).strip()


def find_draft(send, turns, min_ratio=0.12, min_draft=300):
    """Best PRE-SEND turn for this send, or (None, reason)."""
    ts = parse_ts(send.get("sent_ts"))
    sent = send.get("sent") or ""
    if ts is None:
        return None, "no sent_ts (temporal guard impossible; fail-closed)"
    anc = anchors(sent)
    ns = norm(sent)
    best = None
    for sess, tts, text in turns:
        if tts >= ts:
            continue
        if anc and not any(a in text.lower() for a in anc):
            continue
        r = difflib.SequenceMatcher(None, norm(text), ns, autojunk=False).ratio()
        if best is None or r > best[0]:
            best = (r, sess, tts, text)
    if best is None:
        return None, "no pre-send turn matches (human-authored)"
    r, sess, tts, text = best
    if r < min_ratio:
        return None, f"best pre-send match too weak (r={r:.2f}; human-authored)"
    draft = aligned_region(text, sent)
    if len(draft) < min_draft:
        return None, f"aligned draft too short ({len(draft)}c)"
    return {"draft": draft, "match_ratio": round(r, 3), "draft_session": sess,
            "draft_ts": tts.isoformat()}, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sends-first reconcile: find the draft behind each real send.")
    ap.add_argument("--sends", required=True, help="jsonl of {message_id, sent, sent_ts, recipient, ...}")
    ap.add_argument("--transcripts", required=True, help="directory of session .jsonl files")
    ap.add_argument("--format", default="claude-code", choices=["claude-code", "simple"])
    ap.add_argument("--min-ratio", type=float, default=0.12, help="floor on the normalized full-turn match")
    ap.add_argument("--min-draft", type=int, default=300, help="floor on the aligned-draft length")
    ap.add_argument("--min-sent", type=int, default=200, help="sends shorter than this are scheduling/acks: skipped")
    ap.add_argument("--min-turn", type=int, default=400, help="assistant turns shorter than this are ignored")
    ap.add_argument("--skip-prefix", action="append", default=None,
                    help="transcript filename prefixes to skip (default: agent-, journal)")
    ap.add_argument("--apply", action="store_true", help="pipe each candidate through reconcile_helper.py")
    a = ap.parse_args(argv)

    sends, bad = [], 0
    for ln in open(a.sends, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            sends.append(json.loads(ln))
        except json.JSONDecodeError:
            bad += 1
    if bad:
        print(f"warning: {bad} malformed line(s) in {a.sends}", file=sys.stderr)

    skips = tuple(a.skip_prefix) if a.skip_prefix else ("agent-", "journal")
    turns, n_unstamped = load_turns(a.transcripts, a.format, skips, a.min_turn)
    print(f"sweep: {len(turns)} timestamped assistant turns, {len(sends)} sends", file=sys.stderr)
    if n_unstamped:
        print(f"warning: {n_unstamped} turn(s) lacked timestamps and were excluded (fail-closed)", file=sys.stderr)

    out = []
    for s in sends:
        mid = s.get("message_id")
        if not mid:
            print(f"skip (no message_id): {str(s)[:60]}", file=sys.stderr)
            continue
        if len(s.get("sent") or "") < a.min_sent:
            print(f"skip {mid}: sent too short (scheduling/ack)", file=sys.stderr)
            continue
        found, why = find_draft(s, turns, a.min_ratio, a.min_draft)
        if not found:
            print(f"skip {mid}: {why}", file=sys.stderr)
            continue
        cand = {"ep_id": s.get("ep_id") or f"sweep-{mid}",
                "recipient": s.get("recipient", ""), "channel": s.get("channel", ""),
                "context": s.get("context", ""), "message_id": mid,
                "thread_id": s.get("thread_id", ""), "sent_ts": s.get("sent_ts"),
                "source": f"sweep {found['draft_session']}@{found['draft_ts'][:16]} r={found['match_ratio']}",
                "draft": found["draft"], "sent": s["sent"]}
        out.append(cand)
        print(json.dumps(cand, ensure_ascii=False))

    if a.apply:
        for cand in out:
            res = subprocess.run([sys.executable, str(HELPER)], input=json.dumps(cand),
                                 capture_output=True, text=True)
            print(f"apply {cand['message_id']}: {(res.stdout or res.stderr).strip()}", file=sys.stderr)

    print(f"sweep done: {len(out)} candidate pair(s) from {len(sends)} send(s)", file=sys.stderr)
    return out


if __name__ == "__main__":
    main()
