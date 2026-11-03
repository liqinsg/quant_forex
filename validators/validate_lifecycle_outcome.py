#!/usr/bin/env python3
"""Validate reports/lifecycle_outcome.jsonl against the Outcome v1.0 schema.

Standard library only (no extra dependencies).

Usage:
    python validators/validate_lifecycle_outcome.py [path]

Default path: reports/lifecycle_outcome.jsonl

Exit code: 0 = all rows valid, 2 = validation failures, 1 = usage / file error.

Schema notes (matches what lifecycle_shadow_eval.py emits):
  - Identity/Signal/Trend/Structure fields are copied from the lifecycle row and are
    therefore only checked when present;
  - Outcome fields are written per horizon only once the lookahead window is complete,
    so mfe_/mae_/close_/shadow_r_ pairs are optional as a group but must be internally
    consistent when they appear.
"""

import json
import sys
from pathlib import Path

DEFAULT_PATH = Path("reports/lifecycle_outcome.jsonl")

HORIZONS = ("2h", "24h", "72h")

REQUIRED_FIELDS = {
    "record_id": str,
    "outcome_version": str,
    "timestamp": str,
    "instrument": str,
    "signal_dir": str,
    "prob": (int, float),
    "entry_price": (int, float),
    "atr": (int, float),
}

VALID_SIGNALS = {"LONG", "SHORT", "NEUTRAL"}

VALID_STAGES = {"EARLY", "DEVELOPING", "MATURE", "FADING"}

VALID_REGIMES = {"TRENDING", "VOLATILE", "COMPRESSED", "RANGING", "UNKNOWN"}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_enum(record, field, allowed, errors):
    value = record.get(field)
    if value is None:
        return
    if value not in allowed:
        errors.append(f"{field}: invalid value {value!r}")


def _check_range(record, field, lo=None, hi=None, errors=None):
    if field not in record:
        return
    value = record[field]
    if not _is_number(value):
        return
    if lo is not None and value < lo:
        errors.append(f"{field}: {value} < {lo}")
    if hi is not None and value > hi:
        errors.append(f"{field}: {value} > {hi}")


def validate_record(record):
    errors = []

    # ---- required fields + types ----
    for field, expected in REQUIRED_FIELDS.items():
        if field not in record:
            errors.append(f"missing field: {field}")
            continue
        if not isinstance(record[field], expected):
            errors.append(
                f"{field}: expected {expected}, got {type(record[field]).__name__}"
            )

    # ---- enums ----
    _check_enum(record, "signal_dir", VALID_SIGNALS, errors)
    _check_enum(record, "trend_stage", VALID_STAGES, errors)
    _check_enum(record, "market_regime", VALID_REGIMES, errors)

    # ---- ranges ----
    _check_range(record, "prob", 0.0, 1.0, errors)
    if _is_number(record.get("entry_price")) and record["entry_price"] <= 0:
        errors.append(f"entry_price: must be > 0, got {record['entry_price']}")
    if _is_number(record.get("atr")) and record["atr"] < 0:
        errors.append(f"atr: negative value {record['atr']}")

    # ---- optional tri-state flags ----
    aligned = record.get("aligned")
    if aligned is not None and not isinstance(aligned, bool):
        errors.append(f"aligned: expected bool or null, got {type(aligned).__name__}")

    # ---- per-horizon outcome block ----
    for label in HORIZONS:
        mfe_key, mae_key = f"mfe_{label}_atr", f"mae_{label}_atr"
        close_key, r_key = f"close_{label}", f"shadow_r_{label}"
        present = [k for k in (mfe_key, mae_key, close_key, r_key) if k in record]
        if not present:
            continue
        for key in (mfe_key, mae_key):
            if key not in record:
                errors.append(f"{label}: {key} missing while other horizon fields exist")
            elif not _is_number(record[key]):
                errors.append(f"{key}: expected number, got {type(record[key]).__name__}")
            elif record[key] < 0:
                errors.append(f"{key}: negative value {record[key]}")
        if r_key in record and record[r_key] is not None and not _is_number(record[r_key]):
            errors.append(f"{r_key}: expected number or null, got {type(record[r_key]).__name__}")

    return errors


def validate_jsonl(path):
    total = 0
    passed = 0
    failed = 0
    seen_ids = set()

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as ex:
                failed += 1
                print(f"[FAIL] line={line_no} invalid json: {ex}")
                continue

            if not isinstance(record, dict):
                failed += 1
                print(f"[FAIL] line={line_no} not a JSON object")
                continue

            errors = validate_record(record)

            rid = record.get("record_id")
            if rid is not None:
                if rid in seen_ids:
                    errors.append(f"record_id: duplicate {rid!r}")
                else:
                    seen_ids.add(rid)

            if errors:
                failed += 1
                print(f"[FAIL] line={line_no}")
                for err in errors:
                    print(f"    - {err}")
            else:
                passed += 1

    print()
    print("=" * 60)
    print(f"Total  : {total}")
    print(f"Passed : {passed}")
    print(f"Failed : {failed}")
    print("=" * 60)
    return failed == 0


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PATH

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    ok = validate_jsonl(path)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
