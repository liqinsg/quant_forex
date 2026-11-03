"""
Structure dataclasses and schemas.
"""
from dataclasses import dataclass
from typing import Optional

from structure.constants import REGIME_UNKNOWN, STRUCTURE_VERSION


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

    market_regime: str = REGIME_UNKNOWN

    tp2_boundary: Optional[float] = None
    tp2_basis: Optional[str] = None
    tp2_strength: int = 0

    structure_rr: float = 0.0

    sl_atr_ref: float = 0.0
    tp_atr_ref: float = 0.0

    structure_version: str = STRUCTURE_VERSION


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