import pandas as pd
import pytest

from structure.engine import analyze_structure


def _flat_df(n=60, high=1.12, low=1.10):
    return pd.DataFrame(
        {
            "high": [high] * n,
            "low": [low] * n,
        }
    )


def test_buy_analysis():

    df = _flat_df()
    df.loc[30, "low"] = 1.05

    result = analyze_structure(
        symbol="EUR_USD",
        side="BUY",
        entry_price=1.10,
        m15_df=df,
        h1_df=df,
        d1_df=df,
    )

    assert result.sl_boundary > 0
    assert result.tp1_boundary > 0
    assert result.sl_boundary < 1.10

    assert result.sl_basis == "swing_low"
    assert result.tp1_basis == "channel_high"


def test_sell_analysis():

    df = _flat_df()
    df.loc[30, "high"] = 1.20

    result = analyze_structure(
        symbol="EUR_USD",
        side="SELL",
        entry_price=1.12,
        m15_df=df,
        h1_df=df,
        d1_df=df,
    )

    assert result.sl_boundary > 0
    assert result.tp1_boundary > 0
    assert result.sl_boundary > 1.12

    assert result.sl_basis == "swing_high"
    assert result.tp1_basis == "channel_low"


def test_empty_fractal():

    df = pd.DataFrame(
        {
            "high": [1.12] * 60,
            "low": [1.10 + i * 0.0001 for i in range(60)],
        }
    )

    with pytest.raises(ValueError):
        analyze_structure(
            symbol="EUR_USD",
            side="BUY",
            entry_price=1.10,
            m15_df=df,
            h1_df=df,
            d1_df=df,
        )


def test_regime_unknown():

    df = _flat_df()
    df.loc[30, "low"] = 1.05

    result = analyze_structure(
        symbol="EUR_USD",
        side="BUY",
        entry_price=1.10,
        m15_df=df,
        h1_df=df,
        d1_df=df,
    )

    assert result.market_regime == "UNKNOWN"


def test_regime_provided():

    df = _flat_df()
    df.loc[30, "low"] = 1.05

    result = analyze_structure(
        symbol="EUR_USD",
        side="BUY",
        entry_price=1.10,
        m15_df=df,
        h1_df=df,
        d1_df=df,
        adx=30,
        atr20=0.0010,
        atr120=0.0012,
    )

    assert result.market_regime == "TRENDING"
