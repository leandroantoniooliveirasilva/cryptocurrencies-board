# Conviction Board

Personal cryptocurrency scoring for long-term accumulation: category-weighted dimensions, derived actions, dashboard on GitHub Pages.

**Key property:** no server and no hosted database — the repo holds SQLite history and published snapshots.

## How it runs

- **Weekly (Sunday 12:00 UTC):** dimensions + composite → `src/pipeline/storage/history.sqlite` / `public/latest.json` (see `Agents.md` for job detail).
- **Daily (12:00 UTC):** prices, RSI, Wyckoff, GLI, Fear & Greed, RS — refreshes actions on existing composites.
- **Monthly:** discovery report under **`out/discovery/`** (watchlist edits stay manual in **`src/pipeline/assets.yaml`**).
- **Deploy:** GitHub Actions builds the site from `public/`.

Full schedule, launchd labels, and automation live in **`Agents.md`** (not duplicated here).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e .   # editable install so ``python -m pipeline.*`` finds ``src/pipeline`` (scripts also set PYTHONPATH=src)

# Optional: .env with FRED_API_KEY (GLI). Qualitative/supply use Cursor Agent CLI — run `cursor-agent login`.
./scripts/install-launchd.sh install   # macOS schedulers (UTC)

python -m pipeline.run --dimensions-only
# Optional full local run with wall-clock cap: ./scripts/run-scoring.sh

npm run build
```

## Where to read what

| Need | File |
|------|------|
| Setup, repo map (this page) | `README.md` |
| Signal framework, pipeline, commands, env, workers | `Agents.md` |
| Copy-paste Cursor Agent session prompts | `.docs/cursor-agent-prompts.md` |
| Calibration / change log | `.docs/decisions.md` |
| Long-form research & taxonomy | `.docs/research/` |
| Agent skills (watchlist discovery, scan interpretation) | `.agents/skills/crypto-discovery/`, `.agents/skills/crypto-scoring/` |

## Repository layout

**Inputs / source code** live under **`src/`**. **Generated artifacts** live under **`out/`**. **`public/`** holds the dashboard site plus **`latest.json`** (merged snapshot).

```
scripts/                 # entrypoints only (top level); sets PYTHONPATH=src when invoking Python
src/pipeline/            # Python package: assets.yaml, config.yaml, run.py, fetchers/, scoring/, storage/, discovery/prompt.md
out/reports/scoring/     # per-run JSON per asset → merged into public/latest.json
out/discovery/           # monthly discovery markdown (report_YYYY-MM.md, ensemble folders)
public/                  # dashboard bundle + latest.json (GitHub Pages root)
backtest/                # offline experiments (not scheduled jobs)
.docs/                   # calibration log, research, cursor prompts
.agents/skills/          # crypto-discovery, crypto-scoring
```

## Design principles (short)

Repo as database, append-only history, slow weekly cadence, single-user decision support. Full list: **`Agents.md`**.

## Calibration

Track framework tweaks in **`.docs/decisions.md`**.
