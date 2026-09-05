"""Seldon Engine B - Gap analysis (run MANUALLY: python seldon_gaps.py).

Finds where the map of human milestones is thin:
  1. Temporal deserts  - same-category chronological jumps far larger than the
                         category's typical pace (likely missing milestones).
  2. Missing intermediates - semantically tight pairs (high cosine similarity)
                         separated by a large time gap and no recorded edge,
                         suggesting bridging discoveries are absent.
  3. Orphaned milestones - entries with zero influence edges.
  4. Coverage skew     - milestone counts per era and per category.

Outputs:
  - GAP_REPORT.md in this folder (overwritten each run)
  - the same text appended to the Desktop TODO_AI_Research.md; if the report
    content is unchanged since the last run, the existing section is replaced
    instead of duplicated.

Read-only over milestones.json / influences.json / seldon.db - touches nothing
canonical. Requires Ollama only if seldon.db needs rebuilding.
"""
import hashlib
import json
import os
import re
import sqlite3
import statistics
from datetime import datetime

import sqlite_vec

_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_ROOT, "seldon.db")
EDGE_PATH = os.path.join(_ROOT, "influences.json")
MS_PATH = os.path.join(_ROOT, "milestones.json")
OUT_MD = os.path.join(_ROOT, "GAP_REPORT.md")
TODO_PATH = r"C:\Users\milan\Desktop\TODO_AI_Research.md"

SIM_THRESHOLD = 0.80   # "same chain" similarity for missing intermediates
MIN_GAP_YEARS = 50     # bridge candidates must span at least this
DESERT_RATIO = 1.8     # gap must exceed 1.8x the category's median pace
MIN_CAT_SIZE = 4       # categories smaller than this are skipped for deserts
TOP_N = 20             # rows shown per section

db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

rows = db.execute("select id, title, year, category from seldon_meta where year is not null order by year").fetchall()
years = {r[0]: r[2] for r in rows}
titles = {r[0]: r[1] for r in rows}
cats = {r[0]: r[3] for r in rows}

degree = {}
inf = json.load(open(EDGE_PATH, encoding="utf-8"))
for e in inf["edges"]:
    degree[e["from"]] = degree.get(e["from"], 0) + 1
    degree[e["to"]] = degree.get(e["to"], 0) + 1


def fmt_year(y):
    if y < 0:
        return f"{-y:,} BCE"
    return f"{y} CE"


def fmt_gap(g):
    if g >= 10000:
        return f"{g / 1000:,.0f}k y"
    return f"{g:,} y"


# ---------- 1. temporal deserts (same-category consecutive gaps) ----------
by_cat = {}
for mid, title, year, cat in rows:
    by_cat.setdefault(cat, []).append((year, title))

deserts = []
for cat, items in by_cat.items():
    if len(items) < MIN_CAT_SIZE:
        continue
    gaps = [b[0] - a[0] for a, b in zip(items, items[1:])]
    med = statistics.median(gaps)
    if med <= 0:
        continue
    for (ya, ta), (yb, tb), gap in zip(items, items[1:], gaps):
        ratio = gap / med
        if ratio >= DESERT_RATIO:
            deserts.append((ratio, cat, ta, ya, tb, yb, gap, med))
deserts.sort(reverse=True)

# ---------- 2. missing intermediates (semantic bridges) ----------
bridges = {}
for mid, title, year, cat in rows:
    vec = db.execute("select embedding from seldon_vectors where id = ?", (mid,)).fetchone()[0]
    hits = db.execute("""
        select v.id, distance from seldon_vectors v
        where v.embedding match ? and k = 8
        order by distance""", (vec,)).fetchall()
    for hid, dist in hits:
        if hid == mid:
            continue
        sim = 1 - dist * dist / 2
        if sim < SIM_THRESHOLD:
            continue
        if abs(years[hid] - years[mid]) < MIN_GAP_YEARS:
            continue
        if (titles[mid], titles[hid]) in degree or (titles[hid], titles[mid]) in degree:
            continue
        src, dst = (mid, hid) if years[mid] < years[hid] else (hid, mid)
        key = (src, dst)
        if key not in bridges or sim > bridges[key][0]:
            bridges[key] = (sim, src, dst)
bridges = sorted(bridges.values(), reverse=True)[:TOP_N]

# ---------- 3. orphaned milestones ----------
orphans = [t for mid, t, y, c in rows if degree.get(t, 0) == 0]

