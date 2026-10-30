#!/usr/bin/env bash
set -euo pipefail

# ==========================================================
# Forex OANDA v7 — Unified Launcher
# Supports: original / aggressive / conservative / all
# Each loads its own env, logs separately, uses distinct account
# ==========================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/config"
ENV_TPL="run.env"
PID_DIR="${PROJECT_ROOT}/pids"
LOG_DIR="${PROJECT_ROOT}/logs"

# Ensure runtime dirs exist
mkdir -p "${PID_DIR}" "${LOG_DIR}/original" "${LOG_DIR}/aggressive" "${LOG_DIR}/conservative"

usage() {
    cat << EOF
Usage: ./start_trader.sh <mode> [--dry-run] [--live]

Modes:
  original       Start with run.env_original
  aggressive     Start with run.env_aggressive
  conservative   Start with run.env_conservative
  all            Start ALL THREE in parallel (separate accounts/logs/pids)

Flags:
  --dry-run      Override: set DRY_RUN=true (no real orders sent)
  --live         Enable live-mode thresholds (MIN_GAP/ALIGN/CORE rules)

Examples:
  ./start_trader.sh original
  ./start_trader.sh aggressive --dry-run
  ./start_trader.sh all --dry-run
EOF
    exit 1
}

validate_env() {
    local suffix="$1"
    local f="${CONFIG_DIR}/${ENV_TPL}_${suffix}"
    if [[ ! -f "${f}" ]]; then
        echo "❌ Missing env file: ${f}"
        exit 1
    fi
}

launch_one() {
    local suffix="$1"
    shift

    local ENV_FILE="${CONFIG_DIR}/${ENV_TPL}_${suffix}"
    local PID_FILE="${PID_DIR}/${suffix}.pid"
    local LOG_FILE="${LOG_DIR}/${suffix}/runner_$(date +%Y%m%d_%H%M%S).log"

    validate_env "${suffix}"

    # Check already running
    if [[ -f "${PID_FILE}" ]]; then
        local OLD_PID
        OLD_PID=$(<"${PID_FILE}")
        if kill -0 "${OLD_PID}" 2>/dev/null; then
            echo "⚠️  ${suffix} already running (PID ${OLD_PID}) — skip"
            return 0
        else
            rm -f "${PID_FILE}"
        fi
    fi

    echo "▶️  Starting [${suffix}] — ${ENV_FILE}"
    echo "   Log: ${LOG_FILE}"

    # Source env + launch in background
    (
        set -a
        # Load base then allow CLI overrides
        source "${ENV_FILE}"
        # Apply CLI dry-run override if passed
        if [[ " $* " == *"--dry-run"* ]]; then
            DRY_RUN=true
        fi
        set +a

        cd "${PROJECT_ROOT}"
        # --- REPLACE BOT ENTRY POINT HERE ---
        # Adjust the actual Python script name as needed
        nohup python3 -u main_loop_v2.py "$@" >> "${LOG_FILE}" 2>&1

    ) &

    local NEW_PID=$!
    echo "${NEW_PID}" > "${PID_FILE}"
    echo "✅ [${suffix}] started — PID ${NEW_PID}"
    sleep 1
}

# ------------------------------
# Parse args
# ------------------------------
[[ $# -lt 1 ]] && usage

MODE="$1"
shift

case "${MODE}" in
    original|aggressive|conservative)
        launch_one "${MODE}" "$@"
        ;;
    all)
        echo "=========================================="
        echo "🚀 STARTING ALL THREE — parallel mode"
        echo "=========================================="
        launch_one original "$@"
        launch_one aggressive "$@"
        launch_one conservative "$@"
        echo ""
        echo "✅ All launched. Check logs/ per suffix."
        echo "To stop: ./stop_trader.sh all"
        ;;
    *)
        echo "❌ Unknown mode: ${MODE}"
        usage
        ;;
esac