# Monthly Discovery Report — May 2026 (Run #3: DeFi & Infrastructure Focus)

> **Run Focus**: DeFi revenue metrics, TVL changes, protocol upgrades, infrastructure maturation.
> All scoring uses `weights_by_category` from `config.yaml`. Wyckoff is a global filter only — not a composite dimension.

---

## Executive Summary

May 2026 sees DeFi entering a maturation phase: the fee-switch era is arriving (UNI live, MORPHO/JUP pending), RWA integration has scaled beyond tokenized treasuries into equities and institutional lending (ONDO $1B+ tokenized stocks, MORPHO $7.2B TVL), and Bitcoin-native DeFi is emerging as a new asset category via Babylon. The most significant omission from the current watchlist is **TON**, which now has Telegram (300M users) as its largest validator and a CoinShares ETP — a unique distribution moat. New infrastructure plays **Berachain** ($3.26B TVL at L1 launch) and **Babylon** ($4-5B BTC staked natively) warrant watchlist entry. On the downside, **LDO** is structurally losing market share as staking yields compress, and **ADA**'s $1.1B TVL spike rapidly collapsed to $132M — confirming thin ecosystem depth.

---

## Omission Audit

| Asset | In Watchlist? | Recommendation | Rationale |
|-------|---------------|----------------|-----------|
| BNB | No | Do not add | Regulatory cloud from DOJ settlement; ecosystem fees partially accrue to token via BEP-95 burns but value accrual to holder is indirect; centralization risk with Binance as single point |
| DOT | No | Add (Observation, ~59) | Hard supply cap (2.1B DOT) passed via Referendum 1710 — eliminates chronic 10% perpetual inflation; 21Shares ETF launched on Nasdaq; #6 by developer activity. Weak TVL ($1.2B) limits composite score |
| ATOM | No | Do not add | IBC ecosystem healthy but ATOM token captures minimal fees from IBC volume; staking inflation ~14% with no offsetting burns; ATOM 2.0 tokenomics remain contested; classic infrastructure/token value accrual disconnect |
| LTC | No | Do not add | No DeFi or smart contract ecosystem; pure POW payments narrative; LitVM rollup too early; no value accrual beyond speculative ETF thesis |
| TON | No | **Add (Runner-up, ~68)** | Telegram became largest validator May 7 2026; CoinShares ETP live on SIX Swiss Exchange; $1.2B TVL, $750M+ stablecoin liquidity; 300M Telegram users = unmatched distribution moat; Durov legal overhang cleared |
| INJ | No | Do not add | Market cap contracted ~80% from ATH; ~$19M TVL; buyback-and-burn mechanism exists but insufficient scale to justify watchlist entry at this time |
| OP | No | Do not add | OP token is governance-only; sequencer revenue flows to OP treasury/RetroPGF, not token holders; until fee accrual reform passes, value accrual is weak vs. ARB or ETH |
| ARB | No | Do not add | $13.8B TVL (largest L2) but ARB token is governance-only; sequencer revenue to DAO treasury; $131M net capital outflow signal; fee switch not enacted. Monitor governance |
| NEAR | No | Do not add | TVL ~$100M, sharply down; revenue buyback mechanism newly activated but unproven at scale; revisit in 60 days if app revenue (+190% YoY) translates to TVL recovery |

---

## New Discoveries

### TON — Toncoin
- **Asset Category**: `payments-rail`
- **Recommended Tier**: Runner-up
- **Scores** (payments-rail weights: inst 0.35, adoption 0.20, regulatory 0.30, supply 0.15):
  - Institutional: **65** — CoinShares ETP on SIX Swiss Exchange (first TON-specific staking ETP); TON Foundation disclosed $400M+ VC purchases; institutional validator concentration growing
  - Adoption / Activity: **78** — $1.2B DeFi TVL; $750M+ stablecoin liquidity; USDT on TON crossed $500M; Telegram became largest validator May 7 2026; real payment flows through Telegram mini-apps with 300M MAU
  - Regulatory: **70** — Durov/Telegram legal settlement cleared 2025; TON operates as independent foundation; no SEC enforcement actions; EU/MiCA compatible model; cleaner than most L1s
  - Supply: **58** — Telegram holds significant concentrated supply; ongoing validator incentive emissions; token distribution skews toward insiders; partially offset by validator lock-up requirements
