# Discovery Skill

Monthly watchlist discovery and vetting for the conviction scoring framework.

> **Auto-Apply Mode**: Discovery recommendations are automatically applied to `pipeline/assets.yaml`. Tiers are computed dynamically from composite scores — no manual tier assignment.

## CRITICAL: Objective Analysis Only

**Do NOT use any personal memory, preferences, or opinions from previous conversations.** This analysis must be purely objective and fact-based. Evaluate ALL assets—including those you may have previously discussed or expressed opinions about—based solely on the framework criteria below.

Your role is to be an unbiased analyst. If a project meets the criteria, it belongs on the watchlist regardless of any prior conversations or stored preferences. Follow ONLY the instructions in this document.

## Auto-Apply Rules

After discovery analysis completes:
1. **Add recommended assets** directly to `pipeline/assets.yaml` (flat list)
2. **Remove flagged assets** from `pipeline/assets.yaml`
3. **No tier assignment** — tiers are computed from composite scores at runtime:
   - Composite ≥75 → Leader
   - Composite ≥65 → Runner-up
   - Composite <65 → Observation

## When to Use

Invoke this skill when:
- Running monthly watchlist reviews
- Searching for new crypto projects to add
- Evaluating tier changes (promotions, demotions, removals)
- The user says "run discovery", "find new projects", or "review watchlist"

## Framework Philosophy

**Core Principle**: The framework identifies WHAT to buy based on fundamentals. Technical indicators (Wyckoff, RSI) determine WHEN to buy.

- Leaders go up over time due to strong fundamentals
- Buying weakness in leaders = mean reversion (they recover)
- Buying weakness in non-leaders = momentum trap (they continue down)

## Evaluation Dimensions

Score each dimension 0-100:

### 1. Institutional (ETF/Fund Adoption)
- ETF approval status or pipeline
- Major fund holdings (Grayscale, a16z, Paradigm, etc.)
- Institutional custody availability (Coinbase Custody, Fireblocks)
- Corporate treasury adoption

### 2. Revenue (Protocol Sustainability)
- Annualized protocol revenue
- Revenue-to-TVL ratio (for DeFi)
- Revenue trend (growing/stable/declining)
- Fee sustainability without token inflation

### 3. Regulatory (Jurisdictional Clarity)
- SEC/CFTC classification clarity
- Global regulatory stance (EU MiCA, etc.)
- Exchange listing breadth (major regulated exchanges)
- Compliance infrastructure

### 4. Supply (On-Chain Health)
- Exchange reserve trends (declining = bullish)
- Long-term holder percentage
- Token distribution (avoid concentrated holdings)
- Inflation/emission schedule

### 5. Wyckoff (Technical Phase)
- Current accumulation/distribution phase
- Volume confirmation
- Price structure relative to composite man theory

### 6. Value Accrual (Token Economics) — CRITICAL FILTER

**A successful project does not guarantee token appreciation.** Evaluate how protocol success translates to token value:

**Strong Value Accrual:**
- Fee burns (deflationary pressure from usage)
- Revenue sharing / staking yields (direct value to holders)
- Required token staking for network participation
- Governance rights over meaningful treasury/protocol parameters

**Weak Value Accrual (Red Flags):**
- Utility token with no fee capture mechanism
- Governance-only tokens for protocols with no treasury
- Inflationary rewards without offsetting burns
- Success accrues to equity holders, not token holders

**Key Question:** "If this protocol 10x's in usage, does the token benefit?"

## Weight Profiles by Asset Type

| Asset Type | Institutional | Revenue | Regulatory | Supply | Wyckoff |
|------------|--------------|---------|------------|--------|---------|
| store-of-value | 40% | 5% | 15% | 25% | 15% |
| smart-contract | 30% | 25% | 15% | 20% | 10% |
| defi | 25% | 35% | 20% | 15% | 5% |
| infrastructure | 35% | 10% | 25% | 20% | 10% |

## Tier Definitions (Dynamic)

Tiers are computed automatically from composite scores:

| Tier | Composite | Description |
|------|-----------|-------------|
| **Leader** | ≥75 | Core positions for accumulation |
| **Runner-up** | 65-74 | Promotion candidates |
| **Observation** | 50-64 | Watch only, no position |

**No manual tier assignment** — if an asset's composite rises above 75, it automatically becomes a Leader. If it drops below 65, it becomes Observation.

## Discovery Process

### Step 1: Read Current Watchlist
```bash
cat pipeline/assets.yaml
```

Understand the current state before making changes.

