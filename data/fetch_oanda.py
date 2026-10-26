import os, pandas as pd, pytz
import oandapyV20.endpoints.instruments as instruments
from datetime import datetime
from config_oanda import get_oanda_profile

TZ = pytz.timezone(os.getenv("TIMEZONE", "Asia/Singapore"))
# 首次建库回溯月数（须 >= lgb 训练窗口 + 验证窗口，当前 24+3=27）
DEFAULT_LOOKBACK_MONTHS = 36
MAX_PAGES = 50

def get_client():
    return get_oanda_profile()["oanda_client"]

def _candles_to_frame(candles):
    rows = []
    for c in candles:
        m = c["mid"]
        rows.append({"time": pd.to_datetime(c["time"]).astimezone(TZ),
                     "open": float(m["o"]), "high": float(m["h"]), "low": float(m["l"]),
                     "close": float(m["c"]), "volume": int(c["volume"]), "complete": c["complete"]})
    return pd.DataFrame(rows).set_index("time").sort_index()

def fetch_candles(instrument, granularity="H1", count=5000, since=None, lookback_months=DEFAULT_LOOKBACK_MONTHS):
    """拉取 candles，自动分页绕过 OANDA 单次 5000 根上限。

    since=None 时从 (now - lookback_months) 开始，用于首次建库；
    否则从 since 开始增量拉取，直到追平最新。
    """
    client = get_client()
    if since is not None:
        cursor = since.astimezone(pytz.utc)
    else:
        cursor = (pd.Timestamp.now(tz="UTC") - pd.DateOffset(months=lookback_months))

    frames, last_ts = [], None
    for _ in range(MAX_PAGES):
        params = {"granularity": granularity, "count": count, "price": "M",
                  "from": cursor.isoformat()}
        candles = client.request(instruments.InstrumentsCandles(instrument, params))["candles"]
        if not candles:
            break
        frames.append(_candles_to_frame(candles))
        new_last = pd.to_datetime(candles[-1]["time"])
        # 不足一页说明已到最新；时间未推进则防止死循环
        if len(candles) < count or (last_ts is not None and new_last <= last_ts):
            break
        last_ts = new_last
        cursor = new_last + pd.Timedelta(seconds=1)  # 下一段起点，避免重复边界

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "complete"],
                            index=pd.DatetimeIndex([], name="time", tz=TZ))
    df = pd.concat(frames).sort_index()
    return df[~df.index.duplicated(keep="last")]

def update_csv(instrument, granularity="H1", lookback_months=DEFAULT_LOOKBACK_MONTHS):
    path = f"data/datasets/{instrument}_{granularity}.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        df_exist = pd.read_csv(path, index_col="time", parse_dates=["time"])
        df_exist.index = pd.DatetimeIndex(df_exist.index).tz_convert(TZ)
        df_new = fetch_candles(instrument, granularity, since=df_exist.index[-1])
        df = pd.concat([df_exist, df_new])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    else:
        df = fetch_candles(instrument, granularity, lookback_months=lookback_months)
    df.to_csv(path)
    return df
