# Asset Category Taxonomy — Research & Proposal

Date: 2026-04-21
Status: Implemented — weights in `pipeline/config.yaml` (`weights_by_category`), assignments in `pipeline/assets.yaml`.
Related: `.docs/decisions.md`, `pipeline/config.yaml`, `pipeline/assets.yaml`, `pipeline/run.py`, `.agents/skills/discovery/instructions.md`.

## 1. Problem Statement
The current framework uses five universal dimensions — institutional, revenue, regulatory, supply, wyckoff — with four category-specific weight profiles (store-of-value, smart-contract, defi, infrastructure). Two recurring problems:

1. "Revenue" means something different in each category — and sometimes does not apply. Forcing a single definition creates incoherence: BTC gets an LLM-estimated revenue score even though fees go to miners, not holders; CANTON excludes revenue via `fee_model: burn` and redistributes weight; XRP/XLM/HBAR get punitive revenue scores despite fees being minimal by design.
2. The "infrastructure" bucket is too broad. LINK (oracle), CANTON (enterprise-ledger), XRP (payments rail), TIA (data availability), EIGEN (restaking) have materially different value theses and measurable signals. One weight profile cannot represent them all.

User direction:
- Nuance should come from the category, not from one-off asset overrides.
- Weight structure should still keep scoring comparable across categories.
- New dimensions are acceptable where they add signal, and a dimension should be skipped where it genuinely does not apply.
- Burn/mint for CANTON, mining-fee-driven hashrate for BTC/KAS — these "fees" do matter, but they must be read as supply-side / security signals, not as holder revenue.

## 2. Industry Reference Points
### Messari Classification System
Four layers: Entity Type → Sector → Sub-sector → Tag. Thirteen top-level sectors: AI, CeFi, DeFi, Networks, Blockchain Infrastructure, DePIN, Gaming, NFTs, Meme, Stablecoins, Blockchain Services, Tools, Others. Under Networks: Layer-0 / Layer-1 / Layer-2 / Layer-3 / Interoperability. Under Blockchain Infrastructure: Clients, Hosting, Indexing, Oracles, Validator Operations, Wallets, Mining. An asset can belong to multiple sectors.

Key takeaway: a flat "asset_type" list is an oversimplification; even Messari uses a hierarchy plus free-form tags, and the same asset can appear in multiple categories (e.g. XRP is both "Layer-1" and "Centralized Payments").

### Token Terminal — Fees vs Revenue vs Earnings
Token Terminal draws three explicit income-statement lines for every protocol:
- Fees: total paid by users
- Supply-side fees: paid to LPs, miners, validators
- Revenue: protocol's cut of fees (take rate applied to fees)
- Token incentives: emissions spent on growth
- Earnings: revenue − incentives − opex

Reported take rates differ dramatically:
- Ethereum: ~80% take rate (burn + staker tips)
- Uniswap DAO: 0% take rate (all fees to LPs)
- Bitcoin: 0% take rate (all fees to miners, no holder accrual)
- Filecoin: ~99.7% (near-total revenue capture)
- dYdX, Synthetix, MakerDAO: 100%

Guidance: use Fees for early-stage protocols, Revenue for later-stage, Earnings for mature. Compare Revenue/Fees and Earnings/Revenue ratios.

Key takeaway: "Revenue" is a derived number (Fees × take rate). It only accrues to token holders when the take rate is positive and mapped to burns / staking rewards / buybacks. For BTC and Uniswap the take rate is 0%.

### VanEck / MarketVector Fundamental Index
- Blockchain revenue = transaction count × avg fee per transaction (incl. MEV)
- Portfolio weighting uses transaction fees + active addresses (not just fees)
- For BTC: miners capture all fee revenue; holders capture none — but BTC still merits portfolio weight because it functions as the reserve asset of an internet-native economy
- For ETH: network profitability = (tx fees + MEV to holders) > new issuance — the "real yield" test
- For newer chains: developer activity and usage are more relevant than financial metrics

Key takeaway: even institutional indices accept that BTC is a reserve asset whose fee capture is structurally zero for holders, and they don't penalise it for that. Different asset types are evaluated on different primary metrics.

