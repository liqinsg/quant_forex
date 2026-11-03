#!/usr/bin/env python3
"""
weekly_train_daemon.py

周度增量训练守护 — 独立轻量进程，只更新模型，不涉及下单。
职责：
    1. 读取 config.yaml 的 lgb.retrain_interval_days（默认 7 天）。
    2. 首次启动：仅补训缺失的模型（已存在则跳过）。
    3. 之后按周期对全部货币对执行增量重训（update_csv 自动追新 K 线）。
    4. 记录更新时间到 reports/.last_weekly_retrain，供主循环 / deploy.sh status 读取。
    5. 单个货币对失败不影响其他品种，记录完整异常，下个周期自动重试。

用法：
    python weekly_train_daemon.py          # 常驻守护
    python weekly_train_daemon.py --once   # 立即执行一次全量更新后退出（应急）

退出码（--once）：
    0 = 全部成功    1 = 部分失败    2 = 全部失败
"""
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    load_config,
    model_dir,
    current_env,
    REPORTS_DIR,
    LAST_RETRAIN_FILE,
)
from models.train_lgb_signal import run_full_training
from utils.logging_utils import get_logger

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 中心化日志
log = get_logger("weekly_train")

CFG = load_config()
INTERVAL_DAYS = CFG["lgb"]["retrain_interval_days"]
# 训练覆盖外汇 + 加密（加密模型与外汇同样按周期更新）
INSTRUMENTS = CFG["instruments"] + CFG.get("crypto_instruments", [])


def _mark_updated():
    LAST_RETRAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_RETRAIN_FILE.write_text(datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))


def _train_one(inst):
    """Train a single pair; on failure log the full traceback and return False instead of raising."""
    try:
        run_full_training(inst)
        return True
    except Exception:
        log.exception(f"❌ {inst} update failed (skipped, will retry next cycle)")
        return False


def update_missing():
    """First start: only train the models that are missing."""
    instruments = INSTRUMENTS
    md = model_dir()
    missing = [i for i in instruments if not (md / f"lgb_{i}.pkl").exists()]
    if not missing:
        log.info(f"✅ First check: all {len(instruments)} models already exist, nothing to train")
        return [], []
    log.info(f"🏋️ First check: {len(missing)}/{len(instruments)} missing, starting catch-up training ...")
    ok, failed = [], []
    for i, inst in enumerate(missing, 1):
        log.info(f"🏋️ Training {inst} ... ({i}/{len(missing)})")
        (ok if _train_one(inst) else failed).append(inst)
    if ok:
        _mark_updated()
    if failed:
        log.warning(f"⚠️ Initial catch-up training failed for {len(failed)}: {', '.join(failed)}")
    return ok, failed


def update_all():
    """Periodic run: incremental retraining of every instrument; returns (ok list, failed list)."""
    instruments = INSTRUMENTS
    ok, failed = [], []
    for i, inst in enumerate(instruments, 1):
        log.info(f"🏋️ Weekly update {inst} ... ({i}/{len(instruments)})")
        (ok if _train_one(inst) else failed).append(inst)
    if ok:
        _mark_updated()
        log.info(f"✅ Weekly model update done — {len(ok)}/{len(instruments)}: {', '.join(ok)}")
    if failed:
        log.warning(f"⚠️ {len(failed)} failed (retrying next cycle): {', '.join(failed)}")
    return ok, failed


def main():
    run_once = "--once" in sys.argv
    log.info(
        f"🚀 Weekly training daemon started — env {current_env()} | interval {INTERVAL_DAYS} days | "
        f"model dir {model_dir()}"
    )

    if run_once:
        log.info("--once mode: run one full update now")
        ok, failed = update_all()
        total = len(ok) + len(failed)
        if failed and not ok:
            log.error(f"❌ --once finished: all failed ({len(failed)}/{total}), exit code 2")
            return 2
        if failed:
            log.warning(f"⚠️ --once finished: partial failure (ok {len(ok)} / failed {len(failed)}), "
                        f"exit code 1")
            return 1
        log.info(f"✅ --once finished: all succeeded ({len(ok)}/{total})")
        return 0

    try:
        update_missing()
    except Exception:
        log.exception("❌ Unexpected error during initial catch-up training; continuing into the cycle loop")

    while True:
        sleep_s = 86400 * INTERVAL_DAYS
        log.info(f"💤 Sleeping {INTERVAL_DAYS} days ({sleep_s}s) before the next update ...")
        time.sleep(sleep_s)
        try:
            update_all()
        except Exception:
            log.exception("❌ Unexpected error during this update; will retry next cycle")


if __name__ == "__main__":
    sys.exit(main())
