import json
import os
import tempfile
import pandas as pd
from pathlib import Path

from config import data_dir
from features.build_features import add_ta_features

INPUT_LOG = Path("reports/lifecycle.jsonl")
OUTPUT_LOG = Path("reports/lifecycle_outcome.jsonl")
# LOOKAHEAD = {"24h": 24, "72h": 72}
# LOOKAHEAD = {"2h": 2, "6h": 6}
LOOKAHEAD = {
    "2h": 2,   # 快速反馈，观察阶段短期行为
    "24h": 24, # 主力周期，实盘参考
    "72h": 72  # 中长期趋势验证
}

def get_price_df(instrument: str) -> pd.DataFrame:
    """Load cached H1 candles and derive ATR without making a network request."""
    path = data_dir() / f"{instrument}_H1.csv"
    if not path.exists():
        raise FileNotFoundError(f"Cached candle file not found: {path}")

    df = pd.read_csv(path, index_col="time", parse_dates=["time"])
    if df.empty:
        raise ValueError(f"Cached candle file is empty: {path}")
    df.index = pd.DatetimeIndex(df.index)
    return add_ta_features(df.sort_index())

def calc_mfe_mae(df, start_ts, n_bars, trend_dir):
    """计算未来N根K线MFE/MAE，ATR归一化"""
    try:
        ts = pd.Timestamp(start_ts)
        idx = df.index.get_indexer([ts], method="nearest")[0]
        if idx < 0:
            return None, None
        time_diff = abs((df.index[idx] - ts).total_seconds())
        if time_diff > 3600 * 3:  # 放宽到3小时容忍
            return None, None
    except Exception:
        return None, None

    if idx < 0 or idx + n_bars >= len(df):
        return None, None  # 尾部数据不足

    window = df.iloc[idx : idx + n_bars + 1]
    start_price = float(window["close"].iloc[0])
    atr_col = "ta_atr" if "ta_atr" in window.columns else "atr"
    atr_base = float(window[atr_col].iloc[0])
    if pd.isna(atr_base) or atr_base <= 0:
        return None, None

    high = window["high"].max()
    low = window["low"].min()

    if trend_dir == 1:   # LONG基准
        mfe = (high - start_price) / atr_base
        mae = (start_price - low) / atr_base
    elif trend_dir == -1: # SHORT基准
        mfe = (start_price - low) / atr_base
        mae = (high - start_price) / atr_base
    else:
        mfe = max(high - start_price, start_price - low) / atr_base
        mae = max(start_price - low, high - start_price) / atr_base

    return round(mfe, 4), round(mae, 4)

def main():
    outcomes_by_id = {}
    if OUTPUT_LOG.exists() and OUTPUT_LOG.stat().st_size > 0:
        with open(OUTPUT_LOG, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if "record_id" not in rec:
                    raise ValueError(
                        f"{OUTPUT_LOG}:{line_number}: missing record_id"
                    )
                outcomes_by_id.setdefault(rec["record_id"], {}).update(rec)

    new = 0
    updated = 0
    pending = 0
    price_data = {}
    seen = set()
    with open(INPUT_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            
            rid = rec.get("record_id")
            if not rid:
                rid = f"{rec['instrument']}_{rec['timestamp']}"
            if rid in seen:
                continue
            seen.add(rid)

            inst = rec["instrument"]
            if inst not in price_data:
                print(f"⏳ Loading cached H1 candles for {inst}...", flush=True)
                price_data[inst] = get_price_df(inst)
                print(f"✅ Loaded {len(price_data[inst])} bars for {inst}", flush=True)
            df = price_data[inst]
            if "high" not in df.columns or "low" not in df.columns:
                raise ValueError(f"{inst}: cached candle data is missing high/low columns")

            out = outcomes_by_id.get(rid, {
                "record_id": rid,
                "timestamp": rec["timestamp"],
                "instrument": inst,
                "trend_stage": rec.get("trend_stage"),
                "trend_age": rec.get("trend_age"),
                "trend_dir": rec.get("trend_dir"),
                "signal_dir": rec.get("signal_dir", "NEUTRAL"),
                "aligned": rec.get("aligned"),
                "prob": rec.get("prob", 0.0),
                "group_score": rec.get("group_score", 0.0),
                "close": rec.get("close"),
                "atr": rec.get("atr"),
            })
            added_outcome = False
            for label, n in LOOKAHEAD.items():
                mfe_key, mae_key = f"mfe_{label}_atr", f"mae_{label}_atr"
                if out.get(mfe_key) is not None and out.get(mae_key) is not None:
                    continue
                mfe, mae = calc_mfe_mae(df, rec["timestamp"], n, rec["trend_dir"])
                if mfe is None or mae is None:
                    pending += 1
                    continue
                out[mfe_key] = mfe
                out[mae_key] = mae
                added_outcome = True

            if added_outcome:
                if rid in outcomes_by_id:
                    updated += 1
                else:
                    new += 1
                outcomes_by_id[rid] = out

    if new or updated:
        OUTPUT_LOG.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=OUTPUT_LOG.parent,
                delete=False,
            ) as f:
                temp_path = Path(f.name)
                for out in outcomes_by_id.values():
                    f.write(json.dumps(out, ensure_ascii=False) + "\n")
            os.replace(temp_path, OUTPUT_LOG)
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    print(
        f"✅ Shadow eval: {new} new, {updated} updated, "
        f"{pending} horizon(s) pending for more future bars "
        f"→ {OUTPUT_LOG}"
    )

if __name__ == "__main__":
    main()