- **Wyckoff** (filter only): Range consolidation — $2-3 zone; accumulation pattern post-2025 correction
- **Value Accrual**: **Moderate** — transaction fees burned; staking yield from validator participation; Telegram commerce integration creates organic demand flywheel. Weaker than DeFi protocols on fee-per-holder basis, but distribution moat is unique
- **Composite**: **68.0** *(65×0.35 + 78×0.20 + 70×0.30 + 58×0.15 = 22.75 + 15.60 + 21.00 + 8.70)*
- **Thesis**: TON's moat is Telegram distribution — no other L1 has 300M users and a validator with direct product integration. The Durov settlement removes the key overhang. CoinShares ETP confirms institutional demand. DeFi TVL at $1.2B is real economic activity, not liquidity mining. If even 5% of Telegram users engage with TON payments, this dwarfs any other L1's organic adoption.
- **CoinGecko ID**: `the-open-network`
- **DefiLlama Slug**: `ton`

---

### BERA — Berachain
- **Asset Category**: `smart-contract-platform`
- **Recommended Tier**: Runner-up
- **Scores** (smart-contract-platform weights: inst 0.25, adoption 0.20, value_capture 0.20, supply 0.20, regulatory 0.15):
  - Institutional: **65** — $142M total VC funding (Polychain + Framework Ventures Series A/B); Bitcoin Suisse custody offering; institutional-grade validators; VC concentration is also a risk
  - Adoption / Activity: **80** — $3.26B TVL within weeks of Feb 6 2026 mainnet; surpassed Arbitrum and Base TVL at launch; became #6 DeFi blockchain globally; fastest L1 TVL ramp since Solana 2021
  - Value Capture: **68** — BERA gas token + BGT governance emission; Proof-of-Liquidity requires validators to direct liquidity to approved vaults, creating structural DeFi demand for block rewards; complex but genuinely novel alignment
  - Supply: **58** — new L1; BGT is non-transferable (only earned by LP); BERA distribution schedule partially opaque; PoL creates circular tokenomics that may inflate or compress unpredictably
  - Regulatory: **52** — brand-new L1; no regulatory guidance; no commodity classification; high jurisdictional uncertainty; not listed on all major regulated exchanges yet
- **Wyckoff** (filter only): Markup (launching phase) — caution on timing; high volatility post-launch
- **Value Accrual**: **Strong** — PoL consensus structurally requires validators to provide DeFi liquidity in exchange for BGT emissions; gas fees in BERA create direct demand; the circularity of PoL is both the thesis and the risk
- **Composite**: **65.3** *(65×0.25 + 80×0.20 + 68×0.20 + 58×0.20 + 52×0.15 = 16.25 + 16.00 + 13.60 + 11.60 + 7.80)*
- **Thesis**: Berachain's Proof-of-Liquidity is the most structurally novel consensus innovation in L1 design since Ethereum's PoS — it hard-codes DeFi liquidity provision into validator economics. $3.26B TVL at launch (without incentive mining) demonstrates genuine market conviction. Polychain/Framework backing provides institutional credibility. High risk given early stage, but potential to be the DeFi-native L1 that Ethereum aspires to be.
- **CoinGecko ID**: `berachain`
- **DefiLlama Slug**: `berachain`

---

### BABY — Babylon Protocol
- **Asset Category**: `shared-security`
- **Recommended Tier**: Runner-up
- **Scores** (shared-security weights: adoption 0.25, value_capture 0.25, inst 0.20, regulatory 0.15, supply 0.15):
  - Adoption / Activity: **82** — $4.1–5.6B BTC natively staked (56,000+ BTC); no bridging, no wrapping — stakers retain full self-custody; dominant Bitcoin DeFi primitive with no credible competitor at scale; TVL dwarfs most established DeFi protocols
  - Value Capture: **72** — BABY token stakers earn yield from PoS chain security fees paid by consumer chains; direct revenue-to-holder model; chains pay for Bitcoin security validation with real protocol revenue; sustainable fee structure vs. inflationary rewards
  - Institutional: **65** — a16z and Polychain lead investment; strong VC pedigree; appeals to BTC-native institutions who refuse bridging risk; taps $1.8T BTC market with institutional-grade self-custody
  - Regulatory: **60** — inherits Bitcoin's regulatory clarity partially; BABY token itself is newer and lacks classification; multi-chain PoS validation adds complexity; overall relatively clean vs. typical DeFi protocols
  - Supply: **62** — BABY token early stage; emission schedule tied to security services provided; VC unlock schedules standard; BTC collateral doesn't require BABY so TVL and token price partially decouple
