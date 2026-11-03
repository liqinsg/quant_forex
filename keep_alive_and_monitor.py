#!/usr/bin/env python3
# keep_alive_and_monitor.py
import time
import os
import datetime
import logging
from pathlib import Path

SHARED = os.path.expanduser("~/forex_shared")

# Adapted to the new log system: prefer today's/latest fx_bot_*.log, stay compatible with old paths
POSSIBLE_LOG_DIRS = [
    os.path.join(SHARED, "logs"),                  # ✅ new location: date-based rotation
    os.path.join(SHARED, "reports"),              # legacy location
    os.path.join(SHARED, "forex_oanda", "reports"),  # fallback
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
    """Locate the log: prefer today's/latest fx_bot_YYYYMMDD.log, fall back to legacy bot.log"""
    today = datetime.date.today().strftime("%Y%m%d")
    
    for base_dir in POSSIBLE_LOG_DIRS:
        if not os.path.isdir(base_dir):
            continue
        
        # 1. Prefer today's new-format log
        new_path = os.path.join(base_dir, f"fx_bot_{today}.log")
        if os.path.exists(new_path):
            return new_path, "new_format"
        
        # 2. Otherwise the newest fx_bot_*.log in the directory
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
        
        # 3. Legacy bot.log
        old_path = os.path.join(base_dir, "bot.log")
        if os.path.exists(old_path):
            return old_path, "legacy"
    
    return None, "not_found"


def check_master():
    path, status = find_latest_bot_log()
    
    if status == "not_found":
        log.info("⏳ Waiting for the master host's first run to produce a log...")
        return False, "waiting_dir"
    
    # Check the update time
    mtime = os.path.getmtime(path)
    elapsed = (time.time() - mtime) / 3600
    
    if elapsed < MAX_SILENCE_HRS:
        log.info(f"✅ Master host healthy [{status}] — last activity: {elapsed:.1f}h ago | log: {os.path.basename(path)}")
        return True, "ok"
    else:
        log.warning(f"⚠️ Master host silent [{status}]: no update for {elapsed:.1f}h")
        return False, "stale"


def net_heartbeat():
    try:
        import urllib.request
        urllib.request.urlopen("https://cloud.oracle.com", timeout=8)
    except Exception:
        pass


if __name__ == "__main__":
    log.info("🟢 Keep-alive + monitor started (new log system)")
    while True:
        net_heartbeat()
        check_master()
        time.sleep(CHECK_INTERVAL)