#!/usr/bin/env python3
import time
import os
import datetime
import logging

SHARED = os.path.expanduser("~/forex_shared")

# 智能找 reports：优先根目录/reports，没有就试 forex_oanda/reports
POSSIBLE_LOG_PATHS = [
    os.path.join(SHARED, "reports", "bot.log"),                  # ✅ 标准位置
    os.path.join(SHARED, "forex_oanda", "reports", "bot.log"),   # 备选位置
]

HEARTBEAT_LOCAL = os.path.expanduser("~/forex_alive.log")
MAX_SILENCE_HRS = 2
CHECK_INTERVAL = 600

os.makedirs(os.path.dirname(HEARTBEAT_LOCAL), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[logging.FileHandler(HEARTBEAT_LOCAL), logging.StreamHandler()]
)
log = logging.getLogger()

def find_bot_log():
    """自动找到 bot.log 真实位置"""
    for path in POSSIBLE_LOG_PATHS:
        dir_path = os.path.dirname(path)
        if os.path.exists(dir_path):
            if os.path.exists(path):
                return path, "found"
            else:
                return dir_path, "dir_exists_no_file"
    return None, "not_found"

def check_master():
    path, status = find_bot_log()
    
    if status == "not_found":
        log.info("⏳ 等待高配机首次运行生成目录...")
        return False, "waiting_dir"
    
    if status == "dir_exists_no_file":
        log.info(f"⏳ 目录就绪，等待 bot.log 首次写入...")
        return False, "waiting_first_log"
    
    # 找到日志，检查更新时间
    mtime = os.path.getmtime(path)
    elapsed = (time.time() - mtime) / 3600
    
    if elapsed < MAX_SILENCE_HRS:
        log.info(f"✅ 高配机正常 — 最后活动: {elapsed:.1f}小时前")
        return True, "ok"
    else:
        log.warning(f"⚠️ 高配机静默: {elapsed:.1f}小时无更新")
        return False, "stale"

def net_heartbeat():
    try:
        import urllib.request
        urllib.request.urlopen("https://cloud.oracle.com", timeout=8)
    except Exception:
        pass

if __name__ == "__main__":
    log.info("🟢 保活+监控启动")
    while True:
        net_heartbeat()
        check_master()
        time.sleep(CHECK_INTERVAL)