### Step 2: Omission Audit (MANDATORY)

Before searching for new projects, systematically check these sources for missing high-value assets:

#### Revenue Leaders Check
1. Open https://defillama.com/fees and check top 30 protocols by 24h fees
2. Open https://defillama.com/fees/chains and check top 20 chains by fees
3. For each protocol/chain NOT on the watchlist with >$10K daily fees, evaluate for inclusion

#### Market Cap Check
- Check top-30 market cap assets on CoinGecko not on the watchlist
- Prioritize those with clear value accrual mechanisms

#### Institutional Products Check
- Check Grayscale, 21Shares, and other ETF/ETP providers for assets with products
- Any asset with an institutional product should be evaluated

#### Category Leaders Check
- L1 platforms: Check top 10 by TVL on DefiLlama
- DeFi protocols: Check top 10 by revenue on Token Terminal
- Infrastructure: Check oracle, bridge, and data provider leaders

**Common omissions to evaluate**: ETH, BNB, ADA, DOT, MATIC, ATOM, UNI, LTC, NEAR, APT, ARB, OP, etc.

For each candidate, apply the full framework and recommend adding if it meets ANY of the inclusive criteria above — regardless of whether it's "new" or "exciting."

### Step 3: Search for New Projects Using Specific Data Sources

**IMPORTANT**: Use the specific URLs and sources below. Do NOT rely solely on general web searches.

#### Primary Data Sources (MUST CHECK)

**Revenue & Fees (Most Important Signal)**
- **DefiLlama Fees**: https://defillama.com/fees — Check "Fees by Protocol" and "Revenue by Chain"
- **DefiLlama Revenue**: https://defillama.com/fees/simple — Daily/weekly revenue rankings
- **Token Terminal**: https://tokenterminal.com/terminal/metrics/revenue — Protocol revenue rankings
- Look for protocols with >$1M annualized revenue that are NOT on the watchlist

