# Conviction Board

A self-hosted cryptocurrency conviction scoring system for long-term accumulation. Runs locally on demand, deploys to GitHub Pages.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Local Pipeline (on-demand, runs on laptop)                 │
│  ───────────────────────────────────────────                │
│  1. Fetch data (DefiLlama, CoinGecko)                       │
│  2. Claude API for qualitative scoring (regulatory,         │
│     institutional, supply)                                  │
│  3. Compute RSI(14) daily + weekly from OHLC                │
│  4. Compute composite scores per asset (5 dimensions)       │
│  5. Derive action state (Accumulate, Strong, Hold, etc.)    │
│  6. Append snapshot to history.sqlite                       │
│  7. Write latest.json to /public                            │
│  8. Commit and push to repo                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (deploy only)                               │
│  ────────────────────────────                               │
│  Deploys /public to GitHub Pages on push                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Pages (static hosting)                              │
│  ──────────────────────────────                             │
│  index.html + React dashboard                               │
│  Reads /public/latest.json on load                          │
└─────────────────────────────────────────────────────────────┘
```

**Key property**: no server, no database host. The repo *is* the database.

## Scoring Framework

### Dimensions (5)

Weighted by asset type (store-of-value, smart-contract, defi, infrastructure):

- **Institutional**: Fund holdings, ETF products, custody solutions
- **Revenue**: Protocol fees, revenue sustainability
- **Regulatory**: Jurisdictional clarity, compliance posture
- **Supply**: Exchange reserves, holder distribution, inflation
- **Wyckoff**: Technical phase analysis

### Action States

- **Strong Accumulate**: Dislocation in accumulation zone or capitulation (rare)
- **Accumulate**: Leader tranche-eligible zone
- **Promote Candidate**: Runner-up crossing leader threshold
- **Hold & Monitor**: Active position, no action signal
- **Await Confirmation**: Signal building, not yet activated
- **Observe**: Watching only, no position
- **Stand Aside**: Distribution risk, do not engage

### Asset Tiers

- **Leaders** (4-6): Core conviction positions for accumulation
- **Runner-ups** (4-6): Promotion candidates with strong fundamentals
- **Observation** (5-8): Watch list only, no position

See `pipeline/assets.yaml` for current watchlist.

## Setup

### 1. Clone and configure

```bash
git clone https://github.com/yourusername/cryptocurrencies-board.git
cd cryptocurrencies-board

# Create virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set environment variables

Export your API keys:
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. Enable GitHub Pages

Go to repo Settings → Pages:
- Source: `main` branch
- Folder: `/public`

### 4. Run pipeline locally

```bash
# Run daily scoring
python -m pipeline.run

# Build dashboard
npm run build

# Commit and push
git add . && git commit -m "daily scan" && git push
```

## Project Structure

```
cryptocurrencies-board/
├── .github/workflows/
│   └── deploy-pages.yml       # GitHub Pages deployment
├── .agents/skills/            # Local agent skills
│   ├── discovery/             # Monthly watchlist discovery
│   └── daily-summary/         # Daily scan interpretation
├── pipeline/
│   ├── assets.yaml            # Watchlist configuration
│   ├── fetchers/              # Data fetching (DefiLlama, CoinGecko, Claude)
│   ├── scoring/               # Score computation (composite, RSI, actions)
│   ├── storage/               # SQLite persistence
│   └── run.py                 # Orchestrator entry point
├── public/                    # Served by GitHub Pages
│   ├── index.html
│   ├── dashboard.jsx          # React dashboard source
│   ├── dashboard.js           # Compiled bundle
│   └── latest.json            # Today's snapshot
├── discovery/                 # Monthly discovery reports
├── docs/
│   └── decisions.md           # Framework calibration log
└── requirements.txt
```

## Calibration

Track changes in `docs/decisions.md`. Watch for:
- Does Strong Accumulate fire at sensible moments?
- Does Promote Candidate fire too readily or too rarely?
- Is composite stable week-over-week?
- Does Hold feel right for most leaders most of the time?

## Design Principles

1. **No Server**: GitHub repo itself is the database
2. **Immutable History**: SQLite append-only (never update/delete)
3. **Framework-Driven**: Calibration log prevents drift
4. **Lean Dependencies**: No heavy ORMs, frameworks, or bloat
5. **Deliberately Slow**: Daily rhythm, not real-time
6. **Single User**: Personal decision support, not a trading tool

## License

Private repository. Not for redistribution.
