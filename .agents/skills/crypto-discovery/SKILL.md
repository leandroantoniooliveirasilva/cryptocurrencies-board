---

## name: crypto-discovery
description: Run monthly watchlist discovery and vetting for the conviction scoring framework, including omission audits, candidate evaluation, and structured recommendations. Use when asked to run discovery, review watchlist composition, or propose additions/removals.

# Discovery Skill

Use this skill for monthly discovery and watchlist maintenance decisions.

## When to use

- When asked to run monthly discovery
- When evaluating watchlist additions or removals
- When reviewing tier movement candidates

## Instructions

Follow the complete workflow in `instructions.md`.

## Output expectations

- Produce a structured discovery report
- Include rationale per dimension and value-accrual view
- Keep recommendations objective and evidence-based

# crypto-discovery

Monthly watchlist discovery and vetting for the conviction scoring framework. Use when the user asks to find new crypto projects, review the watchlist, evaluate tier changes, or run monthly discovery. Searches for high-conviction assets, evaluates them against **composite dimensions per `asset_category`** (institutional, adoption/activity, value capture, regulatory, supply — see `weights_by_category`), and recommends additions, promotions, demotions, or removals. **Wyckoff phase** is a global filter (daily indicators), not a scored composite dimension.
