#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${PROJECT_ROOT}/pids"
LOG_DIR="${PROJECT_ROOT}/logs"

# Colors
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
BLUE='\033[1;34m'
GRAY='\033[0;90m'
NC='\033[0m'

get_uptime() {
    local pid="$1"
    local start_time
    start_time=$(ps -p "${pid}" -o lstart= 2>/dev/null) || return 1
    local start_epoch=$(date -d "${start_time}" +%s 2>/dev/null) || return 1
    local now_epoch=$(date +%s)
    local diff=$(( now_epoch - start_epoch ))
    local days=$(( diff/86400 ))
    local hrs=$(( (diff%86400)/3600 ))
    local mins=$(( (diff%3600)/60 ))
    if (( days > 0 )); then echo "${days}d ${hrs}h ${mins}m";
    elif (( hrs > 0 )); then echo "${hrs}h ${mins}m";
    else echo "${mins}m"; fi
}

check_one() {
    local suffix="$1"
    local PID_FILE="${PID_DIR}/${suffix}.pid"
    local STATUS="${RED}STOPPED${NC}"
    local PID="-"
    local UP="-"
    local LATEST_LOG="-"

#    if [[ -f "${PID_FILE}" ]]; then
#        PID=$(<"${PID_FILE}")
#        if kill -0 "${PID}" 2>/dev/null; then
#            STATUS="${GREEN}RUNNING${NC}"
#            UP=$(get_uptime "${PID}")
#        else
#            STATUS="${YELLOW}DEAD${NC}"
#        fi
#    fi

    if [[ -f "${PID_FILE}" ]]; then
        PID=$(<"${PID_FILE}")
        if kill -0 "${PID}" 2>/dev/null; then
            STATUS="${GREEN}RUNNING${NC}"
            UP=$(get_uptime "${PID}")
        else
            STATUS="${YELLOW}DEAD — cleaned${NC}"
            rm -f "${PID_FILE}"
        fi
    fi


    # Latest log file
    local LOG_PATH="${LOG_DIR}/${suffix}"
    if [[ -d "${LOG_PATH}" && -n "$(ls -A "${LOG_PATH}"/runner_*.log 2>/dev/null)" ]]; then
        LATEST_LOG=$(basename "$(ls -t "${LOG_PATH}"/runner_*.log | head -n1)")
    fi

    printf "%-15b %-12b %-8s %-12s %-35b\n" \
        "[${suffix}]" "${STATUS}" "${PID}" "${UP}" "${GRAY}${LATEST_LOG}${NC}"
}

echo -e "${BLUE}=========================================================${NC}"
echo -e "${BLUE}  Forex OANDA v7 — Instance Status Overview${NC}"
echo -e "${BLUE}=========================================================${NC}"
printf "%-18s %-12s %-8s %-12s %-35s\n" \
    "MODE" "STATUS" "PID" "UPTIME" "LATEST LOG"
echo -e "---------------------------------------------------------"

check_one "original"
check_one "aggressive"
check_one "conservative"

echo -e "${BLUE}=========================================================${NC}"
echo -e "Root: ${PROJECT_ROOT}"
echo -e "Logs: ${LOG_DIR}/{original,aggressive,conservative}/"
echo -e "PIDs: ${PID_DIR}/"
echo -e "${BLUE}=========================================================${NC}"
