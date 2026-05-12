#!/bin/bash
# Ensemble discovery pipeline with fact-checking
# Runs 3 independent discoveries, reviews them, then merges into final report

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DISCOVERY_DIR="$PROJECT_DIR/out/discovery"
PROMPT_FILE="$PROJECT_DIR/src/pipeline/discovery/prompt.md"

mkdir -p "$LOG_DIR"
mkdir -p "$DISCOVERY_DIR"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MONTH_STAMP=$(date +"%Y-%m")
LOG_FILE="$LOG_DIR/discovery_ensemble_$TIMESTAMP.log"
REPORT_DIR="$DISCOVERY_DIR/$MONTH_STAMP"
mkdir -p "$REPORT_DIR"
START_TS=$(date +%s)
PHASE_ESTIMATE_SECONDS="${DISCOVERY_PHASE_ESTIMATE_SECONDS:-1800}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

elapsed_hms() {
    local now elapsed h m s
    now=$(date +%s)
    elapsed=$((now - START_TS))
    h=$((elapsed / 3600))
    m=$(((elapsed % 3600) / 60))
    s=$((elapsed % 60))
    printf '%02d:%02d:%02d' "$h" "$m" "$s"
}

log_progress() {
    local pct="$1"
    local msg="$2"
    log "progress=${pct}% elapsed=$(elapsed_hms) ${msg}"
}

run_step_with_progress() {
    local label="$1"
    local start_pct="$2"
    local end_pct="$3"
    shift 3

    "$@" &
    local pid=$!
    local waited=0
    local span=$((end_pct - start_pct))

    while kill -0 "$pid" 2>/dev/null; do
        sleep 30
        waited=$((waited + 30))
        local pct=$((start_pct + (waited * span / PHASE_ESTIMATE_SECONDS)))
        if [ "$pct" -ge "$end_pct" ]; then
            pct=$((end_pct - 1))
        fi
        log_progress "$pct" "$label in progress"
    done

    wait "$pid"
}

log "Starting ensemble discovery pipeline (3 independent runs + review + merge)"
log "Project: $PROJECT_DIR"
log "Output directory: $REPORT_DIR"

# Select LLM agent CLI: "claude" (default) or "cursor".
LLM_AGENT_CLI="${LLM_AGENT_CLI:-claude}"
case "$LLM_AGENT_CLI" in
    cursor|cursor-agent)
        AGENT_BIN="${CURSOR_AGENT_BIN:-cursor-agent}"
        AGENT_MODEL="${CURSOR_AGENT_MODEL:-auto}"
        AGENT_LABEL="Cursor Agent"
        AGENT_FLAGS=(--print --trust --force --model "$AGENT_MODEL")
        AGENT_INSTALL_HINT="Install Cursor Agent and run cursor-agent login."
        ;;
    *)
        AGENT_BIN="${CLAUDE_AGENT_BIN:-claude}"
        AGENT_MODEL="${CLAUDE_AGENT_MODEL:-sonnet}"
        # Restrict tools so the report must come on stdout (Write/Edit would
        # otherwise let Claude side-channel the output to disk on its own).
        AGENT_TOOLS="${CLAUDE_AGENT_TOOLS:-WebSearch,WebFetch}"
        AGENT_LABEL="Claude Code"
        AGENT_FLAGS=(--print --dangerously-skip-permissions --tools "$AGENT_TOOLS" --model "$AGENT_MODEL")
        AGENT_INSTALL_HINT="Install Claude Code and run \`claude login\` (or set ANTHROPIC_API_KEY)."
        ;;
esac
if ! command -v "$AGENT_BIN" &> /dev/null; then
    log "ERROR: $AGENT_LABEL CLI ($AGENT_BIN) not found. $AGENT_INSTALL_HINT"
    exit 1
fi

if [ ! -f "$PROMPT_FILE" ]; then
    log "ERROR: Discovery prompt not found at $PROMPT_FILE"
    exit 1
fi

CURRENT_ASSETS=$(cat "$PROJECT_DIR/src/pipeline/assets.yaml")
TODAY=$(date -u +"%Y-%m-%d")

BASE_PROMPT="$(cat "$PROMPT_FILE")

