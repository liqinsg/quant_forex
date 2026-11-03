import pandas as pd
import pytest

from structure.channel import donchian_channel


def test_donchian_channel():

    df = pd.DataFrame(
        {
            "high": [10, 12, 15, 20, 18],
            "low": [5, 6, 7, 8, 9],
        }
    )

    channel = donchian_channel(
        df,
        period=5,
    )

    assert channel.upper == 20
    assert channel.lower == 5
    assert channel.width == 15


def test_donchian_short_dataset():

    df = pd.DataFrame(
        {
            "high": [10, 11],
            "low": [5, 6],
        }
    )

    with pytest.raises(ValueError):
        donchian_channel(
            df,
            period=5,
        )


def test_donchian_flat_market():

    df = pd.DataFrame(
        {
            "high": [10, 10, 10, 10, 10],
            "low": [10, 10, 10, 10, 10],
        }
    )

    channel = donchian_channel(
        df,
        period=5,
    )

    assert channel.upper == 10
    assert channel.lower == 10
    assert channel.width == 0


def test_donchian_lookback_window():

    df = pd.DataFrame(
        {
            "high": [100, 101, 102, 20, 21, 22],
            "low": [1, 2, 3, 10, 11, 12],
        }
    )

    channel = donchian_channel(
        df,
        period=3,
    )

    assert channel.upper == 22
    assert channel.lower == 10