### Onramp / CoinShares — Store-of-Value Security Budget
- BTC's "security budget" = block subsidy + fees
- Hashrate ≈ cost to attack = security wall
- Hashrate growth over multi-year horizons is the structural anchor for BTC valuation above speculative price cycles
- Long-term concern: as issuance halves, fees must grow to keep security budget proportional to secured value
- A sustained drop in hashrate is an existential signal for a PoW SoV

Key takeaway: for PoW SoV assets, the supply/security story is not "how much revenue does the token holder capture" — it is "is mining economically rational and is the network secure." Fees matter here but they matter as a *security-budget input*, not as direct holder revenue.

### Chainlink — Total Value Secured (TVS)
For oracles, TVL does not apply because oracles don't custody value. The industry has converged on TVS: the aggregate TVL across protocols that depend on the oracle. Chainlink's TVS grew from ~$38B (2024) to >$100B (2025) while daily revenue stayed modest (~$15k/day); the token value proposition is dominated by adoption breadth and institutional integrations (DTCC, SBI Group, ICE, US DoC) rather than by take-rate revenue.

Key takeaway: for oracles and data infrastructure, the correct "adoption" metric is TVS + integrations + institutional partnerships. Absolute revenue is a secondary lens at best.

### Canton — Burn/Mint Equilibrium (BME)
Canton publishes a burn/mint ratio trending from 0.025 at launch towards 1.0 (equilibrium). Fees are 100% burned (priced in USD), rewards are minted to Super Validators, synchronisers, app providers, and the protocol dev fund. 100% fee burn means "fees" is a supply-side signal: the closer burn gets to mint, the more real institutional activity is absorbing issuance. Network activity is tracked by TPS, transactions-per-day, validator count (24 at launch → 575+ in 12 months), and institutional wallet count.

Key takeaway: Canton's "revenue" does not exist as a holder-accrual number — it is encoded inside the supply dimension as burn/mint ratio, and inside an activity dimension as TPS / validator growth / institutional adoption. Treating it as an excluded revenue dimension is technically correct but leaves the bulk of the signal uncaptured.

### EigenLayer — Restaking / Shared Security
Different value pattern again. Ecosystem metrics:
- TVL (amount restaked, currently ~$15B)
- Number of AVSs (Actively Validated Services) live / in development
- Number of operators and restakers
- AVS fee capture to token (ELIP-12 proposes 20% AVS fee + 100% EigenCloud infrastructure fees → EIGEN buybacks)
- Slashing events / risk-adjusted yield

Key takeaway: restaking/shared-security tokens are valued on adoption breadth (AVS count, operator count) and the protocol's ability to route a real share of service fees back to the token. Revenue/TVL ratio is less meaningful — the TVL is not the customer, the AVSs are.

## 3. Principles for the Revised Framework
1. Keep the composite score comparable: all categories produce a 0–100 composite, weights always sum to 1.0 (possibly via renormalisation).
2. Replace the single "Revenue" dimension with a **Value Capture** dimension whose definition varies by category. For some categories, value capture is genuinely N/A and is excluded (weight renormalises).
3. Introduce an **Adoption / Network Activity** dimension to capture usage signals (active addresses, TPS, TVS, validators, AVS count). Currently usage signals are implicitly folded into "Institutional" or "Revenue," which is imprecise.
4. Keep **Institutional**, **Regulatory**, and **Supply/Tokenomics** as weighted dimensions, and use **Wyckoff** as a global post-score filter (not a weighted category dimension).
5. Each asset carries an `asset_category` and, optionally, a `fee_model` (how fees translate into token value). The category determines the weight profile; the fee_model determines how the Value Capture dimension is scored, or whether it is excluded.
6. Where a dimension is genuinely excluded, weights redistribute across the remaining dimensions (already supported in `pipeline/scoring/composite.py`).
7. The methodology should work for discovery too: when a new asset appears, the discovery flow assigns category + fee_model, and the scoring flow does the rest.

## 4. Proposed Categories
Nine categories, each mapped to a value thesis. Every category retains comparable weighted dimensions but differs on which extra dimensions apply.

### 4.1 `monetary-store-of-value`
Examples: BTC, KAS, LTC, BCH, XMR, ZEC
Thesis: Digital scarcity + monetary premium + settlement layer. Value accrues through scarcity and security, not through fee capture by holders.
Dimensions:
- institutional 0.40
- supply_and_security 0.35  (stock-to-flow, issuance schedule, exchange reserves, long-term-holder %, hashrate trend, security budget sufficiency)
- regulatory 0.25
Value Capture: excluded. Fees matter here but they are rolled into the supply_and_security dimension as "is the security budget sustainable without issuance." No separate revenue score.

