#!/bin/bash
# Ensemble discovery pipeline with fact-checking
# Runs 3 independent discoveries, reviews them, then merges into final report
#
# Architecture:
#   1. Run 3 parallel discoveries (independent context each)
#   2. Fact-check review of all 3 reports
#   3. Merge into consolidated final report

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DISCOVERY_DIR="$PROJECT_DIR/discovery"
PROMPT_FILE="$PROJECT_DIR/pipeline/discovery/prompt.md"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$DISCOVERY_DIR"

# Timestamp for this run
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MONTH_STAMP=$(date +"%Y-%m")
LOG_FILE="$LOG_DIR/discovery_ensemble_$TIMESTAMP.log"
REPORT_DIR="$DISCOVERY_DIR/$MONTH_STAMP"
mkdir -p "$REPORT_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting ensemble discovery pipeline (3 independent runs + review + merge)"
log "Project: $PROJECT_DIR"
log "Output directory: $REPORT_DIR"

# Check Claude CLI is available
if ! command -v claude &> /dev/null; then
    log "ERROR: Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi

# Check prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    log "ERROR: Discovery prompt not found at $PROMPT_FILE"
    exit 1
fi

# Read current assets for context
CURRENT_ASSETS=$(cat "$PROJECT_DIR/pipeline/assets.yaml")
TODAY=$(date -u +"%Y-%m-%d")

# Base discovery prompt
BASE_PROMPT="$(cat "$PROMPT_FILE")

## Current Watchlist (assets.yaml)

