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
    mkdir -p data/datasets models/model_store reports
}

setup_env() {
    if [[ ! -f .env ]]; then
        cp .env.example .env
        log_warn "Created .env — edit with your OANDA credentials!"
    fi
}

train_all() {
    source .venv/bin/activate
    for inst in EUR_USD GBP_USD USD_JPY; do
        log_info "Training $inst..."
        python models/train_lgb_signal.py "$inst"
    done
    log_info "All trained ✅"
}

start_daemon() {
    source .venv/bin/activate
    [[ -f bot.pid ]] && { log_warn "Running: PID $(cat bot.pid)"; return; }
    nohup python main_loop_v2.py > reports/nohup.out 2>&1 &
    echo $! > bot.pid
    log_info "Daemon started — PID $(cat bot.pid)"
}

stop_daemon() {
    [[ -f bot.pid ]] && { kill $(cat bot.pid) 2>/dev/null; rm -f bot.pid; log_info "Stopped"; } || log_warn "Not running"
}

show_menu() {
    echo ""
    echo "=== Forex Bot v6.8x ==="
    echo "Usage:"
    echo "  ./deploy.sh init    → Full setup"
    echo "  ./deploy.sh deps    → Reinstall deps"
    echo "  ./deploy.sh train   → Train all"
    echo "  ./deploy.sh start    → Foreground run"
    echo "  ./deploy.sh daemon   → Background run"
    echo "  ./deploy.sh stop     → Stop background"
    echo "  ./deploy.sh status   → Check status"
}

case "${1:-init}" in
    init) check_python; install_sys_deps; setup_venv; install_python_deps; setup_dirs; setup_env; show_menu ;;
    deps) setup_venv; install_python_deps ;;
    train) train_all ;;
    start) source .venv/bin/activate; python main_loop_v2.py ;;
    daemon) start_daemon ;;
    stop) stop_daemon ;;
    status) [[ -f bot.pid ]] && echo "PID $(cat bot.pid)" || echo "Not running" ;;
    *) echo "Usage: $0 [init|deps|train|start|daemon|stop|status]" ;;
esac