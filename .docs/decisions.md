# Framework Decisions Log

Track all changes to weights, thresholds, and rationale. This file prevents framework drift.

---

## 2026-05-13 — Hash rate, global trading volume, and staking-% trend added as adoption + supply factors

### What changed

Extended the `adoption_activity` and `supply` prompts to require three additional, consensus-aware factors — all framed as recent (~30 day) live readings, consistent with the freshness preamble from the same day.

**`adoption_activity` prompt** (`src/pipeline/fetchers/qualitative.py:ADOPTION_ACTIVITY_PROMPT`) now scores from four explicit factors:

1. Global trading volume (24h / 7d / 30d, direction of travel) — applies to ALL assets. Proxy for buyer interest. Sources: CoinGecko, CMC, exchange aggregators.
2. Category-specific usage (TVL, TPS, TVS, validators, AVS, etc.) — unchanged.
3. PoW assets only — current network hash rate and 30-day trend. Sources: blockchain.com, mempool.space, hashrateindex, KasFYI.
4. PoS / native-staking assets — current % of total supply staked and 30-day trend. Sources: stakingrewards.com, beaconcha.in, chain dashboards.

**`supply` prompt** (`src/pipeline/fetchers/supply.py:SUPPLY_PROMPT`) gained:

- Sharpened pillar 4 (Staking / Lock-ups): now requires both the current staked % AND its 30-day trend, with explicit reasoning that rising staking = scarcity + confidence signal; falling during strength often precedes distribution. Issuance-adjusted framing added.
- New consensus-conditional sub-section folded into existing pillars:
  - **PoW assets** — hash rate level + 30-day trend treated as the security-budget signal feeding Holder Distribution / Exchange Reserves reasoning (miners are a structural seller cohort).
  - **PoS / native-staking assets** — emphasis on issuance-adjusted staking growth (net-new locks > issuance is what actually tightens float).

### Why

User-requested signal expansion (chat 2026-05-13):

- **Hash rate** captures miner conviction for PoW chains (BTC, KAS) — currently invisible to the framework. Folded into supply (where it drives the security-budget / miner-seller-cohort logic) since `monetary-store-of-value` does not weight adoption. Also included in `adoption_activity` for any future PoW asset in a category that weights adoption.
- **Global trading volume** is a universal interest proxy that the framework was not consulting; cheap to verify via CoinGecko / CMC and applies to every asset.
- **Staking % + trend** double-counts intentionally across two dimensions because the signal carries two different meanings: in supply it represents locked float (scarcity); in adoption it represents holder confidence in the project's future. The user explicitly asked for both.

No weight-profile changes — these are evidence factors the existing dimensions absorb naturally. If post-calibration we see hash rate or staking-% trend systematically swamping other supply factors, revisit the per-pillar weight guidance in the prompt.

### Config / code

- `src/pipeline/fetchers/qualitative.py` — rewritten `ADOPTION_ACTIVITY_PROMPT`.
- `src/pipeline/fetchers/supply.py` — rewritten staking pillar and added consensus-conditional section to `SUPPLY_PROMPT`.

### Validation to watch in the next run

- BTC and KAS supply rationales should cite recent hash rate + 30d trend with a dated source tag.
- ETH, SOL, ADA, AVAX, SUI, POL, TAO supply rationales should cite current staked % AND 30-day trend.
- All non-SoV assets' adoption_activity rationales should include a recent global volume reading with a source tag.

---

## 2026-05-13 — Real-time data freshness preamble for qualitative + supply prompts

### What changed

- Added a `DATA_FRESHNESS_PRINCIPLES` preamble prepended to every qualitative scoring call (`src/pipeline/fetchers/qualitative.py`) and every supply scoring call (`src/pipeline/fetchers/supply.py`).
- The preamble injects today's UTC date and instructs the agent CLI to:
  - Verify time-sensitive metrics (ETF AUM/flows, corporate holdings, TVL, revenue, fees, exchange reserves, staking %, on-chain activity, recent enforcement actions) against live external sources covering the last ~30–60 days, using the agent's web tools.
  - Treat memorised figures from earlier in the year as suspect and not anchor on figures from prior scoring runs.
  - Cite material figures with a short source tag and approximate date (e.g. SoSoValue, Farside, 13F filings, DefiLlama, Glassnode/CryptoQuant, SEC EDGAR).
  - Keep durable historical facts (ETF approvals, MiCA, joint SEC/CFTC commodity guidance, partnerships, supply caps, mainnet launches, halvings) as stable context without re-verifying.
  - Score conservatively and disclose the gap rather than invent specifics when a metric is unverifiable in the last ~60 days.
