"""
Structure dataclasses and schemas.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class FractalPoint:
    """
    Single fractal structure point.
    """

    price: float
    index: int
    timestamp: str
    strength: int
    fractal_type: str


@dataclass(slots=True)
class StructureAnalysis:
    """
    Final structure analysis result.
    """

    symbol: str
    timestamp: str

    sl_boundary: float
    sl_basis: str
    sl_strength: int

    tp1_boundary: float
    tp1_basis: str
    tp1_strength: int

    tp2_boundary: float
    tp2_basis: str
    tp2_strength: int

    market_regime: str

    structure_rr: float

    sl_atr_ref: float
    tp_atr_ref: float

    structure_version: str = "SDS_v1.3"


@dataclass(slots=True)
class DonchianChannel:
    upper: float
    lower: float
    width: float


"""
Market regime detection result.
"""
@dataclass(slots=True)
class RegimeResult:
    regime: str
    adx: float
    atr20: float
    atr120: float