\`\`\`yaml
$CURRENT_ASSETS
\`\`\`

## Output Instructions

1. Search the web for promising crypto projects released or gaining traction in the past 30-60 days
2. Evaluate each candidate against our framework:
   - Institutional (ETF potential, fund holdings, custody)
   - Revenue (protocol fees, sustainable revenue)
   - Regulatory (jurisdictional clarity, compliance)
   - Supply (tokenomics, exchange reserves, holder distribution)
   - Wyckoff (current accumulation/distribution phase)
   - Value Accrual (CRITICAL: how does protocol success translate to token appreciation?)
3. For current watchlist assets, flag any that should be removed (fundamental deterioration)
4. Propose additions with tier placement (leader, runner-up, observation)
5. Output a structured report in markdown format

Today's date: $TODAY"

# ============================================================================
# PHASE 1: Run 3 independent discoveries in parallel
# ============================================================================
log "PHASE 1: Starting 3 independent discoveries in parallel..."

run_discovery() {
    local run_id=$1
    local output_file="$REPORT_DIR/discovery_${run_id}.md"
    local focus=""

    # Each run gets a slightly different focus to encourage diversity
    case $run_id in
        1) focus="Focus particularly on NEW project launches and recent token generation events. Look for projects with strong institutional backing signals." ;;
        2) focus="Focus particularly on EXISTING projects showing momentum shifts. Look for regulatory developments and ETF-related news." ;;
        3) focus="Focus particularly on DeFi and infrastructure projects. Look for revenue metrics, TVL changes, and protocol upgrades." ;;
    esac

    local prompt="$BASE_PROMPT

## Run-Specific Focus (Run #$run_id)
$focus

## Important
- Be thorough in your web research
- Cite specific sources for claims
- Include concrete metrics where available
- This is run $run_id of 3 independent analyses - provide your independent assessment
- CRITICAL: Do NOT use any personal memory or prior opinions - evaluate ALL assets objectively based on the framework criteria only"

    log "  Starting discovery run #$run_id..."

    if claude --model claude-opus-4-5-20251101 --print "$prompt" > "$output_file" 2>> "$LOG_FILE"; then
        log "  Discovery run #$run_id completed: $output_file"
        return 0
    else
        log "  ERROR: Discovery run #$run_id failed"
        return 1
    fi
}

# Run all 3 discoveries in parallel
run_discovery 1 &
PID1=$!
run_discovery 2 &
PID2=$!
run_discovery 3 &
PID3=$!

# Wait for all to complete
log "Waiting for all 3 discoveries to complete..."
FAILED=0

wait $PID1 || { log "Discovery run #1 failed"; FAILED=1; }
wait $PID2 || { log "Discovery run #2 failed"; FAILED=1; }
wait $PID3 || { log "Discovery run #3 failed"; FAILED=1; }

if [ $FAILED -eq 1 ]; then
    log "ERROR: One or more discovery runs failed"
    exit 1
fi

log "All 3 discoveries completed successfully"

# ============================================================================
# PHASE 2: Fact-checking review
# ============================================================================
log "PHASE 2: Running fact-checking review..."

REPORT1=$(cat "$REPORT_DIR/discovery_1.md")
REPORT2=$(cat "$REPORT_DIR/discovery_2.md")
REPORT3=$(cat "$REPORT_DIR/discovery_3.md")

REVIEW_PROMPT="# Fact-Checking Review Task

You are a senior crypto analyst tasked with reviewing and fact-checking 3 independent discovery reports. Your job is to:

1. **Cross-reference claims**: Identify claims that appear in multiple reports (high confidence) vs claims that appear in only one report (needs verification)
2. **Flag contradictions**: Note where reports disagree on facts or assessments
3. **Verify key metrics**: For each proposed asset, verify the key metrics mentioned (market cap, TVL, revenue, etc.) using web search
4. **Assess confidence levels**: Rate each recommendation as HIGH/MEDIUM/LOW confidence based on source agreement and verifiability
5. **Identify gaps**: Note important information that may be missing from all reports

## Report #1 (Institutional & New Projects Focus)
$REPORT1

## Report #2 (Regulatory & Momentum Focus)
$REPORT2

## Report #3 (DeFi & Infrastructure Focus)
$REPORT3

## Output Format

Generate a fact-check report with:

\`\`\`markdown
# Fact-Check Review - $MONTH_STAMP

## Cross-Reference Summary
[Which findings appear in multiple reports]

## Contradictions Found
[Where reports disagree and which is correct]

## Metric Verification
[Key metrics verified via web search]

## Confidence Ratings
| Asset | Reports Mentioning | Confidence | Notes |
|-------|-------------------|------------|-------|
| XXX   | 1,2,3             | HIGH       | ...   |

## Information Gaps
[What's missing that should be researched]

## Recommended Adjustments
[Corrections to make in the final merged report]
\`\`\`

Today's date: $TODAY"

REVIEW_FILE="$REPORT_DIR/fact_check_review.md"

if claude --model claude-opus-4-5-20251101 --print "$REVIEW_PROMPT" > "$REVIEW_FILE" 2>> "$LOG_FILE"; then
    log "Fact-check review completed: $REVIEW_FILE"
else
    log "ERROR: Fact-check review failed"
    exit 1
fi

# ============================================================================
# PHASE 3: Merge into final report
# ============================================================================
log "PHASE 3: Merging into final consolidated report..."

REVIEW_CONTENT=$(cat "$REVIEW_FILE")

MERGE_PROMPT="# Final Report Consolidation Task

You are a senior crypto analyst tasked with creating the final consolidated discovery report. You have:
- 3 independent discovery reports (each with different focus areas)
- A fact-check review identifying agreements, contradictions, and confidence levels

Your task is to synthesize all inputs into a single, authoritative report that:

1. **Prioritizes high-confidence findings**: Recommendations supported by multiple reports get priority
2. **Resolves contradictions**: Use the fact-check review to pick the correct information
3. **Applies corrections**: Incorporate any corrections from the fact-check review
4. **Maintains structure**: Follow the standard report format
5. **Adds synthesis notes**: Where reports disagreed, note the consensus view

## Discovery Report #1
$REPORT1

## Discovery Report #2
$REPORT2

## Discovery Report #3
$REPORT3

## Fact-Check Review
$REVIEW_CONTENT

## Output Format

Generate the final consolidated report following this structure:

\`\`\`markdown
# Monthly Discovery Report - $MONTH_STAMP (Consolidated)

## Methodology Note
This report consolidates 3 independent discovery analyses with cross-referencing and fact-checking. Confidence levels reflect agreement across analyses.

## Executive Summary
[2-3 sentences on overall market state and key findings]

## High-Confidence Recommendations
[Findings agreed upon by 2+ independent analyses]

### New Discoveries
[For each asset, include confidence level and which reports supported it]

### Tier Adjustments
[Promotions, demotions, removals with confidence levels]

## Medium-Confidence Recommendations
[Findings from single analysis but verified]

## Low-Confidence / Needs More Research
[Findings that couldn't be fully verified]

## Existing Asset Reviews
[Status of current watchlist assets]

## Proposed assets.yaml Changes
[YAML snippet - only include high-confidence changes]

## Watchlist Health Summary
- Total assets: [N]
- Leaders: [N] (target: 4-6)
- Runner-ups: [N] (target: 4-6)
- Observation: [N] (target: 5-8)

## Appendix: Analysis Agreement Matrix
[Table showing which reports agreed on which findings]
\`\`\`

Today's date: $TODAY"

FINAL_REPORT="$DISCOVERY_DIR/report_$MONTH_STAMP.md"

if claude --model claude-opus-4-5-20251101 --print "$MERGE_PROMPT" > "$FINAL_REPORT" 2>> "$LOG_FILE"; then
    log "Final consolidated report generated: $FINAL_REPORT"
else
    log "ERROR: Report merge failed"
    exit 1
fi

# ============================================================================
# Summary
# ============================================================================
log ""
log "=========================================="
log "Ensemble Discovery Pipeline Complete"
log "=========================================="
log ""
log "Generated files:"
log "  - Discovery #1: $REPORT_DIR/discovery_1.md"
log "  - Discovery #2: $REPORT_DIR/discovery_2.md"
log "  - Discovery #3: $REPORT_DIR/discovery_3.md"
log "  - Fact-check:   $REPORT_DIR/fact_check_review.md"
log "  - Final report: $FINAL_REPORT"
log ""
log "Review the final report at: $FINAL_REPORT"
log "To apply changes, manually edit pipeline/assets.yaml"

# Show preview of final report
log ""
log "Final report preview:"
head -60 "$FINAL_REPORT" | tee -a "$LOG_FILE"