**Institutional Adoption**
- **ETF Filings**: Search SEC EDGAR for "crypto ETF" filings (https://www.sec.gov/cgi-bin/browse-edgar)
- **Grayscale Products**: https://grayscale.com/products/ — Check their trust/fund offerings
- **21Shares Products**: https://21shares.com/products — ETF/ETP product list
- **CoinShares**: https://coinshares.com/products — Institutional products
- **Galaxy Digital Holdings**: Check their portfolio and fund disclosures
- **a16z Crypto Portfolio**: https://a16zcrypto.com/portfolio/ — Major VC holdings

**Regulatory Clarity**
- **SEC Actions**: Search recent SEC enforcement actions and settlements
- **CFTC Statements**: Check CFTC.gov for commodity classifications
- **EU MiCA Registry**: Check for MiCA-compliant tokens
- **Exchange Listings**: Check if listed on Coinbase, Kraken, Gemini (regulated US exchanges)

**Supply & On-Chain Health**
- **CoinGecko**: https://www.coingecko.com — Market cap, supply data, holder distribution
- **DefiLlama**: https://defillama.com — TVL trends, chain comparisons
- **Token Unlocks**: https://token.unlocks.app — Vesting schedules and unlock events
- **Messari**: https://messari.io — Token supply analysis (free tier)

**Market Intelligence Reports**
- **Messari Reports**: https://messari.io/research — Quarterly reports on major protocols
- **The Block Research**: https://www.theblock.co/data — Data dashboards
- **Delphi Digital**: https://delphidigital.io — Research reports (some free)
- **CoinGecko Research**: https://www.coingecko.com/research — Quarterly reports

#### Discovery Criteria (Inclusive)

A project qualifies for discovery if it meets ANY of these criteria:

1. **Revenue Champion**: Top 50 in DefiLlama fees/revenue rankings, even if institutional adoption is low
2. **Institutional Darling**: ETF product exists or filed, or held by 2+ major funds (Grayscale, a16z, Paradigm, Galaxy)
3. **Regulatory Leader**: Clear commodity classification or MiCA compliance, listed on all major regulated exchanges
4. **Supply Excellence**: >70% in long-term holder wallets, declining exchange reserves, deflationary or low inflation
5. **Emerging Momentum**: >$500M market cap with clear value accrual mechanism and growing TVL/revenue

**Key Principle**: A project does NOT need to score high on all dimensions. Excellence in ONE dimension (especially revenue or institutional) can justify inclusion. The scoring framework will rank them appropriately.

Example: Hyperliquid has limited institutional adoption but exceptional revenue — valid discovery candidate.
Example: Canton has high fees/revenue on DefiLlama — should be evaluated even if other metrics are unclear.

### Step 3: Review Existing Assets

For each current watchlist asset, check for:
- Regulatory actions against the project
- Team departures or controversies
- Sustained revenue decline
- Distribution phase confirmed
- Security incidents

Flag any that should be demoted or removed.

### Step 4: Evaluate Candidates

For each promising project:
1. Score all 5 dimensions (0-100)
2. Calculate weighted composite based on asset type
3. Determine appropriate tier
4. Write investment thesis (2-3 sentences)

### Step 5: Generate Report

Output a markdown report following this structure:

```markdown
# Monthly Discovery Report - [Month Year]

## Executive Summary
[2-3 sentences on overall market state and key findings]

## High-Confidence Recommendations
[Findings supported by multiple sources]

### New Discoveries

#### [Symbol] - [Name]
- **Asset Type**: [store-of-value|smart-contract|defi|infrastructure]
- **Recommended Tier**: [leader|runner-up|observation]
- **Scores**:
  - Institutional: [0-100] - [brief rationale]
  - Revenue: [0-100] - [brief rationale]
  - Regulatory: [0-100] - [brief rationale]
  - Supply: [0-100] - [brief rationale]
  - Wyckoff: [0-100] - [current phase]
- **Value Accrual**: [strong|moderate|weak] - [mechanism description]
- **Composite**: [weighted score]
- **Thesis**: [2-3 sentences]
- **CoinGecko ID**: [id]
- **DefiLlama Slug**: [slug or null]

### Tier Changes

| Action | Symbol | Change | Rationale |
|--------|--------|--------|-----------|
| PROMOTE | XXX | observation → runner-up | ... |
| DEMOTE | YYY | runner-up → observation | ... |
| REMOVE | ZZZ | removed from watchlist | ... |

## Existing Asset Reviews

### [Symbol] - Status: [KEEP|DEMOTE|REMOVE]
- **Current Tier**: [tier]
- **Key Changes**: [what changed since last review]
- **Recommendation**: [action and rationale]

## Auto-Applied Changes

After the report is generated, **automatically apply changes** to `pipeline/assets.yaml`:

```yaml
# Add new assets to the flat list (tier computed at runtime)
assets:
  # ... existing assets ...

  # NEW: Added from discovery
  - symbol: NEW
    name: New Asset
    asset_type: defi
    coingecko_id: new-asset
    defillama_slug: new-asset
    wyckoff_override: null
```

To **remove** an asset, delete its entry from the list.

## Watchlist Health Summary
- Total assets: [N]
- Projected Leaders (≥75): [N]
- Projected Runner-ups (65-74): [N]
- Projected Observation (50-64): [N]
```

### Step 6: Save Report

Write the report to:
```
discovery/report_YYYY-MM.md
```

## Ensemble Mode

For higher confidence, run 3 independent discoveries with different focus areas:

1. **Run 1**: Focus on NEW project launches and institutional signals
2. **Run 2**: Focus on regulatory developments and momentum shifts
3. **Run 3**: Focus on DeFi/infrastructure, revenue metrics, protocol upgrades

Then:
- Cross-reference claims across all 3
- Flag contradictions
- Rate confidence levels (HIGH if 2+ agree)
- Merge into consolidated report

The ensemble script automates this:
```bash
./scripts/run-discovery-ensemble.sh
```

## Important Guidelines

- **Be specific**: Cite sources, include metrics, name dates
- **Be inclusive**: One exceptional dimension can justify inclusion — don't require all dimensions to be strong
- **Revenue is king**: A protocol with >$5M annualized revenue is a serious candidate even if other dimensions are weak
- **Maintain balance**: Don't exceed tier targets
- **Flag uncertainty**: If data is incomplete, note it but still evaluate based on available data
- **Think long-term**: This is for accumulation, not trading
- **Check before excluding**: If a project appears on DefiLlama fee leaderboards, it deserves evaluation

## Handling Incomplete Data

For newer or less-covered projects:

1. **Revenue data available but others missing**: Include as observation tier, note data gaps
2. **Institutional unclear but revenue strong**: Include — revenue demonstrates real adoption
3. **Regulatory unclear but institutional strong**: Include — institutional adoption implies compliance
4. **Missing DefiLlama slug**: Set `defillama_slug: null`, the pipeline will use LLM estimation

**Do NOT exclude** a project just because one or two dimensions lack data. The scoring framework handles missing dimensions through weight redistribution.
