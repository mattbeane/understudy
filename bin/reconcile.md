# reconcile: the self-feeding loop (routine definition)

This is what the scheduled agent does each run (weekly, or on-demand). It turns
"you send an edited draft" into "a new verified, hand-authored pair the spec
learns from", with zero manual harvesting. It encodes every hard-won rule.

## Each run

1. **Work from what you SENT, not from staged drafts.** A capture hook only sees tool-staged
   drafts; most drafts are chat text that fires no tool, and a draft you staged is not proof you
   sent it (you may edit it, replace it, or not send at all). So treat your mailbox as ground
   truth: pull your real sends since the cursor (Gmail/Slack `in:sent newer_than:Nd`), and record
   each one's real `message_id`. `ledger.jsonl` is a bonus for tool-staged drafts, not the engine.

2. **Find the draft behind each send by content, across ALL recent sessions.** For each
   substantive send, search your assistant turns in *every* recent session transcript (not just
   the current one) for the turn whose body best overlaps the sent message; the aligned region is
   your draft. A send with no matching draft was written by the human alone, so skip it (no pair).
   **Provenance is the send's real `message_id`, never the words "shipped it" in chat.** If you
   cannot fetch the send, skip it. Never synthesize, paraphrase, or guess one. (This is the v2
   failure; it cost a full rebuild. The lazy variant is mining one session and calling it done.)

   **And the draft must precede the send.** Match only turns timestamped before the send time.
   A restatement written after the send usually matches better than the true draft, because the
   author writes cleaner once the answer exists; an unguarded content match will pair a message
   with its own echo and learn the edit delta backwards. The same clock check keeps the reconcile
   session itself, which quotes fetched sends, from matching its own quotes.

3. **Filter and append.** Pipe each pair to the helper, which enforces the rules and appends.
   Canonical field names are `draft` and `sent` (the legacy `claude_draft` / `matt_sent` are
   accepted as aliases):
   ```
   echo '{"ep_id":"...","recipient":"...","channel":"...","context":"...","draft":"...","sent":"...","message_id":"...","thread_id":"...","source":"..."}' \
     | python3 bin/reconcile_helper.py
   ```
   It drops bot self-posts / scheduled-task channels / "Sent using Claude" footers (provenance != authorship),
   dedups on message_id, computes sim/edit_weight, and appends to `corpus/pairs.jsonl`.
   (Override the destination with `UNDERSTUDY_PAIRS=/path/to/pairs.jsonl`.)

4. **Re-mine on a threshold.** If >= 10 new hand-authored pairs have accumulated since the last
   spec derivation, run an open re-extraction + adversary pass over the pairs and write spec deltas
   to `corpus/proposals/<date>.md` for the human to gate. **Never auto-apply a spec change.**

5. **Re-calibrate the judge** whenever a fresh batch is tagged: re-score `bin/judge.md` against the
   accumulated blind labels; if agreement drops, propose a tune. The judge is a noisy stand-in until ~85%.

6. **Log.** Append a `metrics.jsonl` line: `{period, n_new_pairs, n_skipped, skip_reasons}`.

## Why the live loop stays clean

The capture hook only fires on drafts *the assistant stages for you to send*, the human-destined comms you
asked for. It never sees the bot autoposts that contaminated the broad harvest. The authorship filter
in the helper is defense-in-depth, not the primary guard. The live path is human-in-the-loop by construction.

## Activation (needs you)

- The capture hook must be live: restart your assistant after the `settings.json` PostToolUse hook is wired.
- Scheduling this routine as a recurring agent is persistent automation, so it needs your sign-off,
  same as the hook. Until then, run it on-demand ("reconcile the new sends").
