#!/usr/bin/env python3
"""主循环入口 — 放在根目录，直接 python main_loop_v2.py 运行"""
import os
import sys
import argparse
from pathlib import Path

# 确保项目根目录在路径里
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args():
    """CLI 参数：--live 切到实盘；--account/-a 选择账号序号（1-based）。"""
    parser = argparse.ArgumentParser(description="Forex OANDA 主循环")
    parser.add_argument(
        "--live",
        action="store_true",
        help="切换到 live 实盘账号（缺省为 demo，无简写）",
    )
    parser.add_argument(
        "--account",
        "-a",
        type=int,
        default=1,
        metavar="N",
        help="选择账号序号 N（1-based）；--live 对应 live 账号，缺省对应 demo 账号",
    )
    parser.add_argument(
        "--lots",
        type=int,
        default=None,
        metavar="N",
        help="下单手数 N（以 unit 计，非合约金额）；缺省读取 run.env 的 "
        "DEMO_LOT_SIZE/LIVE_LOT_SIZE（demo 10000 / live 1）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="空跑模式：正常跑完整流程但不下单/平仓（不发送任何订单）",
    )
    return parser.parse_args()


ARGS = _parse_args()

# 关键：必须在 import config.config_oanda 之前写死环境，
# 才能保证 live/demo 各自使用正确的 TOKEN 与账号列表（.env 以 override=False 加载，不会覆盖）
os.environ["OANDA_ENV"] = "live" if ARGS.live else "practice"
os.environ["OANDA_ACCOUNT_INDEX"] = str(ARGS.account)

import time
import warnings
import pandas as pd
from datetime import datetime
from config.config_oanda import get_oanda_profile, is_market_open
from config import load_config, model_dir, current_env, LAST_RETRAIN_FILE
from utils.logging_utils import get_logger
from utils.structured_logger import StructuredLogger

profile = get_oanda_profile()
OANDA_ACCOUNT_ID = profile["account_id"]
OANDA_TOKEN = profile["token"]
OANDA_ENV = profile["env"]
api = profile["oanda_client"]


def _resolve_lots(cli_lots, env_name):
    """下单手数(units)解析：--lots > run.env 的 DEMO_LOT_SIZE/LIVE_LOT_SIZE > 缺省(demo 10000 / live 1)。"""
    if cli_lots is not None:
        return int(cli_lots)
    key = "LIVE_LOT_SIZE" if env_name == "live" else "DEMO_LOT_SIZE"
    raw = os.getenv(key, "").strip()
    if raw:
        try:
            return int(float(raw))
        except ValueError:
            pass
    return 1 if env_name == "live" else 10000


LOT_SIZE = _resolve_lots(ARGS.lots, OANDA_ENV)
DRY_RUN = ARGS.dry_run

# 中心化日志：主循环用统一 logger，结构化日志记录主动(BOT)操作（按环境分文件）
log = get_logger("main_loop")
struct_log = StructuredLogger(OANDA_ENV)

# 读配置 — 统一入口（含 forex_pairs.yml 的货币对）
CFG = load_config()

# 导入：从 forex_oanda 包加载
from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model, run_full_training
from execution.oanda_conn import (
    place_market_order,
    close_position,
    get_open_position,
    set_dry_run,
)
from execution.risk_gate import enhanced_risk_check, circuit
from arch import arch_model
from arch.utility.exceptions import (
    ConvergenceWarning,
    StartingValueWarning,
    InitialValueWarning,
    DataScaleWarning,
)

# 空跑模式：在执行层拦截所有下单/平仓（应用启动时接线一次即可）
set_dry_run(DRY_RUN)

# 屏蔽 GARCH(arch) 拟合的收敛/初始值/量纲类警告，避免刷屏
for _garch_warn in (ConvergenceWarning, StartingValueWarning, InitialValueWarning, DataScaleWarning):
    warnings.filterwarnings("ignore", category=_garch_warn)

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

def _extract_open_trade_id(resp):
    """从 OANDA 下单响应中提取刚开仓的 tradeID；缺失返回空串。"""
    try:
        return resp["orderFillTransaction"]["tradeOpened"]["tradeID"]
    except (KeyError, TypeError):
        return ""

def _extract_close_trade_id(resp):
    """从 OANDA 平仓响应中提取被平仓的 tradeID；缺失返回空串。"""
    try:
        for key in ("longOrderFillTransaction", "shortOrderFillTransaction"):
            closed = resp.get(key, {}).get("tradesClosed", [])
            if closed:
                return closed[0]["tradeID"]
    except (AttributeError, TypeError):
        pass
    return ""

