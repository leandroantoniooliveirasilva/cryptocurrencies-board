# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Overview

A personal cryptocurrency scoring system for long-term accumulation. Runs locally on demand, stores snapshots in SQLite (committed to repo), displays via React dashboard on GitHub Pages.

**Key property**: No server, no database host. The repo is the database.

## Core Philosophy

**Identifies WHAT to buy based on fundamentals, WHEN to buy based on technicals.**

- Leaders go up over time due to strong fundamentals
- Buying weakness in leaders = mean reversion (they recover)
- Buying weakness in non-leaders = momentum trap (they continue down)
- Weekly scoring, daily indicators — deliberately slow

### Conviction Over Trading

This is a decision support system for patient accumulation:
- Strong-accumulate fires ~5-15 times per year across the watchlist
- Accumulate is active ~20-40% of the time per leader in bull phases
- Hold is the default state — patience is the strategy

## Signal Framework

### Dimensions (5 scored + 1 filter)

Each scored 0-100, weighted by asset type:

| Dimension | What It Measures |
|-----------|------------------|
| Institutional | ETF flows, fund holdings, custody adoption |
| Revenue | Protocol income (actual revenue, not burns) |
| Regulatory | Jurisdictional clarity, compliance |
| Supply | Exchange reserves, holder distribution, inflation, burn rate |
| Wyckoff | Technical phase (accumulation/distribution) |

**Fee Models**: Not all protocol fees are "revenue":
- **Revenue**: Fees → treasury/validators → scored under Revenue dimension
- **Burn**: Fees → destroyed → set `fee_model: burn` in assets.yaml, skip Revenue, evaluate under Supply
- **Hybrid**: Burns + revenue combined (most L1s) → score revenue portion only

Burn-model assets have weight redistributed to other dimensions. Burns are evaluated as tokenomics benefit under Supply.

**Value Accrual (Discovery Filter)**: How protocol success translates to token appreciation. A project may succeed but if success doesn't flow to token holders (fee burns, revenue sharing, staking requirements), it's not a strong candidate. Evaluated during discovery, not scored numerically.

### Weight Profiles

```
store-of-value (BTC):     Inst 40%, Supply 25%, Reg 15%, Wyck 15%, Rev 5%
smart-contract (SOL):     Inst 30%, Rev 25%, Supply 20%, Reg 15%, Wyck 10%
defi (LINK, HYPE):        Rev 35%, Inst 25%, Reg 20%, Supply 15%, Wyck 5%
infrastructure (QNT):     Inst 35%, Reg 25%, Supply 20%, Rev 10%, Wyck 10%
```

### Action States

| State | Tier | Description |
|-------|------|-------------|
| strong-accumulate | Leaders | True capitulation or quality dip — act now |
| accumulate | Leaders | Tranche-eligible zone |
| promote | Runner-ups | Crossing leader threshold |
| hold | Leaders | Default — no action signal |
| await | Runner-ups | Signal building |
| observe | Observation | Watch only |
| stand-aside | Any | Distribution risk — do not engage |

### Signal Logic

**Strong Accumulate** triggers:
1. **Capitulation**: Weekly RSI <30 AND daily RSI <30 (82.9% hit rate)
2. **Wyckoff dip**: Phase C + daily RSI ≤32 + weekly RSI ≥42 + composite stable

**Accumulate** triggers:
- Weekly RSI <30 alone (capitulation without daily confirmation)
- Wyckoff dip when weekly RSI is falling from elevated levels

**Downgrade Filters** (OR logic — any one triggers):
When ANY of these conditions is true:
- GLI contracting (GLI today < GLI 75 days ago)
- RS underperforming BTC (asset/BTC ratio declined ≥10% over 90 days)
- Fear & Greed ≥70 (market euphoria)

The following downgrades apply:
- strong-accumulate → accumulate → **hold**
- accumulate → **hold**

This is aggressive filtering — designed to suppress accumulation signals during unfavorable macro conditions.

### Asset Tiers (Dynamic)

Tiers are computed automatically from composite scores:

| Tier | Composite | Purpose |
|------|-----------|---------|
| Leaders | ≥75 | Core positions for accumulation |
| Runner-ups | 65-74 | Promotion candidates |
| Observation | 50-64 | Watch only, no position |

Thresholds defined in `pipeline/config.yaml`. No manual tier assignment — tiers are purely score-driven.

### Filters

All three filters use OR logic — when ANY is active, signals downgrade ONE level (strong-accumulate→accumulate, accumulate→hold).

**GLI (Global Liquidity Index)**:
- Compares current GLI vs 75 days ago
- If contracting → signal downgrades one level
- Based on 56-90 day lag between liquidity inflection and BTC tops/bottoms
- Sources: FRED M2, Manual override, Fallback (neutral)

