# Radiant of Human Consciousness

A 3D web app inspired by Isaac Asimov's Foundation, mapping the evolution of human consciousness. Milestones of thought are plotted along a logarithmic time axis (deep time to the present day), with positions tied to their geographical origins on Earth.

## Live Demo
- Netlify: https://prime-radiant.netlify.app/

## Features

- **535 milestones** of human thought, from *Habitual Bipedalism* (-7,000,000 BCE) to the present day, each tied to a geographic origin and category
- **Influence Web** — 154 curated `influenced → influenced-by` edges rendered as curved arcs (`influences.json`); selecting a node highlights its lineage in gold
- **Logarithmic timeline** — equal screen space per order of magnitude of age, so 7 million years unfold at honest pacing. Play / pause / replay animation plus a scrubbable slider
- **Seldon Query (semantic search)** — ask by meaning ("how did fire shape early human society"); powered by sqlite-vec + the `nomic-embed-text` embedding model via Ollama
- Filters by category, time period, and keyword

---

# User Guide

## 1. Running the Prime Radiant

### Quick look (visualization only, no setup beyond a static server)

```bash
python -m http.server 8000
# open http://localhost:8000
```

On hosted deployments (Netlify) everything above works; the Seldon semantic-search panel degrades gracefully to keyword search.

### Full experience (Seldon semantic search, local)

Requires [Python 3.10+](https://python.org), [Ollama](https://ollama.com) with two small models, and two pip packages (`flask`, `sqlite-vec`, plus `openpyxl` for the Excel tooling):

```bash
ollama list                # verify nomic-embed-text is installed
pip install flask sqlite-vec openpyxl
python build_seldon_db.py  # one-time: embed all milestones into seldon.db (~1 min, needs Ollama)
python seldon_server.py    # serves app + /api/seldon on http://127.0.0.1:4173
# open http://127.0.0.1:4173/
```

> Tip: use `http://127.0.0.1:4173/` rather than `localhost` (avoids IPv6 resolution issues on some Windows setups). `ollama list` checks the model; start Ollama via its desktop app if it errors.

## 2. The Seldon Engines

The engines form a pipeline: **A** heals the past, **B** maps the gaps, **C** harvests the frontier, and the **Future Sector** projects what the trends imply. All outputs are *drafts* — nothing enters `milestones.json` (the canon) without a human's deliberate promotion, and nothing is published without a commit. Engine B and the Future Sector are manual; Engine C runs automatically alongside the server.

### Engine A — Influence Link Prediction (manual)

`python predict_edges.py`

Reads the semantic vectors in `seldon.db` and finds milestone pairs that are semantically close, chronologically ordered, and not yet linked — probable missing influence edges. With a "many-worlds" safety rule its results live in **`predicted_edges.json`**, separate from canon:

- promotion into `influences.json` is a separate, human-approved step
- also flags suspicious near-duplicate entries (pairs ≤ 2 years apart)

### Engine B — Gap Analysis (manual)

`python seldon_gaps.py`

Finds where the map of human achievement is thin and writes **`GAP_REPORT.md`**:

1. **Temporal deserts** — same-category chronological jumps far larger than the category's typical pace
2. **Missing intermediates** — semantically tight pairs separated by a large time gap and no recorded edge
3. **Orphaned milestones** — entries with zero influence edges
4. **Coverage skew** — milestone counts per era and per category

The same report is appended (dedupe-safe) to the user's `TODO_AI_Research.md` when run on the maintainer's machine. Engine B flags suspects only — historical verification stays human.

### Engine C — Frontier Scanner (automatic while the server runs)

Runs by itself: `seldon_server.py` launches it in the background and re-scans every 24 hours (a freshness stamp prevents re-scans on restart). Set `PR_FRONTIER_AUTO=0` before starting the server to disable, or run manually any time:

`python seldon_frontier.py`

Each scan: fetches recent items from arXiv (6 categories) and Phys.org / Nature / ScienceDaily RSS (default window: last 730 days) → drops anything the existing milestones already cover (semantic dedupe vs `seldon.db`) → one local-LLM pass scores the freshest items for *milestone-worthiness* → drafts the top 15 as schema-complete candidate entries. Needs Ollama with an embedding model and a small chat model (e.g. `qwen2.5:7b`, configurable via `DRAFT_MODEL` in the script).

Outputs: **`FRONTIER_REPORT.md`** (human-readable) and **`frontier_candidates.json`** (machine-readable), plus a run log in `frontier_auto.log`. Every candidate cites its source URL and is a draft for human verification — never auto-promoted.

### Future Sector — Speculative Projection (manual)

`python seldon_future.py [--with-candidates]`

Pure math, no network: within each category it fits sliding windows of year-intervals to a geometric shrink (acceleration), tolerating one non-shrinking step as noise, and continues the fit one step to project the next node's year.

- projections **past the current year** are forward predictions (e.g. sociology ~2028, art ~2030)
- projections **at or before** the present are reported as "overdue by trend"
- `--with-candidates` adds a read-only what-if: what would unlock if Engine C's drafts were promoted (nothing is promoted by it)

Outputs: **`FUTURE_SECTOR.md`** and `future_sector.json`. Every projection is labeled SPECULATIVE — trend math, not fact. Never promote these into `milestones.json`; if rendered in the app they should be ghost/dashed nodes only.

## 3. Maintainer workflow after any dataset change

```bash
python regen_xlsx.py       # refresh both Excel masters (project copy + Documents copy)
python build_seldon_db.py  # re-embed (stop seldon_server.py first)
python seldon_server.py    # restart; check http://127.0.0.1:4173/api/health shows the new row count
```

Then commit when *you* decide the change is canon.

## How to Contribute
This dataset contains 535 entries, each signifying a milestone in human history, with equal representation of all nations' and regions' contributions. Particularly welcome: new influence edges (`influences.json`), new milestones, and Engine C candidate verifications. See `BACKFILL_REVIEW.md` for the review/promotion discipline and the equality principle. If you find this project interesting, please develop it further, visualizing humanity's intellectual journey!

## License

This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
