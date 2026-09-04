import json, re, os, sqlite3, struct, urllib.request, time
import sqlite_vec

_ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(_ROOT, "milestones.json")
DB_PATH = os.path.join(_ROOT, "seldon.db")
OLLAMA = "http://localhost:11434/api/embed"
MODEL = "nomic-embed-text"

def embed_batch(texts):
    req = urllib.request.Request(OLLAMA, data=json.dumps(
        {"model": MODEL, "input": texts}).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["embeddings"]

def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()

ms = sorted(json.load(open(JSON_PATH, encoding="utf-8"))["milestones"], key=lambda m: m["year"])

db = sqlite3.connect(DB_PATH)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)

db.execute("drop table if exists seldon_vectors")
db.execute("drop table if exists seldon_meta")
db.execute("create virtual table seldon_vectors using vec0(id integer primary key, embedding float[768])")
db.execute("""create table seldon_meta(
    id integer primary key, title text, year integer, category text,
    culture text, description text, url text)""")

t0 = time.time()
rows_vec, rows_meta = [], []
texts = []
for i, m in enumerate(ms):
    loc = m.get("location") or {}
    where = f"lat {loc.get('lat')}, lon {loc.get('lon')}" if loc else "location unknown"
    texts.append((f"{norm(m['title'])}. Category: {norm(m.get('category'))}. Year: {m['year']}. "
                  f"Origin: {where}. {norm(m.get('description'))}")[:4000])
    rows_meta.append((i, m["title"], m["year"], m.get("category"), m.get("culture"), norm(m.get("description")), m.get("url")))

vectors = []
BATCH = 32
for start in range(0, len(texts), BATCH):
    chunk = texts[start:start + BATCH]
    t1 = time.time()
    vectors.extend(embed_batch(chunk))
    print(f"embedded {start + len(chunk)}/{len(texts)} ({time.time() - t1:.1f}s)", flush=True)

rows_vec = []
for i, v in enumerate(vectors):
    n = sum(x * x for x in v) ** 0.5
    rows_vec.append((i, struct.pack("%df" % len(v), *[x / n for x in v])))

db.executemany("insert into seldon_vectors(id, embedding) values (?, ?)", rows_vec)
db.executemany("insert into seldon_meta values (?,?,?,?,?,?,?)", rows_meta)
db.commit()

# smoke test: KNN for a semantic query
q = embed_batch(["how did fire shape early human society"])[0]
qbytes = struct.pack("%df" % len(q), *q)
hits = db.execute("""
    select m.title, m.year, distance
    from seldon_vectors v join seldon_meta m on m.id = v.id
    where v.embedding match ? and k = 5""", (qbytes,)).fetchall()
print("\nsmoke test: 'how did fire shape early human society'")
for t, y, d in hits: print(f"  {(1 - d*d/2)*100:.1f}%  {y}  {t}")
print("\nDB ready:", DB_PATH, "| rows:", len(rows_meta), f"| {time.time()-t0:.0f}s total")
