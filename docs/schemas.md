# Artifact schemas

Every file the loop reads or writes, with its shape. The point of the repo is that
the method is portable without exposing anyone's data. These schemas are how.
All `.jsonl` files are one JSON object per line.

## `corpus/pairs.jsonl`: the corpus (the spine)

Your verified `(assistant draft -> what you sent)` pairs. Gitignored; you supply it.
`corpus/pairs.example.jsonl` is a synthetic stand-in with the same shape.

| field | type | required | notes |
|---|---|---|---|
| `ep_id` | string | yes | stable id for the pair |
| `recipient` | string | yes | e.g. `"Sam (investor)"`; the bucket is derived from it |
| `context` | string | no | one line on what the message is about (used for lexical match) |
| `draft` | string | yes | what the assistant wrote |
| `sent` | string | yes | what you actually sent |
| `sim` | number | no | char-overlap ratio of draft vs sent (0-1); computed by the helper |
| `edit_weight` | string | no | `"heavy"` if sim < 0.85 else `"light"` |
| `message_id` | string | when reconciled | provenance: the real mailbox/Slack id the send was fetched from |
| `thread_id` | string | no | provenance: the containing thread |
| `channel` | string | no | `"email"`, `"slack"`, ... |
| `source` | string | no | free-form origin tag |

Legacy alias: `claude_draft` / `matt_sent` are accepted on input wherever `draft` / `sent` are.

## `ledger.jsonl`: captured drafts awaiting reconcile

Written by the PostToolUse capture hook each time the assistant stages a draft for you.

| field | type | notes |
|---|---|---|
| `ts` | string | ISO 8601; the reconcile cursor compares against this |
| `recipient` | string | best-known recipient at draft time |
| `channel` | string | `"email"` / `"slack"` |
| `draft` | string | the staged text |
| `ep_id` | string | optional correlation id |

## `corpus/eval.example/<source>.jsonl`: an eval source

One file per candidate version named in the panel key (`draft`, `revised`, `sent`, ...).

| field | type | notes |
|---|---|---|
| `id` | string | matches the panel-key id |
| `text` | string | the version's text |

## `corpus/eval.example/meta.jsonl`: eval display metadata

| field | type | notes |
|---|---|---|
| `id` | string | matches the panel-key id |
| `recipient` | string | shown above the A/B cards |
| `channel` | string | shown above the A/B cards |
| `context` | string | shown above the A/B cards |

## `panel-key.json`: the blind A/B map

```json
{ "ex-1": {"A": "revised", "B": "draft"}, "ex-2": {"A": "draft", "B": "revised"} }
```

`A` and `B` are source names (file stems). The tagger hides which is which; the key
is read back only at scoring time. A source literally named `sent` is shown as the
post-hoc reference, never as an A/B option you score against itself.

## `understudy-picks-<label>.json`: tagger export

```json
{
  "batch": "eval.example",
  "n": 3,
  "tagged": 3,
  "picks": [
    {"item": 1, "id": "ex-1", "pick": "A", "picked_source": "revised", "note": ""}
  ]
}
```

`pick` is `"A"` | `"B"` | `"tie"`. `picked_source` resolves the blind pick back to its
source. That is what calibration and win-rate are computed from.

## `metrics.jsonl`: the run log

Free-form per-run records; the keys used so far:

| field | type | notes |
|---|---|---|
| `period` | string | run label or date |
| `n_new_pairs` | number | pairs added this reconcile |
| `n_skipped` | number | drafts dropped (no provenance / authorship / dup) |
| `skip_reasons` | object | `{reason: count}` |
| `agreement` | number | judge-vs-human agreement on a tagged batch (0-1) |