# ---------- 4. coverage skew ----------
def era(y):
    if y < -3000:
        return "Prehistory (< 3000 BCE)"
    if y < 500:
        return "Ancient (3000 BCE - 500 CE)"
    if y < 1500:
        return "Medieval (500-1500)"
    if y < 1800:
        return "Early Modern (1500-1800)"
    if y < 1945:
        return "Modern (1800-1945)"
    return "Contemporary (1945-)"

era_counts = {}
cat_counts = {}
for mid, title, year, cat in rows:
    era_counts[era(year)] = era_counts.get(era(year), 0) + 1
    cat_counts[cat] = cat_counts.get(cat, 0) + 1

# ---------- format report ----------
now = datetime.now()
stamp = now.strftime("%Y-%m-%d %H:%M")
L = []
L.append(f"## Seldon Engine B - Gap Report ({stamp})")
L.append("")
L.append(f"Dataset: {len(rows)} milestones | {len(inf['edges'])} influence edges | run manually via `python seldon_gaps.py`")
L.append("")

L.append(f"### 1. Temporal deserts - where history is suspiciously thin (top {min(TOP_N, len(deserts))} of {len(deserts)})")
L.append("")
if deserts:
    L.append("| Pace vs. cat. median | Gap | Category | From | To |")
    L.append("|---|---|---|---|---|")
    for ratio, cat, ta, ya, tb, yb, gap, med in deserts[:TOP_N]:
        L.append(f"| {ratio:,.0f}x | {fmt_gap(gap)} | {cat} | {ta} ({fmt_year(ya)}) | {tb} ({fmt_year(yb)}) |")
else:
    L.append("No deserts found above the threshold.")
L.append("")

L.append(f"### 2. Likely missing intermediates - semantically tight, temporally far, unlinked (top {min(TOP_N, len(bridges))} of {len(bridges)})")
L.append("")
if bridges:
    L.append("| Similarity | Span | Between |")
    L.append("|---|---|---|")
    for sim, src, dst in bridges:
        L.append(f"| {sim * 100:.1f}% | {fmt_gap(years[dst] - years[src])} | {titles[src]} ({fmt_year(years[src])}) <-> {titles[dst]} ({fmt_year(years[dst])}) |")
else:
    L.append("No bridge candidates above the threshold.")
L.append("")

L.append(f"### 3. Orphaned milestones - zero influence edges ({len(orphans)})")
L.append("")
if orphans:
    for t in orphans[:40]:
        L.append(f"- {t}")
    if len(orphans) > 40:
        L.append(f"- ... and {len(orphans) - 40} more")
else:
    L.append("None - every milestone has at least one edge.")
L.append("")

L.append("### 4. Coverage skew")
L.append("")
L.append("**By era:** " + " | ".join(f"{k}: {v}" for k, v in era_counts.items()))
L.append("")
L.append("**Top/bottom categories:** " +
         " | ".join(f"{k}: {v}" for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])[:5]) +
         " ... " +
         " | ".join(f"{k}: {v}" for k, v in sorted(cat_counts.items(), key=lambda x: x[1])[:5]))
L.append("")
L.append("*Engine B flags suspects only - historical verification is human. Nothing canonical was touched.*")
L.append("")
body = "\n".join(L)

# ---------- save into prime-radiant ----------
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(body)

# ---------- append to Desktop TODO_AI_Research.md (dedupe by content hash) ----------
content_hash = hashlib.md5(re.sub(r"\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)", "", body).encode("utf-8")).hexdigest()[:10]
marker = f"<!-- seldon-gap-report:{content_hash} -->"
block = marker + "\n" + body.rstrip() + "\n\n---\n"

if os.path.exists(TODO_PATH):
    todo = open(TODO_PATH, encoding="utf-8").read()
    pattern = re.compile(r"<!-- seldon-gap-report:[0-9a-f]{10} -->\n.*?\n---\n", re.DOTALL)
    existing = pattern.findall(todo)
    same = [m for m in existing if m.startswith(marker)]
    if same:
        todo = todo.replace(same[0], block)
        action = "replaced existing identical section"
    else:
        if existing:
            todo = pattern.sub("", todo)  # drop stale Engine B sections, keep one
        todo = todo.rstrip() + "\n\n" + block
        action = "appended new section"
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.write(todo)
else:
    with open(TODO_PATH, "w", encoding="utf-8") as f:
        f.write(block)
    action = "created TODO file with new section"

# ---------- console summary ----------
print(f"milestones: {len(rows)} | edges: {len(inf['edges'])}")
print(f"temporal deserts: {len(deserts)} | bridge candidates: {len(bridges)} | orphans: {len(orphans)}")
print(f"saved: {OUT_MD}")
print(f"TODO_AI_Research.md: {action}")
