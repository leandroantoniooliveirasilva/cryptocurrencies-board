#!/bin/bash
# Daily technical indicators (RSI, Wyckoff, GLI, Fear & Greed, RS vs BTC, action).
# Scheduled 12:00 UTC via launchd (TZ=UTC in plist).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/.venv"

mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/indicators_$TIMESTAMP.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting daily indicators pipeline"
log "Project: $PROJECT_DIR"

if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    log "Activated virtual environment"
else
    log "ERROR: Virtual environment not found at $VENV_DIR"
    exit 1
fi

export USE_CLAUDE_CLI=true
cd "$PROJECT_DIR"

if python -m pipeline.indicators 2>&1 | tee -a "$LOG_FILE"; then
    log "Indicators completed successfully"
    git add public/latest.json pipeline/storage/history.sqlite
    if git diff --staged --quiet; then
        log "No changes to commit"
    else
        git commit -m "chore: daily indicators $(date -u +%Y-%m-%d)"
        if git push origin main 2>&1 | tee -a "$LOG_FILE"; then
            log "Pushed to GitHub"
        else
            log "WARNING: Push failed"
        fi
    fi
else
    log "ERROR: Indicators pipeline failed"
    exit 1
fi

find "$LOG_DIR" -name "indicators_*.log" -mtime +30 -delete 2>/dev/null || true
log "Done"
