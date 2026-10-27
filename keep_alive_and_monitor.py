#!/usr/bin/env python3
# keep_alive_and_monitor.py
import time
import os
import datetime
import logging
from pathlib import Path

SHARED = os.path.expanduser("~/forex_shared")

# 适配新日志系统：优先按日期找最新 fx_bot_*.log，兼容旧路径
POSSIBLE_LOG_DIRS = [
    os.path.join(SHARED, "logs"),                  # ✅ 新位置：按日期轮转
    os.path.join(SHARED, "reports"),              # 兼容旧位置
    os.path.join(SHARED, "forex_oanda", "reports"),  # 备选
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


def find_latest_bot_log():
    """智能定位：优先找当天/最新的 fx_bot_YYYYMMDD.log，兼容旧 bot.log"""
    today = datetime.date.today().strftime("%Y%m%d")
    
    for base_dir in POSSIBLE_LOG_DIRS:
        if not os.path.isdir(base_dir):
            continue
        
        # 1. 优先当天新日志
        new_path = os.path.join(base_dir, f"fx_bot_{today}.log")
        if os.path.exists(new_path):
            return new_path, "new_format"
        
        # 2. 找目录里最新的 fx_bot_*.log
        try:
            candidates = sorted(
                Path(base_dir).glob("fx_bot_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if candidates:
                return str(candidates[0]), "latest_new"
        except Exception:
            pass
        
        # 3. 兼容旧 bot.log
        old_path = os.path.join(base_dir, "bot.log")
        if os.path.exists(old_path):
            return old_path, "legacy"
    
    return None, "not_found"


def check_master():
    path, status = find_latest_bot_log()
    
    if status == "not_found":
        log.info("⏳ 等待高配机首次运行生成日志...")
        return False, "waiting_dir"
    
    # 检查更新时间
    mtime = os.path.getmtime(path)
    elapsed = (time.time() - mtime) / 3600
    
    if elapsed < MAX_SILENCE_HRS:
        log.info(f"✅ 高配机正常 [{status}] — 最后活动: {elapsed:.1f}小时前 | 日志: {os.path.basename(path)}")
        return True, "ok"
    else:
        log.warning(f"⚠️ 高配机静默 [{status}]: {elapsed:.1f}小时无更新")
        return False, "stale"


def net_heartbeat():
    try:
        import urllib.request
        urllib.request.urlopen("https://cloud.oracle.com", timeout=8)
    except Exception:
        pass


if __name__ == "__main__":
    log.info("🟢 保活+监控启动（已适配新日志系统）")
    while True:
        net_heartbeat()
        check_master()
        time.sleep(CHECK_INTERVAL)