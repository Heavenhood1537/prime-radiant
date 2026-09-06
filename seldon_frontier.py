"""Seldon Engine C - Frontier scanner (run MANUALLY: python seldon_frontier.py).

Harvests the RECENT REAL: scans free news/journal sources (arXiv API, Phys.org,
Nature, ScienceDaily RSS) for the last N days, drops anything your existing
505 milestones already cover (semantic dedupe via seldon.db), then drafts
schema-complete milestone candidates for the surviving items with a local
Ollama LLM.

Everything is a DRAFT: output goes to frontier_candidates.json and
FRONTIER_REPORT.md, plus a dated section appended to the Desktop
TODO_AI_Research.md (replaced, never duplicated, if unchanged). Nothing
canonical (milestones.json / influences.json) is touched - promotion is a
separate, human-approved step, same rule as Engine A and B.

Requirements: Ollama running (nomic-embed-text + DRAFT_MODEL), internet.
"""
import hashlib
import html
import json
import os
import re
import sqlite3
import struct
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

import sqlite_vec

_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_ROOT, "seldon.db")
MS_PATH = os.path.join(_ROOT, "milestones.json")
OUT_JSON = os.path.join(_ROOT, "frontier_candidates.json")
OUT_MD = os.path.join(_ROOT, "FRONTIER_REPORT.md")
TODO_PATH = r"C:\Users\milan\Desktop\TODO_AI_Research.md"

OLLAMA_EMBED = "http://localhost:11434/api/embed"
OLLAMA_CHAT = "http://localhost:11434/api/chat"
EMBED_MODEL = "nomic-embed-text"
DRAFT_MODEL = "qwen2.5:7b"

DAYS_BACK = 730          # scan window: "last couple of years"
WORTHINESS_POOL = 40     # items LLM-scored for registry-worthiness
TOP_K = 15               # candidates sent to the LLM drafter
SIM_EXISTING = 0.85      # drop items this close to an existing milestone
ARXIV_CATS = ["quant-ph", "cs.AI", "cond-mat.mtrl-sci",
              "physics.app-ph", "physics.plasm-ph", "astro-ph.IM"]
RSS_FEEDS = [
    ("Phys.org", "https://phys.org/rss-feed/"),
    ("Nature", "https://www.nature.com/nature.rss"),
    ("ScienceDaily Tech", "https://www.sciencedaily.com/rss/top/technology.xml"),
]
UA = {"User-Agent": "Mozilla/5.0 (Prime Radiant frontier scanner)"}


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def parse_xml(data):
    # some feeds (Nature) intermittently contain invalid control characters
    cleaned = re.sub(b"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", data)
    return ET.fromstring(cleaned)


def norm_ws(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def strip_html(s):
    return norm_ws(html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))))


def ollama_embed_batch(texts):
    req = urllib.request.Request(OLLAMA_EMBED, data=json.dumps(
        {"model": EMBED_MODEL, "input": texts}).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["embeddings"]


# ---------------- sources ----------------
def fetch_arxiv():
    items = []
    for cat in ARXIV_CATS:
        url = (f"https://export.arxiv.org/api/query?search_query=cat:{cat}"
               f"&sortBy=submittedDate&sortOrder=descending&max_results=25")
        root = None
        for attempt in (1, 2):
            try:
                root = parse_xml(http_get(url))
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  arXiv {cat}: FAILED ({e})")
                time.sleep(5)
        if root is None:
            continue
        ns = {"a": "http://www.w3.org/2005/Atom"}
        n = 0
        for e in root.findall("a:entry", ns):
            try:
                pub = datetime.fromisoformat(e.findtext("a:published", "", ns))
            except ValueError:
                continue
            items.append({
                "source": f"arXiv {cat}",
                "title": norm_ws(e.findtext("a:title", "", ns)),
                "summary": norm_ws(e.findtext("a:summary", "", ns))[:900],
                "url": (e.findtext("a:id", "", ns) or "").strip(),
                "date": pub,
            })
            n += 1
        print(f"  arXiv {cat}: {n} items")
        time.sleep(4)   # arXiv API politeness
    return items


def parse_date(raw):
    raw = norm_ws(raw)
    if not raw:
        return None
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", raw):   # ISO only, never "EDT" etc.
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        return None


def fetch_rss():
    items = []
    for name, url in RSS_FEEDS:
        try:
            root = parse_xml(http_get(url))
        except Exception as e:
            print(f"  {name}: FAILED ({e})")
            continue
        n = 0
        for it in root.iter():
            if not (it.tag == "item" or it.tag.endswith("}item")):
                continue
            title = strip_html(it.findtext("title") or next(
                (c.text for c in it if c.tag.endswith("}title")), ""))
            if not title:
                continue
            raw_date = next((c.text for c in it
                             if c.tag == "pubDate" or c.tag.endswith("}date")
                             or c.tag == "date"), "")
            date = parse_date(raw_date)
            if date is None:
                continue
            items.append({
                "source": name,
                "title": title,
                "summary": strip_html(it.findtext("description") or next(
                    (c.text for c in it if c.tag.endswith("}description")
                     or c.tag == "description"), ""))[:900],
                "url": (it.findtext("link") or next(
                    (c.text for c in it if c.tag.endswith("}link")), "")).strip(),
                "date": date,
            })
            n += 1
        print(f"  {name}: {n} items")
    return items


# ---------------- dedupe against existing milestones ----------------
db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

cut = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)

