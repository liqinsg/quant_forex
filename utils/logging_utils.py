import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import time

# 1. 吃宿主机/容器的 TZ 环境变量
logging.Formatter.converter = time.localtime

TZ_NAME = os.getenv("TZ", "UTC").split("/")[-1] # Singapore

# ─── Log Directory ───
# LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR = Path.cwd() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
TZ = os.getenv("TZ")
TZ_NAME = os.getenv("TZ", "Asia/Singapore").split("/")[-1]
LOG_FILE = LOG_DIR / f"fx_bot_{datetime.now().strftime('%Y%m%d')}.log"

# ─── Format ───
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATE_FORMAT = f"%Y-%m-%d %H:%M:%S {TZ_NAME}"

# ─── Initialize ───
logger = logging.getLogger("fx_bot")
logger.setLevel(logging.DEBUG)
logger.propagate = False

# ─── File Handler ───
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
file_handler.setLevel(logging.DEBUG)

# ─── Console Handler ───
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
console_handler.setLevel(logging.INFO)

# ─── Attach ───
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ──────────────────────────────────────────────────────────
# 🔇 Central muting: silence INFO on third-party libraries, keep WARNING and above only
# Add any new library here
# ──────────────────────────────────────────────────────────
SILENCE_LIST = [
    "oandapyV20",              # OANDA HTTP request logs
    "oandapyV20.endpoints", 
    "requests",                # requests library
    "urllib3",                 # requests transport layer
    "httpx",                   # in case we switch to httpx later
    "httpcore",                
    "asyncio",                 # too noisy
]

for _lib in SILENCE_LIST:
    _lib_log = logging.getLogger(_lib)
    _lib_log.setLevel(logging.WARNING) # drop everything below INFO
    _lib_log.propagate = False         # do not bubble up to the root logger


# ─── Central time helpers ───
def now():
    """Single entry point: get local time"""
    return datetime.now()


def today_str():
    """Single entry point: get local date, e.g. 20250902"""
    return now().strftime("%Y%m%d")


def fmt(dt=None, fmt_str="%Y-%m-%d %H:%M:%S"):
    """Unified formatting, including the timezone name"""
    dt = dt or now()
    return f"{dt.strftime(fmt_str)} {TZ_NAME}"


def get_logger(name: str = None) -> logging.Logger:
    """Get a shared logger — use in every .py file"""
    if not name or name == "fx_bot":
        return logger
    # Child logger: named per module, but handlers/format are centrally controlled by fx_bot
    child = logging.getLogger(f"fx_bot.{name}")
    child.propagate = True
    return child
