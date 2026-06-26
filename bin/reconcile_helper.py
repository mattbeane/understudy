#!/usr/bin/env python3
"""
reconcile_helper.py - the deterministic half of the self-feeding loop.

The reconcile routine (a scheduled agent) fetches the real send for each captured
draft from Gmail/Slack. It pipes the resulting pair here. This helper enforces the
two hard-won rules and appends a clean pair to the corpus:

  1. PROVENANCE: a real message_id must be present (the agent fetched it).
  2. AUTHORSHIP: bot self-posts / scheduled-task channels / "Sent using Claude"
     footers are NOT the human's voice even when his account sent them. Drop them.
  3. DEDUP: skip if this message_id is already in the corpus.

stdin: one JSON object
  {ep_id, recipient, channel, claude_draft, matt_sent, message_id, thread_id, source}
Appends a verified, hand-authored pair to pairs_human.jsonl and prints the decision.
"""
import json, re, sys, difflib, pathlib

HUMAN = pathlib.Path(__file__).resolve().parent.parent / "corpus/pairs.jsonl"
BOT = re.compile(r'self;|self-post|scheduled-task|writing-momentum|pipeline channel|research feed|morning brief', re.I)
BOT_FOOTER = re.compile(r'sent using claude|via (zapier|cron|scheduled)', re.I)

def existing_ids():
    ids = set()
    if HUMAN.exists():
        for ln in HUMAN.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                try: ids.add(json.loads(ln).get("message_id"))
                except: pass
    return ids

def main():
    try:
        p = json.loads(sys.stdin.read())
    except Exception as e:
        print(f"SKIP: bad json ({e})"); return

    mid = p.get("message_id")
    rec = p.get("recipient", "")
    draft = p.get("draft", "") or ""
    sent = p.get("sent", "") or ""

    if not mid:
        print("SKIP: no message_id (provenance fails)"); return
    if not sent or not draft:
        print("SKIP: empty draft or send"); return
    if BOT.search(rec) or re.match(r'^C0[A-Z0-9]{8}\b', rec) or BOT_FOOTER.search(sent):
        print(f"SKIP: authorship (bot/self-post: {rec[:40]})"); return
    if mid in existing_ids():
        print(f"SKIP: dup ({mid})"); return

    sim = round(difflib.SequenceMatcher(None, draft, sent).ratio(), 4)
    row = {
        "ep_id": p.get("ep_id") or f"live-{mid}",
        "recipient": rec, "channel": p.get("channel", ""),
        "source": p.get("source", ""), "message_id": mid, "thread_id": p.get("thread_id", ""),
        "sim": sim, "edit_weight": "heavy" if sim < 0.85 else "light",
        "draft": draft, "sent": sent,
    }
    with open(HUMAN, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"KEPT: {rec[:36]} | sim {sim} ({row['edit_weight']}) | msg {mid}")

if __name__ == "__main__":
    main()
