#!/usr/bin/env python3
"""Event-level performance attribution for the lifecycle observer.

Joins reports/lifecycle.jsonl with forward MFE/MAE computed in the SIGNAL
direction (not the trend direction) and aggregates at the EVENT level, so a
single multi-bar trend cannot dominate the statistics.

An "event" = the first concrete signal (LONG/SHORT) of each
(trend_id, signal_dir) pair; later bars of the same run are ignored.

Path-driven (no repo config import) so it runs against any clone:

    python scripts/report_performance_attribution.py \
        --log  <repo>/reports/lifecycle.jsonl \
        --data-dir <repo>/data/practice/datasets

Note: the running observer writes to the *practice* dataset dir (see
reports/bot.runtime -> OANDA_ENV); data/live/datasets is only populated by
live-account runs and may be stale.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import talib

DEFAULT_LOG = Path("reports/lifecycle.jsonl")
DEFAULT_DATA_DIR = Path("data/practice/datasets")

HORIZONS = {"24h": 24, "72h": 72}
ATR_PERIOD = 14
PROB_BUCKETS = [(0.0, 0.50), (0.50, 0.60), (0.60, 0.70), (0.70, 1.01)]


def load_rows(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def prob_bucket(prob):
    if not isinstance(prob, (int, float)):
        return "unknown"
    for lo, hi in PROB_BUCKETS:
        if lo <= prob < hi:
            return f"{lo:.2f}-{hi:.2f}"
    return "unknown"


def load_price_df(path):
    df = pd.read_csv(path, index_col="time", parse_dates=["time"])
    df.index = pd.DatetimeIndex(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("Asia/Singapore")
    df = df.sort_index()
    df["ta_atr"] = talib.ATR(df["high"], df["low"], df["close"], ATR_PERIOD)
    return df


def forward_mfe_mae(df, start_ts, n_bars, direction):
    """MFE/MAE over the next n_bars, ATR-normalized, measured in the SIGNAL
    direction (+1 LONG / -1 SHORT). None when the future window is incomplete."""
    ts = pd.Timestamp(start_ts)
    if ts.tz is None and df.index.tz is not None:
        ts = ts.tz_localize(df.index.tz)
    idx = df.index.get_indexer([ts], method="nearest", tolerance=pd.Timedelta("3h"))[0]
    if idx < 0 or idx + n_bars >= len(df):
        return None, None

    window = df.iloc[idx: idx + n_bars + 1]
    start = float(window["close"].iloc[0])
    atr = float(window["ta_atr"].iloc[0])
    if pd.isna(atr) or atr <= 0:
        return None, None

    high = float(window["high"].max())
    low = float(window["low"].min())
    if direction > 0:      # LONG
        mfe, mae = (high - start) / atr, (start - low) / atr
    else:                  # SHORT
        mfe, mae = (start - low) / atr, (high - start) / atr
    return round(mfe, 4), round(mae, 4)


def build_events(rows, data_dir):
    """One event per (instrument, trend_id, signal_dir) = the earliest bar."""
    first = {}
    for r in rows:
        if r.get("signal_dir") not in ("LONG", "SHORT"):
            continue
        key = (r.get("instrument"), r.get("trend_id"), r.get("signal_dir"))
        ts = r.get("timestamp")
        if key not in first or ts < first[key]["timestamp"]:
            first[key] = r

    price_cache = {}
    events = []
    for (inst, trend_id, sig_dir), r in first.items():
        path = data_dir / f"{inst}_H1.csv"
        if not path.exists():
            continue
        if inst not in price_cache:
            price_cache[inst] = load_price_df(path)
        df = price_cache[inst]
        direction = 1 if sig_dir == "LONG" else -1

        ev = {
            "instrument": inst,
            "trend_id": trend_id,
            "signal_dir": sig_dir,
            "aligned": r.get("aligned"),
            "trend_stage": r.get("trend_stage", "UNKNOWN"),
            "prob": r.get("prob"),
            "timestamp": r.get("timestamp"),
        }
        # Each horizon is scored independently: a signal whose 72h window is still
        # open (e.g. a weekend gap leaves < 72 trading bars) can still contribute
        # its 24h outcome instead of being dropped entirely.
        for label, n in HORIZONS.items():
            mfe, mae = forward_mfe_mae(df, r["timestamp"], n, direction)
            ev[f"mfe_{label}"] = mfe
            ev[f"mae_{label}"] = mae
        events.append(ev)
    return events


def _stats(group):
    out = {"events": len(group)}
    for label in HORIZONS:
        vals = [
            e for e in group
            if e[f"mfe_{label}"] is not None and e[f"mae_{label}"] is not None
        ]
        mfe = [e[f"mfe_{label}"] for e in vals]
        mae = [e[f"mae_{label}"] for e in vals]
        out[f"n_{label}"] = len(vals)
        out[f"mfe_{label}"] = float(np.mean(mfe)) if mfe else None
        out[f"mae_{label}"] = float(np.mean(mae)) if mae else None
        wins = [1 for e in vals if e[f"mfe_{label}"] > e[f"mae_{label}"]]
        out[f"win_{label}"] = (len(wins) / len(vals) * 100) if vals else None
    probs = [e["prob"] for e in group if isinstance(e["prob"], (int, float))]
    out["avg_prob"] = float(np.mean(probs)) if probs else None
    return out


def _fmt(v, spec=".2f"):
    return "   n/a" if v is None else format(v, spec)


def print_table(title, events, keyfn, min_events=1):
    groups = defaultdict(list)
    for e in events:
        groups[keyfn(e)].append(e)

    print(f"\n[{title}]")
    header = (
        f"{'group':<22}{'ev':>4}{'n24':>5}{'n72':>5}"
        f"{'win24%':>8}{'mfe24':>8}{'mae24':>8}"
        f"{'win72%':>8}{'mfe72':>8}{'mae72':>8}{'edge72':>8}{'prob':>7}"
    )
    print(header)
    print("-" * len(header))

    for key in sorted(groups, key=lambda k: (-_stats(groups[k])["events"], str(k))):
        s = _stats(groups[key])
        if s["events"] < min_events:
            continue
        edge = None
        if s["mfe_72h"] is not None and s["mae_72h"] is not None:
            edge = s["mfe_72h"] - s["mae_72h"]
        print(
            f"{str(key):<22}{s['events']:>4}{s['n_24h']:>5}{s['n_72h']:>5}"
            f"{_fmt(s['win_24h'], '.1f'):>8}{_fmt(s['mfe_24h']):>8}{_fmt(s['mae_24h']):>8}"
            f"{_fmt(s['win_72h'], '.1f'):>8}{_fmt(s['mfe_72h']):>8}{_fmt(s['mae_72h']):>8}"
            f"{_fmt(edge):>8}{_fmt(s['avg_prob'], '.3f'):>7}"
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--min-events", type=int, default=1)
    args = ap.parse_args()

    rows = load_rows(args.log)
    events = build_events(rows, args.data_dir)
    concrete_rows = sum(1 for r in rows if r.get("signal_dir") in ("LONG", "SHORT"))

    print("=" * 100)
    print("PERFORMANCE ATTRIBUTION  (event-level, MFE/MAE in SIGNAL direction, ATR-normalized)")
    print("=" * 100)
    print(f"log            : {args.log}")
    print(f"data dir       : {args.data_dir}")
    print(f"rows scanned   : {len(rows)}   concrete signal rows: {concrete_rows}")
    print(f"events         : {len(events)}   (trend_id x signal_dir, first bar)")
    print("ev = events ; n24/n72 = events with a complete lookahead window at that horizon")
    print("win% = share with mfe > mae ; edge72 = mfe72 - mae72")

    print_table("ALIGNMENT", events, lambda e: "ALIGNED" if e["aligned"] is True else ("CONTRARIAN" if e["aligned"] is False else "NEUTRAL"), args.min_events)
    print_table("TREND STAGE", events, lambda e: e["trend_stage"], args.min_events)
    print_table("SIGNAL DIRECTION", events, lambda e: e["signal_dir"], args.min_events)
    print_table("PROB BUCKET", events, lambda e: prob_bucket(e["prob"]), args.min_events)
    print_table("INSTRUMENT", events, lambda e: e["instrument"], args.min_events)
    print_table(
        "ALIGNED x STAGE",
        events,
        lambda e: f"{'ALIGNED' if e['aligned'] is True else 'CONTRARIAN' if e['aligned'] is False else 'NEUTRAL'} / {e['trend_stage']}",
        args.min_events,
    )
    print()


if __name__ == "__main__":
    main()
