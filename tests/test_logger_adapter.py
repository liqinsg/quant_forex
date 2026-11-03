from structure.logger_adapter import structure_to_extra
from structure.types import StructureAnalysis


def test_structure_to_extra():

    analysis = StructureAnalysis(
        symbol="EUR_USD",
        timestamp="2026-11-02T08:00:00",

        sl_boundary=1.0800,
        sl_basis="swing_low",
        sl_strength=6,

        tp1_boundary=1.0920,
        tp1_basis="channel_high",
        tp1_strength=5,

        market_regime="TRENDING",
    )

    extra = structure_to_extra(analysis)

    assert extra["sl_boundary"] == 1.0800
    assert extra["sl_basis"] == "swing_low"
    assert extra["sl_strength"] == 6

    assert extra["tp1_boundary"] == 1.0920
    assert extra["tp1_basis"] == "channel_high"
    assert extra["tp1_strength"] == 5

    assert extra["market_regime"] == "TRENDING"

    assert extra["structure_version"] == "SDS_v1.3"