print("fetching sources...")
raw = fetch_arxiv() + fetch_rss()
seen, items = set(), []
for it in raw:
    key = norm_ws(it["title"]).lower()[:90]
    if key in seen or not it["title"]:
        continue
    seen.add(key)
    if it["date"] and it["date"].replace(tzinfo=it["date"].tzinfo or timezone.utc) < cut:
        continue
    items.append(it)
print(f"raw: {len(raw)} | unique & within {DAYS_BACK} days: {len(items)}")

print("embedding for dedupe...")
vecs = ollama_embed_batch([f"{i['title']}. {i['summary']}"[:2000] for i in items])
for it, v in zip(items, vecs):
    n = sum(x * x for x in v) ** 0.5
    qb = struct.pack("%df" % len(v), *[x / n for x in v])
    best = db.execute("""
        select distance from seldon_vectors v
        where v.embedding match ? and k = 1""", (qb,)).fetchone()
    it["maxSimExisting"] = round(1 - best[0] * best[0] / 2, 4) if best else 0.0

fresh = [it for it in items if it["maxSimExisting"] < SIM_EXISTING]
fresh.sort(key=lambda x: (1 - x["maxSimExisting"]), reverse=True)

SYSTEM = ("You are the Frontier Scanner of the Prime Radiant, a curated registry "
          "of human milestone achievements across all domains. You draft registry "
          "entries from real recent news/research items. Be factual, concise, "
          "never invent facts that are not in the item.")