### 4.2 `smart-contract-platform`
Examples: ETH, SOL, SUI, AVAX, TRON, ADA, TON, APT
Thesis: Native fuel token whose value tracks ecosystem activity, real yield, and institutional integration.
Dimensions:
- institutional 0.25
- adoption_activity 0.20  (active addresses, TPS, DAU, developer count, TVL on chain)
- value_capture 0.20  (fees captured by holders via burn + staking yield minus issuance; "real yield" test)
- supply_and_tokenomics 0.20  (staking ratio, net issuance after burn, unlocks)
- regulatory 0.15
Value Capture: scored. For chains with a hybrid fee model (ETH-style base-fee burn + validator tips), use the holder-accruing share only.

### 4.3 `defi-protocol`
Examples: AAVE, MORPHO, HYPE, PENDLE, UNI, LDO, JUP, ONDO, ENA
Thesis: Application token whose value depends on protocol economics, fee capture, and sustainable yield.
Dimensions:
- value_capture 0.30  (daily revenue, Rev/TVL ratio, earnings after token incentives, take rate)
- adoption_activity 0.15  (TVL growth, active users, integrations)
- institutional 0.20
- regulatory 0.15
- supply_and_tokenomics 0.20  (emission schedule vs revenue, unlocks, distribution concentration)
Value Capture: always scored. Fee model can be `revenue`, `buyback_and_burn`, or `staking_share`.

### 4.4 `oracle-data`
Examples: LINK, PYTH
Thesis: Data infrastructure whose value scales with adoption breadth (TVS) and institutional integrations rather than with take rate.
Dimensions:
- institutional 0.25
- adoption_activity 0.25  (TVS, number of integrations, CCIP / data-streams volume, enterprise integrations)
- regulatory 0.20
- value_capture 0.15  (absolute revenue, staking yields, buyback programs such as Chainlink Reserve)
- supply_and_tokenomics 0.15
Value Capture: scored absolutely (not Rev/TVL — TVL is not the right denominator).

### 4.5 `enterprise-settlement`
Examples: CANTON, QNT (depending on positioning)
Thesis: Permissioned-friendly L1 for regulated finance; value accrues through institutional volume + burn/mint equilibrium + validator growth.
Dimensions:
- institutional 0.30
- adoption_activity 0.25  (TPS trend, transactions/day, validator count, institutional wallet count, production deployments)
- regulatory 0.25
- supply_and_tokenomics 0.20  (burn/mint equilibrium ratio, validator distribution, emission schedule)
Value Capture: excluded as a standalone dimension. Fee capture is embedded inside `supply_and_tokenomics` as the burn/mint ratio (approaching 1.0 is bullish). This is consistent with treating the burn as a supply-side signal, not as holder revenue.

### 4.6 `payments-rail`
Examples: XRP, XLM, HBAR
Thesis: Cross-border settlement / payment rail; fees are intentionally minimal, value tracks institutional adoption and corridor volume.
Dimensions:
- institutional 0.35
- adoption_activity 0.20  (ODL / payment corridor volume, stablecoin settlement volume on chain, institutional partnerships)
- regulatory 0.30
- supply_and_tokenomics 0.15  (escrow / lockups, inflation, concentration)
Value Capture: excluded. Fees are minimal by design and do not accrue to holders. Don't penalise the asset on a dimension that structurally doesn't apply.

### 4.7 `shared-security`
Examples: EIGEN, (Babylon, Symbiotic when added)
Thesis: Shared-security / restaking primitive; value depends on AVS breadth, operator economics, and the protocol's ability to route fees back to the token.
Dimensions:
- adoption_activity 0.25  (AVS count live/in-dev, operators, restakers, TVL restaked)
- value_capture 0.25  (AVS fee capture, buyback mechanisms, EigenCloud / equivalent fees to token)
- institutional 0.20
- regulatory 0.15
- supply_and_tokenomics 0.15  (emission, unlocks, slashing insurance funded)

### 4.8 `data-availability-modular`
Examples: TIA (Celestia), EigenDA-style tokens where separable
Thesis: Modular DA / execution layer serving rollups; adoption tracked by rollup count + DA fees.
Dimensions:
- adoption_activity 0.25  (rollups using DA, bytes posted, DA fees, developer activity)
- value_capture 0.20  (DA fees accruing to holders via burn or staking)
- institutional 0.20
- regulatory 0.15
- supply_and_tokenomics 0.20

