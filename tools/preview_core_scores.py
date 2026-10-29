#!/usr/bin/env python3
"""Core 组级门禁预览 — tools/preview_core_scores.py (v2.0)

用途：在不启动主循环、不发送任何订单的前提下，打印「当前各关联组」的组波动分
与门禁判定结果，并按概率展示外汇候选排序；便于校准 CORE_SCORE_THRESHOLD /
CORE_GROUP_VOL_REF / CORE_MAX_PER_GROUP。

数据来源：本地已缓存的 K 线 CSV（data/<env>/datasets/<INST>_<granularity>.csv）
与已训练模型（models/model_store/<env>/lgb_<INST>.pkl）。
若某品种缺数据或模型，则跳过并给出提示（不会自动联网拉取）。

用法：
    python tools/preview_core_scores.py                # 使用 run.env 的环境(practice)
    python tools/preview_core_scores.py --live         # 使用 live 环境的数据/模型
    python tools/preview_core_scores.py EUR_USD USD_JPY AUD_CAD   # 只看指定品种

口径与主循环一致：
  - 打分对象是「关联组」，打分不跨组；池 = 本轮全部可见品种（外汇），Crypto 不参与；
  - 组波动分 = min(组内最大相对波动率 / CORE_GROUP_VOL_REF, 1) × 100；
  - 低于门槛 → 整组放弃本轮；通过则候选按概率排序（外汇取前 CORE_MAX_PER_GROUP）。
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 关键：在任何 config 导入之前解析 --live 并写死环境，
# 保证使用正确的数据/模型目录（.env / run.env 以 override=False 加载）。
_argv = sys.argv[1:]
if "--live" in _argv:
    os.environ["OANDA_ENV"] = "live"
    _argv.remove("--live")
sys.argv = [sys.argv[0]] + _argv

import pandas as pd

# 导入 config.config_oanda 以加载 .env / run.env（项目规定：仅该模块可读 .env）
from config.config_oanda import get_oanda_profile  # noqa: F401  (触发 load_dotenv 副作用)
from config import load_config, data_dir, model_dir, current_env
from config.pairs import is_crypto, get_all_instruments
from features.build_features import add_ta_features
from models.train_lgb_signal import load_model
from core_scoring import (
    CoreConfig,
    compute_group_scores,
    evaluate_group,
    format_group,
)

# 概率阈值默认值（与主循环 main_loop_v2 的硬编码默认一致）
_DEFAULT_LONG = 0.65
_DEFAULT_SHORT = 0.35

CFG = load_config()
CORE_CFG = CoreConfig.from_env()


def _resolve_instruments(args):
    """品种选择：命令行给定则用之，否则取 instruments.yaml 全部（外汇 + 加密）。"""
    if args:
        return [a.strip().upper() for a in args if a.strip()]
    return get_all_instruments()


def _env_thresholds(inst):
    """按品种解析多/空概率阈值（加密独立阈值），与主循环口径一致。"""
    if is_crypto(inst):
        long_raw = os.getenv("CRYPTO_PROB_LONG_THRESHOLD", "")
        short_raw = os.getenv("CRYPTO_PROB_SHORT_THRESHOLD", "")
    else:
        long_raw = os.getenv("PROB_LONG_THRESHOLD", "")
        short_raw = os.getenv("PROB_SHORT_THRESHOLD", "")

    def _f(raw, default):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    return _f(long_raw, _DEFAULT_LONG), _f(short_raw, _DEFAULT_SHORT)


def _score_one(inst, granularity):
    """计算单个品种的 ATR / 收盘价 / 概率，返回「可见品种指标」；数据或模型缺失返回 None。

    返回 {"inst","tgrp","direction","prob","signal_strength","atr","close"}，
    其中 atr/close 用于计算相对波动率（ATR/收盘价），构成关联组打分池。
    """
    csv_path = data_dir() / f"{inst}_{granularity}.csv"
    model_path = model_dir() / f"lgb_{inst}.pkl"
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        print(f"  ⚠️ {inst}: 缺少数据 {csv_path.name}（可先运行 ./deploy.sh train）")
        return None
    if not model_path.exists():
        print(f"  ⚠️ {inst}: 缺少模型 {model_path.name}（可先运行 ./deploy.sh train）")
        return None

    try:
        df = pd.read_csv(csv_path, index_col="time", parse_dates=["time"])
        df = add_ta_features(df)
        latest = df.dropna().iloc[-1:]
        if len(latest) == 0:
            print(f"  ⚠️ {inst}: 有效数据不足，跳过")
            return None

        pkg = load_model(inst)
        feats = list(pkg["feature_cols"])

        # TCN 融合（存在即启用，与主循环保持一致）
        try:
            from models.train_tcn_extract import get_latest_seq_feature

            sf = get_latest_seq_feature(inst, df)
            for k, v in sf.items():
                latest[k] = v
            feats = feats + list(sf.keys())
        except Exception:
            pass

        if not all(c in latest.columns for c in feats):
            print(f"  ⚠️ {inst}: 特征不匹配，跳过")
            return None

        prob = float(pkg["model"].predict(latest[feats])[0])
        atr = float(latest["ta_atr"].iloc[0])
        close = float(latest["close"].iloc[0])
    except Exception as exc:  # noqa: BLE001 — 单品种失败不影响整体预览
        print(f"  ⚠️ {inst}: 计算失败 ({exc})")
        return None

    long_thr, short_thr = _env_thresholds(inst)
    if prob > long_thr:
        direction, strength = "LONG", prob
    elif prob < short_thr:
        direction, strength = "SHORT", 1.0 - prob
    else:
        direction, strength = "NEUTRAL", None

    return {
        "inst": inst,
        "tgrp": "crypto" if is_crypto(inst) else "forex",
        "direction": direction,
        "prob": prob,
        "signal_strength": strength,
        "atr": atr,
        "close": close,
    }


def main():
    args = sys.argv[1:]
    instruments = _resolve_instruments(args)

    print("=" * 100)
    print("  Core 组级门禁预览 (preview_core_scores v2.0)")
    print("=" * 100)
    print(f"  环境      : {current_env()}")
    print(f"  数据目录  : {data_dir()}")
    print(f"  模型目录  : {model_dir()}")
    print(
        f"  Core 配置 : 模式={CORE_CFG.mode} | 组波动分门槛={CORE_CFG.score_threshold} | "
        f"波动基准={CORE_CFG.group_vol_ref}(等效门槛≈{CORE_CFG.vol_gate:.4%}) | "
        f"外汇每轮名额={CORE_CFG.max_per_group}"
    )
    print(f"  品种数    : {len(instruments)}")
    print("-" * 100)

    candidates = []
    for inst in instruments:
        cand = _score_one(inst, CFG["granularity"])
        if cand:
            candidates.append(cand)

    if not candidates:
        print("❌ 无可评分品种（请先准备数据与模型: ./deploy.sh train）")
        return 1

    # ── 阶段1：关联组门禁（打分对象 = 关联组；Crypto 不参与）──
    pool_metrics = {
        c["inst"]: {"atr": c["atr"], "close": c["close"]}
        for c in candidates
        if not is_crypto(c["inst"])
    }
    groups = compute_group_scores(pool_metrics, CORE_CFG)

    print("\n【关联组门禁】打分对象 = 关联组（打分不跨组）")
    print(f"{'GROUP':<16} {'N':>2} {'MAX_VOL':>9} {'VOL_INST':<10} {'SCORE':>6}  VERDICT")
    print("-" * 100)
    for ge in groups:
        keep, reason = evaluate_group(ge, CORE_CFG)
        mark = "✅" if keep else "🚫"
        print(
            f"{ge['label']:<16} {ge['n']:>2} {ge['max_vol']:>9.4%} "
            f"{ge['vol_inst']:<10} {ge['score']:>6}  {mark} {reason}"
        )
    print("-" * 100)
    print("  " + format_group(groups[0], CORE_CFG) if groups else "  （无外汇可见品种）")

    # ── 阶段2：候选按概率排序（外汇取前 N；Crypto 单列）──
    forex = [c for c in candidates if c["tgrp"] == "forex" and c["signal_strength"] is not None]
    crypto = [c for c in candidates if c["tgrp"] == "crypto" and c["signal_strength"] is not None]
    forex.sort(key=lambda x: x["signal_strength"], reverse=True)
    crypto.sort(key=lambda x: x["signal_strength"], reverse=True)

    print("\n【外汇候选】(按概率排序，通过门禁的组取前 %d)" % CORE_CFG.max_per_group)
    print(f"{'INST':<10} {'DIR':<7} {'PROB':>6} {'STRENGTH':>9}  PICK")
    print("-" * 100)
    for i, c in enumerate(forex):
        pick = "★ 拟开仓" if i < CORE_CFG.max_per_group else ""
        print(
            f"{c['inst']:<10} {c['direction']:<7} {c['prob']:>6.3f} "
            f"{c['signal_strength']:>9.4f}  {pick}"
        )
    if not forex:
        print("  （无外汇候选）")

    if crypto:
        print("\n【加密候选】(不参与组门禁，单列 1 个)")
        print(f"{'INST':<10} {'DIR':<7} {'PROB':>6} {'STRENGTH':>9}  PICK")
        print("-" * 100)
        for i, c in enumerate(crypto):
            pick = "★ 拟开仓" if i < 1 else ""
            print(
                f"{c['inst']:<10} {c['direction']:<7} {c['prob']:>6.3f} "
                f"{c['signal_strength']:>9.4f}  {pick}"
            )

    print("\n  说明: observe 模式下主循环不会拦截任何候选；filter 模式才会整组剔除。")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
