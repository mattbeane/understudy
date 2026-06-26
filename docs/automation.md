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

## Validation without tagging

The blind A/B tagger is the only place a human is required, because the human pick is the
ground truth. But there is a second ground truth that is free and already fetched: **what you
actually sent.** So you can measure effectiveness continuously without tapping anything:

- For each situation, keep the **cold** draft (no pipeline) and the **pipeline** draft.
- At reconcile, fetch the **sent** message.
- Whichever draft lands closer to the sent message wins. (`bin/auto_effectiveness.py`)

This runs every cycle, scores the pipeline against reality rather than a forced preference,
and needs zero human input. It is arguably a better signal than the tagger.

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
  steady, `auto_effectiveness` not regressing on the new pairs), write the diff to version
  control, keep a one-command rollback. Self-driving, with a seatbelt.
- **Gate:** write the proposed delta to `proposals/<date>.md` and apply on one nod.

Default to the interlock if you want true hands-off; keep the gate if voice drift scares you
more than manual review costs you. Never auto-apply silently with no rollback.

## What ends up automated

| Step | Automated? | How |
|---|---|---|
| Capture drafts | yes | transcript mine at reconcile (hook for tool-staged drafts) |
| Reconcile (fetch sends, append pairs) | yes | at session start, where connectors live |
| Effectiveness + judge calibration | yes | against the real send (`auto_effectiveness.py`) |
| Spec re-derivation | yes, guarded | interlock + rollback, or one-nod gate |
| Blind A/B label | no, by design | optional human audit; never the model grading itself |
