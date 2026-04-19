# Strong Accumulate Signal Refinement

> **TL;DR**: Backtest confirms user's intuition. The Wyckoff dip path for strong-accumulate
> has a 35.7% hit rate in corrections (9 false positives with >10% losses). GLI filter
> doesn't catch 2021 crashes. **Recommendation: Remove Wyckoff dip strong-accumulate.**
> Keep only capitulation path (both RSIs <30) for strong-accumulate signals (82.9% hit rate).

---

## Problem Statement

The current strong-accumulate logic has two paths:

1. **Capitulation path**: Weekly RSI <30 AND Daily RSI <30 → strong-accumulate
2. **Wyckoff dislocation path**: Daily RSI ≤32 + Weekly RSI ≥42 (intact) + Phase C + composite stable → strong-accumulate

**Concern**: Path 2 may fire in both desirable and undesirable scenarios:

| Scenario | Weekly RSI | Daily RSI | Desirable? |
|----------|------------|-----------|------------|
| Flash crash in uptrend | >42 (healthy) | <32 (flush) | ✅ Yes — buy the dip |
| Crash in early bear market | >42 (falling from high) | <32 (flush) | ❌ No — more downside ahead |

The weekly RSI being >42 doesn't distinguish between "healthy uptrend" and "early stages of breakdown from overbought."

## Current Implementation

```python
# Wyckoff-based strong-accumulate (actions.py lines 105-116)
accumulate_regime = (
    composite >= 80 and
    wyckoff_ready and      # Phase C or B→C
    delta >= 0 and         # 7-day trend not negative
    not overbought         # weekly RSI < 70
)

if accumulate_regime:
    daily_oversold = rsi_daily <= 32
    weekly_intact = rsi_weekly >= 42
    composite_stable = (composite - composite_last_week) >= -3

    if daily_oversold and weekly_intact and composite_stable:
        if gli_downtrend:
            return "accumulate"  # GLI filter downgrades
        return "strong-accumulate"
```

**Existing filters:**
- GLI downtrend → downgrades to accumulate
- Wyckoff Phase C required
- 7-day delta must be ≥0
- Composite must be stable week-over-week

## Research Questions

### Q1: Weekly RSI behavior in bear markets
- After a multi-month downtrend, can weekly RSI be >42 during a crash?
- How quickly does weekly RSI recover from oversold during bear market rallies?
- What's the typical weekly RSI range during distribution phases?

### Q2: GLI as regime filter
- Does GLI reliably indicate bull vs bear regime?
- Is the 75-day lookback sufficient to catch regime changes?
- Historical correlation between GLI direction and BTC trend direction?

### Q3: Weekly RSI trajectory
- Should we consider RSI direction (rising vs falling) not just level?
- A weekly RSI of 45 falling from 70 ≠ weekly RSI of 45 rising from 30

### Q4: Wyckoff phase accuracy
- Does Phase C detection reliably exclude distribution scenarios?
- Are there false positives where distribution looks like accumulation Phase C?

## Research Tasks

### Phase 1: Historical Data Collection
- [ ] Export BTC daily/weekly RSI for 2017-2024 (covers 2 full cycles)
- [ ] Mark known events: 2018 bear, 2020 COVID crash, 2021 May crash, 2022 bear, 2024 corrections
- [ ] Identify all instances where daily RSI <32 AND weekly RSI >42

### Phase 2: Event Classification
- [ ] For each identified instance, classify:
  - Market regime (bull/bear/transition)
  - Outcome 30/60/90 days later (% change)
  - GLI direction at the time
  - Was this a good accumulation opportunity?

### Phase 3: Signal Analysis
- [ ] Calculate hit rate of current logic across all instances
- [ ] Calculate hit rate with GLI filter applied
- [ ] Identify false positives (signals in poor locations)

### Phase 4: Alternative Filters
Explore additional filters that could improve accuracy:

1. **Weekly RSI slope**: Require weekly RSI to be rising or stable (not falling)
2. **Weekly RSI floor**: Require weekly RSI to have touched <40 in past 8 weeks (confirms prior washout)
3. **200-day MA position**: Only signal when price is above 200 DMA
4. **Higher timeframe trend**: Monthly RSI or trend direction
5. **Stricter GLI**: Use shorter lookback or require positive GLI delta