- **Wyckoff** (filter only): Accumulation Phase A/B — new listing, establishing price range
- **Value Accrual**: **Strong** — clearest revenue-to-holder model in the Bitcoin DeFi category; PoS chains pay security premiums that flow to BABY stakers; demand scales directly with consumer chain adoption
- **Composite**: **69.8** *(82×0.25 + 72×0.25 + 65×0.20 + 60×0.15 + 62×0.15 = 20.50 + 18.00 + 13.00 + 9.00 + 9.30)*
- **Thesis**: Babylon unlocks the first credible yield for Bitcoin HODLers who refuse to bridge — a market worth $1.8T. The no-bridge, no-wrap model eliminates the primary security risk of Bitcoin DeFi. $4-5B TVL demonstrates this is not theoretical. As PoS chains face validator centralization pressure, Bitcoin economic security becomes a premium product. a16z/Polychain conviction strengthens the institutional signal.
- **CoinGecko ID**: `babylon`
- **DefiLlama Slug**: `babylon`

---

### ATH — Aethir
- **Asset Category**: `ai-compute-depin`
- **Recommended Tier**: Runner-up
- **Scores** (ai-compute-depin weights: adoption 0.25, value_capture 0.20, inst 0.20, supply 0.20, regulatory 0.15):
  - Adoption / Activity: **85** — $156M+ ARR (annualized run rate, early 2026); $127.8M actual 2025 revenue; 80%+ H100 GPU utilization; enterprise overflow clients from AWS/Azure; outpaces Filecoin (135×), Render (455×), Bittensor (14×) on revenue/market cap ratio
  - Value Capture: **68** — ATH staked by node operators; protocol revenue distributed to stakers; fee burning component; real USD revenue from enterprise clients (not token-subsidized); clearest revenue→token model in DePIN
  - Institutional: **60** — enterprise clients (AI inference, gaming studios) but limited fund/custody institutional signal; no ETF filings; enterprise adoption is the institutional signal here vs. fund holdings
  - Supply: **52** — newer token; node operator staking locks supply; v3 upgrade and chain migration planned which introduce execution risk; emission schedule moderately inflationary; token concentration risk in early nodes
  - Regulatory: **62** — GPU compute is regulated as commodity business, not financial asset; clean business model; no DeFi complexity; global enterprise clients create natural regulatory anchoring
- **Wyckoff** (filter only): Markup with consolidation — strong 2025 revenue narrative priced in; pullback creates entry opportunity
- **Value Accrual**: **Strong** — enterprise cash revenue (not token issuance) flows to stakers; one of the very few DePIN protocols with real P&L, not ponzinomics
- **Composite**: **66.6** *(85×0.25 + 68×0.20 + 60×0.20 + 52×0.20 + 62×0.15 = 21.25 + 13.60 + 12.00 + 10.40 + 9.30)*
- **Thesis**: Aethir is the only DePIN protocol generating enterprise-grade recurring revenue at scale — $156M ARR with 80%+ GPU utilization is not speculative. The AI inference market is structurally undersupplied (H100 scarcity persists through 2026), and Aethir captures the enterprise overflow market that AWS/Azure cannot serve at cost. Revenue-to-staker model is clearly defined. Compare to TAO ($43M Q1 revenue across 128 subnets, market-cap premium) — ATH delivers more revenue with more direct token value accrual.
- **CoinGecko ID**: `aethir`
- **DefiLlama Slug**: `aethir`

---

