#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${PROJECT_ROOT}/pids"

MODES=(original aggressive conservative)

usage() {
    cat << EOF
Usage: ./stop_trader.sh [mode]

Modes:
  original | aggressive | conservative
  省略 mode 时: 自动停掉当前运行中的那一个实例

说明: 只做两件事 —— 停掉进程, 删除对应的 pids/<mode>.pid
EOF
    exit 1
}

pid_file_of() { printf '%s/%s.pid' "${PID_DIR}" "$1"; }
alive()       { kill -0 "$1" 2>/dev/null; }

# 停掉一个 profile: kill -> 等 2s -> 仍在则强杀 -> 删 PID 文件
stop_one() {
    local suffix="$1"
    local PID_FILE
    PID_FILE=$(pid_file_of "${suffix}")

    if [[ ! -f "${PID_FILE}" ]]; then
        echo "ℹ️  ${suffix} 未启动 (无 PID 文件)"
        return 0
    fi

    local PID
    PID=$(<"${PID_FILE}")

    if ! alive "${PID}"; then
        echo "ℹ️  ${suffix} PID ${PID} 已死, 仅清理 PID 文件"
        rm -f "${PID_FILE}"
        return 0
    fi

    echo "⏹️  停止 ${suffix} — PID ${PID}"
    kill "${PID}" 2>/dev/null || true
    sleep 2

    if alive "${PID}"; then
        echo "⚠️  仍存活, 强制结束 ${suffix} — PID ${PID}"
        kill -9 "${PID}" 2>/dev/null || true
    fi

    rm -f "${PID_FILE}"
    echo "✅ ${suffix} 已停止, PID 文件已删除"
}

# 不带 mode: 找出唯一在跑的实例并停掉, 顺带清掉死掉的残留 PID 文件
stop_current() {
    local suffix f p
    local alive_count=0 running_suffix="" running_pid=""
    local -a stale=()

    for suffix in "${MODES[@]}"; do
        f=$(pid_file_of "${suffix}")
        [[ -f "${f}" ]] || continue
        p=$(<"${f}")
        if alive "${p}"; then
            alive_count=$((alive_count + 1))
            running_suffix="${suffix}"
            running_pid="${p}"
        else
            stale+=("${suffix}")
        fi
    done

    if [[ ${alive_count} -eq 0 ]]; then
        echo "ℹ️  没有运行中的实例"
    elif [[ ${alive_count} -eq 1 ]]; then
        stop_one "${running_suffix}"
    else
        echo "⚠️  检测到多个运行中的实例, 请显式指定 mode:"
        for suffix in "${MODES[@]}"; do
            f=$(pid_file_of "${suffix}")
            [[ -f "${f}" ]] || continue
            p=$(<"${f}")
            alive "${p}" && echo "     ${suffix}  PID ${p}"
        done
        return 1
    fi

    if [[ ${#stale[@]} -gt 0 ]]; then
        for suffix in "${stale[@]}"; do
            rm -f "$(pid_file_of "${suffix}")"
        done
        echo "🧹 清理残留 PID 文件: ${stale[*]}"
    fi
}

if [[ $# -eq 0 ]]; then
    stop_current
    exit 0
fi

case "$1" in
    original|aggressive|conservative)
        stop_one "$1"
        ;;
    *)
        echo "❌ Unknown mode: $1"
        usage
        ;;
esac
