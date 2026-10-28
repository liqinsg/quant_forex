# 文件顶部改导入路径
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 关键：必须在 import config.config_oanda 之前写死环境。
# config_oanda 以 override=False 加载 .env / run.env，因此此处显式设置的
# OANDA_ENV 会覆盖它们里面的 OANDA_ENV=practice。
# --live → 训练写入 models/model_store/live/；否则沿用外部 OANDA_ENV（缺省 practice）。
if "--live" in sys.argv[1:]:
    os.environ["OANDA_ENV"] = "live"
    sys.argv.remove("--live")

from data.fetch_oanda import update_csv
from features import build_features
import yaml, pandas as pd, numpy as np, lightgbm as lgb, pickle
from sklearn.metrics import roc_auc_score
from config import load_config, model_dir, current_env
from config.pairs import is_crypto
CFG = load_config()

def load_model(instrument, env=None):
    with open(model_dir(env) / f"lgb_{instrument}.pkl", "rb") as f: return pickle.load(f)

def run_full_training(instrument, env=None):
    df = update_csv(instrument, CFG["granularity"], env=env)
    df = build_features.add_ta_features(df)
    # 加密波动远高于外汇，使用独立标签阈值（config.yaml 的 crypto.label_threshold_pct）
    label_kw = {}
    if is_crypto(instrument):
        label_kw["threshold_pct"] = CFG.get("crypto", {}).get("label_threshold_pct", 0.01)
    df = build_features.make_label(df, **label_kw)
    feats = build_features.FEATURE_COLS  # add_ta_features 后才被赋值，须在调用后取
    
    # Walk-Forward
    splits, start = [], df.index.min()
    while True:
        train_end = start + pd.DateOffset(months=CFG["lgb"]["train_window_months"])
        valid_end = train_end + pd.DateOffset(months=CFG["lgb"]["valid_window_months"])
        if valid_end > df.index.max(): break
        splits.append(((df.index>=start)&(df.index<train_end),
                       (df.index>=train_end)&(df.index<valid_end)))
        start = valid_end
    
    models, aucs = [], []
    for train_mask, valid_mask in splits:
        tr, va = df.loc[train_mask].dropna(subset=feats), df.loc[valid_mask].dropna(subset=feats)
        lgb_tr = lgb.Dataset(tr[feats], label=tr["y_direction"])
        lgb_va = lgb.Dataset(va[feats], label=va["y_direction"])
        model = lgb.train(CFG["lgb"]["hyperparams"], lgb_tr, valid_sets=[lgb_va],
                          num_boost_round=2000,
                          callbacks=[lgb.early_stopping(50, verbose=False)])
        auc = roc_auc_score(va["y_direction"], model.predict(va[feats]))
        models.append(model); aucs.append(auc); print(f"Fold AUC: {auc:.4f}")
    
    best = models[np.argmax(aucs)]
    pkg = {"model": best, "feature_cols": feats, "instrument": instrument,
           "trained_at": pd.Timestamp.now().isoformat(), "mean_auc": np.mean(aucs)}
    out_dir = model_dir(env)
    os.makedirs(out_dir, exist_ok=True)
    with open(out_dir / f"lgb_{instrument}.pkl", "wb") as f: pickle.dump(pkg, f)
    print(f"Mean AUC: {np.mean(aucs):.4f} — saved lgb_{instrument}.pkl")

if __name__ == "__main__":
    # 用法: python models/train_lgb_signal.py <INST|ALL> [--live]
    # --live 或 OANDA_ENV 决定环境，模型写入 models/model_store/<env>/
    target = sys.argv[1] if len(sys.argv) > 1 else "EUR_USD"
    if target.strip().upper() == "ALL":
        from config.pairs import get_all_instruments

        instruments = get_all_instruments()
        print(f"训练全部 {len(instruments)} 个品种 → 环境 {current_env()} → {model_dir()}")
        for inst in instruments:
            run_full_training(inst)
    else:
        run_full_training(target)