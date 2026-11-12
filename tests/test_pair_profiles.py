"""V8.1 Pair Profile Engine unit tests (frozen spec Section 12.1)."""
from __future__ import annotations

import pytest

from config import pair_profiles as pp


@pytest.fixture(autouse=True)
def _fresh_cache():
    pp.reload_pair_profiles()
    yield
    pp.reload_pair_profiles()


def _use_yaml(tmp_path, monkeypatch, text: str) -> None:
    f = tmp_path / "pair_profiles.yaml"
    f.write_text(text, encoding="utf-8")
    monkeypatch.setattr(pp, "_CONFIG_PATH", f)


def test_known_pair() -> None:
    assert pp.get_pair_style("EUR_USD") == "mean_reversion"


def test_unknown_pair() -> None:
    assert pp.get_pair_style("XYZ_ABC") == "unknown"


def test_profile_dataclass() -> None:
    prof = pp.get_pair_profile("EUR_USD")
    assert prof.style == "mean_reversion"
    assert prof.category == "major"
    assert prof.volatility_rank == "medium"
    assert prof.expected_regime == ("range", "transition")
    with pytest.raises(Exception):
        prof.style = "hacked"  # frozen dataclass


def test_missing_yaml(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(pp, "_CONFIG_PATH", tmp_path / "nope.yaml")
    assert pp.get_pair_style("EUR_USD") == "unknown"


def test_invalid_yaml(tmp_path, monkeypatch) -> None:
    _use_yaml(tmp_path, monkeypatch, "EUR_USD: [unclosed\n")
    assert pp.get_pair_style("EUR_USD") == "unknown"


def test_root_is_list(tmp_path, monkeypatch) -> None:
    _use_yaml(tmp_path, monkeypatch, "- a\n- b\n")
    assert pp.get_pair_style("EUR_USD") == "unknown"


def test_entry_not_dict(tmp_path, monkeypatch) -> None:
    _use_yaml(tmp_path, monkeypatch, "EUR_USD: oops\ndefault: {style: x}\n")
    assert pp.get_pair_style("EUR_USD") == "unknown"


def test_expected_regime_scalar(tmp_path, monkeypatch) -> None:
    _use_yaml(tmp_path, monkeypatch, "EUR_USD: {style: s, expected_regime: range}\n")
    assert pp.get_pair_profile("EUR_USD").expected_regime == ("range",)


def test_cache_not_mutable() -> None:
    pp.load_pair_profiles()["EUR_USD"]["style"] = "hacked"
    assert pp.get_pair_style("EUR_USD") == "mean_reversion"


def test_reload_picks_up_change(tmp_path, monkeypatch) -> None:
    _use_yaml(tmp_path, monkeypatch, "EUR_USD: {style: a}\n")
    assert pp.get_pair_style("EUR_USD") == "a"
    _use_yaml(tmp_path, monkeypatch, "EUR_USD: {style: b}\n")
    pp.reload_pair_profiles()
    assert pp.get_pair_style("EUR_USD") == "b"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("eurusd", "EUR_USD"),
        ("EURUSD", "EUR_USD"),
        ("eur_usd", "EUR_USD"),
        ("EUR/USD", "EUR_USD"),
        ("eur-usd", "EUR_USD"),
        (" AUD_NZD ", "AUD_NZD"),
        ("XAU", "XAU"),
        (None, ""),
        (123, ""),
        ({}, ""),
    ],
)
def test_normalize(raw, expected: str) -> None:
    assert pp.normalize_instrument(raw) == expected
