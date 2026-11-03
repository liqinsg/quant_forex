"""
Indicator helpers for the structure layer.

Regime inputs (ADX / ATR) required by classify_regime, computed from an H1 OHLC
frame per SDS v1.0 §10: ADX(h1, 14), ATR(h1, 20), ATR(h1, 120).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import talib

from structure.constants import REGIME_ADX_PERIOD, REGIME_ATR_FAST, REGIME_ATR_SLOW


def _latest_or_none(values) -> float | None:
    """Last value, or None when it is NaN (indicator still warming up)."""
    value = np.asarray(values)[-1]
    return None if pd.isna(value) else float(value)


def compute_regime_inputs(
    df: pd.DataFrame,
) -> tuple[float | None, float | None, float | None]:
    """Latest (adx, atr20, atr120) on the frame.

    Any value that is still NaN returns None, so analyze_structure safely falls
    back to REGIME_UNKNOWN instead of classifying on garbage.
    """
    high, low, close = df["high"], df["low"], df["close"]
    return (
        _latest_or_none(talib.ADX(high, low, close, timeperiod=REGIME_ADX_PERIOD)),
        _latest_or_none(talib.ATR(high, low, close, timeperiod=REGIME_ATR_FAST)),
        _latest_or_none(talib.ATR(high, low, close, timeperiod=REGIME_ATR_SLOW)),
    )
