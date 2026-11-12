# Quant Forex V8.1: Pair Profile Engine

**Status:** Spec draft (freeze after Section 12 is closed) | **Mode:** Observe-only, switch-gated | **Risk:** Low

| Field          | Value                                                              |
| -------------- | ------------------------------------------------------------------ |
| Roadmap        | V8 Evolution (V8.1 to V8.6)                                        |
| Principle      | Observe, Validate, Deploy, Measure, Iterate                        |
| Scope          | `config/pair_profiles.*`, lifecycle extension, report script, tests |
| Flag           | `V8_PAIR_PROFILE` (default OFF)                                    |
| Trading impact | None: signals, risk gate, SL/TP, sizing, execution unchanged       |

## Table of Contents

1. [Background](#1-background)
2. [Scope](#2-scope)
3. [Design](#3-design)
4. [Reference implementation](#4-reference-implementation)
5. [Safety checks before any dry-run or demo](#5-safety-checks-before-any-dry-run-or-demo)
6. [Engineering standards](#6-engineering-standards)
7. [Acceptance criteria](#7-acceptance-criteria)
8. [Measurement plan](#8-measurement-plan)
9. [Rollout](#9-rollout)
10. [Roadmap notes for V8.2 to V8.6](#10-roadmap-notes-for-v82-to-v86-carried-forward-with-review-changes)
11. [Doc hygiene resolved in this draft](#11-doc-hygiene-resolved-in-this-draft)
12. [Open questions before freeze](#12-open-questions-before-freeze)

---

## 1. Background

V7 pipeline: Market Data, Feature Engine, Per-Pair LGB Model, Risk Gate, Correlation Gate, Core Group Gate, Position Manager, OANDA Execution.

Three suspected weaknesses (to be **measured** in Section 8, not assumed):

1. Trend signals enter late (EMA/MACD/ATR are lagging), so direction is right but risk-reward is poor.
2. Range-bound markets cause repeated breakout, stop-out, re-breakout whipsaws.
3. Exit logic (SL = ATR x N, TP = ATR x M) treats all instruments alike.

V8 goal: move from predicting direction to also predicting entry quality, exit potential, and regime. V8.1 only labels each signal with the pair's style so later phases can be attributed per style.

---

## 2. Scope

**In scope:** pair profile config, loader, lifecycle field, report script, tests.

**Out of scope (must not change):** signal generation, risk gate, SL/TP, position sizing, execution.

---

## 3. Design

### 3.1 Files

```text
config/pair_profiles.yaml
config/pair_profiles.py
tests/test_pair_profiles.py
scripts/report_pair_profile.py
```

### 3.2 Profile config (single source of truth)

Style labels are **priors to be validated**, not facts. Names use the canonical keys below everywhere (docs, YAML, code).

```yaml
default:
  style: unknown
  category: unknown
  volatility_rank: unknown
  expected_regime: []

EUR_USD:
  style: mean_reversion
  category: major
  volatility_rank: medium
  expected_regime: [range, transition]

GBP_USD:
  style: momentum
  category: major
  volatility_rank: medium
  expected_regime: [trend]

AUD_USD:
  style: mean_reversion
  category: major
  volatility_rank: medium
  expected_regime: [range]

USD_JPY:
  style: breakout
  category: major
  volatility_rank: medium
  expected_regime: [trend, transition]

GBP_JPY:
  style: momentum
  category: cross
  volatility_rank: high
  expected_regime: [trend, volatile]

AUD_JPY:
  style: momentum
  category: cross
  volatility_rank: high
  expected_regime: [trend]

AUD_NZD:
  style: channel
  category: cross
  volatility_rank: low
  expected_regime: [range]

BTC_USD:
  style: volatility
  category: crypto
  volatility_rank: extreme
  expected_regime: [volatile, trend]

ETH_USD:
  style: volatility
  category: crypto
  volatility_rank: extreme
  expected_regime: [volatile, trend]
```

Category, `volatility_rank` and `expected_regime` values above are initial placeholders for V8.2; review before relying on them.

### 3.3 Lifecycle schema

Append one key to the lifecycle record (`reports/lifecycle.jsonl`):

```json
{"pair_profile": {"style": "mean_reversion", "category": "major"}}
```

- Nested dict so V8.2+ can add fields without renaming the key.
- Records without the key mean the observer did not run (for example the feature-mismatch path). Reports must show these as `(absent)`, never as `unknown`.
- Legacy string form (`"pair_profile": "mean_reversion"`) is tolerated by the report script.

---

## 4. Reference implementation

### 4.1 `config/pair_profiles.py`

```python
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
    def from_mapping(cls, raw: object) -> PairProfile:
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
    # Normalize to OANDA style (EUR_USD). Never raises.
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
    # Cached raw mapping; returns a copy so callers cannot corrupt the cache.
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = _read_yaml()
    return copy.deepcopy(_PROFILE_CACHE)


def reload_pair_profiles() -> None:
    # Drop the cache; next load re-reads the file (hot-reload / tests).
    global _PROFILE_CACHE
    _PROFILE_CACHE = None


def get_pair_profile(instrument: object) -> PairProfile:
    profiles = load_pair_profiles()
    raw = profiles.get(normalize_instrument(instrument), profiles.get("default"))
    return PairProfile.from_mapping(raw)


def get_pair_style(instrument: object) -> str:
    return get_pair_profile(instrument).style
```

Notes:

- Failure cache: a missing or invalid YAML caches the fallback for the process lifetime. Call `reload_pair_profiles()` after fixing the file.
- `load_pair_profiles()` is called per signal and deep-copies; if profiling shows cost, return a `MappingProxyType` instead.

### 4.2 Integration in `analyze_cycle()` (switch-gated)

Anchor on function names, not line numbers: `_write_lc(...)` is the single lifecycle write point, `extra` comes from `structure_to_extra(analysis)` and may be `None`. The early feature-mismatch `_write_lc` call intentionally carries no `pair_profile`.

```python
# module level, default OFF
_V8_PAIR_PROFILE: Final[bool] = os.getenv("V8_PAIR_PROFILE", "0") == "1"

# in analyze_cycle(), immediately before _write_lc(prob, signal_dir, extra=extra)
if _V8_PAIR_PROFILE:
    try:
        prof = get_pair_profile(inst)
        new_extra = dict(extra or {})
        new_extra.setdefault(
            "pair_profile", {"style": prof.style, "category": prof.category}
        )
        extra = new_extra  # assign only after success
    except Exception:
        log.exception("pair_profile observer failed: %s", inst)
```

Rules:

- Flag defaults OFF: deploying is a no-op until `V8_PAIR_PROFILE=1`. Rollback is unsetting it.
- `extra` is reassigned only on success, so a failure cannot leave it half-modified.
- `setdefault` protects keys written by **earlier** observers. It does not stop a later observer using plain assignment from overwriting this one, so every V8 observer must use `setdefault`.
- A logged `except Exception` is permitted **only** at observer boundaries (see Section 6).

### 4.3 `scripts/report_pair_profile.py`

```python
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def main(path: str = "reports/lifecycle.jsonl") -> int:
    p = Path(path)
    if not p.exists():
        print(f"No lifecycle file: {p}", file=sys.stderr)
        return 1
    counter: Counter[str] = Counter()
    bad = 0
    with p.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            prof = row.get("pair_profile")
            if prof is None:
                counter["(absent)"] += 1  # observer not run
            elif isinstance(prof, dict):
                counter[str(prof.get("style", "unknown"))] += 1
            else:
                counter[str(prof)] += 1  # legacy string form
    print("\nSignals per Profile\n")
    for key, value in sorted(counter.items()):
        print(f"{key:20} {value}")
    if bad:
        print(f"\nSkipped {bad} malformed lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

This script only counts. The outcome join (lifecycle record to closed trade, giving WR, PF, expectancy, MFE, MAE, hold time) is the real reporting work and is specified in Section 8.

### 4.4 `tests/test_pair_profiles.py`

```python
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
    ],
)
def test_normalize(raw, expected: str) -> None:
    assert pp.normalize_instrument(raw) == expected


def test_profile_dataclass_fields() -> None:
    profile = pp.get_pair_profile("eurusd")
    assert profile.style == "mean_reversion"
    assert isinstance(profile.expected_regime, tuple)
```

Add an integration test: with `V8_PAIR_PROFILE=1` and `get_pair_profile` patched to raise, `analyze_cycle()` still returns normally, `extra` is unchanged, and the exception is logged.

---

## 5. Safety checks before any dry-run or demo

- **Dry-run is a hard code path:** confirm `--dry-run` makes zero order calls (assert or mock the execution client in a test).
- **Demo uses the practice endpoint:** log the OANDA endpoint at startup and assert `fxpractice` for demo runs.
- **Default OFF:** `V8_PAIR_PROFILE` unset means identical V7 behaviour.

---

## 6. Engineering standards

- Python 3.11+, full type hints, `from __future__ import annotations`, mypy clean.
- Module-level `log = logging.getLogger(__name__)`.
- Catch specific exceptions; use `log.exception(...)` without repeating the exception in the message.
- No bare `except:`. A logged `except Exception` is permitted only at observer boundaries so an observer bug can never break trading.
- Missing or corrupt config falls back to a safe default and never crashes.
- Lifecycle writes never overwrite keys from other observers (`setdefault`).
- Instrument identifiers always go through `normalize_instrument()`.
- Observe-only by default; every observer behind its own env flag.

---

## 7. Acceptance criteria

**Functional**

- [ ] No trading behaviour change (flag ON vs OFF produce identical orders in replay/dry-run)
- [ ] Lifecycle backward compatible (new key only; consumers tolerate absence)
- [ ] Works if YAML is missing, invalid, or has a non-dict root or entry
- [ ] Instrument normalization (`EURUSD`, `EUR/USD`, `eur-usd` to `EUR_USD`; non-str to empty)
- [ ] Observer failure is contained and logged; `extra` not partially modified
- [ ] Lifecycle write is non-destructive (`setdefault`)
- [ ] Report script handles missing file, malformed lines, `(absent)` bucket

**Quality**

- [ ] mypy clean, pytest pass, no bare `except:`
- [ ] Type-hint coverage above 95%
- [ ] No silent exception swallowing

---

## 8. Measurement plan

### 8.1 Baseline first (before enabling V8.1)

From V7 attribution data, compute per pair: MFE and MAE distributions (in ATR units), whipsaw rate, and entry offset from the last swing. This turns Problems #1 to #3 into measured numbers.

### 8.2 Definitions (initial values; tune on baseline)

- **Whipsaw:** stopped out within N=12 bars of entry, then price moves beyond the entry level in the original direction within M=24 bars after the stop.
- **MFE captured:** realized PnL divided by MFE, per trade, in ATR units.
- **Drawdown:** max drawdown on the same equity basis for all arms.

### 8.3 Hypotheses (pre-registered, one metric each)

Evaluated once V8.2 regime data exists; V8.1 only collects labels.

- **H1:** Signals on `momentum` pairs in TREND regime have a higher median MFE/ATR than signals on `mean_reversion` pairs.
- **H2:** Signals on `mean_reversion` and `channel` pairs in RANGE regime have a lower whipsaw rate than `momentum` signals taken in RANGE.
- **H3 (label validity):** Style generalizes beyond pair identity: predicting a held-out pair's MFE/ATR from the other pairs sharing its style beats a pooled all-pairs baseline. If not, the labels are noise and V8.2+ must not depend on them.

### 8.4 Sample-size rule (replaces calendar window)

- Observe until each pair x regime bucket has at least 30 signals, or stop at 8 weeks and mark the bucket "insufficient".
- Report bootstrap 95% CIs, not just point estimates.
- A bucket counts as improved only if the CI excludes zero difference.
- Use a multiple-comparison correction across buckets; no post-hoc bucket picking.

### 8.5 Comparison design

Compare against a concurrent shadow baseline (V7 behaviour), never before/after, because regimes shift. Apply identical gates to all arms.

### 8.6 Outcome join (to be specified)

Join lifecycle records to closed trades by signal/trade id, then report Signal Count, Win Rate, Profit Factor, Expectancy, Average Hold Time, MFE, MAE per style and per pair. Define the join key before building `report_pair_profile.py` v2.

### 8.7 Success criteria (numeric placeholders, set from baseline variance)

- Whipsaw rate down at least X% relative to baseline.
- MFE captured up at least Y%.
- Profit Factor not below baseline; max drawdown not above baseline + Z.
- All three hold with CIs in a majority of pairs with sufficient samples.

---

## 9. Rollout

V8.1 to V8.3 are independent zero-impact observers: ship each behind its own flag, in parallel, after tests and a short dry-run smoke test. Keep the full gate (24h dry-run, 7d demo, analysis, promotion on statistics) for V8.4 and later, where trading behaviour can change.

1. Develop: code plus unit tests, mypy, integration test.
2. Smoke: `python main_loop_v2.py --dry-run` with `V8_PAIR_PROFILE=1`, confirm lifecycle key appears and orders are identical.
3. Enable on demo (practice endpoint verified), collect per Section 8.4.
4. Analyze against hypotheses; promote labels only if H3 holds.

Rollback: unset `V8_PAIR_PROFILE`.

---

## 10. Roadmap notes for V8.2 to V8.6 (carried forward, with review changes)

- **V8.2 Regime Engine** (TREND / RANGE / VOLATILE / TRANSITION, observe-only): inputs ADX, ATR20/ATR120, EMA20/EMA50 are lagging, so add hysteresis or minimum dwell time, define TRANSITION precisely, and log previous regime plus confidence.
- **V8.3 Structure Score** (observe-only): `structure_score = mean(available components of aligned, channel, fractal)`, range 0.0 to 1.0. Regime is a separate V8.2 field and is not a component. Missing components are excluded from the mean (log the component count); if none are available the score is null. Confirm components share a 0 to 1 scale.
- **V8.4 Entry Quality Model** (research): use triple-barrier labelling rather than separate MFE and MAE targets (ordering matters); normalize in ATR units; include spread and slippage; purged/embargoed walk-forward CV.
- **V8.5 TP Prediction** (research): predict a conservative quantile (for example 30th to 40th percentile of future MFE) or optimize expectancy, because a TP at the mean MFE is hit only about half the time.
- **V8.6 Adaptive SL** (research): `SL = max(ATR * 1.5, expected_pullback)` must be paired with size = `risk_amount / SL distance`, otherwise a wider stop silently raises risk per trade.

---

## 11. Doc hygiene resolved in this draft

- V8.5 priority typo (eight stars) corrected; priorities should be re-ranked after baseline data.
- 3.2 and 12.2 YAML merged into one enriched config (Section 3.2).
- "Volatility Expansion" naming aligned to the `volatility` key.
- Duplicate `setdefault` paragraph removed; line numbers replaced by function anchors.
- Header changed from "spec frozen" to "spec draft".

---

## 12. Open questions before freeze

- Confirm `from config.pair_profiles import get_pair_profile` import path and that `config/__init__.py` exists (earlier note says yes).
- Confirm the lifecycle join key for the outcome report.
- Confirm whether any external caller needs `get_pair_profile()` as a mapping (add `PairProfile.as_dict()` if so).
- Review the placeholder category, `volatility_rank` and `expected_regime` values in Section 3.2.
- Set N, M, X, Y, Z from the V7 baseline.
