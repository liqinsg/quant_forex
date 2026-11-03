"""
Market regime detection.
"""

from structure.constants import (
    ADX_TREND_THRESHOLD,
    COMPRESSED_RATIO,
    REGIME_COMPRESSED,
    REGIME_RANGING,
    REGIME_TRENDING,
    REGIME_VOLATILE,
    VOLATILE_RATIO,
)
from structure.types import RegimeResult


def classify_regime(
    adx: float,
    atr20: float,
    atr120: float,
) -> RegimeResult:
    """
    Classify market regime.

    Priority:

    1. TRENDING
    2. VOLATILE
    3. COMPRESSED
    4. RANGING
    """

    if adx > ADX_TREND_THRESHOLD:
        regime = REGIME_TRENDING

    elif atr20 > atr120 * VOLATILE_RATIO:
        regime = REGIME_VOLATILE

    elif atr20 < atr120 * COMPRESSED_RATIO:
        regime = REGIME_COMPRESSED

    else:
        regime = REGIME_RANGING

    return RegimeResult(
        regime=regime,
        adx=adx,
        atr20=atr20,
        atr120=atr120,
    )
