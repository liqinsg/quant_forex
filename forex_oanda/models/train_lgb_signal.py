# 文件顶部改导入路径
from ..data.fetch_oanda import update_csv
from ..features.build_features import add_ta_features, make_label, FEATURE_COLS
import os, yaml, pandas as pd, numpy as np, lightgbm as lgb, pickle
from sklearn.metrics import roc_auc_score
with open("config/config.yaml") as f: CFG = yaml.safe_load(f)

def load_model(instrument):
    with open(f"models/model_store/lgb_{instrument}.pkl", "rb") as f: return pickle.load(f)

def run_full_training(instrument):
    from data.fetch_oanda import update_csv
    from features.build_features import add_ta_features, make_label, FEATURE_COLS
    df = update_csv(instrument, CFG["granularity"])
    df = add_ta_features(df)
    df = make_label(df)
    
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
        tr, va = df.loc[train_mask].dropna(subset=FEATURE_COLS), df.loc[valid_mask].dropna(subset=FEATURE_COLS)
        lgb_tr = lgb.Dataset(tr[FEATURE_COLS], label=tr["y_direction"])
        lgb_va = lgb.Dataset(va[FEATURE_COLS], label=va["y_direction"])
        model = lgb.train(CFG["lgb"]["hyperparams"], lgb_tr, valid_sets=[lgb_va],
                          num_boost_round=2000, early_stopping_rounds=50, verbose_eval=False)
        auc = roc_auc_score(va["y_direction"], model.predict(va[FEATURE_COLS]))
        models.append(model); aucs.append(auc); print(f"Fold AUC: {auc:.4f}")
    
    best = models[np.argmax(aucs)]
    pkg = {"model": best, "feature_cols": FEATURE_COLS, "instrument": instrument,
           "trained_at": pd.Timestamp.now().isoformat(), "mean_auc": np.mean(aucs)}
    os.makedirs("models/model_store", exist_ok=True)
    with open(f"models/model_store/lgb_{instrument}.pkl", "wb") as f: pickle.dump(pkg, f)
    print(f"Mean AUC: {np.mean(aucs):.4f} — saved lgb_{instrument}.pkl")

if __name__ == "__main__":
    import sys
    run_full_training(sys.argv[1] if len(sys.argv)>1 else "EUR_USD")