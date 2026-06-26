# reconcile — the self-feeding loop (routine definition)

This is what the scheduled agent does each run (weekly, or on-demand). It turns
"Matt sends an edited draft" into "a new verified, hand-authored pair the spec
learns from" — with zero manual harvesting. It encodes every hard-won rule.

## Each run

1. **Read new captures.** `corpus/ledger.jsonl` holds the drafts Claude staged since
   the last run (the PostToolUse capture hook writes them). Use `corpus/v3/_reconcile_cursor`
   (a timestamp) to process only new entries; update it at the end.

2. **Fetch the real send, with provenance.** For each captured draft, find the message
   Matt actually sent: Gmail (`search_threads` + `get_thread`) or Slack (`search` + `read_thread`),
   matching the draft's recipient/subject/thread, authored by Matt, at or after the draft time.
   Copy the body verbatim and record the real `message_id`. **If you cannot fetch it, skip it.
   Never synthesize, paraphrase, or guess a send.** (This is the v2 failure; it cost us a full rebuild.)

3. **Filter and append.** Pipe each pair to the helper, which enforces the rules and appends:
   ```
   echo '{"ep_id":..,"recipient":..,"channel":..,"claude_draft":..,"matt_sent":..,"message_id":..,"thread_id":..,"source":..}' \
     | python3 corpus/bin/reconcile_helper.py
   ```
   It drops bot self-posts / scheduled-task channels / "Sent using Claude" footers (provenance != authorship),
   dedups on message_id, computes sim/edit_weight, and writes to `pairs_human.jsonl`.

4. **Re-mine on a threshold.** If >= 10 new hand-authored pairs have accumulated since the last
   spec derivation, run an open re-extraction + adversary pass over the pairs and write spec deltas
   to `corpus/proposals/<date>.md` for Matt to gate. **Never auto-apply a spec change.**

5. **Re-calibrate the judge** whenever Matt tags a fresh batch: re-score `bin/judge_v3.md` against the
   accumulated blind labels; if agreement drops, propose a tune. The judge is a noisy stand-in until ~85%.

6. **Log.** Append a `metrics.jsonl` line: `{period, n_new_pairs, n_skipped, skip_reasons}`.

## Why the live loop stays clean

The capture hook only fires on drafts *Claude stages for Matt to send* — human-destined comms he
asked for. It never sees the bot autoposts that contaminated the broad harvest. The authorship filter
in the helper is defense-in-depth, not the primary guard. The live path is human-in-the-loop by construction.

## Activation (needs Matt)

- The capture hook must be live: restart Claude Code after the `settings.json` PostToolUse hook is wired.
- Scheduling this routine as a recurring agent is persistent automation — it needs Matt's sign-off,
  same as the hook. Until then, run it on-demand ("reconcile the new sends").
