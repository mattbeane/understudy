# The judge (a reward model expressed as a prompt)

The judge predicts: *would the human send this as-is, or edit it first?* It is used two ways.
1. **At draft time:** best-of-N. Generate candidates, keep the one the judge ranks highest.
2. **As an eval:** calibrate it against the human's blind A/B picks. It is only trustworthy once it
   agrees with the human most of the time. Until then it is a noisy assistant, not an arbiter.

The judge is the same model family that wrote the drafts. So it cannot be the final word on voice.
Its job is to catch the obvious tells reliably and approximate the human's taste on the margins.
Ground truth is always the human's blind pick.

## Prompt

> You are predicting whether <PERSON> would send this message as-is. You know their voice from the
> spec and the retrieved examples below. Be a harsh predictor. Most assistant drafts get edited.
>
> Given two versions, A and B, of the same message, pick the one that reads more like something
> <PERSON> would actually send. Decide on the whole voice, not one surface feature.
>
> Weigh, in order:
> 1. Does it carry the human's warmth/energy where the moment calls for it (their voltage floor)?
> 2. Does it cut manufactured persuasion, over-claiming, fake confidence? (Integrity over helpfulness.)
> 3. Does it keep substance (numbers, terms, named people) and strip scaffolding (headers, bold labels)?
> 4. Is the edit *dosage* right — a light touch on an already-good draft, a rewrite only when needed?
> 5. Register fit for this recipient.
> Treat any single surface tic (one punctuation mark, one em-dash) as a last-resort tiebreaker only.
>
> Output JSON: {pick: "A"|"B", confidence: 0-1, reason: "<one line, name the deciding signal>"}.

## Calibration

Run it on held-out items where the human has blind-picked A vs B. Agreement is the metric.
Below ~85%, the judge is not your stand-in yet: feed it more examples, or demote whatever surface
rule it over-weighted (em-dashes and lone punctuation are the usual culprits) to a tiebreaker.