- The per-dimension prompts (`REGULATORY`, `INSTITUTIONAL`, `VALUE_CAPTURE`, `ADOPTION_ACTIVITY`, `SUPPLY`) were rewritten to lean on recent (last 30–60 day) values for the metrics that drive each score, without naming any specific figure that will age.

### Why

External fact-check (see `.docs/feedback.md`, 2026-05-13) found materially stale numbers leaking into rationales: Strategy BTC count understated by ~28%, IBIT AUM understated by ~25%, SOL ETF cumulative inflows overstated by ~37%, ETH spot ETF AUM stale. Root cause: prompts asked the model to "use your knowledge" without forcing it to verify against live sources, so it quoted training-cutoff figures. Durable framework events (e.g. the March 2026 SEC/CFTC commodity classification) were captured correctly, so the fix is to differentiate decay-prone metrics from durable facts in the prompt itself rather than hard-code current numbers (which would themselves age).

### Config / code

- `src/pipeline/fetchers/qualitative.py` — `DATA_FRESHNESS_PRINCIPLES`, `_freshness_block()`, rewritten REGULATORY/INSTITUTIONAL/VALUE_CAPTURE/ADOPTION_ACTIVITY prompts; preamble prepended in `_query_scoring_llm`.
- `src/pipeline/fetchers/supply.py` — `DATA_FRESHNESS_PRINCIPLES`, `_freshness_block()`, rewritten SUPPLY_PROMPT; preamble prepended in `_invoke_agent_supply`.

### Validation to watch in the next run

- Rationales should cite recent dated figures (e.g. "(SoSoValue, May 2026)") rather than round numbers without provenance.
- Strategy BTC count, IBIT AUM, SOL/ETH ETF flows should track current values, not snapshots from earlier in the year.
- Supply rationales for assets with thin on-chain data coverage should explicitly state the data gap rather than silently fall back to a neutral 50.

---

## 2026-04-21 — Framework v3: nine `asset_category` profiles + value capture / adoption

### What changed

- Replaced flat `asset_type` weight profiles with **`weights_by_category`** in `src/pipeline/config.yaml` (nine categories + `default`).
- Each watchlist asset has **`asset_category`** (and optional **`fee_model`**) in `src/pipeline/assets.yaml`.
- **Value capture** and **adoption_activity** replace a single **revenue** dimension where the taxonomy calls for it; dimensions omitted for a category are excluded and weights renormalise.
- **Wyckoff** is **not** a composite dimension; phase/score fields stay in JSON for **global filter** logic and UI only (with GLI / RS / Fear–Greed), excluded from composite weights.
- SQLite column **`snapshots.revenue`** still stores the value-capture score for backward compatibility.
- **`framework_version`**: `3.0`.

### Why

Align weights with materially different value theses (oracles vs payments vs SoV vs DeFi) and stop forcing a single “revenue” definition where it does not apply. See `.docs/research/asset-category-taxonomy.md`.

### Config / code

- `src/pipeline/category.py` — category resolution and skip rules.
- `src/pipeline/config.yaml` — `weights_by_category`.
- `src/pipeline/scoring/composite.py` — composite keyed by `asset_category`.
- `src/pipeline/run.py`, `src/pipeline/fetchers/qualitative.py` — scoring and rationales.

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
- `src/pipeline/discovery/prompt.md`
- `out/discovery/report_YYYY-MM.md`

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
- Composite ≥80, Phase C or B→C, trend ≥0, weekly RSI <70

**Promote** (runner-ups):
- Composite ≥80, 30d trend ≥+8, 7d trend ≥+2

**Stand Aside** (overrides all):
- Distribution + negative trend
- 7d trend ≤-5

### Design Intent

Strong-accumulate fires rarely (~5-15x/year) during genuine dislocations where fundamentals remain intact but price flushes create opportunity.
