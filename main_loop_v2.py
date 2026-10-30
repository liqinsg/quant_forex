#!/usr/bin/env python3
"""Main loop entry point — lives in the project root, run with `python main_loop_v2.py`."""
import os
import sys
import argparse
from pathlib import Path

# Make sure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args():
    """CLI args: --live switches to the live account; --account/-a picks an account
    (full a/c id or a 1-based index)."""
    parser = argparse.ArgumentParser(description="Forex OANDA main loop")
    parser.add_argument(
        "--live",
        action="store_true",
        help="switch to the live account (defaults to demo, no short form)",
    )
    parser.add_argument(
        "--account",
        "-a",
        type=str,
        default=None,
        metavar="ID",
        help="select an account: full a/c id (e.g. 101-003-39389016-005) or a 1-based index; "
        "when omitted it resolves via run.env > config/.env > first entry in the list",
    )
    parser.add_argument(
        "--lots",
        type=int,
        default=None,
        metavar="N",
        help="order size N (in units, not contract value); when omitted, reads run.env's "
        "DEMO_LOT_SIZE/LIVE_LOT_SIZE (demo 10000 / live 1)",
    )
    _mode = parser.add_mutually_exclusive_group()
    _mode.add_argument(
        "--forex",
        "-f",
        dest="trade_mode",
        action="store_const",
        const="forex",
        help="trade forex only (default)",
    )
    _mode.add_argument(
        "--crypto",
        "-c",
        dest="trade_mode",
        action="store_const",
        const="crypto",
        help="trade crypto only (BTC_USD/ETH_USD)",
    )
    _mode.add_argument(
        "--forex-crypto",
        "-b",
        dest="trade_mode",
        action="store_const",
        const="forex-crypto",
        help="trade forex and crypto together",
    )
    parser.add_argument(
        "--crypto-lots",
        type=float,
        default=None,
        metavar="N",
        help="crypto order size N (in units, fractional allowed); when omitted, reads run.env's "
        "DEMO_LOT_SIZE_CRYPTO/LIVE_LOT_SIZE_CRYPTO (demo 1 / live 0.01)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="dry-run mode: runs the full flow but never places/closes orders (nothing is sent)",
    )
    return parser.parse_args()


ARGS = _parse_args()

# Critical: the environment must be pinned BEFORE importing config.config_oanda, so live/demo
# each pick up the correct TOKEN and account list (.env loads with override=False and won't
# overwrite it).
os.environ["OANDA_ENV"] = "live" if ARGS.live else "practice"
if ARGS.account:
    # CLI passes an a/c id (or 1-based index); bridge it into config_oanda via a dedicated
    # variable so every module's get_oanda_profile() follows the CLI choice
    # (higher priority than run.env/.env).
    os.environ["OANDA_ACCOUNT_CLI"] = str(ARGS.account)

import time
import warnings
import pandas as pd
from datetime import datetime
from config.config_oanda import get_oanda_profile, is_market_open
from config import load_config, model_dir, current_env, LAST_RETRAIN_FILE, REPORTS_DIR
from config.pairs import is_crypto
from config.correlation_groups import group_of
from core_scoring import (
    CoreConfig,
    compute_group_scores,
    evaluate_group,
    format_group,
    group_key,
)
from utils.logging_utils import get_logger
from utils.structured_logger import StructuredLogger

profile = get_oanda_profile()
OANDA_ACCOUNT_ID = profile["account_id"]
OANDA_TOKEN = profile["token"]
OANDA_ENV = profile["env"]
api = profile["oanda_client"]


