"""
Fractal detection engine.
"""
from typing import List

import pandas as pd

from structure.types import FractalPoint

def get_latest_fractal_low(
    df,
    left: int = 3,
    right: int = 3,
):
    """
    Return the latest confirmed fractal low.
    """

    fractals = find_fractal_lows(
        df,
        left=left,
        right=right,
    )

    if not fractals:
        return None

    return fractals[-1]


def get_latest_fractal_high(
    df,
    left: int = 3,
    right: int = 3,
):
    """
    Return the latest confirmed fractal high.
    """

    fractals = find_fractal_highs(
        df,
        left=left,
        right=right,
    )

    if not fractals:
        return None

    return fractals[-1]

def find_fractal_lows(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3,
) -> List[FractalPoint]:

    results = []

    for i in range(left, len(df) - right):

        current = df["low"].iloc[i]

        left_ok = all(
            current < df["low"].iloc[i - j]
            for j in range(1, left + 1)
        )

        right_ok = all(
            current < df["low"].iloc[i + j]
            for j in range(1, right + 1)
        )

        if left_ok and right_ok:

            results.append(
                FractalPoint(
                    price=float(current),
                    index=i,
                    timestamp=str(
                        getattr(
                            df.index[i],
                            "isoformat",
                            lambda: str(df.index[i]),
                        )()
                    ),
                    strength=left + right,
                    fractal_type="fractal_low",
                )
            )

    return results


def find_fractal_highs(
    df: pd.DataFrame,
    left: int = 3,
    right: int = 3,
) -> List[FractalPoint]:

    results = []

    for i in range(left, len(df) - right):

        current = df["high"].iloc[i]

        left_ok = all(
            current > df["high"].iloc[i - j]
            for j in range(1, left + 1)
        )

        right_ok = all(
            current > df["high"].iloc[i + j]
            for j in range(1, right + 1)
        )

        if left_ok and right_ok:

            results.append(
                FractalPoint(
                    price=float(current),
                    index=i,
                    timestamp=str(
                        getattr(
                            df.index[i],
                            "isoformat",
                            lambda: str(df.index[i]),
                        )()
                    ),
                    strength=left + right,
                    fractal_type="fractal_high",
                )
            )

    return results

def get_previous_fractal_low(
    df,
    offset=1,
    left=3,
    right=3,
):
    fractals = find_fractal_lows(
        df,
        left=left,
        right=right,
    )

    if len(fractals) <= offset:
        return None

    return fractals[-(offset + 1)]
