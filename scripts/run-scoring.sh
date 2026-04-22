#!/bin/bash
# Weekly scoring pipeline with a hard wall-clock cap (default 2h).
#
# Why this feels slower than discovery:
# - Discovery is usually a few large Claude prompts (one report per phase).
# - Scoring runs up to several Claude calls *per watchlist asset* (regulatory,
#   institutional, value capture, adoption), each as a separate `claude`
#   subprocess — intended for Claude subscription (CLI); no API key required.
# - A slow or timing-out call can burn the full per-call timeout (see
#   CLAUDE_CLI_TIMEOUT / CLAUDE_ADOPTION_TIMEOUT in .env).
#
# Optional: set USE_CLAUDE_CLI=false only if you want the Anthropic HTTP API
# instead (extra cost vs subscription CLI).
#
# Env (optional):
#   SCORING_WALL_SECONDS   Wall-clock max for the whole run (default 7200).
#   USE_CLAUDE_CLI         true (default) — CLI subscription; false = HTTP API.
#   CLAUDE_CLI_TIMEOUT     Per general qualitative call (default 300 in code).
#   CLAUDE_ADOPTION_TIMEOUT Per adoption_activity call (default 300 in code).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_DIR/.venv"
LOG_DIR="$PROJECT_DIR/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/scoring_$TIMESTAMP.log"
SCORING_WALL_SECONDS="${SCORING_WALL_SECONDS:-7200}"

mkdir -p "$LOG_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting scoring pipeline (wall timeout ${SCORING_WALL_SECONDS}s)"
log "Project: $PROJECT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  log "ERROR: Virtual environment not found at $VENV_DIR"
  exit 1
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

cd "$PROJECT_DIR"

export USE_CLAUDE_CLI="${USE_CLAUDE_CLI:-true}"

run_inner() {
  python -m pipeline.run "$@"
}

EXIT=0
if command -v timeout >/dev/null 2>&1; then
  timeout "$SCORING_WALL_SECONDS" run_inner "$@" 2>&1 | tee -a "$LOG_FILE"
  EXIT=${PIPESTATUS[0]}
elif command -v gtimeout >/dev/null 2>&1; then
  gtimeout "$SCORING_WALL_SECONDS" run_inner "$@" 2>&1 | tee -a "$LOG_FILE"
  EXIT=${PIPESTATUS[0]}
else
  log "WARN: no timeout/gtimeout — running without wall-clock cap"
  run_inner "$@" 2>&1 | tee -a "$LOG_FILE"
  EXIT=${PIPESTATUS[0]}
fi

if [ "$EXIT" -eq 124 ]; then
  log "ERROR: hit wall timeout (${SCORING_WALL_SECONDS}s). Raise SCORING_WALL_SECONDS or lower CLAUDE_*_TIMEOUT values (faster fallbacks)."
elif [ "$EXIT" -eq 142 ]; then
  log "ERROR: subprocess timed out (often same as 124 on macOS)"
elif [ "$EXIT" -ne 0 ]; then
  log "ERROR: pipeline exited with code $EXIT"
else
  log "Pipeline finished OK"
fi

exit "$EXIT"
