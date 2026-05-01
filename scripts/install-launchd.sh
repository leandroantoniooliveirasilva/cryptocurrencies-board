#!/bin/bash
# Install/uninstall launchd jobs for weekly dimension scoring, daily indicators, and discovery

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Weekly dimension scoring (Sunday 12:00 UTC)
SCORING_PLIST_SRC="$SCRIPT_DIR/com.crypto.scoring.plist"
SCORING_PLIST_DST="$HOME/Library/LaunchAgents/com.crypto.scoring.plist"
SCORING_LABEL="com.crypto.scoring"

# Daily indicators (every day 12:00 UTC)
INDICATORS_PLIST_SRC="$SCRIPT_DIR/com.crypto.indicators.plist"
INDICATORS_PLIST_DST="$HOME/Library/LaunchAgents/com.crypto.indicators.plist"
INDICATORS_LABEL="com.crypto.indicators"

# Monthly discovery job
DISCOVERY_PLIST_SRC="$SCRIPT_DIR/com.crypto.discovery.plist"
DISCOVERY_PLIST_DST="$HOME/Library/LaunchAgents/com.crypto.discovery.plist"
DISCOVERY_LABEL="com.crypto.discovery"

usage() {
    echo "Usage: $0 [command] [job]"
    echo ""
    echo "Commands:"
    echo "  install [all|scoring|indicators|discovery]  - Install and load launchd job(s)"
    echo "  uninstall [all|scoring|indicators|discovery] - Unload and remove launchd job(s)"
    echo "  status                            - Check if jobs are loaded"
    echo "  run [scoring|indicators|discovery] - Manually trigger a job now"
    echo ""
    echo "Jobs:"
    echo "  scoring    - Weekly dimension scoring (Sunday 12:00 UTC, TZ=UTC)"
    echo "  indicators - Daily technicals (12:00 UTC, TZ=UTC)"
    echo "  discovery  - Monthly watchlist discovery (day 1 at 18:00 UTC)"
    echo "  all        - scoring + indicators + discovery (default)"
    echo ""
    echo "Examples:"
    echo "  $0 install              # Install all three jobs"
    echo "  $0 install indicators    # Install only daily indicators"
    echo "  $0 run discovery        # Manually run discovery now"
    exit 1
}

install_job() {
    local name=$1
    local src=$2
    local dst=$3
    local label=$4
    local script=$5

    echo "Installing $name job..."

    mkdir -p "$HOME/Library/LaunchAgents"

    sed "s@__CRYPTO_BOARD_ROOT__@${PROJECT_DIR}@g" "$src" > "$dst"
    echo "  Wrote plist to $dst (repo root: $PROJECT_DIR)"

    chmod +x "$script"

    launchctl load "$dst"
    echo "  Job loaded: $label"
}

uninstall_job() {
    local name=$1
    local dst=$2
    local label=$3

    echo "Uninstalling $name job..."

    if [ -f "$dst" ]; then
        launchctl unload "$dst" 2>/dev/null || true
        rm "$dst"
        echo "  Job unloaded and removed: $label"
    else
        echo "  Job not installed: $label"
    fi
}

install() {
    local target=${1:-all}

    case "$target" in
        all)
            install_job "scoring" "$SCORING_PLIST_SRC" "$SCORING_PLIST_DST" "$SCORING_LABEL" "$SCRIPT_DIR/run-local.sh"
            install_job "indicators" "$INDICATORS_PLIST_SRC" "$INDICATORS_PLIST_DST" "$INDICATORS_LABEL" "$SCRIPT_DIR/run-daily-indicators.sh"
            install_job "discovery" "$DISCOVERY_PLIST_SRC" "$DISCOVERY_PLIST_DST" "$DISCOVERY_LABEL" "$SCRIPT_DIR/run-discovery.sh"
            echo ""
            echo "All jobs installed:"
            echo "  - Weekly dimension scoring: Sunday 12:00 UTC"
            echo "  - Daily indicators: every day 12:00 UTC"
            echo "  - Monthly discovery: day 1 at 18:00 UTC"
            ;;
        scoring)
            install_job "scoring" "$SCORING_PLIST_SRC" "$SCORING_PLIST_DST" "$SCORING_LABEL" "$SCRIPT_DIR/run-local.sh"
            echo ""
            echo "Weekly dimension scoring installed (Sunday 12:00 UTC)"
            ;;
        indicators)
            install_job "indicators" "$INDICATORS_PLIST_SRC" "$INDICATORS_PLIST_DST" "$INDICATORS_LABEL" "$SCRIPT_DIR/run-daily-indicators.sh"
            echo ""
            echo "Daily indicators job installed (12:00 UTC)"
            ;;
        discovery)
            install_job "discovery" "$DISCOVERY_PLIST_SRC" "$DISCOVERY_PLIST_DST" "$DISCOVERY_LABEL" "$SCRIPT_DIR/run-discovery.sh"
            echo ""
            echo "Monthly discovery job installed (runs day 1 at 18:00 UTC)"
            ;;
        *)
            echo "Unknown job: $target"
            usage
            ;;
    esac

    echo ""
    echo "To run manually: $0 run [scoring|indicators|discovery]"
    echo "To check status: $0 status"
}