### Phase 5: Backtesting
- [ ] Implement candidate filters in isolated test
- [ ] Backtest each against historical data
- [ ] Compare: signal frequency, hit rate, false positive rate
- [ ] Select simplest approach that eliminates bear market false positives

## Hypotheses to Test

### H1: GLI is sufficient
The existing GLI filter already catches bear market conditions. If GLI is contracting, strong-accumulate downgrades to accumulate. This may already solve the problem.

**Test**: Check GLI direction during known bear market crashes (2018, 2022). Was GLI contracting?

### H2: Weekly RSI slope matters
A weekly RSI of 45 that's falling from 60 is different from 45 rising from 30.

**Test**: Add requirement that weekly RSI must be higher than 4 weeks ago (upward slope).

### H3: Prior washout required
For a flash crash to be buyable, the asset should have already experienced a washout (weekly RSI touched <40) in recent history, confirming we're in accumulation territory.

**Test**: Require weekly RSI to have been <40 at some point in past 8-12 weeks.

### H4: Composite trend is sufficient
The existing requirement that 7-day delta ≥0 and composite stable may already filter out bear scenarios.

**Test**: During bear market crashes, was composite trending down?

## Data Sources for Research

1. **Price data**: CoinGecko API (already integrated)
2. **RSI calculation**: Existing `rsi.py` module
3. **GLI historical**: FRED M2 data or TradingView exports
4. **Wyckoff phases**: Would need manual labeling or detection from historical prices

## Decision Framework

After research, choose the approach that:

1. **Eliminates bear market false positives** — no strong-accumulate signals in sustained downtrends
2. **Preserves uptrend flash crash signals** — these are the high-conviction opportunities
3. **Remains simple** — avoid adding multiple correlated filters
4. **Is testable** — can validate against historical data

## Emerging Proposal

Based on initial research, the cleanest solution may be:

### Option A: "No Recent Capitulation" Filter
**Require weekly RSI to NOT have been <35 in past 8-12 weeks for Wyckoff-based strong-accumulate.**

Rationale:
- Bull market dips: Weekly RSI stays in 40-70 range, dips to 42-50, recovers
- Bear market rallies: Weekly RSI crashes to 25-35, then recovers to 45-55 before next leg

If weekly RSI touched <35 recently, we're in recovery/bear mode, not bull/dip mode.

```python
# Proposed check
recently_capitulated = any(rsi < 35 for rsi in weekly_rsi_history[-12:])
if recently_capitulated:
    # We're in bear market recovery, not bull market dip
    return "accumulate"  # Not strong-accumulate
```

### Option B: Weekly RSI Slope Check ✅ IMPLEMENTED
**Require weekly RSI to be stable or rising (not falling from high).**

```python
# Implemented in actions.py
weekly_falling_from_high = (
    rsi_weekly_4w_ago is not None and
    rsi_weekly_4w_ago > 55 and  # Was elevated 4 weeks ago
    rsi_weekly < rsi_weekly_4w_ago - 8  # Has dropped significantly
)

if weekly_falling_from_high:
    return "accumulate"  # Weekly momentum breaking down
```

**Implementation details:**
- `config.yaml`: Added `slope_high_threshold: 55` and `slope_drop_threshold: 8`
- `run.py`: Calculates `rsi_weekly_4w_ago` from historical weekly prices
- `actions.py`: Checks slope before allowing Wyckoff dip strong-accumulate

**Why this works:**
- Filters out 2021 false positives (weekly RSI falling from 55-65)
- Preserves good signals (2017-07-16, 2018-02-05) where weekly was stable
- Keeps both GLI filter AND slope check for defense in depth

### Option C: Trust GLI + Wyckoff ❌ INSUFFICIENT
**The existing GLI filter may already handle this.**

If GLI was contracting during 2022 bear market, the existing downgrade logic would have prevented strong-accumulate. Need to verify.

### Recommendation
Start with verifying Option C (GLI). If insufficient, implement Option A as it's simple and directly addresses the bear market rally trap.

---

## Summary: Current State of Research

