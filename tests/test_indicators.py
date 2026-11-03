import numpy as np
import pandas as pd

from structure.indicators import compute_regime_inputs


def _trend_df(n):
    close = np.linspace(1.10, 1.20, n)
    return pd.DataFrame({"high": close + 0.0005, "low": close - 0.0005, "close": close})


def test_not_warmed_up_returns_none():
    # 30 bars: ATR120 is far from warmed up -> None (analyze_structure falls back to UNKNOWN)
    adx, atr20, atr120 = compute_regime_inputs(_trend_df(30))

    assert atr120 is None


def test_warmed_up_returns_floats():
    adx, atr20, atr120 = compute_regime_inputs(_trend_df(300))

    assert isinstance(adx, float)
    assert isinstance(atr20, float)
    assert isinstance(atr120, float)

    assert adx > 0
    assert atr20 > 0
    assert atr120 > 0
