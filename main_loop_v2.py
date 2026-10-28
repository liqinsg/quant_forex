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
    """CLI 参数：--live 切到实盘；--account/-a 选择账号（a/c id 或 1-based 序号）。"""
    parser = argparse.ArgumentParser(description="Forex OANDA 主循环")
    parser.add_argument(
        "--live",
        action="store_true",
        help="切换到 live 实盘账号（缺省为 demo，无简写）",
    )
    parser.add_argument(
        "--account",
        "-a",
        type=str,
        default=None,
        metavar="ID",
        help="选择账号：填完整 a/c id（如 101-003-39389016-005）或 1-based 序号；"
        "缺省时按 run.env > config/.env > 名单第 1 个 解析",
    )
    parser.add_argument(
        "--lots",
        type=int,
        default=None,
        metavar="N",
        help="下单手数 N（以 unit 计，非合约金额）；缺省读取 run.env 的 "
        "DEMO_LOT_SIZE/LIVE_LOT_SIZE（demo 10000 / live 1）",
    )
    _mode = parser.add_mutually_exclusive_group()
    _mode.add_argument(
        "--forex",
        "-f",
        dest="trade_mode",
        action="store_const",
        const="forex",
        help="只交易外汇（默认）",
    )
    _mode.add_argument(
        "--crypto",
        "-c",
        dest="trade_mode",
        action="store_const",
        const="crypto",
        help="只交易加密货币（BTC_USD/ETH_USD）",
    )
    _mode.add_argument(
        "--forex-crypto",
        "-b",
        dest="trade_mode",
        action="store_const",
        const="forex-crypto",
        help="外汇与加密同时交易",
    )
    parser.add_argument(
        "--crypto-lots",
        type=float,
        default=None,
        metavar="N",
        help="加密下单手数 N（以 unit 计，支持小数）；缺省读取 run.env 的 "
        "DEMO_LOT_SIZE_CRYPTO/LIVE_LOT_SIZE_CRYPTO（demo 1 / live 0.01）",
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
if ARGS.account:
    # CLI 传 a/c id（或 1-based 序号）；用独立变量桥接到 config_oanda，
    # 使所有模块的 get_oanda_profile() 都跟随 CLI 选择（优先级高于 run.env/.env）
    os.environ["OANDA_ACCOUNT_CLI"] = str(ARGS.account)

import time
import warnings
import pandas as pd
from datetime import datetime
from config.config_oanda import get_oanda_profile, is_market_open
from config import load_config, model_dir, current_env, LAST_RETRAIN_FILE
from config.pairs import is_crypto
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


def _resolve_crypto_lots(cli_lots, env_name):
    """加密手数(units)解析：--crypto-lots > run.env 的 DEMO/LIVE_LOT_SIZE_CRYPTO > 缺省(demo 1 / live 0.01)。

    加密按 unit 计且支持小数（BTC 最小 0.001 / ETH 最小 0.01），故不做 int 截断。
    """
    if cli_lots is not None:
        return float(cli_lots)
    key = "LIVE_LOT_SIZE_CRYPTO" if env_name == "live" else "DEMO_LOT_SIZE_CRYPTO"
    raw = os.getenv(key, "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return 0.01 if env_name == "live" else 1.0


def _resolve_trade_mode(cli_mode):
    """交易品种模式解析：CLI(--forex/-f | --crypto/-c | --forex-crypto/-b)
    > run.env 的 TRADE_MODE > 缺省 'forex'。"""
    if cli_mode:
        return cli_mode
    env_val = os.getenv("TRADE_MODE", "").strip().lower()
    valid = ("forex", "crypto", "forex-crypto")
    if env_val:
        if env_val in valid:
            return env_val
        log.warning(f"⚠️ TRADE_MODE={env_val} 无效，回退为 forex")
    return "forex"


def _resolve_float(env_key, yaml_path, default):
    """
    统一解析配置，优先级：环境变量 > config.yaml > 内置默认值
    :param env_key: run.env 中的环境变量名，如 "PROB_LONG_THRESHOLD"
    :param yaml_path: YAML 深层路径，点号分隔，如 "signal.prob_long_threshold"
    :param default: 兜底默认值
    :return: float 解析结果
    """
    raw = os.getenv(env_key, "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            log.warning(f"⚠️ 环境变量 {env_key}={raw} 无效，回退到 YAML")

    node = CFG
    try:
        for key in yaml_path.split("."):
            node = node[key]
        return float(node)
    except (KeyError, TypeError, ValueError):
        return float(default)


# 中心化日志：主循环用统一 logger，结构化日志记录主动(BOT)操作（按环境分文件）
log = get_logger("main_loop")
struct_log = StructuredLogger(OANDA_ENV)

LOT_SIZE = _resolve_lots(ARGS.lots, OANDA_ENV)
CRYPTO_LOT_SIZE = _resolve_crypto_lots(ARGS.crypto_lots, OANDA_ENV)
TRADE_MODE = _resolve_trade_mode(ARGS.trade_mode)
DRY_RUN = ARGS.dry_run

# 读配置 — 统一入口（含 instruments.yaml 的货币对）
CFG = load_config()
PROB_LONG_THRESHOLD = _resolve_float(
    "PROB_LONG_THRESHOLD", "signal.prob_long_threshold", 0.65
)
PROB_SHORT_THRESHOLD = _resolve_float(
    "PROB_SHORT_THRESHOLD", "signal.prob_short_threshold", 0.35
)
# 加密独立信号概率阈值（未配置时自动沿用上面的外汇阈值）
CRYPTO_PROB_LONG_THRESHOLD = _resolve_float(
    "CRYPTO_PROB_LONG_THRESHOLD", "crypto.prob_long_threshold", PROB_LONG_THRESHOLD
)
CRYPTO_PROB_SHORT_THRESHOLD = _resolve_float(
    "CRYPTO_PROB_SHORT_THRESHOLD", "crypto.prob_short_threshold", PROB_SHORT_THRESHOLD
)
ATR_SL_MULTIPLIER = _resolve_float(
    "STOP_LOSS_ATR_MULTIPLIER", "risk.stop_loss_atr_multiplier", 1.5
)
ATR_TP_MULTIPLIER = _resolve_float(
    "TAKE_PROFIT_ATR_MULTIPLIER", "risk.take_profit_atr_multiplier", 1.8
)
# 加密独立 ATR 倍率（外汇沿用 ATR_SL_MULTIPLIER / ATR_TP_MULTIPLIER）
CRYPTO_SL_MULT = _resolve_float(
    "CRYPTO_ATR_SL_MULTIPLIER", "crypto.atr_sl_multiplier", 2.0
)
CRYPTO_TP_MULT = _resolve_float(
    "CRYPTO_ATR_TP_MULTIPLIER", "crypto.atr_tp_multiplier", 2.5
)
# 加密独立年化波动率阈值（外汇沿用 risk.vol_threshold_annual）
CRYPTO_VOL_THRESHOLD = _resolve_float(
    "CRYPTO_VOL_THRESHOLD", "crypto.vol_threshold_annual", 1.0
)
# 分组控仓：OVERRIDE_MAX_OPEN=1 按分组独立控仓；=0 沿用全局 MAX_OPEN（默认 0=不限）
OVERRIDE_MAX_OPEN = _resolve_float("OVERRIDE_MAX_OPEN", "risk.override_max_open", 0)
MAX_OPEN_PER_GROUP_FOREX = int(
    _resolve_float("MAX_OPEN_PER_GROUP_FOREX", "risk.max_open_per_group_forex", 6)
)
MAX_OPEN_PER_GROUP_CRYPTO = int(
    _resolve_float("MAX_OPEN_PER_GROUP_CRYPTO", "risk.max_open_per_group_crypto", 2)
)
# 全局上限（仅 OVERRIDE_MAX_OPEN=0 时生效；0 表示不限，保持旧行为）
MAX_OPEN = int(_resolve_float("MAX_OPEN", "risk.max_open", 0))

# 导入：从 forex_oanda 包加载
from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model, run_full_training
from execution.oanda_conn import (
    place_market_order,
    close_position,
    get_open_position,
    has_open_bot_trade,
    open_bot_instruments,
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


def _units_for(inst):
    """下单手数：加密用独立 CRYPTO_LOT_SIZE，外汇用 LOT_SIZE。"""
    return CRYPTO_LOT_SIZE if is_crypto(inst) else LOT_SIZE


def _vol_threshold_for(inst):
    """加密用独立波幅阈值；外汇返回 None（交给 risk_gate 默认逻辑）。"""
    return CRYPTO_VOL_THRESHOLD if is_crypto(inst) else None


def _atr_sl_mult_for(inst):
    """ATR 止损倍率：加密用独立 CRYPTO_SL_MULT，外汇用 ATR_SL_MULTIPLIER。"""
    return CRYPTO_SL_MULT if is_crypto(inst) else ATR_SL_MULTIPLIER


def _atr_tp_mult_for(inst):
    """ATR 止盈倍率：加密用独立 CRYPTO_TP_MULT，外汇用 ATR_TP_MULTIPLIER。"""
    return CRYPTO_TP_MULT if is_crypto(inst) else ATR_TP_MULTIPLIER


def _prob_long_thr_for(inst):
    """做多概率阈值：加密用独立阈值，外汇用 PROB_LONG_THRESHOLD。"""
    return CRYPTO_PROB_LONG_THRESHOLD if is_crypto(inst) else PROB_LONG_THRESHOLD


def _prob_short_thr_for(inst):
    """做空概率阈值：加密用独立阈值，外汇用 PROB_SHORT_THRESHOLD。"""
    return CRYPTO_PROB_SHORT_THRESHOLD if is_crypto(inst) else PROB_SHORT_THRESHOLD


def _group_for(inst):
    """返回品种所属分组：'crypto' 或 'forex'。"""
    return "crypto" if is_crypto(inst) else "forex"


def _group_max_open(group):
    """分组开仓上限；OVERRIDE_MAX_OPEN=0 时回退全局 MAX_OPEN（0=不限）。"""
    if OVERRIDE_MAX_OPEN:
        return MAX_OPEN_PER_GROUP_CRYPTO if group == "crypto" else MAX_OPEN_PER_GROUP_FOREX
    return MAX_OPEN


def _count_open_in_group(positions, group):
    """统计当前 bot 持仓中属于指定分组的数量（positions 为品种列表）。"""
    return sum(1 for inst in positions if _group_for(inst) == group)


def _fmt_units(units):
    """单位数展示：整数值原样转 int（如 10000.0 -> 10000），小数（加密）保留原值。"""
    units = float(units)
    return int(units) if units.is_integer() else units


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

def analyze_cycle(inst):
    """分析单个品种：处理停牌/风控/平仓/反手，并返回潜在开仓候选。

    开仓动作被推迟到分组控仓阶段统一执行，故本函数不直接下单。
    返回 (result, candidate)：
      result    = {"open","close","observe","fail"}（"open" 恒为 0）
      candidate = None 或 {"inst","group","direction","prob","signal_strength",
                           "units","sl","tp","close","thr_desc","long_thr","short_thr"}
    """
    result = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    units = _units_for(inst)

    # 市场停牌检测：不可交易时与 --dry-run 同样的下单/平仓限制，并打 tag=market_halt
    if not is_market_open(inst, quiet=True):
        log.info(f"🛑 观望 {inst} | 市场停牌 (tag=market_halt)")
        struct_log.skip_signal(inst, "market_halt")
        result["observe"] += 1
        return result, None

    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: 无有效数据")
        result["fail"] += 1
        return result, None

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
        return result, None

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG, vol_threshold=_vol_threshold_for(inst))

    long_thr = _prob_long_thr_for(inst)
    short_thr = _prob_short_thr_for(inst)
    thr_desc = f"多≥{long_thr:.0%} / 空≤{short_thr:.0%}"

    if not ok:
        log.info(f"{inst}: {reason}")
        log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 风控限制")
        struct_log.skip_signal(inst, "risk_limit", detail=reason, prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
        return result, None

    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])

    if prob > long_thr:
        if pos["units"] < 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 平仓 {inst} | 盈亏: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_long",
                                 units=_fmt_units(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] <= 0:
            if has_open_bot_trade(inst, units):
                log.info(
                    f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 已有同向 bot 持仓(tag=fx_bot_v7)"
                )
                struct_log.skip_signal(
                    inst,
                    "duplicate_bot_trade",
                    detail="same_direction_open_trade",
                    prob=prob,
                    prob_long_threshold=long_thr,
                    prob_short_threshold=short_thr,
                )
                result["observe"] += 1
                return result, None
            sl = close - _atr_sl_mult_for(inst) * atr
            tp = close + _atr_tp_mult_for(inst) * abs(close - sl)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "LONG",
                "prob": prob, "signal_strength": prob, "units": units,
                "sl": sl, "tp": tp, "close": close, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }
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
                                 units=_fmt_units(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] >= 0:
            if has_open_bot_trade(inst, -units):
                log.info(
                    f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 已有同向 bot 持仓(tag=fx_bot_v7)"
                )
                struct_log.skip_signal(
                    inst,
                    "duplicate_bot_trade",
                    detail="same_direction_open_trade",
                    prob=prob,
                    prob_long_threshold=long_thr,
                    prob_short_threshold=short_thr,
                )
                result["observe"] += 1
                return result, None
            sl = close + _atr_sl_mult_for(inst) * atr
            tp = close - _atr_tp_mult_for(inst) * abs(sl - close)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "SHORT",
                "prob": prob, "signal_strength": 1.0 - prob, "units": -units,
                "sl": sl, "tp": tp, "close": close, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }
        log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 已有持仓")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    else:
        log.info(f"⏸️ 观望 {inst} | 概率: {prob:.1%} | 阈值: {thr_desc} | 原因: 概率区间正常")
        struct_log.skip_signal(inst, "no_signal", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1

    return result, None


def _place_candidate(cand):
    """执行单个开仓候选的下单与日志记录。"""
    inst, prob = cand["inst"], cand["prob"]
    direction = cand["direction"]
    resp = place_market_order(inst, cand["units"], cand["sl"], cand["tp"])
    icon = "📈" if direction == "LONG" else "📉"
    log.info(f"{icon} {direction} {inst} p={prob:.2f} SL={cand['sl']:.5f} TP={cand['tp']:.5f}")
    log.info(f"{icon} 开{'多' if direction == 'LONG' else '空'}仓 {inst} | 概率: {prob:.1%} | 入场价: {cand['close']:.4f}")
    struct_log.bot_open(pair=inst, direction=direction, units=cand["units"],
                        entry_price=cand["close"], trade_id=_extract_open_trade_id(resp),
                        sl=cand["sl"], tp=cand["tp"], score_final=prob)


def run_cycle(ready):
    """一轮完整处理：先分析（含平仓/反手），再按分组控仓选最优开仓。

    返回本轮计数 {"open","close","observe","fail"}。
    """
    totals = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    candidates = []
    for inst in ready:
        try:
            r, cand = analyze_cycle(inst)
            for k in totals:
                totals[k] += r.get(k, 0)
            if cand:
                candidates.append(cand)
        except Exception as e:
            log.error(f"❌ {inst}: {e}")
            totals["fail"] += 1

    if not candidates:
        return totals

    # 统计当前 bot 已开持仓（查询失败则本轮不开仓，fail-closed）
    positions = open_bot_instruments()
    if positions is None:
        log.warning("⚠️ 无法读取当前持仓，本轮跳过所有开仓")
        totals["observe"] += len(candidates)
        return totals

    # 分组控仓：每组只选信号最强（signal_strength 最大）的 1 个开仓
    for grp in ("forex", "crypto"):
        grp_candidates = [c for c in candidates if c["group"] == grp]
        if not grp_candidates:
            continue
        open_now = _count_open_in_group(positions, grp)
        grp_limit = _group_max_open(grp)
        if grp_limit > 0 and open_now >= grp_limit:
            log.info(f"📦 {grp} 组已达上限 {open_now}/{grp_limit}，跳过开仓")
            for c in grp_candidates:
                struct_log.skip_signal(c["inst"], "group_cap",
                                       detail=f"{grp}:{open_now}/{grp_limit}",
                                       prob=c["prob"],
                                       prob_long_threshold=c["long_thr"],
                                       prob_short_threshold=c["short_thr"])
            totals["observe"] += len(grp_candidates)
            continue

        grp_candidates.sort(key=lambda x: x["signal_strength"], reverse=True)
        best = grp_candidates[0]
        log.info(f"✅ {grp} 组最优: {best['inst']} (信号分={best['signal_strength']:.4f}) → 开仓")
        _place_candidate(best)
        totals["open"] += 1
        # 同组落选者计为观望
        for c in grp_candidates[1:]:
            struct_log.skip_signal(c["inst"], "not_selected",
                                   detail=f"{grp}:lower_strength",
                                   prob=c["prob"],
                                   prob_long_threshold=c["long_thr"],
                                   prob_short_threshold=c["short_thr"])
        totals["observe"] += len(grp_candidates) - 1

    return totals



if __name__ == "__main__":
    log.info("🚀 Bot v6.8x STARTED")
    log.info(f"环境: {current_env()} | 模型目录: {MODEL_DIR}")

    n_accounts = len(profile["account_ids"])
    if not OANDA_ACCOUNT_ID:
        log.error(
            "❌ 无法解析账号：请检查 --account / run.env / config/.env 的账号配置"
        )
        sys.exit(1)
    source = f"--account {ARGS.account}" if ARGS.account else "配置默认"
    log.info(f"账号: {OANDA_ENV.upper()} ({source}) → {OANDA_ACCOUNT_ID}")
    if OANDA_ACCOUNT_ID not in profile["account_ids"]:
        log.warning(
            f"⚠️ 账号 {OANDA_ACCOUNT_ID} 不在 {OANDA_ENV.upper()} 名单"
            f"（{n_accounts} 个）中，仍按该账号运行"
        )
    if TRADE_MODE == "crypto":
        log.info("下单手数: %s units(加密)", _fmt_units(CRYPTO_LOT_SIZE))
    else:
        log.info(f"下单手数: {LOT_SIZE} units")
        if TRADE_MODE == "forex-crypto":
            log.info("加密下单手数: %s units", _fmt_units(CRYPTO_LOT_SIZE))
    if TRADE_MODE == "crypto":
        log.info(
            "ATR 倍数: SL=%s(加密) | TP=%s(加密)", CRYPTO_SL_MULT, CRYPTO_TP_MULT
        )
    else:
        log.info(
            "ATR 倍数: SL=%s | TP=%s", ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER
        )
        if TRADE_MODE == "forex-crypto":
            log.info("加密 ATR 倍数: SL=%s | TP=%s", CRYPTO_SL_MULT, CRYPTO_TP_MULT)
    if TRADE_MODE == "crypto":
        log.info(
            "信号阈值: LONG=%s(加密) | SHORT=%s(加密)",
            CRYPTO_PROB_LONG_THRESHOLD,
            CRYPTO_PROB_SHORT_THRESHOLD,
        )
    else:
        log.info("信号阈值: LONG=%s | SHORT=%s", PROB_LONG_THRESHOLD, PROB_SHORT_THRESHOLD)
        if TRADE_MODE == "forex-crypto":
            log.info(
                "加密信号阈值: LONG=%s | SHORT=%s",
                CRYPTO_PROB_LONG_THRESHOLD,
                CRYPTO_PROB_SHORT_THRESHOLD,
            )
    if OVERRIDE_MAX_OPEN:
        log.info(
            "分组控仓: 外汇=%s | 加密=%s | 启用=True (每组每轮只开信号最强的 1 个)",
            MAX_OPEN_PER_GROUP_FOREX,
            MAX_OPEN_PER_GROUP_CRYPTO,
        )
    else:
        log.info(
            "分组控仓: 启用=False | 全局上限 MAX_OPEN=%s (0=不限)",
            MAX_OPEN or "不限",
        )
    if DRY_RUN:
        log.warning("🧪 DRY-RUN 模式: 正常运行但不会真正下单/平仓/改单")

    # 品种选择：由 TRADE_MODE 决定（CLI --forex/-f | --crypto/-c | --forex-crypto/-b > run.env TRADE_MODE > forex）
    forex_inst = CFG["instruments"]
    crypto_inst = CFG.get("crypto_instruments", [])
    if TRADE_MODE == "crypto":
        active = list(crypto_inst)
    elif TRADE_MODE == "forex-crypto":
        active = list(forex_inst) + [i for i in crypto_inst if i not in forex_inst]
    else:
        active = list(forex_inst)
    log.info(f"交易模式: {TRADE_MODE}")
    log.info(f"待交易品种: {', '.join(active) or '无'}")
    if TRADE_MODE != "forex":
        log.info(f"加密波动率阈值: {CRYPTO_VOL_THRESHOLD}")

    all_inst = active
    ready, missing = check_models(all_inst)
    if missing:
        log.warning(f"⚠️ 缺少 {len(missing)}/{len(all_inst)} 个品种的模型，先自动训练: {', '.join(missing)}")
        log.warning(f"   将串行训练 {len(missing)} 个品种，耗时较长，请耐心等待（Ctrl-C 可中断，已完成的模型会保留）...")
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
        totals = run_cycle(ready)
        log.info(f"✅ 本轮完成: 开仓 {totals['open']} | 平仓 {totals['close']} | 观望 {totals['observe']} | 失败 {totals['fail']}")
        time.sleep(3600)
