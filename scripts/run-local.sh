#!/bin/bash
# Local pipeline runner for macOS
# Uses Claude CLI (subscription) instead of API

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
VENV_DIR="$PROJECT_DIR/.venv"

# Create logs directory
mkdir -p "$LOG_DIR"

# Timestamp for logging
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/scan_$TIMESTAMP.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting daily scoring pipeline"
log "Project: $PROJECT_DIR"

# Activate virtual environment
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
    log "Activated virtual environment"
else
    log "ERROR: Virtual environment not found at $VENV_DIR"
    log "Run: python3 -m venv $VENV_DIR && pip install -r requirements.txt"
    exit 1
fi

# Check Claude CLI is available
if ! command -v claude &> /dev/null; then
    log "WARNING: Claude CLI not found, will use fallback scores"
fi

# Set environment for CLI usage
export USE_CLAUDE_CLI=true

# Run the pipeline
cd "$PROJECT_DIR"
log "Running pipeline..."

if python -m pipeline.run 2>&1 | tee -a "$LOG_FILE"; then
    log "Pipeline completed successfully"

    # Auto-commit and push to GitHub (enabled by default for dashboard updates)
    log "Committing and pushing to GitHub..."
    cd "$PROJECT_DIR"

    git add public/latest.json pipeline/storage/history.sqlite

    if git diff --staged --quiet; then
        log "No changes to commit"
    else
        git commit -m "chore: daily snapshot $(date -u +%Y-%m-%d)"
        log "Changes committed"

        if git push origin main 2>&1 | tee -a "$LOG_FILE"; then
            log "Pushed to GitHub - dashboard will update automatically"
        else
            log "WARNING: Push failed - changes committed locally only"
        fi
    fi
else
    log "ERROR: Pipeline failed"
    exit 1
fi

# Cleanup old logs (keep last 30 days)
find "$LOG_DIR" -name "scan_*.log" -mtime +30 -delete 2>/dev/null || true

log "Done"
