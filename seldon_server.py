import json, os, re, sqlite3, struct, subprocess, sys, threading, time, urllib.request
from datetime import datetime

import sqlite_vec
from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "seldon.db")
OLLAMA = "http://localhost:11434/api/embeddings"
MODEL = "nomic-embed-text"

FRONTIER_SCRIPT = os.path.join(ROOT, "seldon_frontier.py")
FRONTIER_LAST_RUN = os.path.join(ROOT, "frontier_last_run.txt")
FRONTIER_LOG = os.path.join(ROOT, "frontier_auto.log")
FRONTIER_INTERVAL_H = 24          # min hours between auto-scans
FRONTIER_CHECK_S = 3600           # scheduler poll interval
FRONTIER_TIMEOUT_S = 3600
FRONTIER_AUTO = os.environ.get("PR_FRONTIER_AUTO", "1") != "0"

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
    return jsonify({
        "ok": True,
        "rows": db.execute("select count(*) from seldon_meta").fetchone()[0],
        "frontierAuto": FRONTIER_AUTO,
        "frontierLastRunHoursAgo": round(_frontier_last_run_age_h(), 1),
    })


def _frontier_last_run_age_h():
    try:
        with open(FRONTIER_LAST_RUN, encoding="utf-8") as f:
            t = datetime.fromisoformat(f.read().strip())
        return (datetime.now() - t).total_seconds() / 3600
    except Exception:
        return 1e9


def _run_frontier(trigger):
    print(f"[frontier] auto-scan starting ({trigger})...", flush=True)
    try:
        with open(FRONTIER_LOG, "a", encoding="utf-8") as log:
            log.write(f"\n===== run @ {datetime.now():%Y-%m-%d %H:%M:%S} ({trigger}) =====\n")
            log.flush()
            subprocess.run([sys.executable, FRONTIER_SCRIPT], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT,
                           timeout=FRONTIER_TIMEOUT_S)
        print("[frontier] auto-scan finished", flush=True)
    except Exception as e:
        print(f"[frontier] auto-scan failed: {e}", flush=True)


def _frontier_loop():
    time.sleep(5)   # let the server come up first
    if _frontier_last_run_age_h() >= FRONTIER_INTERVAL_H:
        _run_frontier("startup")
    while True:
        time.sleep(FRONTIER_CHECK_S)
        if _frontier_last_run_age_h() >= FRONTIER_INTERVAL_H:
            _run_frontier("scheduled")


@app.get("/")
def index():
    return send_from_directory(ROOT, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(ROOT, path)


if __name__ == "__main__":
    if FRONTIER_AUTO:
        threading.Thread(target=_frontier_loop, daemon=True).start()
        print("[frontier] Engine C auto-scanner enabled "
              f"(interval {FRONTIER_INTERVAL_H}h, disable with PR_FRONTIER_AUTO=0)")
    else:
        print("[frontier] Engine C auto-scanner disabled (PR_FRONTIER_AUTO=0)")
    app.run(host="127.0.0.1", port=4173, debug=False)
