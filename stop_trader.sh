#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${PROJECT_ROOT}/pids"

usage() {
    cat << EOF
Usage: ./stop_trader.sh <mode>

Modes:
  original | aggressive | conservative
  all — stop all three running instances
EOF
    exit 1
}

stop_one() {
    local suffix="$1"
    local PID_FILE="${PID_DIR}/${suffix}.pid"

    if [[ ! -f "${PID_FILE}" ]]; then
        echo "ℹ️  ${suffix} not running (no PID file)"
        return 0
    fi

    local PID
    PID=$(<"${PID_FILE}")

    if ! kill -0 "${PID}" 2>/dev/null; then
        echo "ℹ️  ${suffix} PID ${PID} already dead"
        rm -f "${PID_FILE}"
        return 0
    fi

    echo "⏹️  Stopping ${suffix} — PID ${PID}"
    kill "${PID}" || true
    sleep 2

    if kill -0 "${PID}" 2>/dev/null; then
        echo "⚠️  Force-kill ${suffix} — PID ${PID}"
        kill -9 "${PID}" || true
    fi

    rm -f "${PID_FILE}"
    echo "✅ ${suffix} stopped"
}

[[ $# -lt 1 ]] && usage

case "$1" in
    original|aggressive|conservative)
        stop_one "$1"
        ;;
    all)
        stop_one original
        stop_one aggressive
        stop_one conservative
        ;;
    *)
        echo "❌ Unknown mode: $1"
        usage
        ;;
esac