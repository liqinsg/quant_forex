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
    local env="practice" live_flag=""
    if [[ "${1:-}" == "--live" ]]; then
        env="live"
        live_flag="--live"
        log_info "🔄 训练环境: LIVE → models/model_store/live/"
    else
        log_info "🔄 训练环境: PRACTICE → models/model_store/practice/"
    fi

    local total
    total=$(OANDA_ENV="$env" "$PY_BIN" -c "from config.pairs import get_all_instruments; print(len(get_all_instruments()))")
    log_info "开始训练 $total 个品种（环境: $env，串行执行，耗时较长；Ctrl-C 可中断）"

    # 关键：先 export，再调用，确保脚本拿到最新值；--live 也显式透传给脚本（双保险，
    # 脚本会在 import config 之前把 OANDA_ENV 写死，覆盖 .env/run.env 里的 practice）
    export OANDA_ENV="$env"
    "$PY_BIN" models/train_lgb_signal.py ALL $live_flag

    log_info "✅ All trained → models/model_store/$env/ ($total/$total)"
}

# BOT_PID=reports/bot.pid
# WEEKLY_PID=reports/weekly_train.pid
# LAST_RETRAIN=reports/.last_weekly_retrain
# 文件路径常量
BOT_PID=reports/bot.pid
WEEKLY_PID=reports/weekly_train.pid
LAST_RETRAIN=reports/.last_weekly_retrain

# 兼容别名（增强版用）
PID_FILE="$BOT_PID"
WEEKLY_PID_FILE="$WEEKLY_PID"
MODEL_DIR=models/model_store
RUN_ENV_FILE=config/run.env

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

