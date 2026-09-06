"""Seldon Future Sector - speculative projection (run MANUALLY: python seldon_future.py).

Pure math on the milestone chains: within each category it fits sliding
windows of intervals to a geometric shrink (acceleration), tolerating one
non-shrinking step as noise, continues the fit one step, and projects the
next node's year. Every projection is clearly labeled SPECULATIVE - it is
trend extrapolation, not fact.

Example: a chain ending with intervals 40y -> 20y -> 9y fits ratio ~0.47
and projects the next event ~4y after the last node. Projections past the
current year are reported as predictions; earlier ones as "overdue by trend".

Add --with-candidates to ALSO run a read-only SIMULATION: same math applied
to milestones.json plus Engine C's frontier_candidates.json, showing what
predictions would unlock if the drafted 2024-2026 entries were promoted.
Simulation results are printed and added to the report marked SIMULATION,
but never written to future_sector.json.

Outputs (real run):
  - future_sector.json  (machine-readable projections)
  - FUTURE_SECTOR.md    (human-readable, overwritten each run)
  - dated section appended to Desktop TODO_AI_Research.md (dedupe-safe,
    same rule as Engines A/B/C)

Read-only over milestones.json. No Ollama, no network needed.
"""
import hashlib
import json
import os
import re
import sys
from datetime import datetime

_ROOT = os.path.dirname(os.path.abspath(__file__))
MS_PATH = os.path.join(_ROOT, "milestones.json")
CAND_PATH = os.path.join(_ROOT, "frontier_candidates.json")
OUT_JSON = os.path.join(_ROOT, "future_sector.json")
OUT_MD = os.path.join(_ROOT, "FUTURE_SECTOR.md")
TODO_PATH = r"C:\Users\milan\Desktop\TODO_AI_Research.md"

MIN_NODES = 4          # chain must have >= 4 milestones (>= 3 intervals)
MIN_SHRINK = 0.5       # last interval must be < 50% of the first in the window
LAST_YEAR_MIN = 1900   # only project chains that reach the modern era
MAX_WINDOW = 6         # max intervals per fitted window
ALLOWED_BUMPS = 2      # tolerated non-shrinking steps inside a window
MAX_RATIO = 0.9        # fitted geometric ratio must be below this
MODERN_INTERVAL_MAX = 200   # first interval of a window must be <= this (years)
MAX_OUT = 15           # max predictions shown in the "ahead" section
CURRENT_YEAR = datetime.now().year


def project_category(cat, items):
    items = sorted(items, key=lambda m: m["year"])
    years = [m["year"] for m in items]
    titles = [m["title"] for m in items]
    out = []
    if len(items) < MIN_NODES:
        return out
    intervals = [b - a for a, b in zip(years, years[1:])]
    # sliding windows fitted to a geometric shrink (noise-tolerant)
    for w in range(3, min(MAX_WINDOW, len(intervals)) + 1):
        for i in range(len(intervals) - w + 1):
            run = intervals[i:i + w]
            if run[0] > MODERN_INTERVAL_MAX:      # modern-scale windows only
                continue
            if 0 in run or run[-1] >= run[0] * MIN_SHRINK:
                continue                          # 0y gaps break a geometric fit
            if sum(1 for a, b in zip(run, run[1:]) if b >= a) > ALLOWED_BUMPS:
                continue
            r = (run[-1] / run[0]) ** (1 / (w - 1))
            if r >= MAX_RATIO:
                continue
            node_end = i + w                      # last node index of the window
            last_year = years[node_end]
            if last_year < LAST_YEAR_MIN:
                continue
            next_iv = max(1, round(run[-1] * r))
            proj = last_year + next_iv
            lo = last_year + max(1, round(run[-1] * r * r))
            hi = last_year + max(2, round(run[-1] * r ** 0.5))
            out.append({
                "category": cat,
                "chain": titles[i:node_end + 1],
                "intervals": run,
                "shrinkRatio": round(r, 3),
                "projectedYear": int(proj),
                "window": [int(lo), int(hi)],
                "theme": " -> ".join(titles[max(0, node_end - 2):node_end + 1]),
                "_confidence": round(1 - r, 2),
                "_isFuture": proj > CURRENT_YEAR,
            })
    return out


def compute(ms_list):
    by_cat = {}
    for m in ms_list:
        by_cat.setdefault(m.get("category") or "uncategorized", []).append(m)
    best = {}
    for cat, items in by_cat.items():
        for p in project_category(cat, items):
            key = (p["category"], p["chain"][-1])
            if key not in best or (p["shrinkRatio"], -len(p["intervals"])) < \
                    (best[key]["shrinkRatio"], -len(best[key]["intervals"])):
                best[key] = p
    return sorted(best.values(),
                  key=lambda p: (not p["_isFuture"], p["shrinkRatio"]))


ms = [m for m in json.load(open(MS_PATH, encoding="utf-8"))["milestones"]
      if m.get("year") is not None]
projections = compute(ms)
ahead = [p for p in projections if p["_isFuture"]]
overdue = [p for p in projections if not p["_isFuture"]]

sim_ahead = []
if "--with-candidates" in sys.argv and os.path.exists(CAND_PATH):
    cands = json.load(open(CAND_PATH, encoding="utf-8"))["candidates"]
    sim = compute(ms + [c for c in cands if c.get("year") is not None])
    sim_ahead = [p for p in sim if p["_isFuture"]]

stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

doc = {
    "_comment": "FUTURE SECTOR - SPECULATIVE projections of the next node on accelerating "
                "milestone chains. NOT FACT. These describe what the trend implies, not "
                "what has happened. Never promote into milestones.json as a real entry; "
                "if used in the app, render as ghost/dashed prediction nodes only.",
    "generatedBy": "Seldon Future Sector (sliding-window geometric continuation of shrinking intervals)",
    "parameters": {"minNodes": MIN_NODES, "minShrink": MIN_SHRINK,
                   "lastYearMin": LAST_YEAR_MIN, "maxWindow": MAX_WINDOW,
                   "allowedBumps": ALLOWED_BUMPS, "maxRatio": MAX_RATIO,
                   "modernIntervalMax": MODERN_INTERVAL_MAX},
    "generated": stamp,
    "count": len(projections),
    "projections": projections,
}
json.dump(doc, open(OUT_JSON, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def rows(ps):
    out = []
    for p in ps:
        yrs = p["projectedYear"] - CURRENT_YEAR
        imp = f"about {yrs} years from now" if yrs > 0 else "the trend says it is already overdue"
        out += [f"### {p['category']}: ~{p['projectedYear']} (window {p['window'][0]}-{p['window'][1]})",
                f"- **Chain:** {p['theme']}",
                f"- **Intervals:** {' -> '.join(str(x) + 'y' for x in p['intervals'])} "
                f"(fitted ratio {p['shrinkRatio']})",
                f"- **Implication:** if the acceleration continues, the next milestone "
                f"in this chain plausibly occurs around {p['projectedYear']} - {imp}.", ""]
    return out


L = [f"## Seldon Future Sector - Speculative Projections ({stamp})", "",
     f"Method: sliding windows of 3-{MAX_WINDOW} intervals per category "
     f"(>= {MIN_NODES} nodes, last interval < {int(MIN_SHRINK * 100)}% of the first, "
     f"up to {ALLOWED_BUMPS} non-shrinking step tolerated), fitted to a geometric "
     f"shrink (ratio < {MAX_RATIO}), windows kept to modern scale "
     f"(first interval <= {MODERN_INTERVAL_MAX} y), and continued one step.", "",
     "*Every line below is SPECULATION - a trend continuation, not a fact. "
     "Never promote into milestones.json; render only as labeled ghost nodes.*", ""]
L.append(f"### Ahead of the present - projections past {CURRENT_YEAR} ({len(ahead)})")
L.append("")
if ahead:
    L += rows(ahead[:MAX_OUT])
else:
    L += [f"No chain currently projects past {CURRENT_YEAR}. Chains can only "
          "extrapolate from where the data ends - refreshing the frontier with "
          "Engine C candidates extends them.", ""]
L.append(f"### Overdue by trend - projections at or before {CURRENT_YEAR} ({len(overdue)})")
L.append("")
L += rows(overdue[:8]) or ["None.", ""]
if "--with-candidates" in sys.argv:
    L += [f"### SIMULATION - projections past {CURRENT_YEAR} if Engine C candidates are promoted "
          f"({len(sim_ahead)})", "",
          "*What-if only: milestones.json + frontier_candidates.json. Nothing was promoted. "
          "These lines exist nowhere else - not in future_sector.json.*", ""]
    L += rows(sim_ahead[:MAX_OUT]) or [
        f"Even with all Engine C candidates promoted, no chain projects past {CURRENT_YEAR} yet - "
        "the promoted entries must extend the SAME chains that are already accelerating.", ""]

body = "\n".join(L)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(body)

content_hash = hashlib.md5(re.sub(r"\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)", "", body).encode("utf-8")).hexdigest()[:10]
marker = f"<!-- seldon-future:{content_hash} -->"
block = marker + "\n" + body.rstrip() + "\n\n---\n"
pat = re.compile(r"<!-- seldon-future:[0-9a-f]{10} -->\n.*?\n---\n", re.DOTALL)
if os.path.exists(TODO_PATH):
    todo = open(TODO_PATH, encoding="utf-8").read()
    existing = pat.findall(todo)
    same = [m for m in existing if m.startswith(marker)]
    if same:
        todo = todo.replace(same[0], block)
        action = "replaced existing identical section"
    else:
        if existing:
            todo = pat.sub("", todo)
        todo = todo.rstrip() + "\n\n" + block
        action = "appended new section"
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.write(todo)
else:
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.write(block)
    action = "created TODO file with new section"


def brief(p):
    tag = "FUTURE" if p["_isFuture"] else "overdue"
    return (f"  [{tag}] {p['category']:14s} ~{p['projectedYear']} "
            f"(window {p['window'][0]}-{p['window'][1]})  r={p['shrinkRatio']}  {p['theme'][:70]}")


print(f"chains found: {len(projections)} ({len(ahead)} project past {CURRENT_YEAR})")
for p in (ahead + overdue)[:10]:
    print(brief(p))
if sim_ahead:
    print(f"\nSIMULATION (Engine C candidates promoted): {len(sim_ahead)} project past {CURRENT_YEAR}")
    for p in sim_ahead[:10]:
        print(brief(p))
print(f"saved: {OUT_JSON}")
print(f"saved: {OUT_MD}")
print(f"TODO_AI_Research.md: {action}")