## Current Watchlist (assets.yaml)

\`\`\`yaml
$CURRENT_ASSETS
\`\`\`

## Output Instructions

1. **OMISSION AUDIT (MANDATORY FIRST)**: Before new discoveries, check if major established assets are missing from the watchlist (ETH, BNB, ADA, DOT, etc.). Evaluate any omissions using the full framework.
2. Search the web for promising crypto projects released or gaining traction in the past 30-60 days
3. Evaluate each candidate against weighted composite dimensions (\`weights_by_category\`) plus value accrual:
   - Institutional (ETF potential, fund holdings, custody)
   - Adoption / value capture (as weighted — fees, TVL, usage)
   - Regulatory (jurisdictional clarity, compliance)
   - Supply (tokenomics, exchange reserves, holder distribution)
   - Value accrual (CRITICAL: how does protocol success translate to token appreciation?)
   Wyckoff phase is a global filter (daily indicators), not a composite dimension — optional qualitative context only.
4. For current watchlist assets, flag any that should be removed (fundamental deterioration)
5. Propose additions with tier placement (leader, runner-up, observation)
6. Output a structured report in markdown format

Today's date: $TODAY"

log_progress 3 "ensemble run initialized"
log "PHASE 1: Starting 3 independent discoveries in parallel..."
log_progress 5 "phase 1 started"

run_discovery() {
    local run_id=$1
    local output_file="$REPORT_DIR/discovery_${run_id}.md"
    local focus=""

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

    if "$AGENT_BIN" "${AGENT_FLAGS[@]}" "$prompt" > "$output_file" 2>> "$LOG_FILE"; then
        log "  Discovery run #$run_id completed: $output_file"
        return 0
    else
        log "  ERROR: Discovery run #$run_id failed"
        return 1
    fi
}

run_discovery 1 & PID1=$!
run_discovery 2 & PID2=$!
run_discovery 3 & PID3=$!

log "Waiting for all 3 discoveries to complete..."
FAILED=0
while true; do
    DONE=0
    kill -0 "$PID1" 2>/dev/null || DONE=$((DONE + 1))
    kill -0 "$PID2" 2>/dev/null || DONE=$((DONE + 1))
    kill -0 "$PID3" 2>/dev/null || DONE=$((DONE + 1))
    PCT=$((5 + DONE * 20))
    log_progress "$PCT" "phase 1 progress (${DONE}/3 discovery runs completed)"
    [ "$DONE" -eq 3 ] && break
    sleep 30
done

wait "$PID1" || { log "Discovery run #1 failed"; FAILED=1; }
wait "$PID2" || { log "Discovery run #2 failed"; FAILED=1; }
wait "$PID3" || { log "Discovery run #3 failed"; FAILED=1; }

if [ $FAILED -eq 1 ]; then
    log "ERROR: One or more discovery runs failed"
    exit 1
fi

log "All 3 discoveries completed successfully"
log_progress 66 "phase 1 complete"

log "PHASE 2: Running fact-checking review..."
log_progress 70 "phase 2 started"

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
if run_step_with_progress "phase 2 fact-check review" 70 84 "$AGENT_BIN" "${AGENT_FLAGS[@]}" "$REVIEW_PROMPT" > "$REVIEW_FILE" 2>> "$LOG_FILE"; then
    log "Fact-check review completed: $REVIEW_FILE"
else
    log "ERROR: Fact-check review failed"
    exit 1
fi

log "PHASE 3: Merging into final consolidated report..."
log_progress 86 "phase 3 started"

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
if run_step_with_progress "phase 3 merge" 86 99 "$AGENT_BIN" "${AGENT_FLAGS[@]}" "$MERGE_PROMPT" > "$FINAL_REPORT" 2>> "$LOG_FILE"; then
    log "Final consolidated report generated: $FINAL_REPORT"
else
    log "ERROR: Report merge failed"
    exit 1
fi

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
log_progress 100 "ensemble discovery pipeline complete"
log "Review the final report at: $FINAL_REPORT"
log "To apply changes, manually edit src/pipeline/assets.yaml"

log ""
log "Final report preview:"
head -60 "$FINAL_REPORT" | tee -a "$LOG_FILE"
