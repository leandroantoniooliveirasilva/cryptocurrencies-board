# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A self-hosted cryptocurrency conviction scoring system. Runs daily via GitHub Actions, stores results in SQLite (committed to repo), and displays via React dashboard on GitHub Pages. **The repository itself is the database.**

## Commands

```bash
# Frontend
npm run build              # Compile dashboard.jsx → dashboard.js (esbuild)
npm run watch              # Watch mode

# Backend pipeline
python -m pipeline.run     # Run daily scoring
python -m pipeline.run --dry-run

# Local dev server
cd public && python -m http.server 8000

# Python setup
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Architecture

```
GitHub Actions (12:00 UTC) → pipeline/run.py → SQLite + JSON → GitHub Pages
```

**Data flow**: Fetch market data (DefiLlama, CoinGecko) → Compute RSI → Claude API for qualitative scoring → 5-dimension weighted composite → Action state → Write latest.json → Commit & push

**Key directories**:
- `pipeline/` – Python scoring engine (fetchers/, scoring/, storage/)
- `public/` – React dashboard + JSON output (served by Pages)
- `pipeline/assets.yaml` – Watchlist configuration

## Scoring Framework

**5 dimensions** with tiered weights by asset type (store-of-value, smart-contract, defi, infrastructure):
- Institutional, Revenue, Regulatory, Supply, Wyckoff

**Action states**: Strong Accumulate → Accumulate → Hold → Await → Observe → Stand Aside

## Git Workflow

This is a personal project. Safe to commit and push directly to main.