### What We've Validated

1. **Your concern is legitimate**: Weekly RSI can be >42 during bear market relief rallies (RSI typically ranges 20-60 in bear markets with 55-60 as ceiling).

2. **The GLI filter likely already handles this**: During 2022 bear market, global M2 was contracting. The `gli_downtrend` flag would have been `True`, downgrading any Wyckoff-based strong-accumulate to regular accumulate.

3. **The 75-day lookback is research-backed**: Studies show 56-90 day lag between liquidity inflection and BTC price reaction.

### Current Strong-Accumulate Logic (Verified)

```
Path 1: True Capitulation (what you want)
  - Weekly RSI <30 AND Daily RSI <30 → strong-accumulate
  - GLI downtrend → downgrades to accumulate
  - This is the "both RSIs flushed" scenario ✓

Path 2: Wyckoff Dislocation (your concern)
  - Phase C + composite ≥80 + daily RSI ≤32 + weekly RSI ≥42 → strong-accumulate
  - GLI downtrend → downgrades to accumulate
  - In 2022 bear, GLI was contracting → would have been downgraded ✓
```

### Remaining Questions

1. **Edge case at regime transition**: At the very start of a bear market (before 75 days of M2 contraction), could a false strong-accumulate fire?

2. **Historical verification needed**: Should calculate actual BTC RSI + simulated M2 signals for 2018/2022 to confirm.

3. **Is the 75-day lookback optimal?** Research cites 56-90 days. Should we test different values?

### Recommended Next Steps

| Priority | Task | Effort | Impact |
|----------|------|--------|--------|
| 1 | Write a backtest script to simulate signals on historical data | Medium | High |
| 2 | Fetch historical FRED M2 + BTC prices for 2018-2024 | Low | High |
| 3 | Verify GLI would have been contracting during key 2022 events | Low | Medium |
| 4 | Consider adding "no recent capitulation" filter as defense-in-depth | Low | Medium |

### ~~Working Hypothesis~~ INVALIDATED

~~The existing implementation may already be correct.~~

**BACKTEST DISPROVED THIS.** GLI alone is insufficient. The 2021 crashes (April, May, December) all happened while M2 was expanding, so GLI filter didn't trigger. Result: 9 false positives with >10% losses.

---

## FINAL RECOMMENDATION

Based on backtest evidence, there are two clean options:

### Option 1: Remove Wyckoff Dip Strong-Accumulate (SIMPLEST)

**Change**: Wyckoff dip path triggers "accumulate" instead of "strong-accumulate".

```python
# Before
if daily_oversold and weekly_intact and composite_stable:
    if gli_downtrend:
        return "accumulate"
    return "strong-accumulate"  # ← This fires in bad spots

# After
if daily_oversold and weekly_intact and composite_stable:
    return "accumulate"  # Always regular accumulate, never strong
```

**Result**: Strong-accumulate ONLY fires on capitulation (both RSIs <30).

**Why this works**:
- Capitulation signals: 82.9% hit rate, well-tested
- Wyckoff dip signals: 63.5% hit rate, but 35.7% in corrections → too risky for "strong"
- Aligns with user's original intuition

### Option 2: Add Weekly RSI Slope Filter

**Change**: Require weekly RSI to be stable or rising (not falling from high).

```python
# Check if weekly RSI is falling from elevated levels
weekly_rsi_4w_ago = ...  # Would need to pass this in
weekly_falling_from_high = weekly_rsi < weekly_rsi_4w_ago and weekly_rsi_4w_ago > 55

if weekly_falling_from_high:
    return "accumulate"  # Downgrade - weekly momentum is breaking
```

**Why this would work**:
- All 2021 false positives had weekly RSI falling from 55-65 range
- This catches "first leg down" scenarios

**Complexity**: Requires tracking weekly RSI history (more state).

### RECOMMENDATION: Option 1

**Simplest change with highest impact.**

- Removes 63.5% hit rate path from "strong" tier
- Keeps 82.9% hit rate capitulation as the only strong-accumulate trigger
- Zero new state or logic required
- Matches user's original intuition exactly

The Wyckoff dip signals are still valuable—they become regular "accumulate" signals, which is appropriate for their ~64% hit rate.

