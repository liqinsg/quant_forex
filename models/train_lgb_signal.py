# 文件顶部改导入路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.fetch_oanda import update_csv
from features import build_features
import os, yaml, pandas as pd, numpy as np, lightgbm as lgb, pickle
from sklearn.metrics import roc_auc_score
with open("config/config.yaml") as f: CFG = yaml.safe_load(f)

def load_model(instrument):
    with open(f"models/model_store/lgb_{instrument}.pkl", "rb") as f: return pickle.load(f)

def run_full_training(instrument):
    df = update_csv(instrument, CFG["granularity"])
    df = build_features.add_ta_features(df)
    df = build_features.make_label(df)
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
    os.makedirs("models/model_store", exist_ok=True)
    with open(f"models/model_store/lgb_{instrument}.pkl", "wb") as f: pickle.dump(pkg, f)
    print(f"Mean AUC: {np.mean(aucs):.4f} — saved lgb_{instrument}.pkl")

if __name__ == "__main__":
    import sys
    run_full_training(sys.argv[1] if len(sys.argv)>1 else "EUR_USD")