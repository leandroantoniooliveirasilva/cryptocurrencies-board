# Framework Decisions Log

Track all changes to weights, thresholds, and rationale here. This is the most important file in the repo - it prevents framework drift.

---

## 2026-04-17 — Initial Framework

### Weights
- Institutional: 30%
- Revenue: 30%
- Regulatory: 25%
- Wyckoff: 15%

### Action State Thresholds

**Strong Accumulate** (leaders only):
- Base requirement: Accumulate regime active
- Daily RSI ≤ 32 (oversold flush)
- Weekly RSI ≥ 42 (trend intact)
- Composite week-over-week change ≥ -3 (stable)

**Accumulate** (leaders only):
- Composite ≥ 75
- Wyckoff Phase C or B→C
- 7-day trend delta ≥ 0
- Weekly RSI < 75 (not overbought)

**Promote Candidate** (runner-ups):
- Composite ≥ 75
- 30-day trend delta ≥ +8
- 7-day trend delta ≥ +2

**Stand Aside** (overrides all):
- Distribution phase + negative trend
- 7-day trend delta ≤ -5

### Rationale

Initial weights balance conviction dimensions:
- Institutional/Revenue (60% combined): Fundamental value signals
- Regulatory (25%): Existential risk factor
- Wyckoff (15%): Technical timing confirmation

Strong Accumulate is designed to fire rarely (5-15x/year across watchlist) during genuine dislocations where fundamentals remain intact but price flushes create opportunity.

### Open Questions (revisit after 60 days)
- [ ] Is daily RSI ≤ 32 too tight? Consider 35.
- [ ] Should weekly RSI floor be 45 instead of 42?
- [ ] Is the revenue scoring heuristic calibrated correctly?
- [ ] Do we need a frequency cap on Strong Accumulate?

---

## 2026-04-18 — Tiered Weights by Asset Type + Supply Dimension

### What Changed
- Added 5th dimension: Supply/On-Chain (exchange reserves, holder distribution)
- Implemented tiered weights by asset type instead of uniform weights
- Added `asset_type` field to asset configuration

### New Weight Profiles

**Store of Value** (BTC, KAS):
- Institutional: 40%
- Supply: 25%
- Regulatory: 15%
- Wyckoff: 15%
- Revenue: 5%

**Smart Contract** (SOL, AVAX):
- Institutional: 30%
- Revenue: 25%
- Supply: 20%
- Regulatory: 15%
- Wyckoff: 10%

**DeFi** (LINK, HYPE, AAVE, MORPHO):
- Revenue: 35%
- Institutional: 25%
- Regulatory: 20%
- Supply: 15%
- Wyckoff: 5%

**Infrastructure** (QNT, XRP, XLM, HBAR):
- Institutional: 35%
- Regulatory: 25%
- Supply: 20%
- Revenue: 10%
- Wyckoff: 10%

### Why

Research indicated that uniform weights across all asset types don't reflect their fundamentally different value propositions:
- Store-of-value assets derive value from scarcity and institutional adoption, not fees
- DeFi protocols need sustainable revenue to be viable long-term
- Infrastructure plays depend on enterprise adoption and regulatory clarity

### Research Basis

1. **Institutional flows**: ETF approval correlates with 15-40% price appreciation in 6 months
2. **Revenue**: DeFi protocols with top-quartile revenue outperform bottom quartile by 3.2x annually
3. **Supply dynamics**: Exchange reserve declines correlate with 30-60 day price appreciation (r=0.42)
4. **Regulatory**: Clear regulatory status reduces volatility and enables institutional participation

### Philosophy Clarification

The framework serves to identify WHO to buy (leaders with strong fundamentals), not WHEN to buy.
- RSI and Wyckoff are timing tools for entries on assets already identified as leaders
- Buying weakness in leaders = mean reversion opportunity (they recover)
- Buying weakness in non-leaders = momentum trap (they continue down)

---

## 2026-04-18 — Dynamic Watchlist with Monthly Discovery

### What Changed
- Daily scoring moved from 09:00 UTC to 12:00 UTC
- Added monthly discovery pipeline (day 1 at 18:00 UTC)
- Watchlist becomes dynamic (assets can be added/removed based on fundamentals)

### Monthly Discovery Process
1. Claude Opus searches web for promising crypto projects
2. Evaluates candidates against 5-dimension framework
3. Reviews existing watchlist for fundamental deterioration
4. Proposes additions/removals/tier changes
5. Human reviews report and manually applies changes to assets.yaml

### Why
Static watchlists miss emerging opportunities and hold onto deteriorating assets. Monthly review ensures:
- New high-conviction projects are identified early
- Fundamental deterioration triggers removal before significant losses
- Tier assignments reflect current reality, not historical assessment

### Implementation
- `scripts/run-discovery.sh` - Monthly runner script
- `pipeline/discovery/prompt.md` - Research prompt for Claude Opus
- `discovery/report_YYYY-MM.md` - Monthly output reports

---

## Template for Future Entries

```markdown
## YYYY-MM-DD — [Change Title]

### What Changed
- [Specific parameter/threshold changed]
- [Old value → New value]

### Why
[1-2 sentences explaining the rationale]

### Observed Behavior That Prompted Change
[What signals or outcomes led to this adjustment]

### Expected Outcome
[What you expect to see after this change]
```
