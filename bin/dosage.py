#!/usr/bin/env python3
"""
dosage.py - the edit-budget gate for the drafting pipeline.

The recurring failure (v1, and the v3 pipeline demo) is over-editing a draft
that is already close to Matt's voice. This scans a cold draft for high-confidence
tells and returns an edit TIER plus the exact tells to remove. The pipeline then
edits ONLY those and preserves everything else verbatim, unless tier == REWRITE.

Usage:
  python3 dosage.py [--bucket Team] < draft.txt
  python3 dosage.py --file draft.txt
"""
import json, re, sys, argparse, pathlib

BANLIST = pathlib.Path(__file__).resolve().parent.parent / "banlist.json"

def banlist_res():
    try:
        ph = json.load(open(BANLIST))["phrases"]
        return [(p["phrase"], re.compile(p["regex"], re.I)) for p in ph
                if p["phrase"] not in ("em-dash", "filler-intensifier", "sharp")]
    except Exception:
        return []

def scan(draft, bucket=""):
    tells = []
    first = draft.strip()[:60]
    low_team = bucket.lower() in ("team", "")  # em-dash native in peer/team

    if re.match(r'^\s*(hi|hey|hello|good morning|morning|dear|greetings)\b', first, re.I):
        tells.append(("greeting", "opener greeting; this register often opens content-first"))

    labels = re.findall(r'\*[^*\n]{1,40}\*', draft)
    if labels:
        tells.append((f"asterisk-scaffolding x{len(labels)}", "strip bold/asterisk labels (the strongest tell); plain or single-underscore"))

    fillers = re.findall(r'\b(honestly|genuinely|frankly|candidly|truthfully)\b|\bto be fair\b', draft, re.I)
    if fillers:
        tells.append((f"filler-intensifier x{len(fillers)}", "cut the filler hedge"))

    for name, rx in banlist_res():
        if rx.search(draft):
            tells.append((f"banlist:{name}", "swap for the plain word"))

    dash = draft.count("—")
    if dash and not low_team:
        tells.append((f"em-dash x{dash}", "to spaced hyphen (weak in peer/team; keep there)"))

    tail = draft.strip()[-160:]
    if re.search(r'(standing by|looking forward to your|i hope this|let me know if|happy to (discuss|chat|hop|jump))', tail, re.I):
        tells.append(("ceremonial-closer", "close on a live ask, status verb, or energy beat instead"))

    if re.search(r'\*?\s*asks?\s*:?\s*\*?', draft, re.I) and len(re.findall(r'\b\w+\s+[-—]\s', draft)) >= 2:
        tells.append(("asks-block / per-person assignment", "delegate by stating your own next action, not an Asks: block"))

    persuasion = re.search(r"(time-limited|no pressure|i'?d be glad to|evidence beats|i'?m switching from|catch for you|don'?t want you to miss|real,? time-limited upside|more tips into desperation)", draft, re.I)
    if persuasion:
        tells.append(("MANUFACTURED-PERSUASION", "remove the lever, keep the fact (integrity reflex)"))

    meta = re.search(r"(which lands better|here'?s what i'?m doing|rather than a (rebuttal|point-by-point)|i'?ll answer with|because it'?s the spine)", draft, re.I)
    if meta:
        tells.append(("meta-narration", "perform the move, don't announce it"))

    # windup because-clauses (long subordinate persuasion tails)
    windups = re.findall(r',\s*(which|since|because|so that)\b[^.?!]{40,}', draft, re.I)
    if windups:
        tells.append((f"windup-clause x{len(windups)}", "tighten or cut the persuasion tail; he trims these"))

    return tells

def tier(tells, draft):
    names = " ".join(t[0] for t in tells).lower()
    hard = sum(1 for t in tells if any(k in t[0].lower() for k in
              ("manufactured", "meta", "asks-block")))
    nlabels = sum(int(re.search(r'x(\d+)', t[0]).group(1)) for t in tells if "asterisk" in t[0])
    words = len(draft.split())
    if hard or nlabels >= 3 or words > 220:
        return "REWRITE", "draft is genuinely off-voice (persuasion-essay / scaffolded / instrumentalizes a person). Full rewrite allowed."
    if len(tells) <= 3:
        return "SURGICAL", "draft is already close. Remove ONLY the tells below. Preserve all other wording, structure, and his soft defers. Do NOT add asks or restructure."
    return "LIGHT", "remove the tells below and lightly smooth. Do not add content or reorder the argument."

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", default="")
    ap.add_argument("--file", default="")
    a = ap.parse_args()
    draft = open(a.file).read() if a.file else sys.stdin.read()
    tells = scan(draft, a.bucket)
    t, why = tier(tells, draft)
    print(f"EDIT TIER: {t}")
    print(why)
    print(f"\nTells found ({len(tells)}):")
    if not tells:
        print("  (none) -> ship the draft nearly as-is; one light warmth/hedge touch at most.")
    for name, fix in tells:
        print(f"  - {name}: {fix}")
    print("\nRule: edit budget = the list above. Everything not listed stays verbatim unless TIER is REWRITE.")

if __name__ == "__main__":
    main()