def main_cycle(inst):
    """处理单个品种。返回本轮计数 {"open": int, "close": int, "observe": int, "fail": int}。"""
    result = {"open": 0, "close": 0, "observe": 0, "fail": 0}

    # 市场停牌检测：不可交易时与 --dry-run 同样的下单/平仓限制，并打 tag=market_halt
    if not is_market_open(inst, quiet=True):
        log.info(f"🛑 观望 {inst} | 市场停牌 (tag=market_halt)")
        struct_log.skip_signal(inst, "market_halt")
        result["observe"] += 1
        return result

    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: 无有效数据")
        result["fail"] += 1
        return result

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
        log.warning(f"{inst}: 特征不匹配，跳过")
        result["fail"] += 1
        return result

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG)

    long_thr = CFG["signal"]["prob_long_threshold"]
    short_thr = CFG["signal"]["prob_short_threshold"]
    thr_desc = f"多≥{long_thr:.0%} / 空≤{short_thr:.0%}"

    if not ok:
        log.info(f"{inst}: {reason}")
        log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 风控限制")
        struct_log.skip_signal(inst, "risk_limit", detail=reason, prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
        return result

    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])

    if prob > long_thr:
        if pos["units"] < 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 平仓 {inst} | 盈亏: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_long",
                                 units=int(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] <= 0:
            sl = close - 1.5 * atr
            tp = close + 1.8 * abs(close - sl)
            resp = place_market_order(inst, LOT_SIZE, sl, tp)
            log.info(f"📈 LONG {inst} p={prob:.2f} SL={sl:.5f} TP={tp:.5f}")
            log.info(f"📈 开多仓 {inst} | 概率: {prob:.1%} | 入场价: {close:.4f}")
            struct_log.bot_open(pair=inst, direction="LONG", units=LOT_SIZE, entry_price=close,
                                trade_id=_extract_open_trade_id(resp), sl=sl, tp=tp,
                                score_final=prob)
            result["open"] += 1
        else:
            log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 已有持仓")
            struct_log.skip_signal(inst, "has_position", prob=prob,
                                   prob_long_threshold=long_thr, prob_short_threshold=short_thr)
            result["observe"] += 1
    elif prob < short_thr:
        if pos["units"] > 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 平仓 {inst} | 盈亏: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_short",
                                 units=int(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] >= 0:
            sl = close + 1.5 * atr
            tp = close - 1.8 * abs(sl - close)
            resp = place_market_order(inst, -LOT_SIZE, sl, tp)
            log.info(f"📉 SHORT {inst} p={prob:.2f} SL={sl:.5f} TP={tp:.5f}")
            log.info(f"📉 开空仓 {inst} | 概率: {prob:.1%} | 入场价: {close:.4f}")
            struct_log.bot_open(pair=inst, direction="SHORT", units=-LOT_SIZE, entry_price=close,
                                trade_id=_extract_open_trade_id(resp), sl=sl, tp=tp,
                                score_final=prob)
            result["open"] += 1
        else:
            log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 已有持仓")
            struct_log.skip_signal(inst, "has_position", prob=prob,
                                   prob_long_threshold=long_thr, prob_short_threshold=short_thr)
            result["observe"] += 1
    else:
        log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 概率区间正常")
        struct_log.skip_signal(inst, "no_signal", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1

    return result

if __name__ == "__main__":
    log.info("🚀 Bot v6.8x STARTED")
    log.info(f"环境: {current_env()} | 模型目录: {MODEL_DIR}")

    n_accounts = len(profile["account_ids"])
    if not (1 <= ARGS.account <= n_accounts):
        log.error(
            f"❌ --account {ARGS.account} 超出范围: 当前 {OANDA_ENV.upper()} 环境有 "
            f"{n_accounts} 个账号，可选 1..{n_accounts}"
        )
        sys.exit(1)
    log.info(f"账号: {OANDA_ENV.upper()} #{ARGS.account} → {OANDA_ACCOUNT_ID}")
    log.info(f"下单手数: {LOT_SIZE} units")
    if DRY_RUN:
        log.warning("🧪 DRY-RUN 模式: 正常运行但不会真正下单/平仓/改单")

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
        log.info(f"📊 本轮处理开始: {datetime.now():%Y-%m-%d %H:%M:%S} | 待处理: {len(ready)} 个品种")
        totals = {"open": 0, "close": 0, "observe": 0, "fail": 0}
        for inst in ready:
            try:
                r = main_cycle(inst)
                for k in totals:
                    totals[k] += r.get(k, 0)
            except Exception as e:
                log.error(f"❌ {inst}: {e}")
                totals["fail"] += 1
        log.info(f"✅ 本轮完成: 开仓 {totals['open']} | 平仓 {totals['close']} | 观望 {totals['observe']} | 失败 {totals['fail']}")
        time.sleep(3600)