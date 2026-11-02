from structure.regime import classify_regime


def test_trending():

    result = classify_regime(
        adx=30,
        atr20=0.0010,
        atr120=0.0012,
    )

    assert result.regime == "TRENDING"


def test_volatile():

    result = classify_regime(
        adx=15,
        atr20=0.0030,
        atr120=0.0010,
    )

    assert result.regime == "VOLATILE"


def test_compressed():

    result = classify_regime(
        adx=15,
        atr20=0.0006,
        atr120=0.0010,
    )

    assert result.regime == "COMPRESSED"


def test_ranging():

    result = classify_regime(
        adx=15,
        atr20=0.0011,
        atr120=0.0010,
    )

    assert result.regime == "RANGING"


def test_adx_boundary():

    result = classify_regime(
        adx=25,
        atr20=0.0011,
        atr120=0.0010,
    )

    assert result.regime == "RANGING"


def test_volatile_boundary():

    result = classify_regime(
        adx=10,
        atr20=0.0015,
        atr120=0.0010,
    )

    assert result.regime == "RANGING"
