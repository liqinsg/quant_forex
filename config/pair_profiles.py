"""V8.1 Pair Profile Engine (observe-only).

Loads per-instrument style/category from ``config/pair_profiles.yaml`` following the
frozen spec ``docs/V8.1_Pair_Profile_Engine.md``.

Never raises to callers: a missing/invalid YAML falls back to the ``default`` profile.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import yaml

log = logging.getLogger(__name__)

_CONFIG_PATH: Final[Path] = Path(__file__).parent / "pair_profiles.yaml"
_UNKNOWN: Final[str] = "unknown"
_FALLBACK: Final[dict[str, dict[str, Any]]] = {"default": {"style": _UNKNOWN}}
_PROFILE_CACHE: dict[str, dict[str, Any]] | None = None


@dataclass(frozen=True, slots=True)
class PairProfile:
    style: str = _UNKNOWN
    category: str = _UNKNOWN
    volatility_rank: str = _UNKNOWN
    expected_regime: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_mapping(cls, raw: object) -> "PairProfile":
        if not isinstance(raw, dict):
            return cls()
        regimes = raw.get("expected_regime") or []
        if not isinstance(regimes, (list, tuple)):
            regimes = [regimes]
        return cls(
            style=str(raw.get("style", _UNKNOWN)),
            category=str(raw.get("category", _UNKNOWN)),
            volatility_rank=str(raw.get("volatility_rank", _UNKNOWN)),
            expected_regime=tuple(str(r) for r in regimes),
        )


def normalize_instrument(instrument: object) -> str:
    """Normalize to OANDA style (EUR_USD). Never raises."""
    if not isinstance(instrument, str):
        return ""
    value = instrument.strip().upper().replace("/", "_").replace("-", "_")
    if "_" not in value and len(value) == 6:
        return f"{value[:3]}_{value[3:]}"
    return value


def _read_yaml() -> dict[str, dict[str, Any]]:
    if not _CONFIG_PATH.exists():
        log.warning("pair_profiles.yaml not found: %s", _CONFIG_PATH)
        return copy.deepcopy(_FALLBACK)
    try:
        with _CONFIG_PATH.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (yaml.YAMLError, OSError):
        log.exception("Cannot load %s", _CONFIG_PATH)
        return copy.deepcopy(_FALLBACK)
    if not isinstance(data, dict):
        log.warning("pair_profiles.yaml root is not a mapping; using fallback")
        return copy.deepcopy(_FALLBACK)
    return data


def load_pair_profiles() -> dict[str, dict[str, Any]]:
    """Cached raw mapping; returns a copy so callers cannot corrupt the cache."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = _read_yaml()
    return copy.deepcopy(_PROFILE_CACHE)


def reload_pair_profiles() -> None:
    """Drop the cache; next load re-reads the file (hot-reload / tests)."""
    global _PROFILE_CACHE
    _PROFILE_CACHE = None


def get_pair_profile(instrument: object) -> PairProfile:
    profiles = load_pair_profiles()
    raw = profiles.get(normalize_instrument(instrument), profiles.get("default"))
    return PairProfile.from_mapping(raw)


def get_pair_style(instrument: object) -> str:
    return get_pair_profile(instrument).style