def _resolve_lots(cli_lots, env_name):
    """Resolve order size (units): --lots > run.env DEMO_LOT_SIZE/LIVE_LOT_SIZE >
    default (demo 10000 / live 1)."""
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
    """Resolve crypto size (units): --crypto-lots > run.env DEMO/LIVE_LOT_SIZE_CRYPTO >
    default (demo 1 / live 0.01).

    Crypto is measured in units and allows fractions (BTC min 0.001 / ETH min 0.01), so no
    int truncation is applied. This is the shared fallback for every crypto instrument that
    has no per-instrument setting; per-instrument sizes are handled by _crypto_lots_for().
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


def _crypto_lots_for(inst):
    """Size (units) for one crypto instrument: per-instrument override, otherwise the shared
    crypto fallback.

    Crypto instruments have different margin requirements (ETH/BTC/LTC/BCH all differ), so
    per-instrument configuration is supported. Priority:
        --crypto-lots
        > run.env <ENV>_LOT_SIZE_CRYPTO_<INST>   (e.g. LIVE_LOT_SIZE_CRYPTO_ETH_USD)
        > run.env <ENV>_LOT_SIZE_CRYPTO          (shared fallback)
        > code default (demo 1 / live 0.01)
    Crypto is measured in units and allows fractions, so no int truncation is applied.
    """
    if ARGS.crypto_lots is not None:
        return float(ARGS.crypto_lots)  # explicitly set on the CLI: overrides all crypto instruments
    prefix = "LIVE_LOT_SIZE_CRYPTO" if OANDA_ENV == "live" else "DEMO_LOT_SIZE_CRYPTO"
    key = f"{prefix}_{str(inst).strip().upper()}"
    raw = os.getenv(key, "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            log.warning(f"⚠️ Env var {key}={raw} is invalid; falling back to the shared crypto size")
    return CRYPTO_LOT_SIZE


def _resolve_trade_mode(cli_mode):
    """Resolve the trade mode: CLI (--forex/-f | --crypto/-c | --forex-crypto/-b)
    > run.env TRADE_MODE > default 'forex'."""
    if cli_mode:
        return cli_mode
    env_val = os.getenv("TRADE_MODE", "").strip().lower()
    valid = ("forex", "crypto", "forex-crypto")
    if env_val:
        if env_val in valid:
            return env_val
        log.warning(f"⚠️ TRADE_MODE={env_val} is invalid; falling back to forex")
    return "forex"


def _resolve_float(env_key, yaml_path, default):
    """
    Unified config resolution, priority: environment variable > config.yaml > built-in default.
    :param env_key: env var name from run.env, e.g. "PROB_LONG_THRESHOLD"
    :param yaml_path: dotted YAML path, e.g. "signal.prob_long_threshold"
    :param default: fallback default
    :return: resolved float
    """
    raw = os.getenv(env_key, "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            log.warning(f"⚠️ Env var {env_key}={raw} is invalid; falling back to YAML")

    node = CFG
    try:
        for key in yaml_path.split("."):
            node = node[key]
        return float(node)
    except (KeyError, TypeError, ValueError):
        return float(default)


def _resolve_bool(env_key, yaml_path, default):
    """
    Boolean resolution, priority: environment variable > config.yaml > built-in default.
    :param env_key: env var name from run.env, e.g. "CORRELATION_CHECK_ENABLED"
    :param yaml_path: dotted YAML path, e.g. "risk.correlation_check_enabled"
    :param default: fallback default
    :return: resolved bool
    """
    raw = os.getenv(env_key, "").strip().lower()
    if raw:
        if raw in ("1", "true", "yes", "on"):
            return True
        if raw in ("0", "false", "no", "off"):
            return False
        log.warning(f"⚠️ Env var {env_key}={raw} is invalid; falling back to YAML")

    node = CFG
    try:
        for key in yaml_path.split("."):
            node = node[key]
        if isinstance(node, bool):
            return node
        return str(node).strip().lower() in ("1", "true", "yes", "on")
    except (KeyError, TypeError):
        return bool(default)


# Centralized logging: the main loop uses the shared logger, and the structured logger records
# active (BOT) operations (one file per environment)
log = get_logger("main_loop")
struct_log = StructuredLogger(OANDA_ENV)

LOT_SIZE = _resolve_lots(ARGS.lots, OANDA_ENV)
CRYPTO_LOT_SIZE = _resolve_crypto_lots(ARGS.crypto_lots, OANDA_ENV)
TRADE_MODE = _resolve_trade_mode(ARGS.trade_mode)
DRY_RUN = ARGS.dry_run

# Load config — single entry point (includes the pairs from instruments.yaml)
CFG = load_config()
PROB_LONG_THRESHOLD = _resolve_float(
    "PROB_LONG_THRESHOLD", "signal.prob_long_threshold", 0.65
)
PROB_SHORT_THRESHOLD = _resolve_float(
    "PROB_SHORT_THRESHOLD", "signal.prob_short_threshold", 0.35
)
# Crypto-specific signal probability thresholds (fall back to the FX thresholds above if absent)
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
# Crypto-specific ATR multipliers (FX keeps ATR_SL_MULTIPLIER / ATR_TP_MULTIPLIER)
CRYPTO_SL_MULT = _resolve_float(
    "CRYPTO_ATR_SL_MULTIPLIER", "crypto.atr_sl_multiplier", 2.0
)
CRYPTO_TP_MULT = _resolve_float(
    "CRYPTO_ATR_TP_MULTIPLIER", "crypto.atr_tp_multiplier", 2.5
)
# Crypto-specific annualized volatility threshold (FX keeps risk.vol_threshold_annual)
CRYPTO_VOL_THRESHOLD = _resolve_float(
    "CRYPTO_VOL_THRESHOLD", "crypto.vol_threshold_annual", 1.0
)
# Per-group position caps: OVERRIDE_MAX_OPEN=1 caps each group separately; =0 falls back to
# the global MAX_OPEN (default 0 = unlimited)
OVERRIDE_MAX_OPEN = _resolve_float("OVERRIDE_MAX_OPEN", "risk.override_max_open", 0)
MAX_OPEN_PER_GROUP_FOREX = int(
    _resolve_float("MAX_OPEN_PER_GROUP_FOREX", "risk.max_open_per_group_forex", 6)
)
MAX_OPEN_PER_GROUP_CRYPTO = int(
    _resolve_float("MAX_OPEN_PER_GROUP_CRYPTO", "risk.max_open_per_group_crypto", 2)
)
# Global cap (only used when OVERRIDE_MAX_OPEN=0; 0 means unlimited, preserving old behavior)
MAX_OPEN = int(_resolve_float("MAX_OPEN", "risk.max_open", 0))

# Correlation-group risk control: when on, candidates are blocked if their correlation group
# already holds an opposite position (instruments outside the group always pass)
CORRELATION_CHECK_ENABLED = _resolve_bool(
    "CORRELATION_CHECK_ENABLED", "risk.correlation_check_enabled", True
)
# JPY-cross strict mode: True = the JPY group also blocks opposite conflicts; False = the JPY
# group is relaxed and always passes
CORRELATION_JPY_STRICT = _resolve_bool(
    "CORRELATION_JPY_STRICT", "risk.correlation_jpy_strict", True
)

# Core group-level gate (group volatility score): observe = log only / filter = actually block
# All settings come from run.env (config.yaml is untouched); missing values fall back to the
# module defaults
CORE_CFG = CoreConfig.from_env()

# Imports: loaded from the forex_oanda package
from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model, run_full_training
from execution.oanda_conn import (
    place_market_order,
    close_position,
    get_open_position,
    has_open_bot_trade,
    get_open_position_snapshot,
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

# Dry-run mode: intercept every order/close at the execution layer (wire once at startup)
set_dry_run(DRY_RUN)

# Silence GARCH (arch) convergence/starting-value/scale warnings to avoid log spam
for _garch_warn in (ConvergenceWarning, StartingValueWarning, InitialValueWarning, DataScaleWarning):
    warnings.filterwarnings("ignore", category=_garch_warn)

BALANCE = 5000.0
MODEL_DIR = model_dir()
RETRAIN_INTERVAL_DAYS = CFG["lgb"]["retrain_interval_days"]


def _units_for(inst):
    """Order size: crypto uses the per-instrument size, FX uses LOT_SIZE."""
    return _crypto_lots_for(inst) if is_crypto(inst) else LOT_SIZE


def _vol_threshold_for(inst):
    """Crypto uses its own volatility threshold; FX returns None (risk_gate default logic)."""
    return CRYPTO_VOL_THRESHOLD if is_crypto(inst) else None


def _atr_sl_mult_for(inst):
    """ATR stop-loss multiplier: crypto uses CRYPTO_SL_MULT, FX uses ATR_SL_MULTIPLIER."""
    return CRYPTO_SL_MULT if is_crypto(inst) else ATR_SL_MULTIPLIER


def _atr_tp_mult_for(inst):
    """ATR take-profit multiplier: crypto uses CRYPTO_TP_MULT, FX uses ATR_TP_MULTIPLIER."""
    return CRYPTO_TP_MULT if is_crypto(inst) else ATR_TP_MULTIPLIER


def _prob_long_thr_for(inst):
    """Long probability threshold: crypto uses its own threshold, FX uses PROB_LONG_THRESHOLD."""
    return CRYPTO_PROB_LONG_THRESHOLD if is_crypto(inst) else PROB_LONG_THRESHOLD


def _prob_short_thr_for(inst):
    """Short probability threshold: crypto uses its own threshold, FX uses PROB_SHORT_THRESHOLD."""
    return CRYPTO_PROB_SHORT_THRESHOLD if is_crypto(inst) else PROB_SHORT_THRESHOLD


def _group_for(inst):
    """Return the group an instrument belongs to: 'crypto' or 'forex'."""
    return "crypto" if is_crypto(inst) else "forex"


def _group_max_open(group):
    """Per-group open-position cap; when OVERRIDE_MAX_OPEN=0 falls back to global MAX_OPEN
    (0 = unlimited)."""
    if OVERRIDE_MAX_OPEN:
        return MAX_OPEN_PER_GROUP_CRYPTO if group == "crypto" else MAX_OPEN_PER_GROUP_FOREX
    return MAX_OPEN


def _count_open_in_group(positions, group):
    """Count current bot positions that belong to the given group (positions is a list of
    instruments)."""
    return sum(1 for inst in positions if _group_for(inst) == group)


def _correlation_conflict(cand, snapshot):
    """Check whether a candidate conflicts with the bot's existing positions ("opposite direction
    within the same correlation group").

    Rule: if any bot position in the candidate's correlation group points the opposite way ->
    conflict (existing trades take precedence). Instruments outside the group, or the JPY group
    in relaxed mode, always pass.
    Returns (blocked, detail).
    """
    grp = group_of(cand["inst"])
    if not grp:
        return False, ""
    if grp == "jpy_cross" and not CORRELATION_JPY_STRICT:
        return False, ""
    for inst, pos in snapshot.items():
        if inst == cand["inst"]:
            continue
        if group_of(inst) != grp:
            continue
        if pos["direction"] != cand["direction"]:
            return True, f"opposite in same group {inst}={pos['direction']}"
    return False, ""


def _fmt_units(units):
    """Units display: integral values become int (e.g. 10000.0 -> 10000), fractional (crypto)
    values keep their original form."""
    units = float(units)
    return int(units) if units.is_integer() else units


def check_models(instruments):
    """Check whether each pair already has a trained LGB model; returns (ready, missing)."""
    ready, missing = [], []
    for inst in instruments:
        if (MODEL_DIR / f"lgb_{inst}.pkl").exists():
            ready.append(inst)
        else:
            missing.append(inst)
    return ready, missing

def check_weekly_status():
    """Read the weekly retrain daemon's update record and report it (does not block the loop)."""
    if not LAST_RETRAIN_FILE.exists():
        log.warning("⚠️ No weekly update record yet — confirm the weekly daemon is running "
                    "(./deploy.sh daemon)")
        return
    try:
        last = datetime.fromisoformat(LAST_RETRAIN_FILE.read_text().strip())
    except Exception as e:
        log.warning(f"⚠️ Cannot parse the weekly update time: {e}")
        return
    age_days = (datetime.now() - last).days
    log.info(f"Model last updated: {last:%Y-%m-%d} ({age_days} days ago)")
    if age_days > RETRAIN_INTERVAL_DAYS:
        log.warning(f"⚠️ More than {RETRAIN_INTERVAL_DAYS} days since the last update — "
                    "confirm the weekly daemon is healthy")