### 4.9 `ai-compute-depin`
Examples: TAO, AKT, RNDR, FIL (for DePIN storage subset)
Thesis: Decentralised physical infrastructure / AI compute marketplace; value tracks subnet / supply-demand economics.
Dimensions:
- adoption_activity 0.25  (subnet / network usage, supply side deployments, demand side revenue)
- value_capture 0.20  (fees vs emissions, "real" revenue vs token incentives)
- institutional 0.20
- supply_and_tokenomics 0.20
- regulatory 0.15

## 5. Fee Model Taxonomy (for the `value_capture` dimension)
`fee_model` tells the scorer how to interpret fees as value accrual to the token holder.

- `revenue`: fees flow to a treasury or are captured via take rate + buybacks. Score using daily revenue and Rev/TVL (or absolute revenue for non-TVL assets like oracles).
- `burn`: fees burned (EIP-1559 style base fee, Canton CC). If category is `enterprise-settlement`, score under supply (burn/mint equilibrium). If category is `smart-contract-platform` (ETH), score under value_capture as net-issuance-after-burn.
- `staking_share`: fees partially distributed to stakers as yield (ETH tips, Solana). Score under value_capture as staking real yield vs inflation.
- `miner`: fees go to miners/validators without holder accrual (BTC, KAS, Filecoin). Value_capture excluded. Fees analysed under supply_and_security as security budget input.
- `minimal`: fees intentionally negligible (XRP, XLM). Value_capture excluded.
- `equity`: revenue accrues to equity holders, not token (legacy XRP interpretation by some analysts). Value_capture excluded for the token, regulatory risk flagged in rationale.

A single asset can only have one fee_model; if the mechanism is hybrid (e.g. ETH) pick the dominant one and describe nuances in the rationale.

## 6. Dimension Definitions and Measurability
### institutional (universal)
ETF products / filings, custody, fund holdings, enterprise partnerships, corporate treasury adoption. Unchanged.

### regulatory (universal)
SEC/CFTC posture, jurisdictional classification, MiCA, exchange listing breadth, compliance integration. Unchanged.

### wyckoff (global filter, not weighted)
Technical phase from price action is evaluated after composite scoring to downgrade riskier entries:
- accumulation: no downgrade
- markup: mild downgrade
- distribution: strong downgrade
- markdown: strongest downgrade / blocks strong-accumulate classification
This keeps category scores fundamentally comparable while preserving Wyckoff as a market-structure guardrail alongside GLI / Fear-Greed / RSI.

### supply_and_tokenomics / supply_and_security (category-variant)
Always scored; the list of features differs by category:
- SoV: stock-to-flow, issuance schedule, exchange reserves, long-term holder %, hashrate trend, security budget / issuance + fees
- L1 fuel: staking ratio, inflation net of burn, validator distribution, unlocks
- DeFi: token emission vs revenue, unlocks, concentration
- Oracle: concentration, unlocks, staking participation
- Enterprise L1: burn/mint equilibrium ratio, validator count trend, CIP-driven emissions
- Payments: supply concentration, escrow releases, issuance
- Shared security: unlocks, slashing pool funding, validator/operator distribution

### adoption_activity (new, most categories)
Usage signals that make the network real. Per-category:
- L1 fuel: active addresses, TPS, DAU, dev count, TVL
- DeFi: TVL trend, users, integrations
- Oracle: TVS, integrations count, data stream volume
- Enterprise L1: TPS, transactions/day, validator count, institutional wallet count
- Payments: ODL volume, corridor count, stablecoin flows on chain
- Shared security: AVS count, operators, restakers
- DA/modular: rollups served, bytes posted, fees captured
- AI/compute: subnet count, compute hours sold

### value_capture (renamed revenue, category-variant or excluded)
- DeFi: daily revenue, Rev/TVL, earnings after incentives
- L1 fuel: holder-accruing fees (burn + staking yield − issuance)
- Oracle: absolute revenue, buyback flows
- Shared security: AVS fee capture, infrastructure fees → token
- DA: DA fees → token
- AI/compute: real revenue vs emissions
- SoV, Enterprise L1, Payments: dimension excluded (see Section 5)

