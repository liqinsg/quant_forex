import pandas as pd

from lifecycle_shadow_eval import calc_mfe_mae, shadow_r, signal_direction


def _df():
    """6 hourly bars; bar-1 is an outlier high/low so LONG vs SHORT differ."""
    idx = pd.date_range("2026-01-01", periods=6, freq="h", tz="Asia/Singapore")
    return pd.DataFrame(
        {
            "close": [100, 101, 102, 103, 104, 105],
            "high": [100, 106, 102, 103, 104, 105],
            "low": [100, 97, 99, 100, 101, 102],
            "ta_atr": [1.0] * 6,
        },
        index=idx,
    )


def test_signal_direction_follows_signal_not_trend():
    assert signal_direction({"signal_dir": "LONG", "trend_dir": -1}) == 1
    assert signal_direction({"signal_dir": "SHORT", "trend_dir": 1}) == -1
    # NEUTRAL falls back to the trend direction
    assert signal_direction({"signal_dir": "NEUTRAL", "trend_dir": -1}) == -1
    assert signal_direction({"signal_dir": "NEUTRAL"}) == 0


def test_calc_mfe_mae_is_measured_in_the_given_direction():
    df = _df()
    start = df.index[0]

    mfe_long, mae_long, close_end = calc_mfe_mae(df, start, 2, 1)
    assert (mfe_long, mae_long) == (6.0, 3.0)

    mfe_short, mae_short, _ = calc_mfe_mae(df, start, 2, -1)
    assert (mfe_short, mae_short) == (3.0, 6.0)

    assert close_end == 102.0


def test_calc_mfe_mae_none_when_window_incomplete():
    df = _df()
    mfe, mae, close_end = calc_mfe_mae(df, df.index[4], 2, 1)

    assert mfe is None
    assert mae is None
    assert close_end is None


def test_shadow_r_long_and_short():
    long_rec = {"close": 100.0, "sl_boundary": 98.0}
    assert shadow_r(long_rec, 104.0, 1) == 2.0

    short_rec = {"close": 100.0, "sl_boundary": 102.0}
    assert shadow_r(short_rec, 96.0, -1) == 2.0


def test_shadow_r_none_on_missing_or_inverted_stop():
    # no stop recorded
    assert shadow_r({"close": 100.0}, 104.0, 1) is None
    # stop on the wrong side of entry for a LONG (risk <= 0)
    assert shadow_r({"close": 100.0, "sl_boundary": 101.0}, 104.0, 1) is None
    # no direction
    assert shadow_r({"close": 100.0, "sl_boundary": 98.0}, 104.0, 0) is None