def calc_garch_vol(returns):
    am = arch_model(returns*100, p=1, q=1, dist="Normal")
    res = am.fit(disp="off")
    fc = res.forecast(horizon=1)
    return float(fc.variance.iloc[-1, 0]**0.5 / 100 * (252**0.5))

def _extract_open_trade_id(resp):
    """Extract the tradeID just opened from an OANDA order response; empty string if absent."""
    try:
        return resp["orderFillTransaction"]["tradeOpened"]["tradeID"]
    except (KeyError, TypeError):
        return ""

def _extract_close_trade_id(resp):
    """Extract the closed tradeID from an OANDA close response; empty string if absent."""
    try:
        for key in ("longOrderFillTransaction", "shortOrderFillTransaction"):
            closed = resp.get(key, {}).get("tradesClosed", [])
            if closed:
                return closed[0]["tradeID"]
    except (AttributeError, TypeError):
        pass
    return ""

def analyze_cycle_old(inst):
    from lifecycle_v1 import calc_lifecycle
    from lifecycle_logger import write_lifecycle_record
    
    """Analyze one instrument: handle market halt / risk limits / close / reverse, and return
    a potential entry candidate.

    Entries are deferred to the grouped position-sizing stage, so this function never places
    orders itself.
    Returns (result, candidate, metrics):
      result    = {"open","close","observe","fail"} ("open" is always 0)
      candidate = None or {"inst","group","direction","prob","signal_strength",
                           "units","sl","tp","close","thr_desc","long_thr","short_thr"}
      metrics   = None or {"inst","atr","close"}, used by Core scoring to build the volatility
                  pool of "visible instruments" (an instrument with valid data counts toward its
                  correlation group even if it does not trade)
    """
    result = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    units = _units_for(inst)

    # Market-halt check: when not tradable, apply the same order/close restrictions as --dry-run
    # and tag the event as market_halt
    if not is_market_open(inst, quiet=True):
        log.info(f"🛑 HOLD {inst} | market halted (tag=market_halt)")
        struct_log.skip_signal(inst, "market_halt")
        result["observe"] += 1
        return result, None, None

    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: no valid data")
        result["fail"] += 1
        return result, None, None

    # "Visibility metrics" for Core scoring: any instrument with a valid bar counts toward its
    # correlation group's volatility pool
    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])
    metrics = {"inst": inst, "atr": atr, "close": close}

    pkg = load_model(inst)
    feats = pkg["feature_cols"]

    # TCN fusion (enabled whenever the artefact exists)
    try:
        from models.train_tcn_extract import get_latest_seq_feature
        sf = get_latest_seq_feature(inst, df)
        for k, v in sf.items():
            latest[k] = v
        feats = feats + list(sf.keys())
    except Exception:
        pass

    if not all(c in latest.columns for c in feats):
        log.warning(f"{inst}: feature mismatch, skipping")
        result["fail"] += 1
        return result, None, metrics

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG, vol_threshold=_vol_threshold_for(inst))

    long_thr = _prob_long_thr_for(inst)
    short_thr = _prob_short_thr_for(inst)
    thr_desc = f"long≥{long_thr:.0%} / short≤{short_thr:.0%}"

    if not ok:
        log.info(f"{inst}: {reason}")
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: risk limit")
        struct_log.skip_signal(inst, "risk_limit", detail=reason, prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
        return result, None, metrics

    if prob > long_thr:
        if pos["units"] < 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_long",
                                 units=_fmt_units(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] <= 0:
            if has_open_bot_trade(inst, units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
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
                return result, None, metrics
            sl = close - _atr_sl_mult_for(inst) * atr
            tp = close + _atr_tp_mult_for(inst) * abs(close - sl)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "LONG",
                "prob": prob, "signal_strength": prob, "units": units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    elif prob < short_thr:
        if pos["units"] > 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_short",
                                 units=_fmt_units(abs(pos["units"])), exit_price=close,
                                 pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] >= 0:
            if has_open_bot_trade(inst, -units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
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
                return result, None, metrics
            sl = close + _atr_sl_mult_for(inst) * atr
            tp = close - _atr_tp_mult_for(inst) * abs(sl - close)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "SHORT",
                "prob": prob, "signal_strength": 1.0 - prob, "units": -units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    else:
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: within neutral band")
        struct_log.skip_signal(inst, "no_signal", prob=prob,
                               prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1

    return result, None, metrics
def analyze_cycle_old1(inst):
    from lifecycle_v1 import calc_lifecycle
    from lifecycle_logger import write_lifecycle_record

    """Analyze one instrument: handle market halt / risk limits / close / reverse, and return
    a potential entry candidate.

    Entries are deferred to the grouped position-sizing stage, so this function never places
    orders itself.
    Returns (result, candidate, metrics):
        result    = {"open","close","observe","fail"} ("open" is always 0)
        candidate = None or {"inst","group","direction","prob","signal_strength",
                            "units","sl","tp","close","thr_desc","long_thr","short_thr"}
        metrics   = None or {"inst","atr","close"}, used by Core scoring to build the
                    volatility pool of "visible instruments" (an instrument with valid data
                    counts toward its correlation group even if it does not trade)
    """
    result = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    units = _units_for(inst)

    # Market-halt check: when not tradable, apply the same order/close restrictions as --dry-run
    # and tag the event as market_halt
    if not is_market_open(inst, quiet=True):
        log.info(f"🛑 HOLD {inst} | market halted (tag=market_halt)")
        struct_log.skip_signal(inst, "market_halt")
        result["observe"] += 1
        return result, None, None

    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: no valid data")
        result["fail"] += 1
        return result, None, None

    # ==================================================
    # 🔭 LIFECYCLE OBSERVER — Zero Side Effect
    # Read data and write logs only; never touches any trading logic
    # ==================================================
    lifecycle = calc_lifecycle(df, inst)

    # "Visibility metrics" for Core scoring: any instrument with a valid bar counts toward its
    # correlation group's volatility pool
    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])
    metrics = {"inst": inst, "atr": atr, "close": close}

    # ---- Write lifecycle record ----
    ts_iso = df.index[-1].isoformat()
    write_lifecycle_record(
        instrument=inst,
        state=lifecycle,
        timestamp=ts_iso,
        prob=0.0,           # placeholder — filled after model predict
        group_score=0.0,    # placeholder
        close_price=close,
        atr=atr,
    )

    pkg = load_model(inst)
    feats = pkg["feature_cols"]

    # TCN fusion (enabled whenever the artefact exists)
    try:
        from models.train_tcn_extract import get_latest_seq_feature
        sf = get_latest_seq_feature(inst, df)
        for k, v in sf.items():
            latest[k] = v
        feats = feats + list(sf.keys())
    except Exception:
        pass

    if not all(c in latest.columns for c in feats):
        log.warning(f"{inst}: feature mismatch, skipping")
        result["fail"] += 1
        return result, None, metrics

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG, vol_threshold=_vol_threshold_for(inst))

    long_thr = _prob_long_thr_for(inst)
    short_thr = _prob_short_thr_for(inst)
    thr_desc = f"long≥{long_thr:.0%} / short≤{short_thr:.0%}"

    # ---- Update lifecycle record with real prob ----
    write_lifecycle_record(
        instrument=inst,
        state=lifecycle,
        timestamp=ts_iso,
        prob=prob,
        group_score=0.0,  # fill when you have it
        close_price=close,
        atr=atr,
    )

    if not ok:
        log.info(f"{inst}: {reason}")
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: risk limit")
        struct_log.skip_signal(inst, "risk_limit", detail=reason, prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
        return result, None, metrics

    if prob > long_thr:
        if pos["units"] < 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_long",
                                units=_fmt_units(abs(pos["units"])), exit_price=close,
                                pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] <= 0:
            if has_open_bot_trade(inst, units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
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
                return result, None, metrics
            sl = close - _atr_sl_mult_for(inst) * atr
            tp = close + _atr_tp_mult_for(inst) * abs(close - sl)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "LONG",
                "prob": prob, "signal_strength": prob, "units": units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    elif prob < short_thr:
        if pos["units"] > 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_short",
                                units=_fmt_units(abs(pos["units"])), exit_price=close,
                                pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] >= 0:
            if has_open_bot_trade(inst, -units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
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
                return result, None, metrics
            sl = close + _atr_sl_mult_for(inst) * atr
            tp = close - _atr_tp_mult_for(inst) * abs(sl - close)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "SHORT",
                "prob": prob, "signal_strength": 1.0 - prob, "units": -units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    else:
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: within neutral band")
        struct_log.skip_signal(inst, "no_signal", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1

    return result, None, metrics

def analyze_cycle(inst):
    from lifecycle_v1 import calc_lifecycle
    from lifecycle_logger import write_lifecycle_record

    """Analyze one instrument: handle market halt / risk limits / close / reverse, and return
    a potential entry candidate.

    Entries are deferred to the grouped position-sizing stage, so this function never places
    orders itself.
    Returns (result, candidate, metrics):
        result    = {"open","close","observe","fail"} ("open" is always 0)
        candidate = None or {"inst","group","direction","prob","signal_strength",
                            "units","sl","tp","close","thr_desc","long_thr","short_thr"}
        metrics   = None or {"inst","atr","close"}, used by Core scoring to build the
                    volatility pool of "visible instruments" (an instrument with valid data
                    counts toward its correlation group even if it does not trade)
    """
    result = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    units = _units_for(inst)

    # Market-halt check
    if not is_market_open(inst, quiet=True):
        log.info(f"🛑 HOLD {inst} | market halted (tag=market_halt)")
        struct_log.skip_signal(inst, "market_halt")
        result["observe"] += 1
        return result, None, None

    df = update_csv(inst)
    df = add_ta_features(df)
    latest = df.dropna().iloc[-1:]
    if len(latest) == 0:
        log.warning(f"{inst}: no valid data")
        result["fail"] += 1
        return result, None, None

    # ==================================================
    # 🔭 LIFECYCLE OBSERVER — zero-intrusion observation starts here
    # ==================================================
    lifecycle = calc_lifecycle(df, inst)
    ts_iso = df.index[-1].isoformat()

    # Core metrics
    atr = float(latest["ta_atr"].iloc[0])
    close = float(latest["close"].iloc[0])
    metrics = {"inst": inst, "atr": atr, "close": close}

    pkg = load_model(inst)
    feats = pkg["feature_cols"]

    # TCN fusion
    try:
        from models.train_tcn_extract import get_latest_seq_feature
        sf = get_latest_seq_feature(inst, df)
        for k, v in sf.items():
            latest[k] = v
        feats = feats + list(sf.keys())
    except Exception:
        pass

    def _write_lc(p, sdir=None, extra=None):
        """Observation write (single, idempotent entry point): one write per (inst, ts).
        aligned = signal direction matches trend direction; None for NEUTRAL."""
        aligned = None if sdir in (None, "NEUTRAL") else (sdir == "LONG") == (lifecycle.trend_dir == 1)
        try:
            write_lifecycle_record(
                instrument=inst, state=lifecycle, timestamp=ts_iso,
                prob=p, group_score=0.0, close_price=close, atr=atr,
                signal_dir=sdir or "NEUTRAL", aligned=aligned, extra=extra,
            )
        except Exception as exc:  # the observation layer must never block the trading flow
            log.warning(f"⚠️ {inst}: lifecycle observation write failed: {exc}")

    if not all(c in latest.columns for c in feats):
        log.warning(f"{inst}: feature mismatch, skipping")
        # No prob available: still write an observation (prob=0) but flag the row via extra as
        # unusable for research, so prob=0.0 is not mistaken for a real prediction in the
        # age x prob analysis
        _write_lc(0.0, extra={"prob_valid": False, "skip_reason": "feature_mismatch"})
        result["fail"] += 1
        return result, None, metrics

    prob = float(pkg["model"].predict(latest[feats])[0])
    ann_vol = calc_garch_vol(df["ta_return_1"].dropna())
    pos = get_open_position(inst)
    ok, reason = enhanced_risk_check(ann_vol, 0.05, 0.0, 0, CFG, vol_threshold=_vol_threshold_for(inst))

    long_thr = _prob_long_thr_for(inst)
    short_thr = _prob_short_thr_for(inst)
    thr_desc = f"long≥{long_thr:.0%} / short≤{short_thr:.0%}"

    # ✅ Single write once prob is known (signal_dir is derived from the thresholds for aligned
    # analysis)
    signal_dir = "LONG" if prob > long_thr else ("SHORT" if prob < short_thr else "NEUTRAL")
    _write_lc(prob, signal_dir)

    if not ok:
        log.info(f"{inst}: {reason}")
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: risk limit")
        struct_log.skip_signal(inst, "risk_limit", detail=reason, prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
        return result, None, metrics

    if prob > long_thr:
        if pos["units"] < 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_long",
                                units=_fmt_units(abs(pos["units"])), exit_price=close,
                                pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] <= 0:
            if has_open_bot_trade(inst, units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
                )
                struct_log.skip_signal(
                    inst, "duplicate_bot_trade", detail="same_direction_open_trade",
                    prob=prob, prob_long_threshold=long_thr, prob_short_threshold=short_thr,
                )
                result["observe"] += 1
                return result, None, metrics
            sl = close - _atr_sl_mult_for(inst) * atr
            tp = close + _atr_tp_mult_for(inst) * abs(close - sl)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "LONG",
                "prob": prob, "signal_strength": prob, "units": units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    elif prob < short_thr:
        if pos["units"] > 0:
            pnl = float(pos["unrealizedPL"])
            resp = close_position(inst)
            log.info(f"🔄 CLOSE {inst} | PnL: {pnl:.2f}")
            struct_log.bot_close(pair=inst, reason="reverse_to_short",
                                units=_fmt_units(abs(pos["units"])), exit_price=close,
                                pnl=pnl, trade_id=_extract_close_trade_id(resp))
            result["close"] += 1
        if pos["units"] >= 0:
            if has_open_bot_trade(inst, -units):
                log.info(
                    f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: "
                    "same-direction bot trade already open (tag=fx_bot_v7)"
                )
                struct_log.skip_signal(
                    inst, "duplicate_bot_trade", detail="same_direction_open_trade",
                    prob=prob, prob_long_threshold=long_thr, prob_short_threshold=short_thr,
                )
                result["observe"] += 1
                return result, None, metrics
            sl = close + _atr_sl_mult_for(inst) * atr
            tp = close - _atr_tp_mult_for(inst) * abs(sl - close)
            return result, {
                "inst": inst, "group": _group_for(inst), "direction": "SHORT",
                "prob": prob, "signal_strength": 1.0 - prob, "units": -units,
                "sl": sl, "tp": tp, "close": close, "atr": atr, "thr_desc": thr_desc,
                "long_thr": long_thr, "short_thr": short_thr,
            }, metrics
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: position already open")
        struct_log.skip_signal(inst, "has_position", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1
    else:
        log.info(f"⏸️ HOLD {inst} | prob: {prob:.1%} | thresholds: {thr_desc} | reason: within neutral band")
        struct_log.skip_signal(inst, "no_signal", prob=prob,
                                prob_long_threshold=long_thr, prob_short_threshold=short_thr)
        result["observe"] += 1

    return result, None, metrics

def _place_candidate(cand):
    """Place the order for a single entry candidate and log it."""
    inst, prob = cand["inst"], cand["prob"]
    direction = cand["direction"]
    resp = place_market_order(inst, cand["units"], cand["sl"], cand["tp"])
    icon = "📈" if direction == "LONG" else "📉"
    log.info(f"{icon} {direction} {inst} p={prob:.2f} SL={cand['sl']:.5f} TP={cand['tp']:.5f}")
    log.info(f"{icon} OPEN {'LONG' if direction == 'LONG' else 'SHORT'} {inst} | "
             f"prob: {prob:.1%} | entry: {cand['close']:.4f}")
    struct_log.bot_open(pair=inst, direction=direction, units=cand["units"],
                        entry_price=cand["close"], trade_id=_extract_open_trade_id(resp),
                        sl=cand["sl"], tp=cand["tp"], score_final=prob)


def run_cycle(ready):
    """One full cycle: analyze first (including closes/reversals), then pick the best entries
    per group.

    Flow (crypto is always separate and never competes with FX for slots):
      1) Analyze every instrument (including closes/reversals), collect entry candidates plus
         each instrument's volatility metrics;
      2) Once all closes are done, take the bot position snapshot (for correlation-conflict
         checks + grouped sizing; if it fails, skip all entries this cycle);
      3) Correlation-conflict filter (when enabled): skip candidates whose correlation group
         already holds an opposite position;
      4) Core group-level gate: compute the group volatility score per correlation group
         (scores never cross groups); if a group's score < threshold the whole group is dropped
         for this cycle (observe = log only / filter = actually block);
      5) FX / crypto each sort by probability (signal_strength) and take the top N
         (FX: N=CORE_MAX_PER_GROUP, default 1, tunable 1~3; crypto: fixed 1).

    Returns this cycle's counters {"open","close","observe","fail"}.
    """
    totals = {"open": 0, "close": 0, "observe": 0, "fail": 0}
    candidates = []
    pool_metrics = {}  # {inst: {"atr","close"}} — every visible instrument this cycle, for Core scoring pools
    for inst in ready:
        try:
            r, cand, metrics = analyze_cycle(inst)
            for k in totals:
                totals[k] += r.get(k, 0)
            if metrics:
                pool_metrics[inst] = metrics
            if cand:
                candidates.append(cand)
        except Exception as e:
            log.error(f"❌ {inst}: {e}")
            totals["fail"] += 1

    if not candidates:
        return totals

    # Take the snapshot only after all closes/reversals are done, so trades closed in this same
    # cycle are not mistaken for open positions
    snapshot = get_open_position_snapshot()
    if snapshot is None:
        log.warning("⚠️ Cannot read current positions; skipping all entries this cycle")
        totals["observe"] += len(candidates)
        return totals
    positions = list(snapshot.keys())

    # Correlation-conflict filter: skip candidates whose correlation group already holds an
    # opposite position this cycle (everything outside the group passes)
    if CORRELATION_CHECK_ENABLED:
        kept = []
        for c in candidates:
            blocked, detail = _correlation_conflict(c, snapshot)
            if blocked:
                log.info(f"🚫 SKIP {c['inst']} | correlation-group conflict: {detail}")
                struct_log.skip_signal(c["inst"], "correlation_conflict",
                                       detail=detail, prob=c["prob"],
                                       prob_long_threshold=c["long_thr"],
                                       prob_short_threshold=c["short_thr"])
                totals["observe"] += 1
            else:
                kept.append(c)
        candidates = kept
    if not candidates:
        return totals

    # ── Core group-level gate (stage 2/3): scores the correlation group, not the instrument ──
    # Group volatility score = max relative volatility in the group (ATR/close) / reference
    # x 100; below the threshold the whole group is dropped for this cycle.
    # observe mode: log only, never block (backward compatible, no behavior change);
    # filter mode: every candidate in a group that fails the gate is skipped this cycle
    # (regardless of how good the individual signals in that group are).
    gate = {}
    for ge in compute_group_scores(pool_metrics, CORE_CFG):
        keep, reason = evaluate_group(ge, CORE_CFG)
        gate[ge["group"]] = (keep, reason)
        log.info(f"🧮 {format_group(ge, CORE_CFG)}")

    kept = []
    for c in candidates:
        if is_crypto(c["inst"]):
            kept.append(c)  # crypto is not subject to the group gate; behavior unchanged
            continue
        keep, reason = gate.get(group_key(c["inst"]), (True, "no volatility data for this group -> pass"))
        if keep or not CORE_CFG.filter_enabled:
            kept.append(c)
        else:
            log.info(f"🚫 SKIP {c['inst']} | correlation-group gate not passed: {reason}")
            struct_log.skip_signal(
                c["inst"], "core_group_gate", detail=reason, prob=c["prob"],
                prob_long_threshold=c["long_thr"],
                prob_short_threshold=c["short_thr"],
            )
            totals["observe"] += 1
    candidates = kept
    if not candidates:
        return totals

    # Pick the best entries: the FX pool takes the top N by probability (CORE_MAX_PER_GROUP,
    # default 1, tunable 1~3); crypto has its own separate slot, kept at 1 per cycle; both groups
    # are still bound by their per-group open-position caps.
    for grp in ("forex", "crypto"):
        grp_candidates = [c for c in candidates if c["group"] == grp]
        if not grp_candidates:
            continue
        open_now = _count_open_in_group(positions, grp)
        grp_limit = _group_max_open(grp)
        if grp_limit > 0 and open_now >= grp_limit:
            log.info(f"📦 {grp} group already at cap {open_now}/{grp_limit}; skipping entries")
            for c in grp_candidates:
                struct_log.skip_signal(c["inst"], "group_cap",
                                       detail=f"{grp}:{open_now}/{grp_limit}",
                                       prob=c["prob"],
                                       prob_long_threshold=c["long_thr"],
                                       prob_short_threshold=c["short_thr"])
            totals["observe"] += len(grp_candidates)
            continue

        grp_candidates.sort(key=lambda x: x["signal_strength"], reverse=True)
        slots = 1 if grp == "crypto" else CORE_CFG.max_per_group
        if grp_limit > 0:
            slots = min(slots, grp_limit - open_now)
        chosen = grp_candidates[:max(slots, 0)]
        for best in chosen:
            log.info(f"✅ {grp} group pick: {best['inst']} (score={best['signal_strength']:.4f}) → open")
            _place_candidate(best)
            totals["open"] += 1
        for c in grp_candidates[len(chosen):]:
            struct_log.skip_signal(c["inst"], "not_selected",
                                   detail=f"{grp}:lower_strength",
                                   prob=c["prob"],
                                   prob_long_threshold=c["long_thr"],
                                   prob_short_threshold=c["short_thr"])
        totals["observe"] += len(grp_candidates) - len(chosen)

    return totals



if __name__ == "__main__":
    log.info("🚀 Bot v6.8x STARTED")
    log.info(f"Environment: {current_env()} | Model dir: {MODEL_DIR}")

    n_accounts = len(profile["account_ids"])
    if not OANDA_ACCOUNT_ID:
        log.error(
            "❌ Cannot resolve an account: check the account settings in --account / run.env / config/.env"
        )
        sys.exit(1)
    source = f"--account {ARGS.account}" if ARGS.account else "config default"
    log.info(f"Account: {OANDA_ENV.upper()} ({source}) → {OANDA_ACCOUNT_ID}")
    if OANDA_ACCOUNT_ID not in profile["account_ids"]:
        log.warning(
            f"⚠️ Account {OANDA_ACCOUNT_ID} is not in the {OANDA_ENV.upper()} list"
            f" ({n_accounts} entries); running with it anyway"
        )

    # Publish runtime state so `deploy.sh status` can show the real environment/account/trade mode
    # (run.env is only the default; CLI --live/-a/-f/-c/-b may override it, so it cannot be used
    # to judge the live runtime state)
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / "bot.runtime").write_text(
            f"OANDA_ENV={OANDA_ENV}\n"
            f"OANDA_ACCOUNT_ID={OANDA_ACCOUNT_ID}\n"
            f"TRADE_MODE={TRADE_MODE}\n",
            encoding="utf-8",
        )
    except Exception as exc:
        log.warning(f"⚠️ Failed to write runtime state: {exc}")
    if TRADE_MODE == "crypto":
        log.info(
            "Order size (crypto, units): %s",
            " | ".join(
                f"{i}={_fmt_units(_crypto_lots_for(i))}"
                for i in CFG.get("crypto_instruments", [])
            ),
        )
    else:
        log.info(f"Order size: {LOT_SIZE} units")
        if TRADE_MODE == "forex-crypto":
            log.info(
                "Crypto order size (units): %s",
                " | ".join(
                    f"{i}={_fmt_units(_crypto_lots_for(i))}"
                    for i in CFG.get("crypto_instruments", [])
                ),
            )
    if TRADE_MODE == "crypto":
        log.info(
            "ATR multipliers: SL=%s (crypto) | TP=%s (crypto)", CRYPTO_SL_MULT, CRYPTO_TP_MULT
        )
    else:
        log.info(
            "ATR multipliers: SL=%s | TP=%s", ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER
        )
        if TRADE_MODE == "forex-crypto":
            log.info("Crypto ATR multipliers: SL=%s | TP=%s", CRYPTO_SL_MULT, CRYPTO_TP_MULT)
    if TRADE_MODE == "crypto":
        log.info(
            "Signal thresholds: LONG=%s (crypto) | SHORT=%s (crypto)",
            CRYPTO_PROB_LONG_THRESHOLD,
            CRYPTO_PROB_SHORT_THRESHOLD,
        )
    else:
        log.info("Signal thresholds: LONG=%s | SHORT=%s", PROB_LONG_THRESHOLD, PROB_SHORT_THRESHOLD)
        if TRADE_MODE == "forex-crypto":
            log.info(
                "Crypto signal thresholds: LONG=%s | SHORT=%s",
                CRYPTO_PROB_LONG_THRESHOLD,
                CRYPTO_PROB_SHORT_THRESHOLD,
            )
    if OVERRIDE_MAX_OPEN:
        log.info(
            "Per-group caps: FX cap=%s | crypto cap=%s | enabled=True "
            "(only the strongest signal per group each cycle)",
            MAX_OPEN_PER_GROUP_FOREX,
            MAX_OPEN_PER_GROUP_CRYPTO,
        )
    else:
        log.info(
            "Per-group caps: enabled=False | global MAX_OPEN=%s (0=unlimited)",
            MAX_OPEN or "unlimited",
        )
    log.info(
        "Correlation-group risk control: enabled=%s | JPY strict=%s",
        CORRELATION_CHECK_ENABLED,
        CORRELATION_JPY_STRICT,
    )
    log.info(
        "Core group gate: mode=%s | score threshold=%s | vol reference=%s (equivalent gate≈%s) "
        "| FX slots per cycle=%s",
        CORE_CFG.mode,
        CORE_CFG.score_threshold,
        CORE_CFG.group_vol_ref,
        f"{CORE_CFG.vol_gate:.4%}",
        CORE_CFG.max_per_group,
    )
    if DRY_RUN:
        log.warning("🧪 DRY-RUN mode: runs normally but never actually places/closes/modifies orders")

    # Instrument selection: driven by TRADE_MODE
    # (CLI --forex/-f | --crypto/-c | --forex-crypto/-b > run.env TRADE_MODE > forex)
    forex_inst = CFG["instruments"]
    crypto_inst = CFG.get("crypto_instruments", [])
    if TRADE_MODE == "crypto":
        active = list(crypto_inst)
    elif TRADE_MODE == "forex-crypto":
        active = list(forex_inst) + [i for i in crypto_inst if i not in forex_inst]
    else:
        active = list(forex_inst)
    log.info(f"Trade mode: {TRADE_MODE}")
    log.info(f"Instruments: {', '.join(active) or 'none'}")
    if TRADE_MODE != "forex":
        log.info(f"Crypto volatility threshold: {CRYPTO_VOL_THRESHOLD}")

    all_inst = active
    ready, missing = check_models(all_inst)
    if missing:
        log.warning(f"⚠️ Missing models for {len(missing)}/{len(all_inst)} instruments; "
                    f"auto-training first: {', '.join(missing)}")
        log.warning(f"   Training {len(missing)} instruments serially; this takes a while, please be "
                    f"patient (Ctrl-C to interrupt; finished models are kept)...")
        for i, inst in enumerate(missing, 1):
            try:
                log.info(f"🏋️ Training {inst} ... ({i}/{len(missing)})")
                run_full_training(inst)
            except Exception as e:
                log.error(f"❌ {inst} training failed: {e}")
        ready, still_missing = check_models(all_inst)
        if still_missing:
            log.error(f"❌ Still missing {len(still_missing)} models; not starting: {', '.join(still_missing)}")
            log.error("   Train with: ./deploy.sh train   |   python models/train_lgb_signal.py <INST>")
            sys.exit(1)
    log.info(f"✅ All models ready {len(ready)}/{len(all_inst)}; starting the trading loop")
    check_weekly_status()

    while True:
        log.info(f"📊 Cycle start: {datetime.now():%Y-%m-%d %H:%M:%S} | instruments: {len(ready)}")
        totals = run_cycle(ready)
        log.info(f"✅ Cycle done: opened {totals['open']} | closed {totals['close']} | "
                 f"held {totals['observe']} | failed {totals['fail']}")
        time.sleep(3600)