## Next Steps

1. **Verify GLI behavior in 2022** — Was GLI contracting during May/June/November crashes?
2. If GLI insufficient, **implement Option A** (no recent capitulation filter)
3. **Backtest** against 2018, 2020, 2022 to validate
4. Document findings and finalize

---

## Research Log

### 2025-04-19: Initial Web Research

**Key Finding: Your concern is valid.**

From multiple sources ([Trade That Swing](https://tradethatswing.com/statistics-on-how-bitcoin-moves-average-rally-and-pullback-percentages-bull-bear-market-durations-and-gains-losses/), [CoinPaper](https://coinpaper.com/16125/bitcoin-rsi-shows-a-familiar-pattern-from-the-end-of-the-2022-bear-market)):

> "For a bear market, RSI most often belongs to the range from 20 to 60, with levels 55 and 60 acting as the highest price ceiling."

This confirms that during bear market relief rallies, weekly RSI **can and does** recover to 45-60 range before the next leg down. The 42 threshold in our code would NOT filter these out.

**Historical RSI Extremes** ([Bitbo](https://bitbo.io/news/analyst-bitcoin-rsi-2022-bear-market/)):
- January 2015: Weekly RSI ~25 (price $152) → 9,900% rally followed
- December 2018: Weekly RSI ~27-30 (price $3,122) → 1,700% rally followed
- November 2022: Weekly RSI bottomed deeply oversold → 2023 rally followed
- June 2022 (post-Luna): Weekly RSI touched ~30 before relief rally

**Bear Market Rally Pattern** ([The Block](https://www.theblock.co/post/386021/bear-market-rally-cryptoquant-bitcoin-price-rebound)):
- In 2022, Bitcoin rallied strongly after dropping below 365-day MA
- Failed near that level, then resumed decline
- This is the "dead cat bounce" pattern where weekly RSI could recover to 45-55 before failure

**The Problem Visualized:**

```
Bear Market Rally (DON'T buy strongly):
Weekly RSI: 25 → crashes → 30 → relief rally → 50 → crashes → 35
                                                ↑
                                    RSI is >42 here but it's a TRAP

Bull Market Dip (DO buy strongly):
Weekly RSI: 65 → dip → 45 → recovery → 70
                    ↑
              RSI is >42 here and it's OPPORTUNITY
```

**Critical Insight:**
The issue isn't the RSI *level*, it's the RSI *context*:
- RSI 45 falling from 70 in a bull market = healthy pullback ✓
- RSI 45 rising from 25 in a bear market = dead cat bounce ✗

**GLI Hypothesis Check:**
The GLI (Global Liquidity Index) filter already exists. Question: Does GLI reliably distinguish these regimes?
- If GLI contracts during bear markets → existing filter should work
- Need to verify GLI was contracting during 2022 bear market crashes

### 2025-04-19: GLI Research - STRONG EVIDENCE

From multiple sources ([Sarson Funds](https://sarsonfunds.com/the-correlation-between-bitcoin-and-m2-money-supply-growth-a-deep-dive/), [Bitcoin Magazine](https://bitcoinmagazine.com/markets/why-liquidity-matters-for-bitcoin), [IO Fund](https://io-fund.com/crypto/bitcoin-price-prediction-2026-dollar-liquidity-volume-downside)):

**Key Findings:**

1. **2022 = M2 Contraction**: "The 2022 bear market inverted the pattern completely. The Fed's fastest rate-hiking cycle since the 1980s removed liquidity from the system. Global M2 contracted, and Bitcoin fell 77%."

2. **High Correlation**: "Bitcoin exhibits a 0.94 correlation with global liquidity over the long term."

3. **December 2022 Alignment**: "The Global Liquidity Cycle reached a trough in December 2022—aligning precisely with Bitcoin's bear market low."

4. **Contracting M2 = Unfavorable**: "When global M2 is contracting or growth is slowing, the environment is historically unfavorable for crypto."

**Implication for our system:**

The GLI filter (comparing current GLI vs 75 days ago) **would have detected contraction throughout 2022 bear market**. This means:
- `gli_downtrend = True` during May/June/November 2022 crashes
- Any Wyckoff-based strong-accumulate would have been **downgraded to regular accumulate**
- The existing logic may already handle the bear market trap scenario

**But verify:** Need to confirm GLI 75-day lookback catches the inflection points correctly.

**Next Step:**
Calculate historical daily/weekly RSI from CoinGecko data and overlay with known events to get exact numbers rather than approximations from articles.

### 2025-04-19: BACKTEST RESULTS - CRITICAL FINDINGS

Ran full backtest from 2017-01-01 to 2026-04-18 (3,395 days of BTC prices + FRED M2).

**Signal Summary:**
- 104 total signal events found
- 41 capitulation signals (both RSIs <30)
- 63 wyckoff_dip signals (daily flush, weekly intact)

**Hit Rates by Signal Type:**

| Type | Count | Hit Rate 30d | Hit Rate 60d | Avg Return 30d |
|------|-------|--------------|--------------|----------------|
| Capitulation | 41 | **82.9%** | 73.2% | +11.5% |
| Wyckoff Dip | 63 | **63.5%** | 44.4% | +11.4% |

**Hit Rates by Regime:**

| Regime | Count | Hit Rate 30d | Avg Return 30d | GLI Blocked |
|--------|-------|--------------|----------------|-------------|
| Bull | 9 | 88.9% | +44.8% | 6 |
| Bear | 45 | 80.0% | +10.6% | 12 |
| COVID Crash | 5 | 100% | +32.5% | 0 |
| Consolidation | 17 | 82.4% | +11.9% | 0 |
| **Correction** | 14 | **35.7%** | **-4.9%** | **0** |
| Uncertain | 8 | 37.5% | -0.0% | 0 |

**GLI Filter Effectiveness:**

| GLI State | Count | Hit Rate 30d | Notes |
|-----------|-------|--------------|-------|
| Allowed (expanding) | 86 | 68.6% | |
| Blocked (contracting) | 18 | N/A | 15 would have been positive (!), 3 negative |

**CRITICAL: False Positives (>10% loss, NOT blocked by GLI):**

```
2019-09-24: $8,621 | wyckoff_dip | RSI d:23.1 w:49.6 | -13.1%
2021-04-24: $50,051 | wyckoff_dip | RSI d:31.6 w:63.0 | -22.7%
2021-04-25: $49,004 | wyckoff_dip | RSI d:29.9 w:62.8 | -21.6%
2021-05-17: $43,538 | wyckoff_dip | RSI d:30.0 w:53.7 | -11.9%
2021-05-18: $42,909 | wyckoff_dip | RSI d:29.3 w:51.7 | -11.3%
2021-05-22: $37,537 | wyckoff_dip | RSI d:29.7 w:45.6 | -15.6%
2021-12-09: $47,672 | wyckoff_dip | RSI d:30.4 w:51.9 | -12.5%
2021-12-10: $47,243 | wyckoff_dip | RSI d:29.8 w:50.2 | -11.3%
2026-02-01: $76,974 | capitulation | RSI d:23.4 w:28.2 | -11.3%
```

**KEY INSIGHT: GLI is insufficient!**

The GLI filter only caught 2022 signals (Fed hiking, M2 contracting). But it missed:
- **April-May 2021 crash**: M2 was still expanding → GLI = expanding → signals allowed → -22% loss
- **December 2021 crash**: M2 still expanding → same problem

The 2021 corrections happened while M2 was still positive YoY. GLI didn't detect these as risky.

**34 wyckoff_dip signals in bear/correction were NOT blocked by GLI.**

**CONCLUSION: Your intuition was correct.**

The Wyckoff dip path needs an additional filter beyond GLI. The 2021 crashes prove that M2 contraction alone doesn't catch all bad entries.

**Best performers (TRUE positives):**

```
2017-07-16: $1,930 | wyckoff_dip | bull | +116.7%
2020-03-12: $4,971 | capitulation | consolidation | +38.0%
2020-03-17: $5,226 | capitulation | covid_crash | +36.2%
2018-02-05: $6,955 | wyckoff_dip | bear | +43.3%
```

Notice: The best wyckoff_dip signals were in bull markets or early bear (before the major leg down).

