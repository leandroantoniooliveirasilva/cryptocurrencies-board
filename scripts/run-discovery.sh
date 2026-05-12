#!/bin/bash
# Monthly discovery pipeline runner
# Uses CursorAgent CLI to find and vet new crypto projects
# Runs on day 1 of each month at 18:00 UTC

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DISCOVERY_DIR="$PROJECT_DIR/out/discovery"
PROMPT_FILE="$PROJECT_DIR/src/pipeline/discovery/prompt.md"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$DISCOVERY_DIR"

# Timestamp for logging
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MONTH_STAMP=$(date +"%Y-%m")
LOG_FILE="$LOG_DIR/discovery_$TIMESTAMP.log"
REPORT_FILE="$DISCOVERY_DIR/report_$MONTH_STAMP.md"
START_TS=$(date +%s)
DISCOVERY_ESTIMATE_SECONDS="${DISCOVERY_ESTIMATE_SECONDS:-1800}"

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

log "Starting monthly discovery pipeline"
log "Project: $PROJECT_DIR"

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
        AGENT_LABEL="Claude Code"
        AGENT_FLAGS=(--print --dangerously-skip-permissions --model "$AGENT_MODEL")
        AGENT_INSTALL_HINT="Install Claude Code and run \`claude login\` (or set ANTHROPIC_API_KEY)."
        ;;
esac
if ! command -v "$AGENT_BIN" &> /dev/null; then
    log "ERROR: $AGENT_LABEL CLI ($AGENT_BIN) not found. $AGENT_INSTALL_HINT"
    exit 1
fi

# Check prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    log "ERROR: Discovery prompt not found at $PROMPT_FILE"
    exit 1
fi

# Read current assets for context
CURRENT_ASSETS=$(cat "$PROJECT_DIR/src/pipeline/assets.yaml")

# Build the discovery prompt with current state
DISCOVERY_PROMPT="$(cat "$PROMPT_FILE")

## Current Watchlist (assets.yaml)

\`\`\`yaml
$CURRENT_ASSETS
\`\`\`

## Output Instructions

1. Search the web for promising crypto projects released or gaining traction in the past 30-60 days
2. Evaluate each candidate against weighted composite dimensions (`weights_by_category` in config):
   - Institutional (ETF potential, fund holdings, custody)
   - Adoption / value capture (as weighted — fees, TVL, usage)
   - Regulatory (jurisdictional clarity, compliance)
   - Supply (tokenomics, exchange reserves, holder distribution)
   Wyckoff phase is a global filter (daily indicators), not a composite dimension — optional qualitative context only.
3. For current watchlist assets, flag any that should be removed (fundamental deterioration)
4. Propose additions with tier placement (leader, runner-up, observation)
5. Output a structured report in markdown format

Today's date: $(date -u +"%Y-%m-%d")
"

log "Running $AGENT_LABEL discovery (model: $AGENT_MODEL)..."
log_progress 5 "discovery generation started"
cd "$PROJECT_DIR"

"$AGENT_BIN" "${AGENT_FLAGS[@]}" "$DISCOVERY_PROMPT" > "$REPORT_FILE.tmp" 2>> "$LOG_FILE" &
DISCOVERY_PID=$!
SECONDS_WAITED=0

while kill -0 "$DISCOVERY_PID" 2>/dev/null; do
    sleep 30
    SECONDS_WAITED=$((SECONDS_WAITED + 30))
    PCT=$((5 + (SECONDS_WAITED * 85 / DISCOVERY_ESTIMATE_SECONDS)))
    if [ "$PCT" -gt 90 ]; then
        PCT=90
    fi
    log_progress "$PCT" "discovery generation in progress"
done

if wait "$DISCOVERY_PID"; then
    mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    log_progress 96 "discovery output written"
    log "Discovery report generated: $REPORT_FILE"

    log "Report preview:"
    head -50 "$REPORT_FILE" | tee -a "$LOG_FILE"
else
    log "ERROR: $AGENT_LABEL discovery failed"
    rm -f "$REPORT_FILE.tmp"
    exit 1
fi

# Cleanup old logs (keep last 12 months)
find "$LOG_DIR" -name "discovery_*.log" -mtime +365 -delete 2>/dev/null || true

log_progress 100 "discovery pipeline complete"
log "Review the report at: $REPORT_FILE"
log "To apply changes, manually edit src/pipeline/assets.yaml"
