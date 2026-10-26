#!/usr/bin/env python3
import time
import datetime
import os

# 轻量写盘 + 可选：ping高配机/外网保网络活跃
LOG_FILE = os.path.join(os.path.dirname(__file__), "alive.log")
INTERVAL = 600  # 10分钟一次，足够了

def heartbeat():
    while True:
        t = datetime.datetime.now().isoformat()
        # 写盘：证明进程/文件系统活跃
        with open(LOG_FILE, "a") as f:
            f.write(f"{t} — alive\n")
        # 可选：轻量网络心跳（防止网络 idle）
        try:
            import urllib.request
            urllib.request.urlopen("https://www.google.com", timeout=10)
        except:
            pass
        time.sleep(INTERVAL)

if __name__ == "__main__":
    print("Keep-alive daemon started...")
    heartbeat()