## 7. Consistency Fixes Enabled by This Taxonomy
- BTC and CANTON are now consistent: both have `value_capture` excluded. BTC's fee signal lives in `supply_and_security` as hashrate / security budget. CANTON's fee signal lives in `supply_and_tokenomics` as burn/mint ratio.
- KAS follows BTC (`monetary-store-of-value`, fee_model `miner`).
- XRP / XLM / HBAR become `payments-rail` with fee_model `minimal`; revenue is not scored and they are no longer penalised on a dimension that does not describe them.
- LINK gets `oracle-data` with adoption_activity driven by TVS and integrations, not a Rev/TVL figure.
- TIA stays `data-availability-modular` (or moves to `smart-contract-platform` if re-classified as general-purpose L1 — decide per asset).
- EIGEN becomes `shared-security`.

## 8. Handling of Hybrid Cases
- ETH: `smart-contract-platform`, fee_model `burn` (base-fee burn is dominant signal), with supplementary staking-yield read under value_capture.
- SOL: `smart-contract-platform`, fee_model `staking_share` with 50% burn noted.
- HYPE: `defi-protocol` with fee_model `revenue` (or `buyback_and_burn`).
- TAO: `ai-compute-depin`, fee_model `revenue` — but revenue is small vs emissions, so value_capture score will be low; this is factually correct and should not be hidden.

## 9. Implementation Outline (for follow-up work)
Not executed yet — awaiting approval.
1. Extend `pipeline/assets.yaml` schema: add `asset_category` (one of Section 4) and richer `fee_model` (Section 5). Keep `asset_type` during transition for backward compatibility.
2. Rewrite `pipeline/config.yaml` weights section: one profile per category without `wyckoff`; each profile enumerates only weighted dimensions.
3. Generalise `pipeline/scoring/composite.py`: support variable dimension sets per category (already mostly works via missing-dim renormalisation; add guard for unknown dimension keys).
4. Add fetchers / scorers for new metrics:
   - hashrate + security budget (SoV)
   - adoption_activity scorer that pulls category-specific inputs (TVS for oracle, burn/mint ratio for Canton, AVS count for EIGEN, etc.)
   - Rename `revenue` scoring path to `value_capture` and dispatch by fee_model.
5. Update `pipeline/run.py` narrative builder to describe the per-category dimension set and explain excluded dimensions (no more "⚠️ ESTIMATED" text for assets whose value_capture is excluded by design).
6. Add a post-score Wyckoff filter step that applies phase-based downgrades before final recommendations.
7. Update `pipeline/discovery/prompt.md` and `.agents/skills/discovery/instructions.md` with the new taxonomy, fee-model options, and category assignment guidance.
8. Document the change in `.docs/decisions.md` once implemented.

## 10. Open Questions
- Should `adoption_activity` be optional (i.e. excluded for categories where data is not available) or mandatory? Proposal: mandatory but scoreable from LLM research when API data missing, flagged as estimated (reuse existing pattern).
- Should we split `monetary-store-of-value` into `pow-store-of-value` (BTC, KAS, LTC) and `tokenized-sound-money` (e.g. tokenized gold) later? Defer.
- Should QNT remain `enterprise-settlement` or move to `oracle-data` given its interoperability framing? Decide per asset review.
- Expected drift in composite scores after migration: BTC, KAS, CANTON, XRP, XLM, HBAR will all move because the revenue dimension is no longer pulling them down with punitive / inapplicable numbers. Plan a one-time backtest snapshot before/after.

## 11. References
- Messari Classification System — https://docs.messari.io/glossary/classification-system
- Token Terminal, "Who earns fees in crypto?" (2023) and "Rainmakers of the Crypto Market" (2024)
- VanEck / MarketVector Token Terminal interview with Matthew Sigel (2024)
- Onramp Bitcoin, "Security budget" (2024)
- CoinShares Q4 2024 Mining Report — Bitcoin hashrate / hash price model
- SmartContent, "Defining Total Value Secured (TVS) in Decentralized Oracle Networks" (2021); Chainlink TVS reports 2024–2026
- Canton Network Series Parts 2 & 4 (The Tie); Canton Foundation CIP-0100 / CIP-0104 docs
- EigenLayer ELIP-12 proposal; EigenLayer Eigen Economy dashboard; Hindenrank EigenLayer analysis (2026)