### KMNO — Kamino Finance
- **Asset Category**: `defi-protocol`
- **Recommended Tier**: Observation
- **Scores** (defi-protocol weights: value_capture 0.30, adoption 0.15, inst 0.20, regulatory 0.15, supply 0.20):
  - Value Capture: **62** — borrowing fees generated at $3.2B scale; fee distribution to KMNO holders developing; Anchorage mirror-token model generates institutional borrow fees; fee switch terms not finalized
  - Adoption / Activity: **85** — $3.2B TVL (Solana's #2 protocol behind Jupiter); $600M PRIME institutional market; RWA market crossed $1B; Anchorage Digital integration (March 2026) enables institutional borrow-against-custody flow; top-6 DeFi lending globally
  - Institutional: **62** — Anchorage Digital partnership (premier institutional custodian); institutional lending market pipeline; hedge fund/family office borrow flows; limited fund holdings or ETF angle
  - Regulatory: **62** — Solana ecosystem, post-ETF regulatory clarity benefit; lending protocol (not derivatives); no enforcement actions; PRIME market compliance wrappers
  - Supply: **58** — KMNO token relatively new; incentive emissions ongoing; fee switch timing uncertain; supply schedule transparent but modest lockup duration
- **Wyckoff** (filter only): Accumulation range — TVL growing while token consolidates
- **Value Accrual**: **Moderate-Strong** — real borrowing revenue at Solana scale; institutional borrow fees via Anchorage are high-margin; fee switch activation is the clear catalyst; until then, value accrual path is speculative
- **Composite**: **64.6** *(62×0.30 + 85×0.15 + 62×0.20 + 62×0.15 + 58×0.20 = 18.60 + 12.75 + 12.40 + 9.30 + 11.60)*
- **Thesis**: Kamino is the dominant Solana lending protocol with $3.2B TVL and the only DeFi lender with a direct institutional pipeline via Anchorage (institutions borrow against custodied assets using mirror tokens). As Solana's on-chain economy grows post-ETF ($1.1T Q1 activity), Kamino is the primary beneficiary. The fee switch is the missing piece — once activated, KMNO becomes productive. Key risk: Solana protocol concentration risk.
- **CoinGecko ID**: `kamino`
- **DefiLlama Slug**: `kamino`

---

### DOT — Polkadot
- **Asset Category**: `smart-contract-platform`
- **Recommended Tier**: Observation
- **Scores** (smart-contract-platform weights: inst 0.25, adoption 0.20, value_capture 0.20, supply 0.20, regulatory 0.15):
  - Institutional: **60** — 21Shares TDOT spot ETF launched Nasdaq March 2026 (modest $545K first-day inflows); limited major fund holdings; #6 globally by developer activity (98 active contributors)
  - Adoption / Activity: **55** — ~$1.2B ecosystem TVL; Polkadot parachains varied; IBC-competing relay chain design limits DeFi composability; ecosystem activity genuine but not dominant
  - Value Capture: **55** — DOT staking yields; coretime sales (parachain slot replacement); governance over treasury; fee accrual indirect vs. DeFi protocols
  - Supply: **65** — **Referendum 1710 passed**: hard cap of 2.1B DOT imposed, eliminating prior ~10% perpetual inflation; this is the single most important DOT fundamental development in 2 years; dramatically reduces dilution sell pressure
  - Regulatory: **60** — European regulatory presence (Web3 Foundation Swiss); no SEC enforcement; MiCA-compatible pathway; no ETF pressure from US regulators
- **Wyckoff** (filter only): Accumulation Phase B — post-inflation-fix revaluation underway but market hasn't priced it fully
- **Value Accrual**: **Moderate** — staking rewards + coretime fees; supply cap improves holder value retention significantly; not a high-yield DeFi protocol but improving
- **Composite**: **59.0** *(60×0.25 + 55×0.20 + 55×0.20 + 65×0.20 + 60×0.15 = 15.00 + 11.00 + 11.00 + 13.00 + 9.00)*
- **Thesis**: The 2.1B DOT hard supply cap is a structural inflection — the same class of change that Ethereum's EIP-1559 was for ETH inflation. Combined with the 21Shares ETF and genuine developer activity (#6 globally), DOT has a viable recovery thesis for 2026. TVL remains thin and ecosystem lacks Ethereum/Solana DeFi depth, but at observation tier the bar is met for monitoring.
- **CoinGecko ID**: `polkadot`
- **DefiLlama Slug**: `polkadot`

---

### EUL — Euler v2
- **Asset Category**: `defi-protocol`
- **Recommended Tier**: Observation
- **Scores** (defi-protocol weights: value_capture 0.30, adoption 0.15, inst 0.20, regulatory 0.15, supply 0.20):
  - Value Capture: **62** — EUL fee distribution to stakers; permissionless vault model enables long-tail lending markets with premium fees; fee structure clearly defined post-v2 rebuild
  - Adoption / Activity: **58** — ~$890M TVL (April 2026, down from ~$2B peak); handled April 2026 Kelp DAO contagion without losses; 38× TVL growth in 3 months (The Defiant); 90% net revenue growth QoQ
  - Institutional: **48** — limited; post-hack reputation still rebuilding; no major fund holding signal; Pendle/Morpho-level institutional presence not yet achieved
  - Regulatory: **58** — standard permissionless DeFi lending; no enforcement actions; permissionless vault design raises novel jurisdictional questions
  - Supply: **55** — EUL token with unclear inflation schedule post-rebuild; distribution still establishing
- **Wyckoff** (filter only): Accumulation Phase B — TVL rebuilding, price consolidating
- **Value Accrual**: **Moderate** — fee distribution is real; permissionless vault architecture creates premium-rate long-tail markets; execution risk post-hack remains
- **Composite**: **56.6** *(62×0.30 + 58×0.15 + 48×0.20 + 58×0.15 + 55×0.20 = 18.60 + 8.70 + 9.60 + 8.70 + 11.00)*
- **Thesis**: Euler v2's permissionless vault model is genuinely differentiated — it enables custom risk vaults that Aave/Morpho cannot match for long-tail asset lending. The 90% net revenue growth QoQ and resilience during the Kelp DAO contagion event demonstrate improved risk management vs. v1. Entry at observation tier pending institutional signal and TVL recovery to >$1.5B.
- **CoinGecko ID**: `euler`
- **DefiLlama Slug**: `euler-finance`

---

## Existing Asset Reviews

### BTC — Status: KEEP
- **Current Tier**: Leader (anchor)
- **Recommendation**: KEEP — unchanged thesis; `wyckoff_override: Phase B→C` remains valid
- **Key Changes**: Spot Bitcoin ETFs surpassed $100B AUM in Q1 2026; MicroStrategy/Strategy has accumulated 550K+ BTC; Fed policy uncertainty continues to support BTC as macro hedge. No fundamental changes.

### KAS — Status: KEEP
- **Current Tier**: Observation
- **Recommendation**: KEEP — POW store-of-value narrative stable; no material changes in past 60 days

### ETH — Status: KEEP
- **Current Tier**: Runner-up / Leader threshold
- **Recommendation**: KEEP — BlackRock launched staking ETH ETF (April 2026); ETH staking ETFs mark institutional deepening; Aave V4 hub-and-spoke launches on Ethereum mainnet (March 2026); Pectra upgrade delivered; EIP-4844 blobs continue scaling. No existential threats.
- **Key Changes**: Staking ETFs (BlackRock) represent the largest new institutional unlock since spot ETF approval. ETH regulatory commodity classification confirmed. No demotion trigger.

### SOL — Status: KEEP
- **Current Tier**: Leader
- **Recommendation**: KEEP — spot SOL ETFs active since October 2025; $1.1T on-chain Q1 2026 (+6,500% QoQ); Alpenglow consensus upgrade (Q3 2026) targets ~150ms finality; ecosystem dominance in consumer DeFi, DEX volume, meme coins
- **Key Changes**: ETF approval was the catalyst; Alpenglow is the next technical milestone. No demotion trigger.

### AVAX — Status: KEEP
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — commodity classification by SEC/CFTC (March 17 2026) is a material regulatory catalyst; enterprise subnet pipeline maturing (T. Rowe Price, WisdomTree, Wellington on Spruce testnet); Toyota, SK Group production deployments
- **Key Changes**: Commodity classification matches BTC/ETH status — significant legitimacy milestone. Evergreen Subnet enterprise pipeline is real. DeFi TVL still lags Ethereum/Solana but institutional angle differentiates.

### SUI — Status: KEEP
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — spot SUI ETF launched February 2026; 219% YoY developer growth; $111B stablecoin transfers in January 2026; ~$1B+ DeFi TVL with 19.9% QoQ growth
- **Key Changes**: ETF provides institutional on-ramp; stablecoin velocity suggests real economic activity; developer growth rate is highest in peer L1 set.

### ADA — Status: FLAG FOR DEMOTION
- **Current Tier**: Observation
- **Recommendation**: **DEMOTE toward removal** — TVL spiked to $1.1B in March 2026 then collapsed to $132M; spike was speculative (23% in 12 days), not organic; DeFi ecosystem remains structurally thin relative to $10B+ market cap; USDCx stablecoin integration announced but unproven; 672 active developers is real but output remains thin in DeFi
- **Key Changes**: TVL collapse from $1.1B to $132M is a warning signal. If TVL does not recover to $500M+ organically within 2 months, recommend removal.

### POL — Status: KEEP (monitor)
- **Current Tier**: Observation
- **Recommendation**: KEEP for now — Polygon CDK L2s growing; AggLayer cross-chain aggregation delivering; enterprise deployments ongoing. Fee accrual to POL token remains weak vs. earlier Matic model. Watch AggLayer adoption milestones.

### LINK — Status: KEEP (upgrade conviction)
- **Current Tier**: Leader
- **Recommendation**: KEEP with upgraded conviction — CCIP volume +1,972% YoY ($7.77B annualized transfers); LayerZero exploit (April 2026) accelerated CCIP migration with Solv Protocol ($700M) and Re ($160M) switching; TVS $100B+ all-time high; Lido CCIP adoption for wstETH cross-chain
- **Key Changes**: Competitor exploit is a structural tailwind. CCIP is becoming the de facto institutional cross-chain standard. Link staking v0.2 improving token accrual. No demotion trigger — if anything, LINK is underweighted.

### HYPE — Status: KEEP
- **Current Tier**: Leader
- **Recommendation**: KEEP — $607M annualized fee run rate; $50.95M distributed on May 10 alone; $9.3B open interest; top-10 market cap asset. Security incidents (JELLY liquidation, vault exploits) are real operational risks but TVL rebuilt
- **Key Changes**: Multiple security incidents reveal operational risk in aggressive DeFi approach. Revenue generation remains exceptional — $800M+ all-time fees. At $10.6B market cap, institutional recognition is priced in. Monitor vault security discipline.

### MORPHO — Status: KEEP (upgrade conviction)
- **Current Tier**: Runner-up / Leader threshold
- **Recommendation**: KEEP with high conviction — $7.2B TVL (Solana's Aave equivalent), second only to Aave in lending; B2B infrastructure model is unique (Coinbase, Apollo, Bitwise, Société Générale building on Morpho); $174.6M annualized fees
- **Key Changes**: B2B distribution moat is the clearest in DeFi lending. **Critical risk**: zero fees distributed to MORPHO holders to date — "empty wallet by design." Fee switch timing is the most important catalyst. Score reflects strong adoption but weak current value accrual to token.

### AAVE — Status: KEEP
- **Current Tier**: Leader
- **Recommendation**: KEEP — $57.3B peak TVL (January 2026); V4 live on Ethereum mainnet (March 2026) with hub-and-spoke architecture; Horizon institutional RWA product with $550M net deposits; 29% share of total DeFi TVL; Chainlink wstETH integration
- **Key Changes**: V4 launch and Horizon are execution milestones delivered. Staking ETH integration adds demand vector. Position as DeFi lending's dominant incumbent is unquestioned.

### ONDO — Status: KEEP (strong)
- **Current Tier**: Leader
- **Recommendation**: KEEP — $3.53B TVL; Ondo Global Markets exceeded $1B in tokenized stocks/ETFs; Fidelity OUSG integration, PayPal $25M facility, Mastercard Multi-Token Network, JPMorgan/Kinexys, Franklin Templeton in Q1 2026; 60%+ tokenized equities market share; $18B+ trading volume
- **Key Changes**: Q1 2026 established ONDO as the institutional tokenized securities layer of record. Partnership density is unprecedented for a DeFi-native protocol.

### PENDLE — Status: KEEP (caution flag)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP with close monitoring — TVL compressed from $13.1B (September 2025) to $1.499B; 7-day fee generation down 71% while TVL up 9% (capital trapped, not trading); Boros/V3 cross-chain markets expected Q2 2026 is the recovery thesis; sPENDLE upgrade routes 80% of revenue to buybacks; Grayscale Q2 2026 watchlist inclusion is a structural positive signal
- **Key Changes**: TVL collapse is material. If Boros/V3 launch does not revive fee generation to $50M+ annualized within 60 days, recommend demotion to observation.

### JUP — Status: KEEP (monitor)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — 95% Solana DEX aggregator market share; $2-4B daily trading volume; Solana ETF ecosystem tailwind
- **Key Changes**: Revenue to JUP token holders remains limited — most flows to LPs. $0.24 price reflects weak token accrual relative to protocol dominance. Fee switch is the key unlock — monitor governance.

### ENA — Status: KEEP (monitor)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — USDe supply contracted from $14B to $5.92B (leverage unwind); iUSDe institutional product launched (hedge funds, family offices onboarded); fee switch activated with revenues to sENA stakers; Grayscale ENA included at 13.59% in DeFi Fund
- **Key Changes**: Fee switch activation converts ENA from governance to productive asset. Grayscale inclusion is a clear institutional signal. Reserve fund at 1.18% of TVL is narrow — negative funding rate scenario is systemic risk to monitor.

### QNT — Status: KEEP (monitor)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — SWIFT ISO 20022 integration completed April 4 2026; Great British Tokenized Deposit (GBTD) with HSBC, Barclays, Lloyds targeting mid-2026 production; DTCC-adjacent positioning; staking mechanism planned for 2026
- **Key Changes**: GBTD production launch (mid-2026) is the key catalyst. If staking mechanism doesn't launch by Q3 2026, token value accrual remains a concern. Illiquid market cap raises execution risk.

### XLM — Status: KEEP
- **Current Tier**: Observation
- **Recommendation**: KEEP — Stellar/USDC settlement infrastructure; payments-rail thesis intact; limited changes in past 60 days

### XRP — Status: KEEP
- **Current Tier**: Leader (payments-rail)
- **Recommendation**: KEEP — SEC lawsuit resolved; XRP ETF pipeline progressing; ODL volume growing; Ripple USD (RLUSD) stablecoin expanding; XRPL DeFi ecosystem developing
- **Key Changes**: Post-litigation clarity continues to attract institutional interest. No demotion trigger.

### HBAR — Status: KEEP (monitor)
- **Current Tier**: Observation
- **Recommendation**: KEEP — enterprise Hedera deployments ongoing; HBAR Foundation institutional partnerships; limited DeFi TVL
- **Key Changes**: No material changes.

### TAO — Status: KEEP (upgrade conviction)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP with upgraded conviction — Grayscale private placements reopened (May 9 2026); Bitwise and Grayscale both filed spot TAO ETF applications (decision expected August 2026); $43M AI revenue Q1 2026; 128 subnets scaling to 256; TAO bridged to Solana via Wormhole/Jupiter
- **Key Changes**: Dual ETF filings are major institutional signals — Grayscale + Bitwise in parallel is rare and signals strong institutional demand. Q1 revenue validates the AI subnet narrative.

### TIA — Status: KEEP (strong upgrade)
- **Current Tier**: Runner-up
- **Recommendation**: KEEP with materially upgraded conviction — Matcha Upgrade (January 2026) cut annual token issuance from 5% to 0.25% (a 20× reduction in inflation); V8 upgrade imminent (Q2 2026) with single-signature cross-chain, ZK-verified messaging, 3-second blocks, 32 MiB capacity; 50% DA market share; 55× cheaper than Ethereum blobs
- **Key Changes**: Issuance cut from 5% to 0.25% is the single most impactful tokenomics change of any L1 in 2026. DA market leadership is entrenched — every major rollup framework (OP Stack, Arbitrum Orbit, Polygon CDK) supports Celestia. V8 delivery is execution validation.

### EIGEN — Status: KEEP
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — $18B+ restaked ETH; 93.9% restaking market share; slashing framework live (April 2025); EigenCompute & EigenVerify Q2 2026; Kelp DAO breach ($300M, $5.4B withdrawals) affected ecosystem but not core protocol
- **Key Changes**: Ecosystem contagion risk is demonstrated. Core TVL dominance unquestioned. EIGEN token accrual mechanism still maturing — AVS adoption drives the long-term value case.

### CANTON — Status: KEEP (strong)
- **Current Tier**: Observation (likely scoring toward runner-up)
- **Recommendation**: KEEP with upgraded conviction — DTCC announced limited production of tokenized securities July 2026, full launch October 2026 involving 50+ firms (BlackRock, JPMorgan); $1.5T+ processed monthly; $6T+ tokenized assets on network; Kresus partnership (May 2026); Protocol 3.5 with zero-downtime upgrades
- **Key Changes**: DTCC deployment is the single largest real-world enterprise blockchain deployment ever announced. $1.5T monthly processing is operational, not speculative. Canton is de facto enterprise settlement infrastructure — the scoring should reflect this.

### UNI — Status: KEEP
- **Current Tier**: Runner-up
- **Recommendation**: KEEP — UNIfication fee switch passed December 25 2025 and is live; ~$26M annualized protocol fees (early data); 100M UNI (~$600M) burned retroactively; V4 live with hook architecture
- **Key Changes**: Fee switch activation is the structural catalyst this protocol needed. Value accrual to UNI holders is finally real. Early revenue is modest but growing as activation rolls out.

### LDO — Status: FLAG FOR DEMOTION
- **Current Tier**: Runner-up
- **Recommendation**: **MONITOR for demotion** — market share dropped from 32% to ~22-28% of staked ETH; staking APR compressed from 13.06% to 2.62% (primary structural driver); institutional alternatives emerging (Coinbase staking, BitMine); stVaults (V3) target 1M ETH by institutions; NEST buyback (stETH revenue → LDO repurchase) is positive for token but doesn't address market share decline
- **Key Changes**: Yield compression is structural, not cyclical — ETH staking rewards fall as total ETH staked increases, making Lido's dominant position a paradox (success → lower yield → market share loss). If stVaults don't capture $1B+ institutional staking by Q3 2026, recommend formal demotion to observation.

---

## Proposed assets.yaml Changes

```yaml
# ADDITIONS

  - symbol: TON
    name: Toncoin
    asset_category: payments-rail
    asset_type: infrastructure
    fee_model: burn
    coingecko_id: the-open-network
    defillama_slug: ton
    wyckoff_override: null

  - symbol: BERA
    name: Berachain
    asset_category: smart-contract-platform
    asset_type: smart-contract
    coingecko_id: berachain
    defillama_slug: berachain
    wyckoff_override: null

  - symbol: BABY
    name: Babylon Protocol
    asset_category: shared-security
    asset_type: infrastructure
    fee_model: staking_share
    coingecko_id: babylon
    defillama_slug: babylon
    wyckoff_override: null

  - symbol: ATH
    name: Aethir
    asset_category: ai-compute-depin
    asset_type: infrastructure
    fee_model: staking_share
    coingecko_id: aethir
    defillama_slug: aethir
    wyckoff_override: null

  - symbol: KMNO
    name: Kamino Finance
    asset_category: defi-protocol
    asset_type: defi
    fee_model: revenue
    coingecko_id: kamino
    defillama_slug: kamino
    wyckoff_override: null

  - symbol: DOT
    name: Polkadot
    asset_category: smart-contract-platform
    asset_type: smart-contract
    coingecko_id: polkadot
    defillama_slug: polkadot
    wyckoff_override: null

  - symbol: EUL
    name: Euler v2
    asset_category: defi-protocol
    asset_type: defi
    fee_model: staking_share
    coingecko_id: euler
    defillama_slug: euler-finance
    wyckoff_override: null

# FLAGGED FOR REVIEW (no immediate removal — pending 60-day confirmation)
# ADA: TVL collapse from $1.1B to $132M — flag for removal if no organic recovery
# LDO: Market share erosion structural — flag for demotion if stVaults miss $1B target by Q3
```

---

## Watchlist Health Summary

**Before this report:**
- Total assets: 26
- Leaders: ~6 (BTC, ETH, SOL, XRP, LINK, HYPE, AAVE, ONDO)
- Runner-ups: ~10 (AVAX, SUI, MORPHO, PENDLE, ENA, JUP, TAO, TIA, EIGEN, QNT, UNI, LDO)
- Observation: ~10 (KAS, ADA, POL, HBAR, XLM, CANTON, KAS, ENA, etc.)

**Proposed Additions (7)**: TON, BERA, BABY, ATH, KMNO, DOT, EUL

**After this report (proposed):**
- Total assets: **33**
- Leaders: 6-8 (unchanged composition)
- Runner-ups: +4 (TON ~68, BABY ~70, BERA ~65, ATH ~67)
- Observation: +3 (KMNO ~65, DOT ~59, EUL ~57)
- Removals this month: **0** (ADA and LDO flagged for 60-day review)
- Additions this month: **7** (TON, BERA, BABY, ATH, KMNO, DOT, EUL)

**Key Convictions from Run #3:**
1. **BABY** (69.8) — Bitcoin DeFi leader with no credible competitor; a16z/Polychain; strongest shared-security addition since EIGEN
2. **TON** (68.0) — Telegram distribution moat is unmatched; Durov overhang cleared; institutional ETP live
3. **ATH** (66.6) — Only DePIN with enterprise-grade recurring revenue at $156M ARR; TAO comparison strongly favors ATH on Rev/MC
4. **TIA upgrade** — Issuance cut 5%→0.25% is the most important tokenomics change in L1 2026; V8 imminent
5. **LINK upgrade** — LayerZero exploit accelerated CCIP adoption; structural tailwind from competitor failure

**Watches for Next Cycle:**
- Symbiotic (no token yet — monitor TGE)
- Spark Protocol (SPK TGE expected — watch terms)
- Sky/MakerDAO (SKY) — $124M gross Q1 revenue, dominant RWA-backed stablecoin issuer; worth formal scoring

---

*Sources: CoinGecko, DefiLlama, Token Terminal, Messari, The Block, The Defiant, Chainlink Blog, Lido Blog, BlockEden, Benzinga, AInvest, CryptoTimes, Solana Compass, Fensory, KuCoin Blog, a16z crypto blog, Chainwire, PR Newswire, CoinDesk, MEXC Research, PixelPlex, Blockonomi, Stablecoin Insider, Spoted Crypto, Genfinity.*