**RS (Relative Strength vs BTC)**:
- Compares each asset's price ratio to BTC over 90 days
- If underperforming BTC by ≥10% → signal downgrades one level
- Rationale: if an asset is underperforming BTC, you may be better off just holding BTC
- BTC excluded (RS vs itself is always 1.0)

**Fear & Greed Index**:
- Fetches Bitcoin Fear & Greed Index from Alternative.me API
- If ≥70 (Greed/Extreme Greed) → signal downgrades one level
- Rationale: buying during euphoria often means buying near local tops

### Display Threshold

Assets with composite score below 50 are hidden from the dashboard.

## Pipeline

```
Weekly (Sundays via cron)
├── Fetch: DefiLlama (TVL, revenue)
├── Score: Claude API for regulatory, institutional, supply
├── Detect: Wyckoff phase from price structure
├── Composite: Weighted score by asset type
└── Store: Append snapshot to history.sqlite

Daily (via cron)
├── Fetch: Prices (DefiLlama)
├── Compute: RSI(14) daily + weekly
├── Check: Macro filters (GLI, RS vs BTC, Fear & Greed)
├── Action: Derive signal from composite + indicators
└── Output: Write latest.json, commit, push
         │
         ▼
GitHub Actions → Deploy /public to GitHub Pages
```

## Commands

```bash
# Weekly full scoring (all dimensions + Wyckoff)
python -m pipeline.run
python -m pipeline.run --dry-run

# Daily indicators update (RSI, GLI, RS, F&G)
python -m pipeline.indicators
python -m pipeline.indicators --dry-run

# Frontend
npm run build
npm run watch

# Discovery (monthly)
./scripts/run-discovery-ensemble.sh

# Local dev
cd public && python -m http.server 8000
```

## Local Cron Setup (macOS)

The pipeline runs locally via cron, not GitHub Actions:

```bash
# Edit crontab
crontab -e

# Add these entries (adjust paths as needed):
# Weekly full scoring - Sunday 00:00 UTC
0 0 * * 0 cd ~/Projects/personal/cryptocurrencies-board && source .venv/bin/activate && python -m pipeline.run && git add -A && git commit -m "chore: weekly scoring update" && git push

# Daily indicators - 00:00 UTC
0 0 * * * cd ~/Projects/personal/cryptocurrencies-board && source .venv/bin/activate && python -m pipeline.indicators && git add -A && git commit -m "chore: daily indicators update" && git push
```

**Note**: Adjust for your timezone. UTC 00:00 = PT 17:00 (previous day).

## Environment

Store in `.env` (auto-loaded):

```bash
FRED_API_KEY=xxx               # Optional (GLI filter)
```

## Key Files

```
pipeline/
├── assets.yaml              # Watchlist (source of truth)
├── config.yaml              # All thresholds and parameters
├── run.py                   # Orchestrator
├── fetchers/                # Data sources
├── scoring/
│   ├── actions.py           # Signal derivation (core logic)
│   ├── composite.py         # Weighted scoring
│   ├── rsi.py               # RSI calculation
│   └── wyckoff.py           # Phase detection
└── storage/
    ├── migrations.py        # SQLite schema
    └── history.sqlite       # Append-only database

public/
├── dashboard.jsx            # React source
├── dashboard.js             # Compiled bundle
├── latest.json              # Today's snapshot
└── index.html               # Entry point

.docs/
├── decisions.md             # Calibration log (change history)
└── research/                # Research and backtests

.agents/skills/
├── discovery/               # Monthly watchlist discovery
└── daily-summary/           # Scan interpretation
```

## Design Principles

1. **No Server** — GitHub repo is the database
2. **Immutable History** — Append-only SQLite
3. **Framework-Driven** — Calibration log prevents drift
4. **Lean Dependencies** — No heavy ORMs or frameworks
5. **Deliberately Slow** — Weekly scoring, daily indicators
6. **Single User** — Personal decision support
7. **Warm Minimalism** — Clean without being cold (see .impeccable.md)

## Git Workflow

Personal project. Commit directly to main. No PR process.

Format: conventional commits, under 100 chars, no footer signatures.

Author: `leandroantoniooliveirasilva@gmail.com` (personal account)

## Calibration

Track changes in `.docs/decisions.md`. Monitor:
- Does strong-accumulate fire at sensible moments?
- Does promote fire appropriately?
- Is composite stable week-over-week?
- Does hold feel right most of the time?

## Skills

- `discovery` — Monthly watchlist discovery and vetting
- `daily-summary` — Interpret daily scan results

## Documentation Updates

When framework changes occur (new dimensions, thresholds, action states), update:
1. README.md
2. CLAUDE.md
3. .agents/skills/ instructions
4. pipeline/discovery/prompt.md (if scoring logic changes)
