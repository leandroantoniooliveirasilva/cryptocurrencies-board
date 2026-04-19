# Discovery Skill

Monthly watchlist discovery and vetting for the conviction scoring framework.

> **Note**: The scoring pipeline runs locally (not via GitHub Actions). Discovery informs manual updates to `assets.yaml`, which are then processed by the local pipeline.

## CRITICAL: Objective Analysis Only

**Do NOT use any personal memory, preferences, or opinions from previous conversations.** This analysis must be purely objective and fact-based. Evaluate ALL assets—including those you may have previously discussed or expressed opinions about—based solely on the framework criteria below.

Your role is to be an unbiased analyst. If a project meets the criteria, it belongs on the watchlist regardless of any prior conversations or stored preferences. Follow ONLY the instructions in this document.

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

## Tier Definitions

**Leaders** (4-6 assets): Core positions for accumulation
- Composite ≥75 consistently
- Clear institutional adoption path
- No existential regulatory risk

**Runner-ups** (4-6 assets): Promotion candidates
- Composite 65-74 or improving
- Strong in 2-3 dimensions
- Clear path to leader status

**Observation** (5-8 assets): Watch only
- Interesting but gaps exist
- May have single strong dimension
- Early stage or unproven

## Discovery Process

### Step 1: Read Current Watchlist
```bash
cat pipeline/assets.yaml
```

Understand the current state before making changes.

### Step 2: Omission Audit (MANDATORY)

Before searching for new projects, explicitly evaluate whether any **major established assets** are missing from the watchlist:

- Check top-20 market cap assets not on the watchlist
- Check assets with significant ETF infrastructure
- Check category leaders (L1s, DeFi, infrastructure) that are absent

**Common omissions to evaluate**: ETH, BNB, ADA, DOT, MATIC, ATOM, UNI, LTC, etc.

For each candidate, apply the full framework and recommend adding if it scores well — regardless of whether it's "new" or "exciting."

### Step 3: Search for New Projects

Use web search to find projects that:
- Launched or gained traction in the past 60 days
- Have institutional interest signals (fund raises, partnerships)
- Show sustainable revenue or clear path to it
- Have favorable tokenomics
- Are NOT already in the watchlist

Search sources:
- CoinGecko / CoinMarketCap (market data)
- DefiLlama (TVL, revenue data)
- Token Terminal (revenue metrics)
- Messari (institutional reports)
- The Block Research
- Protocol documentation and blogs
- SEC filings and regulatory news

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

## Proposed assets.yaml Changes

```yaml
# Changes to apply
leaders:
  - symbol: NEW
    name: New Asset
    asset_type: defi
    coingecko_id: new-asset
    defillama_slug: new-asset
    wyckoff_override: null
```

## Watchlist Health Summary
- Total assets: [N]
- Leaders: [N] (target: 4-6)
- Runner-ups: [N] (target: 4-6)
- Observation: [N] (target: 5-8)
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
- **Be conservative**: Only recommend what you can verify
- **Maintain balance**: Don't exceed tier targets
- **Flag uncertainty**: If data is incomplete, say so
- **Think long-term**: This is for accumulation, not trading
