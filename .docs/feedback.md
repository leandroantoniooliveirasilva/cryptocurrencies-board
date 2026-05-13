Leandro, this is a solid request. Let me systematically fact-check the key claims across your framework's scoring data against current information. I'll work through the major assets and dimensions.Good data to work with. Here's my fact-check assessment, organized by what's materially wrong, what's stale, and what holds up.

---

**MATERIALLY WRONG — update these in the pipeline**

**Strategy (MicroStrategy) BTC holdings**: Your JSON says "~640K BTC." As of April 27, 2026, Strategy holds 818,334 BTC — a 28% undercount. This is the single largest factual error in the dataset and directly affects the BTC institutional rationale.

**IBIT AUM**: Your JSON says "~$50B AUM." IBIT's total AUM is approximately $66.9B as of early May, and IBIT ended Q1 with approximately $55 billion in assets, holding more than 800,000 Bitcoin. The $50B figure is ~25% stale. The ~805K BTC count is roughly correct.

**SOL ETF cumulative inflows**: Your JSON says "$1.45B in cumulative inflows since October 2025 launch." Cumulative Solana ETF inflows have reached just over $1.06 billion, with total assets exceeding $987 million. The $1.45B claim overstates reality by ~37%.

**ETH spot ETF AUM**: Your JSON says "spot ETFs exceeding $16B AUM." The spot ETH ETFs hold $14.14 billion in AUM as of early May 2026, down from a peak of $18-19B. The "$16B+" claim was likely accurate at some point but is now stale — ETH ETFs have been bleeding.

---

**STALE BUT DIRECTIONALLY CORRECT**

**BTC cumulative ETF inflows**: JSON says "$56B+." Cumulative net inflows since launch stand at $58.72 billion, still shy of the record $61.19 billion peak in October. Minor understatement.

**Stablecoin market cap**: JSON says $310.2B. CoinGecko shows stablecoins' market cap at $319 billion. Minor.

**BTC dominance**: JSON says 58.2%. Current readings range from 58.3% (CoinGecko) to 60.2% (Newhedge, which may use a different methodology). Close enough.

---

**CONFIRMED SOUND — these all check out**

**SEC/CFTC commodity classification (March 17, 2026)**: The SEC and CFTC jointly released interpretive guidance clarifying when crypto transactions are subject to securities laws, explicitly identifying BTC, ETH, SOL, ADA, XRP, AVAX, LINK, HBAR, XLM, and others as digital commodities. Your regulatory scores for these assets correctly reflect this landmark event.

**Canton TCAN ETF**: 21Shares launched the Canton Network ETF (TCAN) on Nasdaq on May 7, 2026 — confirmed as the first U.S. ETF for Canton. Goldman Sachs, DTCC, Deutsche Bank participation confirmed. The $350B+ daily repo volume figure is supported.

**HYPE ETF filings**: All four filings confirmed — Bitwise filed first with ticker BHYP, Grayscale filed for GHYP in March 2026, VanEck plans VHYP, and 21Shares advanced its filing under ticker THYP.

**Morpho/Apollo deal**: Apollo agreed to acquire up to 90 million MORPHO tokens over 48 months, with a potential $112.5 million commitment at current prices, positioning Apollo as a major token holder. Exactly as stated.

**ETH staking ETFs**: BlackRock launched ETHB, the iShares Staked Ethereum Trust ETF, on March 12, 2026 with $107 million in seed capital. ETHA at ~$6.5B AUM confirmed.

**ETH ~30% staked**: Approximately 35.8 million ETH (roughly 30% of total circulating supply) is staked as of early 2026. Your rationale is accurate.

---

**STRUCTURAL CONCERNS worth flagging**

**Supply dimension — systematic data gap**: Nine assets carry a neutral 50/100 because "Supply APIs unavailable, fallback neutral score applied." That's CANTON, LINK, HYPE, HBAR, XLM, QNT, AAVE, TIA, EIGEN, TAO, ENA, PENDLE, SUI. This means ~60% of your watchlist is effectively unscored on supply. For a framework that weights supply at 15-20%, you're flying partially blind on more than half the assets. The scores themselves acknowledge this, but the composite numbers absorb the neutral fallback without any visible penalty — a 50/100 on supply flatters assets that might genuinely score 30 or 70 if data existed.

**Wyckoff heuristic classifier limitations**: Several assets simultaneously sit at "Distribution Phase A" (LINK, SOL, ETH, HYPE, MORPHO, ONDO, JUP, SUI, TIA, LDO, EIGEN, ENA, PENDLE, KAS). When your classifier labels nearly everything with recent price appreciation as "early distribution after buying climax," it may be overweighting mean-reversion in the heuristic. For SOL specifically, the Wyckoff signal flipped from "Accumulation Phase D → Distribution Phase A" in a single snapshot — that's a two-phase jump that suggests the heuristic is reading short-term price positioning (100% in 90d range) rather than structural volume-confirmed distribution. Worth cross-referencing with actual volume analysis before trusting the distribution labels.

**LINK composite drop**: LINK went from 81 last week to 70 this week (delta -11), yet its action remains "await." The 7-day composite delta of -7 and 30-day delta of -6 are both notable degradations. The drop appears driven by a sharp value_capture score (54) — daily revenue of only ~$9K/year is indeed thin for an asset with $100B+ TVS. This isn't wrong per se, but worth asking whether the oracle/infra revenue model is fundamentally mismatched with the DeFi-protocol value_capture scoring template.

**CANTON note_detailed inconsistency**: The detailed note says "final_action: Hold" with "downgrades: levels_applied=1, macro_levels=1" (GLI contracting), but the top-level `action` field says "hold" without macro downgrade. Meanwhile, BTC's top-level `action` says "accumulate" but its detailed note says "final_action: Hold" after 1 downgrade level from GLI contracting. This looks like the `note_detailed` field may be from a different pipeline run than the `action` field. If the pipeline generates these asynchronously, there's a desync risk you should audit.

---

**NET ASSESSMENT**

The framework logic is sound. The scoring architecture, weight profiles by asset category, decision traces, and action-state machinery all reflect the disciplined, rejection-over-speculation philosophy you've built. The regulatory dimension is particularly well-calibrated — the March 2026 SEC/CFTC classification is correctly captured across assets.

The main remediation priorities are: fix the Strategy BTC count and IBIT AUM (both substantially wrong), correct the SOL ETF inflow overstatement, add a staleness flag for ETH ETF AUM, and investigate the supply data gap — either find alternative APIs or apply a visible discount rather than a neutral default that silently inflates composites.