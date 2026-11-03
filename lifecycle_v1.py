"""
Trend Lifecycle v1.0.0
Observation-Only Module — NO trading logic touched
"""
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
from utils.logging_utils import get_logger

log = get_logger("lifecycle")

LIFECYCLE_VERSION = "v1.0.0"


@dataclass
class LifecycleState:
    trend_id: str
    trend_dir: int          # 1=LONG, -1=SHORT, 0=NEUTRAL/RANGE
    trend_age: int          # bars since trend start

    trend_strength: float   # normalized EMA gap: (ema20-ema50)/ATR
    trend_peak_strength: float

    trend_disp_atr: float   # total displacement in ATR since start
    strength_chg_5: float   # strength delta over last 5 bars

    trend_stage: str        # WARMUP / RANGE / EARLY / DEVELOPING / MATURE / FADING
    warmup_ok: bool
    # Added: trend-start candle time (ISO string), so the shadow evaluator can compute future
    # MFE/MAE from both the "trend start" and the "current bar" anchors.
    # Defaults to None to stay compatible with existing callers.
    trend_start_ts: Optional[str] = None


def _make_trend_id(instrument: str, trend_dir: int, start_ts) -> str:
    side = "LONG" if trend_dir > 0 else "SHORT"
    ts_str = pd.Timestamp(start_ts).strftime("%Y%m%d_%H%M")
    return f"{instrument}_{side}_{ts_str}"

