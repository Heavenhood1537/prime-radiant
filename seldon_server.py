import json, os, re, sqlite3, struct, urllib.request
import sqlite_vec
from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "seldon.db")
OLLAMA = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

app = Flask(__name__, static_folder=None)

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)


def embed(text):
    req = urllib.request.Request(OLLAMA, data=json.dumps(
        {"model": MODEL, "prompt": text[:2000]}).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["embedding"]


@app.get("/api/seldon")
def seldon():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"results": []})
    try:
        k = min(int(request.args.get("k", 8)), 25)
    except ValueError:
        k = 8
    vec = embed(q)
    n = sum(x * x for x in vec) ** 0.5
    qbytes = struct.pack("%df" % len(vec), *[x / n for x in vec])
    hits = db.execute("""
        select m.title, m.year, m.category, m.description, m.url, m.culture, distance
        from seldon_vectors v join seldon_meta m on m.id = v.id
        where v.embedding match ? and k = ?""", (qbytes, k)).fetchall()
    return jsonify({"results": [
        {"title": t, "year": y, "category": c, "description": d,
         "url": u, "culture": cu, "score": round(1 - dist * dist / 2, 4)}
        for t, y, c, d, u, cu, dist in hits]})


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "rows": db.execute("select count(*) from seldon_meta").fetchone()[0]})


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(ROOT, path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4173, debug=False)
