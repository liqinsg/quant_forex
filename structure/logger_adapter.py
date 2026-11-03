"""
Structure → Lifecycle Logger adapter.

Convert StructureAnalysis into the `extra`
dictionary consumed by lifecycle_logger.
"""

from structure.types import StructureAnalysis


def structure_to_extra(
    analysis: StructureAnalysis,
) -> dict:
    """
    Translate StructureAnalysis into
    lifecycle_logger extra fields.
    """

    return {
        "sl_boundary": analysis.sl_boundary,
        "sl_basis": analysis.sl_basis,
        "sl_strength": analysis.sl_strength,

        "tp1_boundary": analysis.tp1_boundary,
        "tp1_basis": analysis.tp1_basis,
        "tp1_strength": analysis.tp1_strength,

        "market_regime": analysis.market_regime,

        "structure_version": analysis.structure_version,
    }
