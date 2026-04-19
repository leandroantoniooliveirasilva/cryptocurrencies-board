# Framework Decisions Log

Track all changes to weights, thresholds, and rationale. This file prevents framework drift.

---

## 2026-04-19 — Strong Accumulate Slope Check

### What Changed

Added weekly RSI slope check to filter "first leg down" scenarios from strong-accumulate.

**Signal triggers** (current):
1. **Capitulation**: Weekly RSI <30 AND daily RSI <30 (82.9% hit rate)
2. **Wyckoff dip**: Phase C + daily RSI ≤32 + weekly RSI ≥42 + composite stable

**Filters** (downgrade to accumulate):
- GLI contracting
- Weekly RSI was >55 four weeks ago AND dropped >8 points (slope check)

### Why

Backtest of 104 BTC signal events (2017-2024):
- Capitulation signals: 82.9% hit rate at 30 days
- Wyckoff dip signals: 63.5% overall, but 35.7% in corrections
- All 9 false positives had weekly RSI falling from elevated levels

The slope check preserves quality dips while filtering breakdown scenarios.

### Config

```yaml
rsi:
  slope_high_threshold: 55
  slope_drop_threshold: 8
```

See `.docs/research/strong-accumulate-refinement.md` for full backtest.

---

## 2026-04-18 — Dynamic Watchlist with Monthly Discovery

### What Changed

- Added monthly discovery pipeline (ensemble mode with fact-checking)
- Watchlist becomes dynamic (assets added/removed based on fundamentals)

### Process

1. 3x parallel discovery runs with different focus areas
2. Cross-reference and fact-check claims
3. Human reviews report and applies changes to assets.yaml

### Implementation

- `scripts/run-discovery-ensemble.sh`
- `pipeline/discovery/prompt.md`
- `discovery/report_YYYY-MM.md`

---

## 2026-04-18 — Tiered Weights by Asset Type + Supply Dimension

### What Changed

- Added 5th dimension: Supply/On-Chain
- Implemented weight profiles by asset type

### Weight Profiles

| Type | Inst | Rev | Reg | Supply | Wyck |
|------|------|-----|-----|--------|------|
| store-of-value | 40% | 5% | 15% | 25% | 15% |
| smart-contract | 30% | 25% | 15% | 20% | 10% |
| defi | 25% | 35% | 20% | 15% | 5% |
| infrastructure | 35% | 10% | 25% | 20% | 10% |

### Why

Uniform weights don't reflect fundamentally different value propositions:
- Store-of-value: scarcity and institutional adoption, not fees
- DeFi: sustainable revenue is essential
- Infrastructure: enterprise adoption and regulatory clarity

---

## 2026-04-17 — Initial Framework

### Thresholds

**Strong Accumulate** (leaders):
- Daily RSI ≤32 + weekly RSI ≥42 + composite stable
- OR both RSI <30 (capitulation)

**Accumulate** (leaders):
- Composite ≥75, Phase C or B→C, trend ≥0, weekly RSI <70

**Promote** (runner-ups):
- Composite ≥75, 30d trend ≥+8, 7d trend ≥+2

**Stand Aside** (overrides all):
- Distribution + negative trend
- 7d trend ≤-5

### Design Intent

Strong-accumulate fires rarely (~5-15x/year) during genuine dislocations where fundamentals remain intact but price flushes create opportunity.
