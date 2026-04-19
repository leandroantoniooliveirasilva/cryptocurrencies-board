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
- Daily rhythm, not real-time — deliberately slow

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
| Revenue | Protocol fees, sustainable revenue |
| Regulatory | Jurisdictional clarity, compliance |
| Supply | Exchange reserves, holder distribution, inflation |
| Wyckoff | Technical phase (accumulation/distribution) |

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

**Filters** (downgrade to regular accumulate):
- GLI contracting (GLI today < GLI 75 days ago)
- Weekly RSI falling from elevated levels (>55, dropped >8 points)

**Accumulate** triggers:
- Weekly RSI <30 alone (capitulation without daily confirmation)
- Wyckoff dip when filtered out of strong-accumulate

### Asset Tiers

| Tier | Count | Purpose |
|------|-------|---------|
| Leaders | 4-6 | Core positions for accumulation |
| Runner-ups | 4-6 | Promotion candidates |
| Observation | 5-8 | Watch only, no position |

### Macro Filters

**GLI (Global Liquidity Index)**:
- Compares current GLI vs 75 days ago
- If contracting → strong-accumulate downgrades to accumulate
- Based on 56-90 day lag between liquidity inflection and BTC tops/bottoms
- Sources: Manual override, TradingView, FRED M2, Fallback (neutral)

### Display Threshold

Assets with composite score below 50 are hidden from the dashboard.

## Pipeline

```
Local (on-demand)
├── Fetch: DefiLlama (TVL, revenue), CoinGecko (prices)
├── Score: Claude API for regulatory, institutional, supply
├── Compute: RSI(14) daily + weekly from 120 days OHLC
├── Detect: Wyckoff phase from price structure
├── Composite: Weighted score by asset type
├── Action: Derive signal from composite + RSI + Wyckoff + trend
├── Store: Append snapshot to history.sqlite
└── Output: Write latest.json, commit, push
         │
         ▼
GitHub Actions → Deploy /public to GitHub Pages
```

## Commands

```bash
# Pipeline
python -m pipeline.run
python -m pipeline.run --dry-run

# Frontend
npm run build
npm run watch

# Discovery (monthly)
./scripts/run-discovery-ensemble.sh

# Local dev
cd public && python -m http.server 8000
```

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
5. **Deliberately Slow** — Daily rhythm, not real-time
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
