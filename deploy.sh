#!/bin/bash
set -euo pipefail
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
log_info() { echo -e "${GREEN}✅ $*${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $*${NC}"; }
log_err() { echo -e "${RED}❌ $*${NC}"; }

check_python() {
    command -v python3 &>/dev/null || { log_err "Install Python 3.9+ first"; exit 1; }
    log_info "Python: $(python3 --version)"
}

install_sys_deps() {
    if [[ "$(uname)" == Linux && -f /etc/debian_version ]]; then
        log_info "Installing TA-Lib system libs..."
        sudo apt update -qq && sudo apt install -y -qq libta-lib-dev
    fi
}

setup_venv() {
    [[ -d .venv ]] || python3 -m venv .venv
    source .venv/bin/activate
}

install_python_deps() {
    pip install --upgrade pip -q
    pip install -r requirements.txt
}

setup_dirs() {
    mkdir -p data/practice/datasets data/live/datasets data/common \
             models/model_store/practice models/model_store/live reports
}

setup_env() {
    if [[ ! -f config/.env ]]; then
        cp config/.env.example config/.env
        log_warn "Created config/.env — edit with your OANDA credentials!"
    fi
}

# 选择解释器：.venv 装了依赖就用它，否则沿用当前 PATH 的 python（如 conda 环境）
PY_BIN=""
use_python() {
    if [[ -x .venv/bin/python ]] && .venv/bin/python -c "import yaml, pandas, lightgbm" &>/dev/null; then
        PY_BIN="$PWD/.venv/bin/python"
        log_info "Python: $PY_BIN (.venv)"
    else
        PY_BIN="$(command -v python || command -v python3 || true)"
        [[ -n "$PY_BIN" ]] || { log_err "No python found"; exit 1; }
        log_warn "跳过空的 .venv，使用当前环境: $PY_BIN"
    fi
}

train_all() {
    use_python
    local pairs total i
    pairs=$("$PY_BIN" -c "from config.pairs import get_instruments; print(' '.join(get_instruments()))")
    total=$(echo "$pairs" | wc -w)
    log_info "开始训练 $total 个货币对（串行执行，耗时较长；Ctrl-C 可中断，已完成的模型会保留）"
    i=0
    for inst in $pairs; do
        i=$((i+1))
        log_info "Training $inst ... ($i/$total)"
        "$PY_BIN" models/train_lgb_signal.py "$inst"
    done
    log_info "All trained ✅ ($total/$total)"
}

BOT_PID=reports/bot.pid
WEEKLY_PID=reports/weekly_train.pid
LAST_RETRAIN=reports/.last_weekly_retrain

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

start_bot() {
    use_python
    if pid_alive "$BOT_PID"; then log_warn "主循环已在运行: PID $(cat "$BOT_PID")"; return; fi
    rm -f "$BOT_PID"
    mkdir -p reports
    nohup "$PY_BIN" main_loop_v2.py > reports/bot_console.out 2>&1 &
    echo $! > "$BOT_PID"
    log_info "主循环已启动 — PID $(cat "$BOT_PID")"
}

start_weekly() {
    use_python
    if pid_alive "$WEEKLY_PID"; then log_warn "周守护已在运行: PID $(cat "$WEEKLY_PID")"; return; fi
    rm -f "$WEEKLY_PID"
    mkdir -p reports
    nohup "$PY_BIN" weekly_train_daemon.py > reports/weekly_console.out 2>&1 &
    echo $! > "$WEEKLY_PID"
    log_info "周守护已启动 — PID $(cat "$WEEKLY_PID")"
}

stop_all() {
    local stopped=0
    if pid_alive "$BOT_PID"; then kill "$(cat "$BOT_PID")" 2>/dev/null || true; stopped=1; fi
    rm -f "$BOT_PID"
    if pid_alive "$WEEKLY_PID"; then kill "$(cat "$WEEKLY_PID")" 2>/dev/null || true; stopped=1; fi
    rm -f "$WEEKLY_PID"
    if [[ $stopped -eq 1 ]]; then log_info "已停止 主循环 + 周守护"; else log_warn "无运行中的进程"; fi
}

status_all() {
    local ts age ts_epoch
    if pid_alive "$BOT_PID"; then
        log_info "🟢 主循环运行中 (PID $(cat "$BOT_PID"))"
    else
        log_warn "⚪ 主循环未运行"
    fi
    if pid_alive "$WEEKLY_PID"; then
        log_info "🟢 周守护运行中 (PID $(cat "$WEEKLY_PID"))"
    else
        log_warn "⚪ 周守护未运行"
    fi
    if [[ -f "$LAST_RETRAIN" ]]; then
        ts=$(head -n1 "$LAST_RETRAIN")
        if ts_epoch=$(date -d "$ts" +%s 2>/dev/null); then
            age=$(( ( $(date +%s) - ts_epoch ) / 86400 ))
            log_info "模型上次更新: $ts (${age}天前)"
            if [[ $age -gt 7 ]]; then log_warn "⚠️ 距上次更新: ${age}天 (建议 ≤7天)"; fi
        else
            log_warn "无法解析更新时间: $ts"
        fi
    else
        log_warn "尚无周度更新记录 ($LAST_RETRAIN)"
    fi
}

retrain_now() {
    use_python
    log_info "立即执行一次全量更新 (retrain-now) ..."
    local rc=0
    set +e
    "$PY_BIN" weekly_train_daemon.py --once
    rc=$?
    set -e
    case $rc in
        0) log_info  "retrain-now: 全部成功 (0)" ;;
        1) log_warn  "retrain-now: 部分失败 (1) — 详见 reports/weekly_train.log" ;;
        2) log_err   "retrain-now: 全部失败 (2) — 详见 reports/weekly_train.log" ;;
        *) log_err   "retrain-now: 异常退出码 $rc" ;;
    esac
    return $rc
}

show_menu() {
    echo ""
    echo "=== Forex Bot v6.8x ==="
    echo "Usage:"
    echo "  ./deploy.sh init         → Full setup"
    echo "  ./deploy.sh deps         → Reinstall deps"
    echo "  ./deploy.sh train        → Train all (foreground)"
    echo "  ./deploy.sh start        → Foreground bot run"
    echo "  ./deploy.sh daemon       → Start both: bot + weekly trainer"
    echo "  ./deploy.sh stop         → Stop both"
    echo "  ./deploy.sh restart      → Restart both"
    echo "  ./deploy.sh status       → Both processes + last model update"
    echo "  ./deploy.sh retrain-now  → Run one full retrain now"
}

case "${1:-init}" in
    init) check_python; install_sys_deps; setup_venv; install_python_deps; setup_dirs; setup_env; show_menu ;;
    deps) setup_venv; install_python_deps ;;
    train) train_all ;;
    start) use_python; "$PY_BIN" main_loop_v2.py ;;
    daemon) start_bot; start_weekly ;;
    stop) stop_all ;;
    restart) stop_all; start_bot; start_weekly ;;
    status) status_all ;;
    retrain-now) retrain_now ;;
    *) echo "Usage: $0 [init|deps|train|start|daemon|stop|restart|status|retrain-now]" ;;
esac