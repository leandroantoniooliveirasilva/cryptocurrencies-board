#!/bin/bash
# Monthly discovery pipeline runner
# Uses OpenCode CLI (default Big Pickle) to find and vet new crypto projects
# Runs on day 1 of each month at 18:00 UTC

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
DISCOVERY_DIR="$PROJECT_DIR/discovery"
PROMPT_FILE="$PROJECT_DIR/pipeline/discovery/prompt.md"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$DISCOVERY_DIR"

# Timestamp for logging
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
MONTH_STAMP=$(date +"%Y-%m")
LOG_FILE="$LOG_DIR/discovery_$TIMESTAMP.log"
REPORT_FILE="$DISCOVERY_DIR/report_$MONTH_STAMP.md"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting monthly discovery pipeline"
log "Project: $PROJECT_DIR"

# CursorAgent CLI
CURSOR_AGENT_BIN="${CURSOR_AGENT_BIN:-cursor-agent}"
CURSOR_AGENT_MODEL="${CURSOR_AGENT_MODEL:-gpt-5}"
if ! command -v "$CURSOR_AGENT_BIN" &> /dev/null; then
    log "ERROR: cursor-agent CLI not found. Install Cursor Agent and run cursor-agent login."
    exit 1
fi

# Check prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    log "ERROR: Discovery prompt not found at $PROMPT_FILE"
    exit 1
fi

# Read current assets for context
CURRENT_ASSETS=$(cat "$PROJECT_DIR/pipeline/assets.yaml")

# Build the discovery prompt with current state
DISCOVERY_PROMPT="$(cat "$PROMPT_FILE")

## Current Watchlist (assets.yaml)

\`\`\`yaml
$CURRENT_ASSETS
\`\`\`

## Output Instructions

1. Search the web for promising crypto projects released or gaining traction in the past 30-60 days
2. Evaluate each candidate against our 5-dimension framework:
   - Institutional (ETF potential, fund holdings, custody)
   - Revenue (protocol fees, sustainable revenue)
   - Regulatory (jurisdictional clarity, compliance)
   - Supply (tokenomics, exchange reserves, holder distribution)
   - Wyckoff (current accumulation/distribution phase)
3. For current watchlist assets, flag any that should be removed (fundamental deterioration)
4. Propose additions with tier placement (leader, runner-up, observation)
5. Output a structured report in markdown format

Today's date: $(date -u +"%Y-%m-%d")
"

log "Running CursorAgent discovery (model: $CURSOR_AGENT_MODEL)..."
cd "$PROJECT_DIR"

if "$CURSOR_AGENT_BIN" --print --trust --force --model "$CURSOR_AGENT_MODEL" "$DISCOVERY_PROMPT" 2>&1 | tee -a "$LOG_FILE" > "$REPORT_FILE.tmp"; then
    mv "$REPORT_FILE.tmp" "$REPORT_FILE"
    log "Discovery report generated: $REPORT_FILE"

    # Extract proposed changes summary
    log "Report preview:"
    head -50 "$REPORT_FILE" | tee -a "$LOG_FILE"
else
    log "ERROR: OpenCode discovery failed"
    rm -f "$REPORT_FILE.tmp"
    exit 1
fi

# Cleanup old logs (keep last 12 months)
find "$LOG_DIR" -name "discovery_*.log" -mtime +365 -delete 2>/dev/null || true

log "Discovery pipeline complete"
log "Review the report at: $REPORT_FILE"
log "To apply changes, manually edit pipeline/assets.yaml"
