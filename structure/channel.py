"""
Donchian Channel calculations.
"""

from __future__ import annotations

import pandas as pd

from structure.types import DonchianChannel


def donchian_channel(
    df: pd.DataFrame,
    period: int = 50,
) -> DonchianChannel:
    """
    Calculate Donchian channel.

    Parameters
    ----------
    df : DataFrame
        Must contain:
            high
            low

    period : int
        Rolling lookback window.

    Returns
    -------
    DonchianChannel
    """

    if len(df) < period:
        raise ValueError(
            f"Not enough candles: "
            f"{len(df)} < {period}"
        )

    window = df.tail(period)

    upper = float(window["high"].max())
    lower = float(window["low"].min())

    return DonchianChannel(
        upper=upper,
        lower=lower,
        width=upper - lower,
    )
