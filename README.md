# Radiant of Human Consciousness

A 3D web app inspired by Isaac Asimov's Foundation, mapping the evolution of human consciousness. Milestones of thought are plotted along a logarithmic time axis (deep time to the present day), with positions tied to their geographical origins on Earth.

## Live Demo
- Netlify: https://prime-radiant.netlify.app/

## Features

- **505 milestones** of human thought, from *Habitual Bipedalism* (-7,000,000 BCE) to the present day, each tied to a geographic origin and category
- **Influence Web** — 154 curated `influenced → influenced-by` edges rendered as curved arcs (`influences.json`); selecting a node highlights its lineage in gold
- **Logarithmic timeline** — equal screen space per order of magnitude of age, so 7 million years unfold at honest pacing. Play / pause / replay animation plus a scrubbable slider
- **Seldon Query (semantic search)** — ask by meaning ("how did fire shape early human society"); powered by sqlite-vec + the `nomic-embed-text` embedding model via Ollama
- Filters by category, time period, and keyword

## Running locally

The 3D visualization works from any static server:

```bash
python -m http.server 8000
# open http://localhost:8000
```

### Seldon semantic search (optional, local)

The semantic search needs a small local Flask server plus [Ollama](https://ollama.com) with the `nomic-embed-text` model:

```bash
ollama list                # verify nomic-embed-text is installed
python seldon_server.py    # serves the app + /api/seldon on http://127.0.0.1:4173
```

On hosted deployments the Seldon panel degrades gracefully — keyword search still works.

Rebuilding the vector index after changing `milestones.json`:

```bash
python build_seldon_db.py
```

## How to Contribute
This updated set contains ~505 entries each signifying a milestone in human history. Particularly welcome: new influence edges (`influences.json`) and new milestones. If you find this project interesting, please develop it further, visualizing humanity's intellectual journey!

## License

This project is licensed under the GNU General Public License v3.0. See the LICENSE file for details.
