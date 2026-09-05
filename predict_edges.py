"""Seldon Engine A - Influence link prediction.

Predicts missing influence edges between EXISTING milestones using the
semantic vectors in seldon.db. Predictions are written to predicted_edges.json
and NEVER touch influences.json - promotion is a separate, human-approved step.

Score = cosine similarity (vectors are L2-normalized, so sim = 1 - dist^2/2).
Ordering: influence flows forward in time (from earlier milestone to later).
"""
import json, os, sqlite3, struct, urllib.request
import sqlite_vec

_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_ROOT, "seldon.db")
EDGE_PATH = os.path.join(_ROOT, "influences.json")
OUT_PATH = os.path.join(_ROOT, "predicted_edges.json")

SIM_THRESHOLD = 0.72      # minimum cosine similarity to consider
MAX_PER_NODE = 4          # cap predicted edges per milestone (avoid hub spam)
MAX_TOTAL = 120
MAX_YEARS_BACK = 2000     # influence plausible within 2000 years of the source

db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

rows = db.execute("select id, title, year, category from seldon_meta order by year").fetchall()
titles = {r[0]: r[1] for r in rows}
by_title = {r[1]: r[0] for r in rows}
years = {r[0]: r[2] for r in rows}
cats = {r[0]: r[3] for r in rows}

existing = set()
inf = json.load(open(EDGE_PATH, encoding="utf-8"))
for e in inf["edges"]:
    existing.add((e["from"], e["to"]))
    existing.add((e["to"], e["from"]))   # either direction counts as known

# collect candidates from each node's KNN
candidates = {}
for mid, title, year, cat in rows:
    if year is None:
        continue
    vec = db.execute("select embedding from seldon_vectors where id = ?", (mid,)).fetchone()[0]
    hits = db.execute("""
        select v.id, distance from seldon_vectors v
        where v.embedding match ? and k = 15
        order by distance""", (vec,)).fetchall()
    for hid, dist in hits:
        if hid == mid:
            continue
        sim = 1 - dist * dist / 2
        if sim < SIM_THRESHOLD:
            continue
        # order: earlier -> later (strict); skip same-year pairs
        if years[mid] < years[hid]:
            src, dst, s = mid, hid, sim
        elif years[hid] < years[mid]:
            src, dst, s = hid, mid, sim
        else:
            continue
        if years[dst] - years[src] > MAX_YEARS_BACK:
            continue
        pair = (titles[src], titles[dst])
        if pair in existing or (pair[1], pair[0]) in existing:
            continue
        key = (src, dst)
        if key not in candidates or sim > candidates[key][0]:
            candidates[key] = (sim, src, dst)

ranked = sorted(candidates.values(), reverse=True)

# per-node cap, then global cap
out, per_node = [], {}
for sim, src, dst in ranked:
    if per_node.get(src, 0) >= MAX_PER_NODE or per_node.get(dst, 0) >= MAX_PER_NODE:
        continue
    gap = years[dst] - years[src]
    same_cat = cats[src] == cats[dst]
    out.append({
        "from": titles[src], "to": titles[dst],
        "similarity": round(sim, 4),
        "yearsBetween": gap,
        "sameCategory": same_cat,
        "suggestedInfluence": f"{titles[src]} contributed to {titles[dst]}"
    })
    per_node[src] = per_node.get(src, 0) + 1
    per_node[dst] = per_node.get(dst, 0) + 1
    if len(out) >= MAX_TOTAL:
        break

doc = {
    "_comment": "PREDICTED influence edges - review and promote selected entries into influences.json. Not rendered as fact.",
    "generatedBy": "Seldon Engine A (semantic link prediction over seldon.db)",
    "parameters": {"similarityThreshold": SIM_THRESHOLD, "maxPerNode": MAX_PER_NODE,
                   "maxYearsBetween": MAX_YEARS_BACK},
    "count": len(out),
    "edges": out,
}
json.dump(doc, open(OUT_PATH, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

print(f"candidates above threshold: {len(ranked)} | after caps: {len(out)}")
print(f"saved: {OUT_PATH}\n")
print("Top 25 predictions:")
for e in out[:25]:
    cat_note = "" if e["sameCategory"] else "  [cross-category]"
    print(f"  {e['similarity']*100:5.1f}%  {e['yearsBetween']:>6}y  {e['from'][:45]} -> {e['to'][:45]}{cat_note}")