# ---------------- worthiness filter (one batched LLM call) ----------------
def score_worthiness(pool):
    """Score each item 0-10 for 'permanent milestone of human achievement' value."""
    listing = "\n".join(f"{i}. [{p['source']}] {p['title']}" for i, p in enumerate(pool, 1))
    user = f"""You curate a permanent registry of human milestone achievements (entries like
"First Human Heart Transplant", "Discovery of Penicillin", "First Quantum Communication Satellite").
Score each numbered item 0-10 for how registry-worthy it is:
- 8-10: a discrete achievement, discovery, first, or deployment of lasting significance
- 3-7: genuinely new but incremental or narrow technique
- 0-2: obituaries, opinion pieces, editorials, policy talk, studies of problems, minor analyses
Items:
{listing}
Respond with ONLY a JSON object: {{"scores": [{{"i": 1, "s": 7}}, ...]}} giving a score for every item."""
    for attempt in (1, 2):
        req = urllib.request.Request(OLLAMA_CHAT, data=json.dumps({
            "model": DRAFT_MODEL, "stream": False, "format": "json",
            "options": {"temperature": 0.1},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
        }).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.loads(json.load(r)["message"]["content"])
            scores = {int(x["i"]): int(x["s"]) for x in out["scores"]
                      if isinstance(x.get("s"), (int, float))}
            if len(scores) >= len(pool) // 2:
                return scores
        except Exception as e:
            print(f"  worthiness scoring attempt {attempt} failed: {e}")
    return None


if len(fresh) > TOP_K:
    pool = fresh[:WORTHINESS_POOL]
    print(f"scoring {len(pool)} freshest items for milestone-worthiness...")
    scores = score_worthiness(pool)
    if scores:
        scored = [(scores.get(i, 0), 1 - p["maxSimExisting"], p) for i, p in enumerate(pool, 1)]
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        picks = [p for s, _, p in scored if s >= 3][:TOP_K]
        print("worthiness top scores:",
              ", ".join(f"{s} ({p['title'][:40]})" for s, _, p in scored[:5]))
        if not picks:
            picks = [p for _, _, p in scored[:TOP_K]]
    else:
        picks = pool[:TOP_K]   # fall back to pure novelty ranking
else:
    picks = fresh[:TOP_K]
print(f"fresh: {len(fresh)} -> drafting top {len(picks)}")

# ---------------- LLM drafting ----------------
ms = json.load(open(MS_PATH, encoding="utf-8"))["milestones"]
categories = sorted({m["category"] for m in ms if m.get("category")})
CURRENT_YEAR = datetime.now().year


def draft(it):
    user = f"""Draft ONE milestone registry entry from this real recent item.
Rules:
- "title": concise milestone-style name (like "Solid-State Battery Pilot Production Line"). No trailing punctuation.
- "year": integer, the year the event occurred, taken from the item date.
- "category": choose exactly one from: {", ".join(categories)}
- "description": 2-3 factual sentences based ONLY on the item. No hype adjectives.
- "originators": list of the people, teams or organizations responsible (from the item).
- "culture": the country or region, or null if unclear.
- "url": {it['url'] or "null"}
- "humanType": null
Item source: {it['source']}
Item title: {it['title']}
Item date: {it['date'].strftime('%Y-%m-%d')}
Item summary: {it['summary']}
Respond with ONLY a JSON object with keys: title, year, category, description, originators, culture, url, humanType."""
    for attempt in (1, 2):
        req = urllib.request.Request(OLLAMA_CHAT, data=json.dumps({
            "model": DRAFT_MODEL, "stream": False, "format": "json",
            "options": {"temperature": 0.3},
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
        }).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(json.load(r)["message"]["content"])
        except Exception as e:
            print(f"  draft attempt {attempt} failed: {e}")
            continue
        title = norm_ws(out.get("title")).rstrip(".,;")
        year = out.get("year")
        if not title or not isinstance(year, int) or year < 2000 or year > CURRENT_YEAR + 1:
            continue
        cat = out.get("category") if out.get("category") in categories else "technology"
        return {
            "category": cat,
            "title": title,
            "description": norm_ws(out.get("description"))[:900],
            "year": year,
            "yearsAgo": CURRENT_YEAR - year,
            "location": None,
            "humanType": out.get("humanType") or None,
            "culture": out.get("culture") or None,
            "originators": [norm_ws(o) for o in (out.get("originators") or []) if norm_ws(o)][:4] or None,
            "ideas": [title],
            "url": out.get("url") or it["url"] or None,
            "_status": "draft - human review required before promotion",
            "_source": it["source"],
            "_sourceTitle": it["title"],
            "_sourceDate": it["date"].strftime("%Y-%m-%d"),
            "_maxSimExisting": it["maxSimExisting"],
        }
    return None


drafts = []
for i, it in enumerate(picks, 1):
    print(f"drafting {i}/{len(picks)}: {it['title'][:70]}")
    d = draft(it)
    if d:
        drafts.append(d)
        print(f"  -> [{d['category']}] {d['title']} ({d['year']})")
    else:
        print("  -> skipped (LLM draft failed validation)")

# ---------------- outputs ----------------
doc = {
    "_comment": "FRONTIER CANDIDATES - real recent milestones drafted by Engine C for human review. "
                "Promote selected entries into milestones.json (both copies) only after verification.",
    "generatedBy": f"Seldon Engine C (frontier scanner, sources: arXiv + RSS, drafter: {DRAFT_MODEL})",
    "parameters": {"daysBack": DAYS_BACK, "topK": TOP_K, "simExistingCutoff": SIM_EXISTING},
    "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "count": len(drafts),
    "candidates": drafts,
}
json.dump(doc, open(OUT_JSON, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

now = datetime.now().strftime("%Y-%m-%d %H:%M")
L = [f"## Seldon Engine C - Frontier Scan ({now})", "",
     f"Window: last {DAYS_BACK} days | raw items: {len(raw)} | fresh after dedupe: {len(fresh)} | drafted: {len(drafts)}",
     "Sources: arXiv (" + ", ".join(ARXIV_CATS) + ") + " + ", ".join(n for n, _ in RSS_FEEDS), "",
     "*All entries are DRAFTS from a local LLM - verify each before promoting into milestones.json.*", ""]
for d in drafts:
    L.append(f"### [{d['category']}] {d['title']} ({d['year']})")
    L.append(f"- **Description:** {d['description']}")
    if d["originators"]:
        L.append(f"- **Originators:** {', '.join(d['originators'])}")
    if d["culture"]:
        L.append(f"- **Region:** {d['culture']}")
    L.append(f"- **Source:** {d['_source']} - {d['_sourceTitle']} ({d['_sourceDate']})")
    if d["url"]:
        L.append(f"- **URL:** {d['url']}")
    L.append("")
body = "\n".join(L)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(body)

content_hash = hashlib.md5(re.sub(r"\(\d{4}-\d{2}-\d{2} \d{2}:\d{2}\)", "", body).encode("utf-8")).hexdigest()[:10]
marker = f"<!-- seldon-frontier:{content_hash} -->"
block = marker + "\n" + body.rstrip() + "\n\n---\n"
pat = re.compile(r"<!-- seldon-frontier:[0-9a-f]{10} -->\n.*?\n---\n", re.DOTALL)
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

print(f"\nfrontier candidates: {len(drafts)}")
print(f"saved: {OUT_JSON}")
print(f"saved: {OUT_MD}")
print(f"TODO_AI_Research.md: {action}")
with open(os.path.join(_ROOT, "frontier_last_run.txt"), "w", encoding="utf-8") as f:
    f.write(datetime.now().isoformat())
print("frontier_last_run.txt stamped")
