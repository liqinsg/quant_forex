import json
from pathlib import Path
from typing import Optional
from lifecycle_v1 import LIFECYCLE_VERSION, LifecycleState

LOG_FILE = Path("reports/lifecycle.jsonl")
# 关键：自动建目录
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


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
    extra: Optional[dict] = None,
) -> None:
    rec = {
        "label_version": LIFECYCLE_VERSION,
        "timestamp": timestamp,
        "instrument": instrument,

        "trend_id": state.trend_id,
        "trend_dir": state.trend_dir,
        "trend_stage": state.trend_stage,
        "trend_age": state.trend_age,

        "trend_strength": state.trend_strength,
        "trend_peak_strength": state.trend_peak_strength,
        "trend_disp_atr": state.trend_disp_atr,
        "strength_chg_5": state.strength_chg_5,

        "prob": round(prob, 4),
        "group_score": round(group_score, 2),

        "close": close_price,
        "atr": atr,

        "mfe_fwd_pips": round(mfe, 2),
        "mae_fwd_pips": round(mae, 2),
    }
    if extra:
        rec.update(extra)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")