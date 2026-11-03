import numpy as np, talib
FEATURE_COLS = []

def add_ta_features(df):
    dfc = df.copy()
    dfc["ta_return_1"] = dfc["close"].pct_change()
    dfc["ta_return_3"] = dfc["close"].pct_change(3)
    dfc["ta_return_5"] = dfc["close"].pct_change(5)
    dfc["ta_vol_10"] = dfc["ta_return_1"].rolling(10).std()
    dfc["ta_vol_20"] = dfc["ta_return_1"].rolling(20).std()
    dfc["ta_atr"] = talib.ATR(dfc["high"], dfc["low"], dfc["close"], 14)
    dfc["ta_sma_20"] = talib.SMA(dfc["close"], 20)
    dfc["ta_sma_60"] = talib.SMA(dfc["close"], 60)
    dfc["ta_rsi"] = talib.RSI(dfc["close"], 14)
    dfc["ta_macd"], dfc["ta_macd_sig"], _ = talib.MACD(dfc["close"])

    dfc["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    dfc["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    
    if "atr14" in df.columns and "ta_atr" not in dfc.columns:
        dfc["ta_atr"] = dfc["atr14"]
    global FEATURE_COLS
    FEATURE_COLS = sorted([c for c in dfc.columns if c.startswith("ta_")])
    return dfc

def make_label(df, horizon=3, threshold_pct=0.002):
    dfc = df.copy()
    future_ret = dfc["close"].shift(-horizon)/dfc["close"] - 1
    dfc["y_direction"] = np.nan
    dfc.loc[future_ret>threshold_pct, "y_direction"] = 1
    dfc.loc[future_ret<-threshold_pct, "y_direction"] = 0
    return dfc.dropna(subset=["y_direction"])