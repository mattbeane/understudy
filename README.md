# Understudy

![Understudy social preview](assets/understudy-social-preview-shakespearean.jpg)

An understudy learns your part by watching you play it, then goes on in your place. This one
watches what you change about an AI's drafts, learns your voice from the difference, and writes
the next one as you.

No fine-tuning. Validated against your own blind judgment, not a vibe.

Built in an afternoon by Matt Beane with Claude, then stress-tested until it stopped lying.

---

## The idea in one breath

Every time an AI drafts an email for you and you edit it before sending, you produce a perfect
training example: *here is what the machine wrote, here is what I actually sent.* That signal is
already being generated. Almost nobody captures it. The Understudy captures it, distills the
difference into a model of your voice, and uses that to draft toward you instead of toward generic-AI.

The whole thing is expressed as data and prompts, not weights. That makes it cheap, instantly
editable, and fully inspectable. You can read every rule and trace it to a real message you sent.

## The bet: no fine-tuning

A "voice model" without training, in five parts:

1. **A corpus** of `(assistant draft -> what you sent)` pairs, plus your steering ("shorter", "warmer"),
   tagged by recipient.
2. **A spec**, distilled from the corpus: the moves you add, the tells you cut, your lexicon, your
   per-recipient registers. Re-derived on a cadence.
3. **Retrieval** at draft time: pull your nearest real edits for that recipient and condition on them.
   Nearest-neighbor few-shot is the no-weights stand-in for fine-tuning.
4. **A judge**: an LLM scoring "would they send this?", calibrated against your blind A/B picks.
5. **A held-out eval** so claims are measured, not asserted.

## The loop

```
 you ask for a draft
        |
   RETRIEVE  your nearest real edits for this recipient  (bin/retrieve.py)
        |
   DRAFT     toward the SENT style, not generic-AI
        |
   DOSAGE    cap the edit budget; near-right drafts get a light touch  (bin/dosage.py)
        |
   JUDGE     self-score, revise once  (bin/judge.md)
        |
   you edit and send  --->  CAPTURE the edit  --->  RECONCILE into the corpus  (bin/reconcile_helper.py)
        ^                                                      |
        +------------------ the spec re-derives ---------------+
```

## The honest part (this is where the credibility is)

The system was confidently wrong twice before it was right. That arc is the most useful thing here.

- **v1** scored the spec with string-distance against the messages actually sent, on a sample where
  the drafts were already nearly identical to the sends. It concluded the spec made drafts *worse*.
  A blind human check overturned it: string-distance measures overlap, not voice.
- **v2** found the real error (v1 had built a *cold* model; the human's edits mostly *add* warmth,
  not strip it). Then the v2 evaluation harness, asked to find "what the human sent," *fabricated*
  plausible sends it could not actually retrieve. The human caught it cold on the first screen:
  *"I did not ship either of these."* Root cause: the harvest required a real message to exist, but
  never required *proof* that it did.
- **v3** made proof non-negotiable. Every "sent" message is fetched from the live mailbox with its
  real message id, or it is **discarded**. 38 of them were dropped rather than invented. The spec,
  rebuilt on verified-only data, then won a blind A/B test **13 to 3**. The drafting pipeline,
  validated the same way, won **15 to 2**.

The measurement only became trustworthy at the moment it was forced to be as honest as the person it
was modeling. That is not a footnote. It is the whole method.

## The rules that fell out of it

- **Provenance, not plausibility.** A ground-truth example must trace to a real artifact (here, a
  mailbox message id). If you can't fetch it, you don't have it. Never synthesize the target.
- **Authorship is not provenance.** A message your account *sent* is not necessarily one you *wrote*.
  Scheduled bot posts passed the provenance check and polluted the corpus until the human flagged
  them. Filter for human-in-the-loop authorship on top of provenance.
- **Dosage is the recurring failure.** The number-one bug, three times over, was over-editing a draft
  that was already close. A draft that needs four small cuts and gets a full rewrite moves *away* from
  the human. The fix is a gate that measures how off-voice a draft is and caps the edit budget.
- **Warmth is a floor, not a ceiling** (for this human). The edits almost never strip energy; they add
  it. A cold model is the predictable failure mode of learning only from deletions.
- **Adversarial distillation.** Every candidate voice-pattern is attacked by a skeptic pass that hunts
  counterexamples in the real sends. What can't be refuted survives; absolutes get demoted to tendencies.
- **The human is the gate.** The judge is a noisy stand-in. Blind human picks are the only ground truth,
  and every spec change is approved by the human, never auto-applied.

## Results, with the caveats attached

- ~560 work sessions mined; 52 provenance-verified pairs; **36 after the authorship filter**.
- Spec validated **13/16** on blind human A/B picks. Drafting pipeline validated **15/17**.
- Judge agrees with the human ~**81%** (small, in-sample; tightens as labels accrue).

These are small-n, single-human, single-judge numbers, scored partly with a voice-blind string metric
and a spec the eval had partial sight of. They are directional, not a benchmark. The direction is not
ambiguous, and every number above is honest about what it is.

## Build your own

You supply one thing: `corpus/pairs.jsonl`, your own `(draft -> sent)` pairs. They accrue passively
once you capture them. Pair schema:

```json
{"ep_id":"...","recipient":"Sam (investor)","context":"...","draft":"<what the AI wrote>",
 "sent":"<what you actually sent>","sim":0.41,"edit_weight":"heavy"}
```

The reference implementation (`bin/`):
- `retrieve.py` - register + nearest real edits as conditioning. Configure `BUCKETS` to your recipients.
- `dosage.py` - the edit-budget governor. Scans a draft, returns a tier and the exact tells to remove.
- `judge.md` - the reward-model prompt and how to calibrate it.
- `reconcile_helper.py` - appends a new pair with provenance + authorship + dedup enforced.
- `reconcile.md` - the routine that fetches your real sends and feeds the loop.
- `build_tagger.py` - generates a keyboard-driven blind A/B tagger so the human can label fast.

Run the example out of the box (no setup, it falls back to the synthetic corpus):
```bash
python3 bin/retrieve.py --recipient "Sam (investor)" --k 2
echo 'Hi Sam, *Round:* confirming $4M...' | python3 bin/dosage.py --bucket "Investors / board"
python3 bin/build_tagger.py   # builds a blind A/B tagger from corpus/eval.example/
```
Then drop in your own `corpus/pairs.jsonl` and it drafts toward you instead of the example.

Schemas for every artifact: [docs/schemas.md](docs/schemas.md). The exact eval flow: [docs/eval-protocol.md](docs/eval-protocol.md).

## What's in here, and what isn't

This repo is the **method and the code**. It does **not** contain anyone's real correspondence. The
working corpus (actual emails, numbers, customer threads) stays private on the author's machine and
is never committed. The example pairs are synthetic. That separation is the point: share the loop,
keep the data.

## License

MIT. Take it, build your own, tell us what your voice turned out to be.
