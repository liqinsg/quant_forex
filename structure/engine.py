"""
Structure analysis entry point.
"""

from __future__ import annotations

import pandas as pd

from structure.channel import donchian_channel
from structure.constants import DONCHIAN_PERIOD, REGIME_UNKNOWN
from structure.fractal import (
    get_latest_fractal_high,
    get_latest_fractal_low,
)
from structure.regime import classify_regime
from structure.types import StructureAnalysis


def analyze_structure(
    symbol: str,
    side: str,
    entry_price: float,
    m15_df: pd.DataFrame,
    h1_df: pd.DataFrame,
    d1_df: pd.DataFrame,
    adx: float | None = None,
    atr20: float | None = None,
    atr120: float | None = None,
) -> StructureAnalysis:
    """
    Assemble a StructureAnalysis from the structure components.

    MVP v0.1 scope:

        SL     <- latest fractal   (read from h1_df)
        TP1    <- donchian channel (read from h1_df)
        Regime <- classify_regime  (UNKNOWN when adx/atr inputs missing)
        TP2    <- not implemented (None)
        RR     <- not implemented (0.0)

    m15_df / d1_df are accepted for forward compatibility (finer SL,
    TP2 lookback) but are not consumed yet.
    """

    # entry_price reserved for RR calculation
    side = side.upper()

    channel = donchian_channel(h1_df, period=DONCHIAN_PERIOD)

    if side == "BUY":

        fractal = get_latest_fractal_low(h1_df)
        sl_basis = "swing_low"
        tp1_boundary = channel.upper
        tp1_basis = "channel_high"

    elif side == "SELL":

        fractal = get_latest_fractal_high(h1_df)
        sl_basis = "swing_high"
        tp1_boundary = channel.lower
        tp1_basis = "channel_low"

    else:

        raise ValueError(f"Unknown side: {side}")

    if fractal is None:
        raise ValueError(
            f"{symbol}: no fractal found for side={side}"
        )

    if all(x is not None for x in (adx, atr20, atr120)):
        market_regime = classify_regime(adx, atr20, atr120).regime
    else:
        market_regime = REGIME_UNKNOWN

    timestamp = (
        h1_df.index[-1].isoformat()
        if hasattr(h1_df.index[-1], "isoformat")
        else str(h1_df.index[-1])
    )

    return StructureAnalysis(
        symbol=symbol,
        timestamp=timestamp,

        sl_boundary=fractal.price,
        sl_basis=sl_basis,
        sl_strength=fractal.strength,

        tp1_boundary=tp1_boundary,
        tp1_basis=tp1_basis,
        # TODO v2.2: derive channel strength
        tp1_strength=0,

        market_regime=market_regime,
    )
