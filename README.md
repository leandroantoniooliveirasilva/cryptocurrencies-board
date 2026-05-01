# Conviction Board

A personal cryptocurrency scoring system for long-term accumulation. Scores assets across category-weighted dimensions, derives action signals, and displays results on a dashboard.

**Key property**: No server, no hosted database. The repo is the database.

## How It Works

Scheduling is **macOS launchd** (`scripts/install-launchd.sh`), with `**TZ=UTC`** in the plists. Typical flow:

```
Sunday 12:00 UTC — weekly dimensions (pipeline.run --dimensions-only)
├── Qualitative dimensions, DefiLlama where needed, composite + tiers
├── Snapshots → history.sqlite; latest.json (macro reused from prior publish)
└── commit / push

Every day 12:00 UTC — daily indicators (pipeline.indicators)
├── RSI, Wyckoff from prices, GLI, Fear & Greed, RS vs BTC
├── Re-derive action on existing composites → latest.json
└── commit / push

GitHub Actions → deploy /public to GitHub Pages → dashboard reads latest.json
```

Optional: run a **full** `pipeline.run` (no `--dimensions-only`) locally for RSI/action in one shot; see `scripts/run-scoring.sh` for a wall-clock cap.

## Signal Framework

### Dimensions

Assets are scored 0-100 on the dimensions that apply to each `asset_category` (see `pipeline/config.yaml`), weighted by asset type:


| Dimension           | What It Measures                                       |
| ------------------- | ------------------------------------------------------ |
| Institutional       | ETF flows, fund holdings, custody adoption             |
| Value capture       | Holder-accruing fees / real yield (category-dependent) |
| Regulatory          | Jurisdictional clarity, compliance                     |
| Supply              | Exchange reserves, holder distribution                 |
| Adoption / activity | Category-specific usage (where weighted)               |


Wyckoff phase is **not** part of the composite score; it is updated on the **daily indicators** run and used for action filters.

### Action States


| State                 | When         | What It Means                              |
| --------------------- | ------------ | ------------------------------------------ |
| **strong-accumulate** | Leaders only | True capitulation or quality dip — act now |
| **accumulate**        | Leaders only | Tranche-eligible zone                      |
| **promote**           | Runner-ups   | Crossing leader threshold                  |
| **hold**              | Leaders      | Default — patience (also downgrade target) |
| **await**             | Runner-ups   | Signal building                            |
| **observe**           | Observation  | Watch only                                 |
| **stand-aside**       | Any          | Distribution risk — do not engage          |


### Signal Logic

**Strong Accumulate** fires rarely (~5-15x/year across the watchlist):

1. **Capitulation**: Weekly RSI <30 AND daily RSI <30 (82.9% hit rate)
2. **Wyckoff dip**: Phase C + daily RSI ≤32 + weekly RSI ≥42 + composite stable

**Downgrade Filters (OR logic)** — when ANY is true, signals downgrade one level (strong-accumulate→accumulate, accumulate→hold):

- **GLI contracting**: Global Liquidity Index today < 75 days ago
- **RS underperforming**: Asset/BTC ratio declined ≥10% over 90 days
- **Fear & Greed ≥70**: Market in greed/extreme greed territory

Additional filter: Weekly RSI falling from elevated levels (>55, dropping >8 points) downgrades strong-accumulate to accumulate only.

### Asset Tiers (Dynamic)

Tiers are computed automatically from composite scores:


| Tier        | Composite | Purpose                         |
| ----------- | --------- | ------------------------------- |
| Leaders     | ≥75       | Core positions for accumulation |
| Runner-ups  | 65-74     | Promotion candidates            |
| Observation | 50-64     | Watch only, no position         |


## Quick Start

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure (create .env)
FRED_API_KEY=your_fred_key_here  # Optional, for GLI filter
# Scoring uses Cursor Agent CLI (default model `auto`). Run `cursor-agent login`.

# Scheduled: install launchd agents (Sunday dimensions, daily indicators, monthly discovery)
./scripts/install-launchd.sh install

# Weekly dimension pass (matches launchd job; or use ./scripts/run-local.sh)
python -m pipeline.run --dimensions-only

# Optional full local run with wall-clock cap (see scripts/run-scoring.sh)
./scripts/run-scoring.sh

# Build dashboard
npm run build

# Commit and push
git add . && git commit -m "update" && git push
```

## Parallel Workers

Asset scoring in `pipeline.run` and indicator updates in `pipeline.indicators` can run in parallel.
All database/output writes are still done by the master process at the end to avoid conflicts.

Configure worker counts with environment variables:

```bash
# Weekly pipeline workers (default: 4)
export PIPELINE_MAX_WORKERS=4

# Daily indicators workers (default: uses INDICATORS_MAX_WORKERS, then PIPELINE_MAX_WORKERS, else 4)
export INDICATORS_MAX_WORKERS=4
```

Recommended starting points:

- `2` on laptops when you want lower heat/fan usage
- `4` as a balanced default for most machines
- `6` for higher-end CPUs with good network stability

If APIs start rate-limiting or Cursor Agent runs become unstable, reduce workers and retry.

## Project Structure

```
pipeline/
├── assets.yaml          # Watchlist (source of truth)
├── config.yaml          # All thresholds and parameters
├── run.py               # Weekly scoring orchestrator
├── fetchers/            # Data sources
├── scoring/             # Score computation
└── storage/             # SQLite persistence

public/
├── dashboard.jsx        # React dashboard
├── latest.json          # Weekly snapshot
└── index.html           # Entry point

.docs/
├── decisions.md         # Calibration log (change history)
└── research/            # Research and backtests

.agents/skills/
├── crypto-discovery/    # Monthly watchlist discovery
└── crypto-scoring/      # Scan interpretation
```

## Design Principles

1. **No Server** — GitHub repo is the database
2. **Immutable History** — Append-only SQLite
3. **Framework-Driven** — Calibration log prevents drift
4. **Deliberately Slow** — Weekly scoring rhythm
5. **Single User** — Personal decision support

## Calibration

Track changes in `.docs/decisions.md`. Monitor:

- Does strong-accumulate fire at sensible moments?
- Is composite stable week-over-week?
- Does hold feel right most of the time?

