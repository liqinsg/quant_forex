import os, pandas as pd, pytz
from dotenv import load_dotenv
import oandapyV20, oandapyV20.endpoints.instruments as instruments
from datetime import datetime
load_dotenv()
TZ = pytz.timezone(os.getenv("TIMEZONE", "Asia/Singapore"))

def get_client():
    env = "practice" if os.getenv("OANDA_ENV")=="practice" else "live"
    return oandapyV20.API(access_token=os.getenv("OANDA_TOKEN"), environment=env)

def fetch_candles(instrument, granularity="H1", count=5000, since=None):
    client = get_client()
    params = {"granularity": granularity, "count": count, "price": "M"}
    if since: params["from"] = since.astimezone(pytz.utc).isoformat()
    data = client.request(instruments.InstrumentsCandles(instrument, params))
    rows = []
    for c in data["candles"]:
        m = c["mid"]
        rows.append({"time": pd.to_datetime(c["time"]).astimezone(TZ),
                     "open": float(m["o"]), "high": float(m["h"]), "low": float(m["l"]),
                     "close": float(m["c"]), "volume": int(c["volume"]), "complete": c["complete"]})
    return pd.DataFrame(rows).set_index("time").sort_index()

def update_csv(instrument, granularity="H1"):
    path = f"data/datasets/{instrument}_{granularity}.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        df_exist = pd.read_csv(path, index_col="time", parse_dates=["time"])
        df_exist.index = pd.DatetimeIndex(df_exist.index).tz_convert(TZ)
        df_new = fetch_candles(instrument, granularity, since=df_exist.index[-1])
        df = pd.concat([df_exist, df_new]).loc[~pd.IndexSlice[~df_new.index.duplicated()]]
    else:
        df = fetch_candles(instrument, granularity)
    df.to_csv(path)
    return df