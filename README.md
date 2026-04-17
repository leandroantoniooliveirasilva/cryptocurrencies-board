# Conviction Scoring Dashboard

A self-hosted daily scoring system for cryptocurrency investment framework. Runs automatically via GitHub Actions, costs nothing, lives in one git repo.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (daily cron @ 09:00 UTC)                    │
│  ──────────────────────────────────────                     │
│  1. Fetch data (DefiLlama, CoinGecko)                       │
│  2. Compute composite scores per asset                      │
│  3. Compute RSI(14) daily + weekly from OHLC                │
│  4. Claude API pass for qualitative regulatory scoring      │
│  5. Derive action state (Accumulate, Strong, Hold, etc.)    │
│  6. Append snapshot to history.sqlite                       │
│  7. Write latest.json + history.json to /public             │
│  8. Commit changes back to repo                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  GitHub Pages (static hosting, free)                        │
│  ──────────────────────────────────                         │
│  index.html + React dashboard                               │
│  Reads /public/latest.json on load                          │
│  Shows score cards, action banners, RSI, trends             │
└─────────────────────────────────────────────────────────────┘
```

**Key property**: no server, no database host, no always-on compute. The repo *is* the database.

## Scoring Framework

### Dimensions (Weights)
- **Institutional** (30%): Fund holdings, ETF products, custody solutions
- **Revenue** (30%): Protocol fees, revenue sustainability
- **Regulatory** (25%): Jurisdictional clarity, compliance posture
- **Wyckoff** (15%): Technical phase analysis

### Action States
- **Strong Accumulate**: Dislocation in accumulation zone (rare, ~5-15x/year)
- **Accumulate**: Leader tranche-eligible zone
- **Promote Candidate**: Runner-up crossing leader threshold
- **Hold & Monitor**: Active position, no action signal
- **Await Confirmation**: Signal building, not yet activated
- **Observe**: Watching only, no position
- **Stand Aside**: Distribution risk, do not engage

### Asset Tiers
- **Leaders**: Core conviction positions (BTC, SOL, LINK, HYPE)
- **Runner-ups**: Promotion candidates (MORPHO, QNT, XLM, KAS)
- **Observation**: Watch list only (XRP, AVAX, HBAR, CANTON, ONDO, AAVE)

## Setup

### 1. Clone and configure

```bash
# Clone the repo
git clone https://github.com/yourusername/cryptocurrencies-board.git
cd cryptocurrencies-board

# Copy environment template
cp .env.example .env
# Edit .env with your API keys
```

### 2. Set GitHub Secrets

Go to repo Settings → Secrets → Actions and add:
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `COINGECKO_API_KEY`: (Optional) CoinGecko API key for higher rate limits

### 3. Enable GitHub Pages

Go to repo Settings → Pages:
- Source: `main` branch
- Folder: `/public`

Dashboard will be available at `https://yourusername.github.io/cryptocurrencies-board/`

### 4. Run locally (optional)

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run pipeline
python -m pipeline.run

# Serve dashboard locally
cd public && python -m http.server 8000
```

## Project Structure

```
cryptocurrencies-board/
├── .github/workflows/
│   └── daily-scan.yml          # GitHub Actions cron job
├── pipeline/
│   ├── assets.yaml             # Watchlist configuration
│   ├── fetchers/               # Data fetching (DefiLlama, CoinGecko, Claude)
│   ├── scoring/                # Score computation (composite, RSI, actions)
│   ├── storage/                # SQLite persistence
│   └── run.py                  # Orchestrator entry point
├── public/                     # Served by GitHub Pages
│   ├── index.html
│   ├── dashboard.jsx           # React dashboard
│   ├── latest.json             # Today's snapshot
│   └── history.json            # Rolling 90-day history
├── docs/
│   └── decisions.md            # Framework calibration log
├── requirements.txt
└── .env.example
```

## Calibration

The framework needs calibration over the first 5-7 days. Track all changes in `docs/decisions.md`.

### What to Watch
- Does Strong Accumulate fire at sensible moments?
- Does Promote Candidate fire too readily or too rarely?
- Is composite stable week-over-week?
- Does Hold feel right for most leaders most of the time?

### Target Frequencies
- **Accumulate**: ~20-40% of the time per leader in bull phase
- **Strong Accumulate**: ~5-15 times per year total across watchlist
- **Promote**: Only when something genuinely earns it

## Design Principles

1. **No Server**: GitHub repo itself is the database
2. **Immutable History**: SQLite append-only (never update/delete)
3. **Framework-Driven**: Calibration log prevents drift
4. **Lean Dependencies**: No heavy ORMs, frameworks, or bloat
5. **Deliberately Slow**: Daily rhythm, not real-time
6. **Single User**: Personal decision support, not a trading tool

## License

Private repository. Not for redistribution.