uninstall() {
    local target=${1:-all}

    case "$target" in
        all)
            uninstall_job "scoring" "$SCORING_PLIST_DST" "$SCORING_LABEL"
            uninstall_job "indicators" "$INDICATORS_PLIST_DST" "$INDICATORS_LABEL"
            uninstall_job "discovery" "$DISCOVERY_PLIST_DST" "$DISCOVERY_LABEL"
            ;;
        scoring)
            uninstall_job "scoring" "$SCORING_PLIST_DST" "$SCORING_LABEL"
            ;;
        indicators)
            uninstall_job "indicators" "$INDICATORS_PLIST_DST" "$INDICATORS_LABEL"
            ;;
        discovery)
            uninstall_job "discovery" "$DISCOVERY_PLIST_DST" "$DISCOVERY_LABEL"
            ;;
        *)
            echo "Unknown job: $target"
            usage
            ;;
    esac
}

status() {
    echo "Launchd Job Status:"
    echo ""

    echo "Weekly dimension scoring ($SCORING_LABEL):"
    if launchctl list 2>/dev/null | grep -q "$SCORING_LABEL"; then
        echo "  Status: LOADED"
        launchctl list "$SCORING_LABEL" 2>/dev/null | sed 's/^/  /'
    else
        echo "  Status: NOT LOADED"
    fi

    echo ""
    echo "Daily indicators ($INDICATORS_LABEL):"
    if launchctl list 2>/dev/null | grep -q "$INDICATORS_LABEL"; then
        echo "  Status: LOADED"
        launchctl list "$INDICATORS_LABEL" 2>/dev/null | sed 's/^/  /'
    else
        echo "  Status: NOT LOADED"
    fi

    echo ""
    echo "Monthly Discovery ($DISCOVERY_LABEL):"
    if launchctl list 2>/dev/null | grep -q "$DISCOVERY_LABEL"; then
        echo "  Status: LOADED"
        launchctl list "$DISCOVERY_LABEL" 2>/dev/null | sed 's/^/  /'
    else
        echo "  Status: NOT LOADED"
    fi
}

run_now() {
    local target=${1:-scoring}

    case "$target" in
        scoring)
            echo "Running weekly dimension scoring..."
            launchctl start "$SCORING_LABEL"
            echo "Started. Check logs at: $SCRIPT_DIR/../logs/"
            ;;
        indicators)
            echo "Running daily indicators pipeline..."
            launchctl start "$INDICATORS_LABEL"
            echo "Started. Check logs at: $SCRIPT_DIR/../logs/"
            ;;
        discovery)
            echo "Running monthly discovery pipeline..."
            echo "Note: Discovery uses Cursor Agent and may take several minutes."
            launchctl start "$DISCOVERY_LABEL"
            echo "Started. Check logs at: $SCRIPT_DIR/../logs/"
            ;;
        *)
            echo "Unknown job: $target"
            echo "Use: $0 run [scoring|indicators|discovery]"
            exit 1
            ;;
    esac
}

case "${1:-}" in
    install)
        install "${2:-all}"
        ;;
    uninstall)
        uninstall "${2:-all}"
        ;;
    status)
        status
        ;;
    run)
        run_now "${2:-scoring}"
        ;;
    *)
        usage
        ;;
esac
