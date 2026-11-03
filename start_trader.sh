#!/usr/bin/env bash
set -euo pipefail

# ==========================================================
# Forex OANDA v7 — Unified Launcher 【FIXED】
# Fixes: PID capture, stale PID cleanup, log rotation, status validation
# ==========================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${PROJECT_ROOT}/config"
ENV_TPL="run.env"
PID_DIR="${PROJECT_ROOT}/pids"
LOG_DIR="${PROJECT_ROOT}/logs"

# Runtime dirs
mkdir -p "${PID_DIR}" "${LOG_DIR}/original" "${LOG_DIR}/aggressive" "${LOG_DIR}/conservative"

# ─── Configurable Retention ───
MAX_LOGS_PER_MODE=10   # Keep last N log files per mode
CHECK_PROCESS_NAME="python"  # Validate by process name too

usage() {
    cat << EOF
Usage: ./start_trader.sh <mode> [--dry-run] [--live]

Modes:
  original       (-o)  Start with run.env_original
  aggressive     (-a)  Start with run.env_aggressive
  conservative   (-c)  Start with run.env_conservative
  status         Show full status

Flags:
  --dry-run      Override: DRY_RUN=true
  --live         Enable live-mode thresholds
EOF
    exit 1
}

validate_env() {
    local suffix="$1"
    local f="${CONFIG_DIR}/${ENV_TPL}_${suffix}"
    [[ -f "${f}" ]] || { echo "❌ Missing env: ${f}"; exit 1; }
}

# ─── NEW: Dual-check PID + process name ───
is_process_running() {
    local pid="$1"
    local suffix="$2"
    # 1. PID exists
    [[ -d /proc/${pid} ]] || return 1
    # 2. Command line matches expected process
    local cmdline
    cmdline=$(cat /proc/${pid}/cmdline 2>/dev/null | tr '\0' ' ')
    [[ "${cmdline}" == *"${CHECK_PROCESS_NAME}"* && "${cmdline}" == *"main_loop"* ]] && return 0
    return 2  # PID reused or wrong process
}

# ─── NEW: Log rotation ───
rotate_logs() {
    local suffix="$1"
    local mode_log_dir="${LOG_DIR}/${suffix}"
    mkdir -p "${mode_log_dir}"
    # Keep only newest MAX_LOGS_PER_MODE, delete older
    ls -t "${mode_log_dir}"/runner_*.log 2>/dev/null | tail -n +$((MAX_LOGS_PER_MODE + 1)) | xargs -r rm -f
}

launch_one() {
    local suffix="$1"
    shift

    local ENV_FILE="${CONFIG_DIR}/${ENV_TPL}_${suffix}"
    local PID_FILE="${PID_DIR}/${suffix}.pid"
    local LOG_FILE="${LOG_DIR}/${suffix}/runner_$(date +%Y%m%d_%H%M%S).log"

    validate_env "${suffix}"
    rotate_logs "${suffix}"  # ✅ Auto-clean before start

    # ─── Check & clean stale PID ───
    if [[ -f "${PID_FILE}" ]]; then
        local OLD_PID
        OLD_PID=$(<"${PID_FILE}")
        if is_process_running "${OLD_PID}" "${suffix}"; then
            echo "⚠️  ${suffix} already running (PID ${OLD_PID}) — skip"
            return 0
        else
            echo "🧹 Clean stale PID file: ${OLD_PID}"
            rm -f "${PID_FILE}"
        fi
    fi

    echo "▶️  Starting [${suffix}] — ${ENV_FILE}"
    echo "   Log: ${LOG_FILE}"

    # ─── FIXED: Capture REAL child PID, not subshell ───
    local DRY_RUN_FLAG=false
    local LIVE_MODE=false
    [[ " $* " == *"--dry-run"* ]] && DRY_RUN_FLAG=true
    [[ " $* " == *"--live"* ]] && LIVE_MODE=true

    # Launch in background, capture Python PID directly
    nohup bash -c "
        set -a
        source '${ENV_FILE}'
        DRY_RUN=${DRY_RUN_FLAG}
        LIVE_MODE=${LIVE_MODE}
        cd '${PROJECT_ROOT}'
        exec python3 -u main_loop_v2.py $@
    " >> "${LOG_FILE}" 2>&1 &

    local NEW_PID=$!
    echo "${NEW_PID}" > "${PID_FILE}"

    # Verify it actually started
    sleep 1
    if is_process_running "${NEW_PID}" "${suffix}"; then
        echo "✅ [${suffix}] started — PID ${NEW_PID}"
    else
        echo "❌ Start failed! Check log: ${LOG_FILE}"
        rm -f "${PID_FILE}"
        exit 1
    fi
}

show_status() {
    echo "────────────────────────────────────────────────────────────"
    echo "  交易实例状态  (来源: ${PID_DIR}/<mode>.pid)"
    echo "────────────────────────────────────────────────────────────"
    local suffix pid_file pid running=0
    for suffix in original aggressive conservative; do
        pid_file="${PID_DIR}/${suffix}.pid"
        if [[ ! -f "${pid_file}" ]]; then
            echo "⚪ ${suffix}  未启动"
            continue
        fi
        pid=$(<"${pid_file}")
        if is_process_running "${pid}" "${suffix}"; then
            echo "✅ 🟢 ${suffix}  运行中 PID: ${pid}"
            running=1
        else
            echo "⚠️  ⚪ ${suffix}  未运行 (已清理残留 PID: ${pid})"
            rm -f "${pid_file}"
        fi
    done
    [[ ${running} -eq 1 ]] || echo "   （当前没有运行中的交易实例）"
    echo "────────────────────────────────────────────────────────────"
}

show_deploy_status() {
    echo "──── deploy.sh status（周守护 / 模型 / 持仓）────"
    "${PROJECT_ROOT}/deploy.sh" status
}

# ------------------------------
# Parse args
# ------------------------------
[[ $# -lt 1 ]] && usage

MODE="$1"
shift

case "${MODE}" in
    -o) MODE="original" ;;
    -a) MODE="aggressive" ;;
    -c) MODE="conservative" ;;
esac

case "${MODE}" in
    original|aggressive|conservative)
        launch_one "${MODE}" "$@"
        ;;
    status|--status)
        show_status
        show_deploy_status
        ;;
    *)
        echo "❌ Unknown mode: ${MODE}"
        usage
        ;;
esac