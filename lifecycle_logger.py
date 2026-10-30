"""Lifecycle observation log writer (observation-only, never touches trading logic).

v1.1.0 changes (backward compatible with old records):
  - Added record_id = f"{instrument}_{timestamp}" as the dedup key (written once per id);
  - Added signal_dir (LONG/SHORT/NEUTRAL) and aligned (signal direction == trend direction);
  - Added trend_start_ts (trend-start bar) so the shadow evaluator can backfill from the
    trend-start anchor;
  - group_score is reserved (assign it directly once Core is wired in, no schema change).
"""
import json
from pathlib import Path
from typing import Optional

from config import PROJECT_ROOT, REPORTS_DIR
from lifecycle_v1 import LIFECYCLE_VERSION, LifecycleState

# Absolute path: the same main log is written no matter which cwd the process starts from
LOG_FILE = REPORTS_DIR / "lifecycle.jsonl"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_seen_ids() -> set:
    """Read the set of already-written record_ids; skip missing files / corrupt lines."""
    seen = set()
    if not LOG_FILE.exists():
        return seen
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rid = json.loads(line).get("record_id")
            except (ValueError, AttributeError):
                continue
            if rid:
                seen.add(rid)
    return seen


def write_lifecycle_record(
    instrument: str,
    state: LifecycleState,
    timestamp: str,
    prob: float = 0.0,
    group_score: float = 0.0,
    close_price: float = 0.0,
    atr: float = 0.0,
    mfe: float = 0.0,
    mae: float = 0.0,
    signal_dir: str = "NEUTRAL",
    aligned: Optional[bool] = None,
    extra: Optional[dict] = None,
) -> str:
    """Write one lifecycle observation record.

    Idempotent: each (instrument, timestamp) is written once; a repeated call returns
    "duplicate:<record_id>" without writing, so retries/multiple entry points cannot
    create duplicate samples.

    :return: "written:<record_id>" or "duplicate:<record_id>"
    """
    record_id = f"{instrument}_{timestamp}"

    if record_id in _load_seen_ids():
        return f"duplicate:{record_id}"

    start_ts = getattr(state, "trend_start_ts", None)
    rec = {
        "record_id": record_id,
        "label_version": LIFECYCLE_VERSION,
        "timestamp": timestamp,
        "instrument": instrument,

        "trend_id": state.trend_id,
        "trend_dir": state.trend_dir,
        "trend_start_ts": start_ts,

        # Signal direction and whether "signal vs trend" is aligned (key tag for
        # later age x prob x alignment analysis)
        "signal_dir": signal_dir,
        "aligned": aligned,

        "trend_stage": state.trend_stage,
        "trend_age": state.trend_age,

        "trend_strength": state.trend_strength,
        "trend_peak_strength": state.trend_peak_strength,
        "trend_disp_atr": state.trend_disp_atr,
        "strength_chg_5": state.strength_chg_5,

        "prob": round(prob, 4),
        "group_score": round(group_score, 4),

        "close": close_price,
        "atr": atr,

        "mfe_fwd_pips": round(mfe, 2),
        "mae_fwd_pips": round(mae, 2),

        # Shadow backfill placeholders (written to the outcome file by lifecycle_shadow_eval.py,
        # never written back into this log)
        "mfe_24h_atr": 0.0,
        "mae_24h_atr": 0.0,
        "mfe_72h_atr": 0.0,
        "mae_72h_atr": 0.0,
    }
    if extra:
        rec.update(extra)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return f"written:{record_id}"
