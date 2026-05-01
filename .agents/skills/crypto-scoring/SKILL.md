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

## Output expectations

- Report inconsistency count first
- Explain action states (`strong-accumulate`, `accumulate`, `hold`, `await`, `observe`, `promote`, `stand-aside`)
- Cite evidence from `score_rationales`, RSI, Wyckoff, GLI, RS, and Fear & Greed
- Keep recommendations framework-aligned and non-trading

# crypto-scoring

Asset-by-asset conviction scoring for the weekly pipeline.

Use this skill when running or debugging scoring quality, with strict evidence-backed rationales for each weighted dimension (institutional, adoption_activity, value_capture, regulatory, supply). Prefer focused single-asset analysis when quality is low or rationales are vague.
