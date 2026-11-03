import pandas as pd

from structure.fractal import (
    find_fractal_highs,
    find_fractal_lows,
)


def test_fractal_low():

    df = pd.DataFrame({
        "low": [
            10,
            9,
            8,
            7,
            5,
            7,
            8,
            9,
            10,
        ]
    })

    lows = find_fractal_lows(df)

    assert len(lows) == 1

    assert lows[0].index == 4
    assert lows[0].price == 5
    assert lows[0].fractal_type == "fractal_low"


def test_fractal_high():

    df = pd.DataFrame({
        "high": [
            1,
            2,
            3,
            4,
            9,
            4,
            3,
            2,
            1,
        ]
    })

    highs = find_fractal_highs(df)

    assert len(highs) == 1

    assert highs[0].index == 4
    assert highs[0].price == 9
    assert highs[0].fractal_type == "fractal_high"
    
def test_empty_result():

    df = pd.DataFrame({
        "low": [1, 2, 3, 4, 5, 6, 7]
    })

    result = find_fractal_lows(df)

    assert result == []

def test_multiple_fractal_lows():

    df = pd.DataFrame({
        "low": [
            10, 9, 8, 5, 8, 9, 10,
            9, 8, 4, 8, 9, 10
        ]
    })

    lows = find_fractal_lows(
        df,
        left=2,
        right=2,
    )

    assert len(lows) == 2

    assert lows[0].index == 3
    assert lows[0].price == 5

    assert lows[1].index == 9
    assert lows[1].price == 4
    
def test_multiple_fractal_highs():

    df = pd.DataFrame({
        "high": [
            1, 2, 3, 9, 3, 2, 1,
            2, 3, 10, 3, 2, 1
        ]
    })

    highs = find_fractal_highs(
        df,
        left=2,
        right=2,
    )

    assert len(highs) == 2

    assert highs[0].index == 3
    assert highs[0].price == 9

    assert highs[1].index == 9
    assert highs[1].price == 10
    
from structure.fractal import (
    get_latest_fractal_low,
    get_latest_fractal_high,
)

def test_latest_fractal_low():

    df = pd.DataFrame({
        "low": [
            10, 9, 8, 5, 8, 9, 10,
            9, 8, 4, 8, 9, 10
        ]
    })

    latest = get_latest_fractal_low(
        df,
        left=2,
        right=2,
    )

    assert latest is not None

    assert latest.index == 9
    assert latest.price == 4
    
def test_latest_fractal_high():

    df = pd.DataFrame({
        "high": [
            1, 2, 3, 9, 3, 2, 1,
            2, 3, 10, 3, 2, 1
        ]
    })

    latest = get_latest_fractal_high(
        df,
        left=2,
        right=2,
    )

    assert latest is not None

    assert latest.index == 9
    assert latest.price == 10
    
def test_latest_fractal_none():

    df = pd.DataFrame({
        "low": [1, 2, 3, 4, 5, 6, 7]
    })

    latest = get_latest_fractal_low(df)

    assert latest is None
    
