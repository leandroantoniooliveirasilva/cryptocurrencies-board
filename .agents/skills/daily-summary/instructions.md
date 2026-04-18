# Daily Summary Skill

Interpret daily scan results and provide actionable insights.

> **Note**: The scoring pipeline runs locally via `python -m pipeline.run`. This skill interprets the results in `public/latest.json`.

## When to Use

Invoke this skill when:
- After running the daily pipeline (`python -m pipeline.run`)
- The user asks "what's the signal today?", "summarize the scan", or "what should I do?"
- Reviewing `public/latest.json` for today's results

## Quick Interpretation

### Step 1: Read Today's Scan

```bash
cat public/latest.json
```

Or read the file directly to understand current state.

### Step 2: Identify Action Items

Look for assets with actionable signals:

| Action | Meaning | What To Do |
|--------|---------|------------|
| `strong-accumulate` | Rare dislocation or capitulation | **Act today** — high-conviction entry |
| `accumulate` | Tranche-eligible | Add to position in measured size |
| `promote` | Runner-up earning activation | Review for tier promotion |
| `stand-aside` | Distribution risk | **Do not engage** regardless of price |
| `hold` | No signal | Do nothing — patience |
| `await` | Building | Monitor, don't act yet |
| `observe` | Watching | No position warranted |

### Step 3: Generate Summary

Provide a concise summary in this format:

```markdown
## Daily Conviction Signals — [Date]

### Action Required
[List any strong-accumulate or accumulate signals with context]

### Stand Aside
[List any stand-aside warnings]

### Notable Changes
[Any significant score movements, new RSI extremes, or phase changes]

### Watchlist Health
- Leaders firing accumulate: X/Y
- Strong signals active: N days
- Assets below threshold: N (filtered from view)

### Interpretation
[1-2 sentences on overall market posture and what it means for the framework]
```

## Signal Interpretation Guidelines

### Strong Accumulate
This is rare (~5-15 times per year across all assets). When it fires:

**Capitulation-triggered** (RSI-based):
- Weekly RSI < 30 AND daily RSI < 30
- Indicates panic selling in a quality leader
- High probability of recovery — act decisively

**Wyckoff-triggered** (structural):
- Daily RSI ≤ 32 while weekly RSI ≥ 42
- Composite stable week-over-week
- Phase C spring zone
- Short-term dip within healthy structure

If strong-accumulate has been firing for multiple consecutive days, note the day count. Continuation signals are valid but early entries are better.

### Accumulate
More common signal. Valid when:

**Capitulation** (RSI-based):
- Weekly RSI < 30 alone
- Leaders typically recover from panic selling

**Wyckoff** (structural):
- Composite ≥ 75
- Phase C or B→C
- Non-negative 7-day trend
- Weekly RSI < 70 (not overbought)

### Stand Aside
Framework says do not engage when:
- Distribution phase detected AND negative delta
- Weekly delta ≤ -5 points (sharp decline)

This overrides all other signals. Even if price looks attractive, structural breakdown suggests more downside.

### Promote
Runner-up showing leader-quality metrics:
- Composite ≥ 75
- 30-day trend ≥ +8 points
- 7-day trend ≥ +2 points

Requires manual decision to actually promote in `assets.yaml`.

## RSI Context

Provide RSI context for actionable assets:

| RSI Range | Daily | Weekly | Interpretation |
|-----------|-------|--------|----------------|
| < 30 | Oversold | Capitulation | Strong buy zone for leaders |
| 30-40 | Weak | Building | Watch for confirmation |
| 40-60 | Neutral | Healthy | Normal range |
| 60-70 | Strong | Extended | Momentum intact |
| ≥ 70 | Overbought | Euphoric | Accumulation paused |

## Example Summary

```markdown
## Daily Conviction Signals — 2026-04-18

### Action Required

**LINK** — Strong Accumulate (Day 2)
- Composite: 78 (+2 WoW)
- Daily RSI: 28 | Weekly RSI: 45
- Wyckoff dislocation in Phase C
- *This is a high-conviction entry window*

**SOL** — Accumulate
- Composite: 82 (stable)
- Weekly RSI: 31 (capitulation zone)
- *Measured tranche building appropriate*

### Stand Aside

None — all leaders structurally healthy

### Notable Changes

- BTC weekly RSI dropped from 55 to 48 (approaching accumulate zone)
- HYPE composite improved +4 to 76 (crossing leader threshold)
- QNT removed from view (composite 58, below threshold)

### Watchlist Health
- Leaders firing accumulate: 2/5
- Strong signals active: LINK (day 2)
- Assets below threshold: 3

### Interpretation
Market showing localized weakness with LINK and SOL in accumulation zones while BTC approaches. Framework posture: selective accumulation in leaders, patience elsewhere.
```

## Historical Context

When interpreting signals, consider:

1. **Trend arrays** (`trend` and `trend_30d`): Are scores improving or declining?
2. **Days since label change** (`label_changed_days_ago`): Recent changes are more actionable
3. **Strong accumulate streak** (`strong_accumulate_days_active`): Continuation or new signal?
4. **Missing dimensions** (`missing_dimensions`): Incomplete data lowers confidence

## What NOT to Do

- Don't interpret hold/await/observe as requiring action
- Don't ignore stand-aside signals
- Don't assume daily RSI extremes alone trigger signals (weekly matters more)
- Don't recommend action on assets below the 60-score threshold
- Don't treat this as trading advice — it's accumulation guidance
