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