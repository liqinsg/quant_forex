from structure.types import (
    DonchianChannel,
    FractalPoint,
    RegimeResult,
    StructureAnalysis,
)


def test_fractal_point():

    p = FractalPoint(
        price=1.1000,
        index=10,
        timestamp="2026-11-02",
        strength=6,
        fractal_type="fractal_low",
    )

    assert p.price == 1.1000
    assert p.index == 10
    assert p.strength == 6


def test_donchian_channel_type():

    d = DonchianChannel(
        upper=20,
        lower=10,
        width=10,
    )

    assert d.upper == 20
    assert d.lower == 10
    assert d.width == 10


def test_regime_result():

    r = RegimeResult(
        regime="TRENDING",
        adx=30,
        atr20=0.002,
        atr120=0.001,
    )

    assert r.regime == "TRENDING"
    assert r.adx == 30


def test_structure_analysis():

    s = StructureAnalysis(
        symbol="EUR_USD",
        timestamp="2026-11-02",

        sl_boundary=1.0800,
        sl_basis="swing_low",
        sl_strength=8,

        tp1_boundary=1.0920,
        tp1_basis="channel_high",
        tp1_strength=7,

        tp2_boundary=1.1080,
        tp2_basis="d1_swing",
        tp2_strength=9,

        market_regime="TRENDING",

        structure_rr=2.4,

        sl_atr_ref=1.0790,
        tp_atr_ref=1.0910,
    )

    assert s.symbol == "EUR_USD"

    assert s.sl_boundary == 1.0800
    assert s.tp1_boundary == 1.0920
    assert s.tp2_boundary == 1.1080

    assert s.market_regime == "TRENDING"


def test_structure_version_default():

    s = StructureAnalysis(
        symbol="EUR_USD",
        timestamp="2026-11-02",

        sl_boundary=1,
        sl_basis="a",
        sl_strength=1,

        tp1_boundary=1,
        tp1_basis="b",
        tp1_strength=1,

        tp2_boundary=1,
        tp2_basis="c",
        tp2_strength=1,

        market_regime="TRENDING",

        structure_rr=1,

        sl_atr_ref=1,
        tp_atr_ref=1,
    )

    assert s.structure_version == "SDS_v1.3"


def test_structure_analysis_without_tp2():

    s = StructureAnalysis(
        symbol="EUR_USD",
        timestamp="2026-11-02",

        sl_boundary=1.0800,
        sl_basis="swing_low",
        sl_strength=8,

        tp1_boundary=1.0920,
        tp1_basis="channel_high",
        tp1_strength=7,

        market_regime="RANGING",
    )

    assert s.tp2_boundary is None
    assert s.tp2_basis is None
    assert s.tp2_strength == 0

    assert s.structure_rr == 0.0
    assert s.sl_atr_ref == 0.0
    assert s.tp_atr_ref == 0.0

    assert s.structure_version == "SDS_v1.3"
