# Automation: fire-and-forget, honestly

The goal is a loop that improves without you babysitting it. Most of it can run on
its own. One step cannot, for a reason worth understanding rather than working around.

## Where the loop runs (and why not a 3am cron)

Reconcile fetches what you actually sent from your mailbox / chat with provenance. Those
connectors usually live inside your interactive assistant session, authenticated through
the app. A headless cron job or cloud runner often cannot see them. So a job that wakes at
3am has nothing to fetch, and the iron rule is **never fabricate a send to fill the gap**.

The fix is not to grant a background process broad mailbox access. It is to run reconcile
**in the context that already has the connectors**: at the start of your assistant sessions.
You open the tool most days, reconcile sweeps the new sends in silently, you never trigger
it by hand. Same fire-and-forget from your seat, timed to when the access actually exists.

## Capturing your drafts (the part that quietly fails)

A `PostToolUse` hook can only record drafts your assistant produces **as tool calls** (a
"create draft" / "send message" tool). Most drafts arrive as chat text you copy, edit, and
send yourself. Those fire no tool, so a hook-only capture records almost nothing.

The reliable source of your drafts is the **session transcript**, which holds them whether
they were tool calls or plain text. So the durable capture is a transcript pass at reconcile
time, not the hook alone. The hook is a bonus for tool-staged drafts; the transcript mine is
the engine. (This is also what bootstraps the first corpus.)

The mine runs **sends-first**, not drafts-first: pull what you actually sent from the mailbox,
then for each send find the draft behind it by **content overlap** against your assistant turns
across *all* recent sessions, and keep the aligned region as the draft (your chat framing around
it is not part of the comm). Three failure modes to avoid, all learned the hard way: mining only
the current session and declaring the rest empty; trusting a "shipped it" in chat as proof a
draft went out; and pairing a post-send restatement as if it were the draft, so enforce
turn-timestamp < send-timestamp before matching. A draft you staged is not a draft you sent;
only the mailbox knows what shipped, and only the clock knows which text came first.

## Validation without tagging

The blind A/B tagger is the only place a human is required, because the human pick is the
ground truth. But there is a second ground truth that is free and already fetched: **what you
actually sent.** If the loop is learning, your edits shrink: mean draft-to-sent similarity
rises and the heavy-edit rate falls, month over month. Every reconciled pair already carries
the measurement (`sim`, computed on formatting-normalized text, plus `sent_ts`), so the curve
costs nothing. `bin/trend.py` computes it; pairs from a bootstrap harvest form the baseline
cohort and dated pairs group by month. Sim up, heavy rate down: the loop is working.

An earlier revision shipped a different tag-free metric here: compare a *cold* draft and a
*pipeline* draft against the real send. Honest in principle, unusable in practice, because
nothing in a normal workflow produces the cold twin (you draft once, with the loop active),
so the metric could never run on real data. It is gone. The lesson is worth keeping: never
ship a measurement whose input the system cannot produce.

## The line you can't automate

You cannot have the model label its own A/B set. The judge is the model; a model grading its
own output is circular, and it turns the win-rate and the calibration number into fiction. The
whole method exists to keep ground truth real (provenance over plausibility, the human as the
gate). Auto-labeling quietly throws that away.

So the blind tagger stays human. But with automatic effectiveness above, it drops from "the
engine" to "an occasional optional audit": auto-assemble a batch when enough fresh pairs
accrue, pop it for a 4-minute pass, auto-score on export. Ignore it and the system still
validates itself against your real sends. Tap it now and then as an independent check that
send-proximity still tracks your felt preference.

## Spec changes: auto-apply with a guardrail, or gate

Re-deriving the spec changes how the system writes as you, so a bad one means silent voice
drift. Two honest options:

- **Auto-apply with an interlock:** apply only when the guardrails hold (judge calibration
  steady, the `trend.py` shrinkage curve not regressing on the new pairs), write the diff to version
  control, keep a one-command rollback. Self-driving, with a seatbelt.
- **Gate:** write the proposed delta to `proposals/<date>.md` and apply on one nod.

Default to the interlock if you want true hands-off; keep the gate if voice drift scares you
more than manual review costs you. Never auto-apply silently with no rollback.

## What ends up automated

| Step | Automated? | How |
|---|---|---|
| Capture drafts | yes | transcript mine at reconcile (hook for tool-staged drafts) |
| Reconcile (fetch sends, append pairs) | yes | at session start, where connectors live |
| Effectiveness | yes | edit-shrinkage trend vs your real sends (`bin/trend.py`) |
| Reconcile core (match, extract) | yes | deterministic `bin/sweep.py`, not improvised each run |
| Spec re-derivation | yes, guarded | interlock + rollback, or one-nod gate |
| Blind A/B label | no, by design | optional human audit; never the model grading itself |
