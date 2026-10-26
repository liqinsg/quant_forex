#!/usr/bin/env python3
import time
import os
import datetime
import logging

SHARED = os.path.expanduser("~/forex_shared")
LOG_FILE = os.path.join(SHARED, "reports", "bot.log")
HEARTBEAT_LOCAL = os.path.expanduser("~/forex_alive.log")
MAX_SILENCE_HRS = 2
CHECK_INTERVAL = 600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[logging.FileHandler(HEARTBEAT_LOCAL), logging.StreamHandler()]
)
log = logging.getLogger()

def check_master():
    if not os.path.exists(LOG_FILE):
        log.warning("❌ 共享未就绪或文件不存在")
        return False, "mount_missing"
    mtime = os.path.getmtime(LOG_FILE)
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
    except:
        pass

if __name__ == "__main__":
    log.info("🟢 保活+监控启动")
    while True:
        net_heartbeat()
        check_master()
        time.sleep(CHECK_INTERVAL)
