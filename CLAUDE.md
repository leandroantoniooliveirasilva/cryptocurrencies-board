# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

A self-hosted cryptocurrency conviction scoring system for long-term accumulation. Runs daily via GitHub Actions, stores results in SQLite (committed to repo), and displays via React dashboard on GitHub Pages. **The repository itself is the database.**

## Core Philosophy

### The Framework Principle
**Identifies WHAT to buy based on fundamentals, WHEN to buy based on technicals.**

- Leaders go up over time due to strong fundamentals
- Buying weakness in leaders = mean reversion opportunity (they recover)
- Buying weakness in non-leaders = momentum trap (they continue down)
- Daily rhythm, not real-time — deliberately slow

### Conviction Over Trading
This is a decision support system for patient accumulation, not a trading tool:
- Strong Accumulate fires ~5-15 times per year across the entire watchlist
- Accumulate should be active ~20-40% of the time per leader in bull phases
- Hold is the default state — patience is the strategy

## Key Abstractions

### Asset Tiers
```
Leader (4-6 assets)
├── Core positions for accumulation
├── Composite ≥75 consistently
├── Clear institutional adoption path
└── No existential regulatory risk

Runner-up (4-6 assets)
├── Promotion candidates
├── Composite 65-74 or improving
├── Strong in 2-3 dimensions
└── Clear path to leader status

Observation (5-8 assets)
├── Watch only, no position
├── Interesting but gaps exist
└── May have single strong dimension
```

### Scoring Dimensions (5)
Each scored 0-100, weighted by asset type:

| Dimension | What It Measures |
|-----------|------------------|
| **Institutional** | ETF flows, fund holdings, custody adoption |
| **Revenue** | Protocol fees, sustainable revenue |
| **Regulatory** | Jurisdictional clarity, compliance |
| **Supply** | Exchange reserves, holder distribution, inflation |
| **Wyckoff** | Technical phase (accumulation/distribution) |

### Weight Profiles by Asset Type
```
store-of-value (BTC):     Inst 40%, Supply 25%, Reg 15%, Wyck 15%, Rev 5%
smart-contract (SOL):     Inst 30%, Rev 25%, Supply 20%, Reg 15%, Wyck 10%
defi (LINK, HYPE):        Rev 35%, Inst 25%, Reg 20%, Supply 15%, Wyck 5%
infrastructure (QNT):     Inst 35%, Reg 25%, Supply 20%, Rev 10%, Wyck 10%
```

### Action States (Signal Hierarchy)
```
strong-accumulate    Dislocation in accumulation zone OR capitulation (leaders only)
                     Triggers: (1) Weekly RSI <30 AND daily RSI <30
                               (2) Wyckoff Phase C + RSI dip + composite stable

accumulate           Tranche-eligible zone (leaders only)
                     Triggers: (1) Weekly RSI <30 alone
                               (2) Composite ≥75, Phase C+, trend stable, RSI <70

promote              Runner-up earning activation (runner-ups only)
                     Composite ≥75 + 30-day trend ≥+8

hold                 Default for leaders — no action signal
await                Default for runner-ups — signal building
observe              Default for observation — scanning only
stand-aside          Distribution risk — do not engage
```

### Display Threshold
Assets with composite score below 50 are not displayed on the dashboard.

## Data Pipeline

The pipeline runs **locally** on demand (not via GitHub Actions). Only deployment is automated.

```
Local Pipeline (on-demand)
    │
    ├─→ Fetch: DefiLlama (TVL, revenue), CoinGecko (prices)
    ├─→ Score: Claude API for regulatory + institutional + supply
    ├─→ Compute: RSI(14) daily + weekly from 120 days OHLC
    ├─→ Detect: Wyckoff phase from price structure (or use override)
    ├─→ Composite: Weighted score by asset type
    ├─→ Action: Derive signal from composite + RSI + Wyckoff + trend
    ├─→ Store: Append snapshot to history.sqlite
    └─→ Output: Write latest.json, commit and push
         │
         ▼
GitHub Actions → Deploy /public to GitHub Pages
```

## Commands

```bash
# Frontend
npm run build              # Compile dashboard.jsx → dashboard.js
npm run watch              # Watch mode

# Backend pipeline
python -m pipeline.run     # Run daily scoring
python -m pipeline.run --dry-run

# Discovery (monthly)
./scripts/run-discovery-ensemble.sh    # 3x parallel discovery + fact-check + merge

# Local dev
cd public && python -m http.server 8000

# Python setup
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Key Files

```
pipeline/
├── assets.yaml              # Watchlist configuration (THE source of truth)
├── run.py                   # Pipeline orchestrator
├── fetchers/
│   ├── defillama.py         # TVL, revenue data
│   ├── qualitative.py       # Claude API for regulatory/institutional
│   └── supply.py            # Claude API for supply/on-chain
├── scoring/
│   ├── composite.py         # Weighted score calculation
│   ├── actions.py           # Action state derivation (THE core logic)
│   ├── rsi.py               # RSI(14) calculation
│   └── wyckoff.py           # Phase detection
└── storage/
    ├── migrations.py        # SQLite schema + queries
    └── history.sqlite       # Append-only database

public/
├── dashboard.jsx            # React dashboard source
├── dashboard.js             # Compiled bundle
├── latest.json              # Today's snapshot (auto-generated)
└── index.html               # Entry point

.agents/skills/
├── discovery/               # Monthly watchlist discovery skill
└── daily-summary/           # Daily scan interpretation skill

discovery/
├── report_YYYY-MM.md        # Monthly consolidated reports
└── YYYY-MM/                 # Individual discovery runs
```

## Design Principles

1. **No Server**: GitHub repo itself is the database
2. **Immutable History**: SQLite append-only (never update/delete snapshots)
3. **Framework-Driven**: Calibration prevents emotional drift
4. **Lean Dependencies**: No heavy ORMs, frameworks, or bloat
5. **Deliberately Slow**: Daily rhythm, not real-time
6. **Single User**: Personal decision support, not a trading platform
7. **Warm Minimalism**: Clean without being cold (see .impeccable.md)

## Git Workflow

Personal project. Commit and push directly to main. No PR process needed.

Commit format: conventional commits, under 100 chars, no footer signatures.

**Author**: Commits must use `leandroantoniooliveirasilva@gmail.com` (personal account), NOT the work account. If using a separate git config, ensure the correct identity is set for this repo:
```bash
git config user.email "leandroantoniooliveirasilva@gmail.com"
git config user.name "Leandro Silva"
```

## Calibration Guidelines

Track changes in `docs/decisions.md`. Watch for:
- Does Strong Accumulate fire at sensible moments?
- Does Promote fire too readily or rarely?
- Is composite stable week-over-week?
- Does Hold feel right for leaders most of the time?

## Skills

See `.agents/skills/` for:
- `discovery` — Monthly watchlist discovery and vetting
- `daily-summary` — Interpret daily scan results

## Documentation Maintenance

When structural changes are made to the framework (new dimensions, changed thresholds, new action states, etc.), update:

1. **README.md** — User-facing overview
2. **CLAUDE.md** — This file (Claude Code guidance)
3. **`.agents/skills/`** — Skill instructions to match implementation
4. **`pipeline/discovery/prompt.md`** — Discovery prompt if scoring logic changes