start_bot() {
    use_python
    if pid_alive "$BOT_PID"; then log_warn "主循环已在运行: PID $(cat "$BOT_PID")"; return; fi
    rm -f "$BOT_PID"
    mkdir -p reports
    rm -f reports/bot.runtime      # 清掉上次残留，避免新进程启动前误显示旧状态
    nohup "$PY_BIN" main_loop_v2.py "$@" > reports/bot_console.out 2>&1 &
    echo $! > "$BOT_PID"
    # 等待主循环写入运行时状态（最多 ~10s），让紧跟其后的 status 立即读到真实环境/账号
    local _i
    for _i in $(seq 1 20); do
        [[ -f reports/bot.runtime ]] && break
        sleep 0.5
    done
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

cmd_status() {
    echo "============================================================"
    echo "  $(basename "$PWD")"
    echo "============================================================"

    local running=0

    # ---------- 主循环 ----------
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" >/dev/null 2>&1; then
            running=1
            local etime=$(ps -p "$pid" -o etime= 2>/dev/null | sed 's/^ *//')
            local start=$(ps -p "$pid" -o lstart= 2>/dev/null | sed 's/^ *//')
            local env_info="practice"
            local acc_name="PRACTICE"
            local acc_id=""
            local rt_file="reports/bot.runtime"
            if [[ -f "$rt_file" ]]; then
                # 优先读取主循环启动时写入的真实运行态（CLI --live/-a 会覆盖 run.env 缺省）
                local rt_env=$(grep "^OANDA_ENV=" "$rt_file" 2>/dev/null | head -1 | cut -d'=' -f2)
                [[ -n "$rt_env" ]] && env_info="$rt_env"
                acc_id=$(grep "^OANDA_ACCOUNT_ID=" "$rt_file" 2>/dev/null | head -1 | cut -d'=' -f2)
                [[ "$env_info" == "live" ]] && acc_name="LIVE" || acc_name="PRACTICE"
            elif [[ -f "$RUN_ENV_FILE" ]]; then
                # 回退：老进程无 runtime 文件时按 run.env 缺省展示
                env_line=$(grep "^OANDA_ENV=" "$RUN_ENV_FILE" 2>/dev/null | cut -d'=' -f2)
                [[ -n "$env_line" ]] && env_info="$env_line"
                if [[ "$env_info" == "live" ]]; then
                    acc_id=$(grep "^OANDA_ACCOUNT_ID_LIVE=" "$RUN_ENV_FILE" 2>/dev/null | cut -d'=' -f2)
                    acc_name="LIVE"
                else
                    acc_id=$(grep "^OANDA_ACCOUNT_ID=" "$RUN_ENV_FILE" 2>/dev/null | cut -d'=' -f2)
                    acc_name="PRACTICE"
                fi
                # 去掉可能的引号
                acc_id=$(echo "$acc_id" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
            fi
            # 交易模式：优先运行时实际取值，回退 run.env 的 TRADE_MODE（CLI 覆盖 run.env）
            local trade_mode=""
            if [[ -f "$rt_file" ]]; then
                trade_mode=$(grep "^TRADE_MODE=" "$rt_file" 2>/dev/null | head -1 | cut -d'=' -f2) || true
            fi
            if [[ -z "$trade_mode" && -f "$RUN_ENV_FILE" ]]; then
                trade_mode=$(grep "^TRADE_MODE=" "$RUN_ENV_FILE" 2>/dev/null | tail -1 | cut -d'=' -f2) || true
            fi
            trade_mode="${trade_mode//\"/}"; trade_mode="${trade_mode//\'/}"; trade_mode="${trade_mode// /}"
            [[ -n "$trade_mode" ]] || trade_mode="forex"
            local mode_label
            case "$trade_mode" in
                crypto)       mode_label="crypto only" ;;
                forex-crypto) mode_label="forex + crypto" ;;
                *)            mode_label="forex only" ;;
            esac
            echo "✅ 🟢 主循环  运行中 PID: $pid"
            echo "   环境: $env_info"
            echo "   账号: $acc_name | $acc_id"
            echo "   交易模式: $mode_label"
            echo "   启动: $start"
            echo "   已运行: $etime"
        else
            echo "⚠️  ⚪ 主循环  未运行 (PID文件存在但进程消失)"
        fi
    else
        echo "⚠️  ⚪ 主循环  未启动"
    fi

    # ---------- 周守护 ----------
    if [[ -f "$WEEKLY_PID_FILE" ]]; then
        local wpid=$(cat "$WEEKLY_PID_FILE")
        if ps -p "$wpid" >/dev/null 2>&1; then
            local w_etime=$(ps -p "$wpid" -o etime= 2>/dev/null | sed 's/^ *//')
            local w_start=$(ps -p "$wpid" -o lstart= 2>/dev/null | sed 's/^ *//')
            echo "✅ 🟢 周守护  运行中 PID: $wpid"
            echo "   启动: $w_start"
            echo "   已运行: $w_etime"
        else
            echo "⚠️  ⚪ 周守护  未运行 (PID文件存在但进程消失)"
        fi
    else
        echo "⚠️  ⚪ 周守护  未启动"
    fi

    # ---------- 模型 ----------
    if [[ -d "$MODEL_DIR" ]]; then
        local mtime_full=$(find "$MODEL_DIR" -name "*.pkl" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1)
        local mtime_sec=${mtime_full%% *}   # 去掉文件名
        local mtime_int=${mtime_sec%.*}    # 只取整数部分，去掉小数点
        if [[ -n "$mtime_int" ]]; then
            local mtime_str=$(date -d "@$mtime_int" +"%Y-%m-%d %H:%M:%S")
            local now=$(date +%s)
            local age_sec=$((now - mtime_int))
            local age_days=$((age_sec / 86400))
            local age_hours=$(((age_sec % 86400) / 3600))
            local age_mins=$(((age_sec % 3600) / 60))
            echo "✅ 模型目录: $MODEL_DIR"
            echo "   最后训练: $mtime_str"
            echo "   距今: ${age_days}天 ${age_hours}小时 ${age_mins}分钟"
        fi
    fi

    echo "============================================================"
    return $running
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
    echo "  ./deploy.sh train        → Train all forex + crypto → model_store/practice"
    echo "  ./deploy.sh train --live → Train all forex + crypto → model_store/live"
    echo "  ./deploy.sh start        → Foreground bot run"
    echo "  ./deploy.sh daemon       → Start both: bot + weekly trainer"
    echo "  ./deploy.sh stop         → Stop both"
    echo "  ./deploy.sh restart      → Restart both"
    echo "  ./deploy.sh status       → Both processes + last model update"
    echo "  ./deploy.sh retrain-now  → Run one full retrain now"
    echo ""
    echo "  start/daemon/restart 可透传主循环参数，例如:"
    echo "    ./deploy.sh daemon --live -a 2 --lots 1"
    echo "    ./deploy.sh daemon --live -a 2 --forex           # 只交易外汇（默认）"
    echo "    ./deploy.sh daemon --live -a 2 --crypto          # 只交易加密"
    echo "    ./deploy.sh daemon --live -a 2 --forex-crypto    # 外汇+加密"
    echo "    ./deploy.sh daemon --live -a 2 -c --crypto-lots 0.01  # 仅加密并覆盖手数"
    echo "    (-f/--forex 仅外汇 | -c/--crypto 仅加密 | -b/--forex-crypto 两者 |"
    echo "     --crypto-lots N 加密手数 | 未指定时以 run.env 的 TRADE_MODE 为准)"
}

case "${1:-init}" in
    init) check_python; install_sys_deps; setup_venv; install_python_deps; setup_dirs; setup_env; show_menu ;;
    deps) setup_venv; install_python_deps ;;
    train) train_all "${@:2}" ;;
    start) use_python; "$PY_BIN" main_loop_v2.py "${@:2}" ;;
    daemon) start_bot "${@:2}"; start_weekly ;;
    stop) stop_all ;;
    restart) stop_all; start_bot "${@:2}"; start_weekly ;;
    status) cmd_status ;;
    status_all) status_all ;;
    retrain-now) retrain_now ;;
    *) echo "Usage: $0 [init|deps|train|start|daemon|stop|restart|status|retrain-now]" ;;
esac