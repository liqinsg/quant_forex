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
  status         Show status (pids/<mode>.pid + ./deploy.sh status)

Flags:
  --dry-run      Override: set DRY_RUN=true (no real orders sent)
  --live         Enable live-mode thresholds (MIN_GAP/ALIGN/CORE rules)

Examples:
  ./start_trader.sh original
  ./start_trader.sh aggressive --dry-run
  ./start_trader.sh status
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

# 各 profile 的状态：以本脚本自己的 pids/<mode>.pid 为准
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
        if kill -0 "${pid}" 2>/dev/null; then
            echo "✅ 🟢 ${suffix}  运行中 PID: ${pid}"
            running=1
        else
            echo "⚠️  ⚪ ${suffix}  未运行 (PID文件存在但进程消失: ${pid})"
        fi
    done
    [[ ${running} -eq 1 ]] || echo "   （当前没有运行中的交易实例）"
    echo "────────────────────────────────────────────────────────────"
}

# 再打一份 deploy.sh 概览（周守护 / 模型 / 持仓）。
# 注意: deploy.sh 里的「主循环」只认 reports/bot.pid, 与上面的 pids/*.pid 不是同一套记录。
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