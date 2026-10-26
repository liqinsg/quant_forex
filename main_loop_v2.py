#!/usr/bin/env python3
"""主循环入口 — 放在根目录，直接 python main_loop_v2.py 运行"""
import sys
from pathlib import Path

# 确保项目根目录在路径里
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import logging
import pandas as pd
from datetime import datetime
from config.config_oanda import get_oanda_profile, is_market_open
from config import load_config, model_dir, current_env, LAST_RETRAIN_FILE

profile = get_oanda_profile()
OANDA_ACCOUNT_ID = profile["account_ids"][0]
OANDA_TOKEN = profile["token"]
OANDA_ENV = profile["env"]
api = profile["oanda_client"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "reports" / "bot.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("bot")

# 读配置 — 统一入口（含 forex_pairs.yml 的货币对）
CFG = load_config()

# 导入：从 forex_oanda 包加载
from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model, run_full_training
from execution.oanda_conn import place_market_order, close_position, get_open_position
from execution.risk_gate import enhanced_risk_check, circuit
from arch import arch_model

BALANCE = 5000.0
MODEL_DIR = model_dir()
RETRAIN_INTERVAL_DAYS = CFG["lgb"]["retrain_interval_days"]


def check_models(instruments):
    """检查每个货币对是否已有训练好的 LGB 模型，返回 (可用列表, 缺失列表)。"""
    ready, missing = [], []
    for inst in instruments:
        if (MODEL_DIR / f"lgb_{inst}.pkl").exists():
            ready.append(inst)
        else:
            missing.append(inst)
    return ready, missing

def check_weekly_status():
    """读取周守护的更新记录并提示（不阻断主循环）。"""
    if not LAST_RETRAIN_FILE.exists():
        log.warning("⚠️ 尚无周度更新记录，请确认周守护进程已运行 (./deploy.sh daemon)")
        return
    try:
        last = datetime.fromisoformat(LAST_RETRAIN_FILE.read_text().strip())
    except Exception as e:
        log.warning(f"⚠️ 无法解析周度更新时间: {e}")
        return
    age_days = (datetime.now() - last).days
    log.info(f"模型最后更新: {last:%Y-%m-%d} ({age_days}天前)")
    if age_days > RETRAIN_INTERVAL_DAYS:
        log.warning(f"⚠️ 距上次更新已超{RETRAIN_INTERVAL_DAYS}天，请确认周守护进程正常")

def calc_garch_vol(returns):
    am = arch_model(returns*100, p=1, q=1, dist="Normal")
    res = am.fit(disp="off")
    fc = res.forecast(horizon=1)
    return float(fc.variance.iloc[-1, 0]**0.5 / 100 * (252**0.5))

def main_cycle(inst):
    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: 无有效数据")
        return

    pkg = load_model(inst)
    feats = pkg["feature_cols"]

    # TCN 融合（存在即启用）
    try:
        from models.train_tcn_extract import get_latest_seq_feature
        sf = get_latest_seq_feature(inst, df)
        for k, v in sf.items():
            latest[k] = v
        feats = feats + list(sf.keys())
    except Exception:
        pass

    if not all(c in latest.columns for c in feats):
        log.warning(f"{inst}: 特征不匹配，跳过"); return

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG)
    if not ok:
        log.info(f"{inst}: {reason}"); return

    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])

    if prob > CFG["signal"]["prob_long_threshold"]:
        if pos["units"] < 0: close_position(inst)
        if pos["units"] <= 0:
            sl = close - 1.5 * atr
            tp = close + 1.8 * abs(close - sl)
            place_market_order(inst, 1000, sl, tp)
            log.info(f"📈 LONG {inst} p={prob:.2f} SL={sl:.5f} TP={tp:.5f}")
    elif prob < CFG["signal"]["prob_short_threshold"]:
        if pos["units"] > 0: close_position(inst)
        if pos["units"] >= 0:
            sl = close + 1.5 * atr
            tp = close - 1.8 * abs(sl - close)
            place_market_order(inst, -1000, sl, tp)
            log.info(f"📉 SHORT {inst} p={prob:.2f} SL={sl:.5f} TP={tp:.5f}")

if __name__ == "__main__":
    log.info("🚀 Bot v6.8x STARTED")
    log.info(f"环境: {current_env()} | 模型目录: {MODEL_DIR}")

    all_inst = CFG["instruments"]
    ready, missing = check_models(all_inst)
    if missing:
        log.warning(f"⚠️ 缺少 {len(missing)}/{len(all_inst)} 个货币对的模型，先自动训练: {', '.join(missing)}")
        log.warning(f"   将串行训练 {len(missing)} 个对，耗时较长，请耐心等待（Ctrl-C 可中断，已完成的模型会保留）...")
        for i, inst in enumerate(missing, 1):
            try:
                log.info(f"🏋️ 训练 {inst} ... ({i}/{len(missing)})")
                run_full_training(inst)
            except Exception as e:
                log.error(f"❌ {inst} 训练失败: {e}")
        ready, still_missing = check_models(all_inst)
        if still_missing:
            log.error(f"❌ 仍有 {len(still_missing)} 个模型缺失，未启动: {', '.join(still_missing)}")
            log.error("   训练方式: ./deploy.sh train   |   python models/train_lgb_signal.py <INST>")
            sys.exit(1)
    log.info(f"✅ 模型齐备 {len(ready)}/{len(all_inst)}，启动交易循环")
    check_weekly_status()

    while True:
        for inst in ready:
            try:
                main_cycle(inst)
            except Exception as e:
                log.error(f"❌ {inst}: {e}")
        time.sleep(3600)