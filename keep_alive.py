#!/usr/bin/env python3
import time
import datetime
import os

# Lightweight disk write + optional: ping the master host / internet to keep the network active
LOG_FILE = os.path.join(os.path.dirname(__file__), "alive.log")
INTERVAL = 600  # every 10 minutes is enough

def heartbeat():
    while True:
        t = datetime.datetime.now().isoformat()
        # Write to disk: proves the process/filesystem is alive
        with open(LOG_FILE, "a") as f:
            f.write(f"{t} — alive\n")
        # Optional: lightweight network heartbeat (prevents the link going idle)
        try:
            import urllib.request
            urllib.request.urlopen("https://www.google.com", timeout=10)
        except:
            pass
        time.sleep(INTERVAL)

if __name__ == "__main__":
    print("Keep-alive daemon started...")
    heartbeat()
