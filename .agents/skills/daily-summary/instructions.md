# Daily Summary Skill

Interpret daily scan results and provide actionable insights.

## When to Use

- After running `python -m pipeline.indicators` (daily) or `python -m pipeline.run` (weekly)
- When asked "what's the signal today?" or "summarize the scan"
- When reviewing `public/latest.json`

## Interpretation

### Step 1: Read Today's Scan

```bash
cat public/latest.json
```

### Step 2: Identify Action Items

| Action | Meaning | Response |
|--------|---------|----------|
| strong-accumulate | Rare dislocation or capitulation | Act today — high conviction |
| accumulate | Tranche-eligible | Add measured size |
| promote | Runner-up earning activation | Review for tier change |
| stand-aside | Distribution risk | Do not engage |
| hold | No signal | Do nothing |
| await | Building | Monitor |
| observe | Watching | No position |

### Step 3: Consistency Check (MANDATORY)

Before generating the summary, scan for logical inconsistencies:

| Check | Inconsistency | Fix |
|-------|---------------|-----|
| Wyckoff vs Action | Accumulation phase + stand-aside | If stand-aside from delta (not distribution), note "sharp decline despite accumulation structure" |
| RSI vs Action | Oversold RSI + stand-aside | If composite declined sharply, stand-aside is correct; note the conflict |
| Composite vs Tier | Leader with composite <60 | Flag for potential demotion review |
| Action vs Description | Action text contradicts Wyckoff phase | Rewrite description to match actual trigger |

**If inconsistencies found:**
1. Note them in the summary under "⚠️ Inconsistencies Detected"
2. Explain the actual reason (e.g., "SOL shows stand-aside due to -7pt weekly decline, not distribution")
3. Flag for potential calibration review if pattern repeats

### Step 4: Generate Summary

```markdown
## Daily Signals — [Date]

### Action Required
[List strong-accumulate or accumulate signals with context]

### Stand Aside
[List warnings with actual trigger reason]

### ⚠️ Inconsistencies Detected (if any)
[List any logical conflicts between dimensions, phases, and actions]

### Notable Changes
[Score movements, RSI extremes, phase changes]

### Watchlist Health
- Leaders firing accumulate: X/Y
- Strong signals active: N days
- GLI status: [expanding/contracting]

### Interpretation
[1-2 sentences on market posture]
```

## Signal Details

### Strong Accumulate

Fires ~5-15 times per year. Two paths:

**Capitulation** (RSI-based):
- Weekly RSI <30 AND daily RSI <30
- 82.9% hit rate — act decisively

**Wyckoff dip** (structural):
- Daily RSI ≤32 while weekly RSI ≥42 (stable/rising)
- Composite stable week-over-week
- Phase C spring zone

**Downgrade Filters** (OR logic — any one downgrades one level: strong-acc→acc, acc→hold):
- GLI contracting (liquidity withdrawal)
- RS underperforming BTC by ≥10% over 90 days
- Fear & Greed ≥70 (market greed/euphoria)
- Weekly RSI was >55 and dropped >8 points (downgrades to accumulate only)

### Accumulate

**Capitulation** (RSI-based):
- Weekly RSI <30 alone

**Wyckoff** (structural):
- Composite ≥75, Phase C or B→C
- Non-negative 7-day trend
- Weekly RSI <70

**Downgrades one level when any filter active** (strong-acc→acc, acc→hold):
- GLI contracting
- RS underperforming BTC
- Fear & Greed ≥70
- Weekly RSI falling from elevated levels (to accumulate only)

### Stand Aside

- Distribution phase + negative trend
- Weekly delta ≤-5 points

Overrides all other signals.

### Promote

Runner-up showing leader metrics:
- Composite ≥75
- 30-day trend ≥+8
- 7-day trend ≥+2

Requires manual decision to promote in `assets.yaml`.

## RSI Context

| Range | Daily | Weekly | Interpretation |
|-------|-------|--------|----------------|
| <30 | Oversold | Capitulation | Strong buy zone for leaders |
| 30-40 | Weak | Building | Watch for confirmation |
| 40-60 | Neutral | Healthy | Normal range |
| 60-70 | Strong | Extended | Momentum intact |
| ≥70 | Overbought | Euphoric | Accumulation paused |

## Historical Context

Check in the JSON:
- `trend` and `trend_30d`: Score trajectory
- `label_changed_days_ago`: Signal freshness
- `strong_accumulate_days_active`: Continuation vs new
- `gli.downtrend`: Whether GLI filter is active
- `fear_greed.greedy`: Whether Fear & Greed filter is active
- `rs.enabled`: Whether RS vs BTC filter is enabled
- `rs_vs_btc.underperforming`: Per-asset RS filter status

## What NOT to Do

- Don't interpret hold/await/observe as requiring action
- Don't ignore stand-aside signals
- Don't assume daily RSI extremes alone trigger signals
- Don't recommend action on assets below 50 composite (hidden from dashboard)
- Don't treat this as trading advice — it's accumulation guidance