def calc_lifecycle(df: pd.DataFrame, instrument: str) -> LifecycleState:
    """
    Required columns: close, [atr_col], [ema20_col], [ema50_col]
    Auto-detects common column naming conventions.
    """
    MIN_BARS = 300
    if len(df) < MIN_BARS:
        return LifecycleState(
            trend_id="", trend_dir=0, trend_age=0,
            trend_strength=0.0, trend_peak_strength=0.0,
            trend_disp_atr=0.0, strength_chg_5=0.0,
            trend_stage="WARMUP", warmup_ok=False,
        )

    # === Auto-detect column names ===
    def pick_col(candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    atr_col = pick_col(["ta_atr", "atr", "atr14", "atr_14"])
    ema20_col = pick_col(["ema20", "ema_20", "ema_fast", "ewm20"])
    ema50_col = pick_col(["ema50", "ema_50", "ema_slow", "ewm50"])

    if not all([atr_col, ema20_col, ema50_col]):
        # Record the missing columns and return WARMUP instead of crashing
        missing = []
        if not atr_col: missing.append("ATR(ta_atr/atr/atr14)")
        if not ema20_col: missing.append("EMA20(ema20/ema_20)")
        if not ema50_col: missing.append("EMA50(ema50/ema_50)")
        log.warning(f"{instrument}: missing lifecycle indicators: {', '.join(missing)}")
        return LifecycleState(
            trend_id="MISSING_COLS", trend_dir=0, trend_age=0,
            trend_strength=0.0, trend_peak_strength=0.0,
            trend_disp_atr=0.0, strength_chg_5=0.0,
            trend_stage="WARMUP", warmup_ok=False,
        )

    # Note: ema20/ema50 (produced by add_ta_features) are already smoothed columns and must
    # not be ewm-smoothed again here. atr_series / diff are whole-column vectors, not scalars,
    # so they are named to avoid ambiguity.
    atr_series = df[atr_col]
    diff = df[ema20_col] - df[ema50_col]
    # ==================== Unchanged from here on ====================

    upper = 0.25 * atr_series
    lower = -0.25 * atr_series

    trend_dir = np.zeros(len(df), dtype=int)
    current_dir = 0
    for i in range(len(df)):
        if diff.iloc[i] > upper.iloc[i]:
            current_dir = 1
        elif diff.iloc[i] < lower.iloc[i]:
            current_dir = -1
        trend_dir[i] = current_dir

    latest_dir = int(trend_dir[-1])
    if latest_dir == 0:
        return LifecycleState(
            trend_id="NONE", trend_dir=0, trend_age=0,
            trend_strength=0.0, trend_peak_strength=0.0,
            trend_disp_atr=0.0, strength_chg_5=0.0,
            trend_stage="RANGE", warmup_ok=True,
        )

    start_idx = len(df) - 1
    for i in range(len(df) - 1, 0, -1):
        if trend_dir[i - 1] != latest_dir and trend_dir[i] == latest_dir:
            start_idx = i
            break

    start_ts = df.index[start_idx]
    start_close = float(df["close"].iloc[start_idx])
    trend_age = len(df) - start_idx - 1

    trend_strength_series = diff * latest_dir / atr_series
    trend_strength = float(trend_strength_series.iloc[-1])
    trend_peak_strength = float(trend_strength_series.iloc[start_idx:].max())

    atr_start = float(atr_series.iloc[start_idx])
    trend_disp_atr = (
        (float(df["close"].iloc[-1]) - start_close) * latest_dir / atr_start
    )

    strength_chg_5 = (
        float(trend_strength_series.iloc[-1]) -
        float(trend_strength_series.iloc[-6])
    ) if len(trend_strength_series) >= 6 else 0.0

    if trend_peak_strength >= 2.0 and trend_strength <= 0.7 * trend_peak_strength:
        trend_stage = "FADING"
    elif trend_age < 12:
        trend_stage = "EARLY"
    elif trend_age < 48:
        trend_stage = "DEVELOPING"
    else:
        trend_stage = "MATURE"

    trend_id = _make_trend_id(instrument, latest_dir, start_ts)

    return LifecycleState(
        trend_id=trend_id, trend_dir=latest_dir, trend_age=trend_age,
        trend_strength=round(trend_strength, 4),
        trend_peak_strength=round(trend_peak_strength, 4),
        trend_disp_atr=round(trend_disp_atr, 4),
        strength_chg_5=round(strength_chg_5, 4),
        trend_stage=trend_stage, warmup_ok=True,
        trend_start_ts=pd.Timestamp(start_ts).isoformat(),
    )
    
def calc_lifecycle_old(df: pd.DataFrame, instrument: str) -> LifecycleState:
    """
    Required columns: close, ta_atr, ema20, ema50
    Returns current bar lifecycle state
    """
    MIN_BARS = 300
    if len(df) < MIN_BARS:
        return LifecycleState(
            trend_id="", trend_dir=0, trend_age=0,
            trend_strength=0.0, trend_peak_strength=0.0,
            trend_disp_atr=0.0, strength_chg_5=0.0,
            trend_stage="WARMUP", warmup_ok=False,
        )

    atr_series = df["ta_atr"]
    diff = df["ema20"] - df["ema50"]
    upper = 0.25 * atr_series
    lower = -0.25 * atr_series

    trend_dir = np.zeros(len(df), dtype=int)
    current_dir = 0
    for i in range(len(df)):
        if diff.iloc[i] > upper.iloc[i]:
            current_dir = 1
        elif diff.iloc[i] < lower.iloc[i]:
            current_dir = -1
        trend_dir[i] = current_dir

    latest_dir = int(trend_dir[-1])
    if latest_dir == 0:
        return LifecycleState(
            trend_id="NONE", trend_dir=0, trend_age=0,
            trend_strength=0.0, trend_peak_strength=0.0,
            trend_disp_atr=0.0, strength_chg_5=0.0,
            trend_stage="RANGE", warmup_ok=True,
        )

    start_idx = len(df) - 1
    for i in range(len(df) - 1, 0, -1):
        if trend_dir[i - 1] != latest_dir and trend_dir[i] == latest_dir:
            start_idx = i
            break

    start_ts = df.index[start_idx]
    start_close = float(df["close"].iloc[start_idx])
    trend_age = len(df) - start_idx - 1

    trend_strength_series = diff * latest_dir / atr_series
    trend_strength = float(trend_strength_series.iloc[-1])
    trend_peak_strength = float(trend_strength_series.iloc[start_idx:].max())

    atr_start = float(atr_series.iloc[start_idx])
    trend_disp_atr = (
        (float(df["close"].iloc[-1]) - start_close) * latest_dir / atr_start
    )

    strength_chg_5 = (
        float(trend_strength_series.iloc[-1]) -
        float(trend_strength_series.iloc[-6])
    ) if len(trend_strength_series) >= 6 else 0.0

    if trend_peak_strength >= 2.0 and trend_strength <= 0.7 * trend_peak_strength:
        trend_stage = "FADING"
    elif trend_age < 12:
        trend_stage = "EARLY"
    elif trend_age < 48:
        trend_stage = "DEVELOPING"
    else:
        trend_stage = "MATURE"

    trend_id = _make_trend_id(instrument, latest_dir, start_ts)

    return LifecycleState(
        trend_id=trend_id, trend_dir=latest_dir, trend_age=trend_age,
        trend_strength=round(trend_strength, 4),
        trend_peak_strength=round(trend_peak_strength, 4),
        trend_disp_atr=round(trend_disp_atr, 4),
        strength_chg_5=round(strength_chg_5, 4),
        trend_stage=trend_stage, warmup_ok=True,
    )