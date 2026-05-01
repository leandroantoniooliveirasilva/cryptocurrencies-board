---

## name: crypto-scoring
description: Interpret weekly scoring output and produce actionable signal analysis with consistency checks and evidence-backed rationale validation. Use after scoring runs or when the user asks for weekly signal summaries, action interpretation, or quality review of dimension rationales.

# Scoring Skill

Use this skill for weekly scan interpretation and signal-quality validation.

## When to use

- After `python -m pipeline.run`
- When reviewing `public/latest.json`
- When asked to summarize signals, actions, or inconsistencies

## Instructions

Follow the full procedure in `instructions.md`.

## How results are produced (repo contract)

Weekly scoring runs up to **`PIPELINE_MAX_WORKERS`** assets in parallel (default **10**): each slot uses **one isolated Python child process** per asset. Inside each child, qualitative dimensions call **`cursor-agent`** (see `src/pipeline/fetchers/qualitative.py`). Workers write **`out/reports/scoring/assets/<YYYY-MM-DD>/<SYMBOL>.json`** per asset; the main process **merges** successful assets into **`public/latest.json`** and SQLite in watchlist order. Use per-asset JSON for debugging; **`latest.json`** is the merged dashboard snapshot.

## Output expectations

- Report inconsistency count first
- Explain action states (`strong-accumulate`, `accumulate`, `hold`, `await`, `observe`, `promote`, `stand-aside`)
- Cite evidence from `score_rationales`, RSI, Wyckoff, GLI, RS, and Fear & Greed
- Keep recommendations framework-aligned and non-trading

# crypto-scoring

Asset-by-asset conviction scoring for the weekly pipeline: **cursor-agent** inside each asset subprocess → **`out/reports/scoring/assets/…/<SYMBOL>.json`** → merged **`public/latest.json`**.

Use this skill when running or debugging scoring quality, with strict evidence-backed rationales for each weighted dimension (institutional, adoption_activity, value_capture, regulatory, supply). Prefer focused single-asset analysis when quality is low or rationales vague — inspect that asset’s file under `out/reports/scoring/assets/<date>/`.
