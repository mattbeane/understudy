#!/usr/bin/env python3
"""
retrieve.py - the retrieval layer of the understudy drafting pipeline.

Given a recipient (and optionally a description of the task), return the
conditioning block to draft against: the matching register profile + the
k nearest real (assistant-draft -> human-sent) edits from the corpus.

No embeddings needed: recipient-bucket match + lexical overlap. This is enough
at small corpus sizes and keeps the whole thing inspectable.

CONFIGURE: edit BUCKETS below to your own recipient groups. They should match
the section headers in corpus/registers.md.

Usage:
  python3 retrieve.py --recipient "Some Person" [--query "what it's about"] [--k 3] [--exclude id]
"""
import json, re, sys, argparse, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAIRS = ROOT / "corpus/pairs.jsonl"        # your verified, hand-authored (draft -> sent) pairs
REG = ROOT / "corpus/registers.md"          # per-recipient voice profiles

# CONFIGURE THESE for your own world. Keys must match registers.md section headers.
BUCKETS = {
    "Investors / board": ["investor", "board", "vc", "partner"],
    "Team": ["team", "eng", "engineering", "product", "ops"],
    "Customers / external": ["customer", "client", "vendor", "partner-ext"],
    "Academic / personal": ["prof", "academic", ".edu", "personal"],
}
STOP = set("a an the to of for and or is are was were be been on in at by with from as it this that "
           "i you he she we they me him her them my your our their re you're i'm we're it's "
           "will would can could should about into over up out so if not no yes do done get got "
           "one two three here there now then just like also more most can't don't".split())

def toks(s):
    return {w for w in re.split(r"[^a-z0-9']+", (s or "").lower()) if w and w not in STOP and len(w) > 2}

def bucket_of(recipient):
    r = (recipient or "").lower()
    best, hits = None, 0
    for b, kws in BUCKETS.items():
        h = sum(1 for k in kws if k in r)
        if h > hits:
            best, hits = b, h
    return best

def load_pairs():
    out = []
    if PAIRS.exists():
        for ln in PAIRS.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                try: out.append(json.loads(ln))
                except: pass
    return out

def register_section(bucket):
    if not bucket or not REG.exists():
        return ""
    txt = REG.read_text(encoding="utf-8")
    m = re.search(r"(^##\s+" + re.escape(bucket) + r".*?)(?=^##\s+|\Z)", txt, re.S | re.M)
    return m.group(1).strip() if m else ""

def trunc(s, n=900):
    s = s or ""
    return s if len(s) <= n else s[:n] + " ...[truncated]"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipient", required=True)
    ap.add_argument("--query", default="")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--exclude", default="")
    a = ap.parse_args()

    bucket = bucket_of(a.recipient)
    pairs = load_pairs()
    q = toks(a.recipient + " " + a.query)

    scored = []
    for p in pairs:
        if a.exclude and p.get("ep_id") == a.exclude:
            continue
        prec = (p.get("recipient") or "")
        rec_share = len(toks(a.recipient) & toks(prec))
        same_bucket = 1 if bucket and bucket_of(prec) == bucket else 0
        lex = len(q & toks(p.get("context", "") + " " + p.get("draft", "") + " " + p.get("sent", "")))
        heavy = 0.5 if p.get("edit_weight") == "heavy" else 0
        scored.append((4.0 * rec_share + 1.5 * same_bucket + 1.0 * lex + heavy, p))
    scored.sort(key=lambda x: -x[0])
    top = [p for s, p in scored[:a.k] if s > 0] or [p for s, p in scored[:a.k]]

    out = [f"# Drafting as <you> -> {a.recipient}",
           f"_bucket: {bucket or 'unclassified'}  |  corpus: {len(pairs)} pairs  |  showing {len(top)} nearest_\n"]
    reg = register_section(bucket)
    if reg:
        out.append("## Register profile\n" + reg + "\n")
    out.append("## Nearest real edits (assistant draft -> what you actually sent)\n"
               "Study the delta: what you cut, what you added, the dosage. Draft like the SENT column.\n")
    for i, p in enumerate(top, 1):
        out.append(f"### {i}. to {p.get('recipient','?')}  |  edit={p.get('edit_weight')} (sim {p.get('sim')})")
        out.append(f"**ASSISTANT DRAFT:**\n```\n{trunc(p.get('draft',''))}\n```")
        out.append(f"**YOU SENT:**\n```\n{trunc(p.get('sent',''))}\n```\n")
    out.append("## Then\n"
               "1. Draft toward the SENT style above.\n"
               "2. Run the dosage gate (`bin/dosage.py`) to cap the edit budget; remove only the tells it flags.\n"
               "3. Self-score with the judge (`bin/judge.md`); revise once toward higher.\n"
               "4. Leave conviction and values as a named hook for the human. Show the draft + one line on what you applied.")
    print("\n".join(out))

if __name__ == "__main__":
    main()
