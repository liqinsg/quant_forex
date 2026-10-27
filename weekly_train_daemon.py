#!/usr/bin/env python3
"""周度增量训练守护 — 独立轻量进程，只更新模型，不涉及下单。

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
    """训练单个货币对；失败时记录完整异常并返回 False，不向外抛出。"""
    try:
        run_full_training(inst)
        return True
    except Exception:
        log.exception(f"❌ {inst} 更新失败（已跳过，将在下个周期重试）")
        return False


def update_missing():
    """首次启动：只补训缺失的模型。"""
    instruments = INSTRUMENTS
    md = model_dir()
    missing = [i for i in instruments if not (md / f"lgb_{i}.pkl").exists()]
    if not missing:
        log.info(f"✅ 首次检查：{len(instruments)} 个模型均已存在，无需补训")
        return [], []
    log.info(f"🏋️ 首次检查：缺失 {len(missing)}/{len(instruments)} 个，开始补训 ...")
    ok, failed = [], []
    for i, inst in enumerate(missing, 1):
        log.info(f"🏋️ 训练 {inst} ... ({i}/{len(missing)})")
        (ok if _train_one(inst) else failed).append(inst)
    if ok:
        _mark_updated()
    if failed:
        log.warning(f"⚠️ 首次补训失败 {len(failed)} 个: {', '.join(failed)}")
    return ok, failed


def update_all():
    """周期性：对全部品种执行增量重训，返回 (成功列表, 失败列表)。"""
    instruments = INSTRUMENTS
    ok, failed = [], []
    for i, inst in enumerate(instruments, 1):
        log.info(f"🏋️ 周度更新 {inst} ... ({i}/{len(instruments)})")
        (ok if _train_one(inst) else failed).append(inst)
    if ok:
        _mark_updated()
        log.info(f"✅ 周度模型更新完成 — {len(ok)}/{len(instruments)}: {', '.join(ok)}")
    if failed:
        log.warning(f"⚠️ 失败 {len(failed)} 个（下个周期重试）: {', '.join(failed)}")
    return ok, failed


def main():
    run_once = "--once" in sys.argv
    log.info(
        f"🚀 周度训练守护启动 — 环境 {current_env()} | 周期 {INTERVAL_DAYS} 天 | 模型目录 {model_dir()}"
    )

    if run_once:
        log.info("--once 模式：立即执行一次全量更新")
        ok, failed = update_all()
        total = len(ok) + len(failed)
        if failed and not ok:
            log.error(f"❌ --once 完成：全部失败 ({len(failed)}/{total})，退出码 2")
            return 2
        if failed:
            log.warning(f"⚠️ --once 完成：部分失败（成功 {len(ok)} / 失败 {len(failed)}），退出码 1")
            return 1
        log.info(f"✅ --once 完成：全部成功 ({len(ok)}/{total})")
        return 0

    try:
        update_missing()
    except Exception:
        log.exception("❌ 首次补训出现未预期异常，继续进入周期循环")

    while True:
        sleep_s = 86400 * INTERVAL_DAYS
        log.info(f"💤 休眠 {INTERVAL_DAYS} 天（{sleep_s}s）后执行下次更新 ...")
        time.sleep(sleep_s)
        try:
            update_all()
        except Exception:
            log.exception("❌ 本轮更新出现未预期异常，将在下个周期重试")


if __name__ == "__main__":
    sys.exit(main())
