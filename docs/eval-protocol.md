# Eval protocol

How a claim like "the spec won 13 to 3" gets made, end to end, so you can reproduce
it on your own corpus and so the numbers mean what they say. The repo ships a tiny
synthetic batch (`corpus/eval.example/`) you can run start to finish in a minute.

## The ground truth is a blind human pick

Not a string metric, not the judge. The only thing that settles "is this more you" is
you, choosing between two versions without knowing which is which. Everything else is
an instrument calibrated against that.

## The flow

1. **Assemble candidates.** For each held-out item, gather the versions you want to
   compare as `corpus/eval.example/<source>.jsonl` (`{id, text}`). The example ships
   three sources: `draft` (cold assistant draft), `revised` (spec rewrite), `sent`
   (what was actually sent, the reference, not scored against itself).

2. **Write the blind key.** `panel-key.json` maps each id to `{A, B}` source names.
   Randomize which side each version lands on so position carries no signal.

3. **Build the tagger.**
   ```bash
   python3 bin/build_tagger.py corpus/eval.example
   ```
   Open `understudy-tagger.html`. It shows A vs B with a word-level diff, hides the
   sources, and records keyboard picks (`a` / `b` / `t` for tie). Press `e` to export
   `understudy-picks-eval.example.json`.

4. **Score.** Resolve each pick back through `picked_source`:
   - **Win rate** = how often the version under test (e.g. `revised`) beat its baseline
     (e.g. `draft`), excluding ties. "13 to 3" and "15 to 2" are these counts.
   - **Judge agreement** = run `bin/judge.md` on the same A/B items and compare its pick
     to yours. That fraction is the `agreement` you log to `metrics.jsonl`. Below ~85%
     the judge is a noisy assistant, not an arbiter. Feed it more examples or demote
     whatever surface rule it over-weighted (em-dashes, lone punctuation) to a tiebreaker.

## What keeps it honest

- **Provenance before a pair is eligible.** The `sent` text must trace to a real fetched
  message (its `message_id`), or it never enters the corpus. The eval cannot grade against
  a target that was invented. That was the v2 failure this whole protocol exists to prevent.
- **Blind position.** The key is written before tagging and read only at scoring.
- **Ties count as ties.** Don't fold them into the winner; report them.
- **Name the caveats with the number.** Small-n, single-human, single-judge, and the judge
  is the same model family that wrote the drafts. The direction is the claim, not a benchmark.

## Reproduce the shipped example

```bash
python3 bin/build_tagger.py corpus/eval.example   # -> understudy-tagger.html
# tag the 3 items, export, then compute win-rate from picked_source
```

Three items is too few to mean anything. It exists to exercise the exact pipeline the
real eval uses, on data that exposes nobody.
