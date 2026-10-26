#!/usr/bin/env python3
"""主循环入口 — 放在根目录，直接 python main_loop_v2.py 运行"""
import sys
from pathlib import Path

# 确保项目根目录在路径里
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import yaml
import logging
import pandas as pd
from datetime import datetime
from config_oanda import get_oanda_profile, is_market_open

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

# 读配置 — 路径正确
with open(PROJECT_ROOT / "config" / "config.yaml") as f:
    CFG = yaml.safe_load(f)

# 导入：从 forex_oanda 包加载
from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model
from execution.oanda_conn import place_market_order, close_position, get_open_position
from execution.risk_gate import enhanced_risk_check, circuit
from arch import arch_model

BALANCE = 5000.0

def calc_garch_vol(returns):
    am = arch_model(returns*100, p=1, q=1, dist="Normal")
    res = am.fit(disp="off")
    fc = res.forecast(horizon=1)
    return float(fc.variance.iloc[-1]**0.5 / 100 * (252**0.5))

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

    atr = float(latest["ta_atr"])
    close = float(latest["close"])

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
    while True:
        for inst in CFG["instruments"]:
            try:
                main_cycle(inst)
            except Exception as e:
                log.error(f"❌ {inst}: {e}")
        time.sleep(3600)