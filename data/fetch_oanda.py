import os, pandas as pd, pytz
import oandapyV20.endpoints.instruments as instruments
from datetime import datetime
from config import data_dir
from config.config_oanda import get_oanda_profile
from utils.logging_utils import get_logger

log = get_logger("fetch_oanda")

TZ = pytz.timezone(os.getenv("TIMEZONE", "Asia/Singapore"))
# Lookback months for the initial database build (must be >= LGB training window + validation
# window, currently 24+3=27)
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
    """Fetch candles, paginating automatically to bypass OANDA's 5000-candle-per-call limit.

    When since=None it starts from (now - lookback_months) for the initial full build;
    otherwise it fetches incrementally from since until it catches up with the latest.
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
        # Fewer than a full page means we reached the latest; no time progress guards against loops
        if len(candles) < count or (last_ts is not None and new_last <= last_ts):
            break
        last_ts = new_last
        cursor = new_last + pd.Timedelta(seconds=1)  # next page start, avoids duplicating the boundary

    if not frames:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "complete"],
                            index=pd.DatetimeIndex([], name="time", tz=TZ))
    df = pd.concat(frames).sort_index()
    return df[~df.index.duplicated(keep="last")]

def update_csv(instrument, granularity="H1", lookback_months=DEFAULT_LOOKBACK_MONTHS, env=None):
    """Incrementally update the CSV under data/<env>/datasets/ (env defaults to the current
    OANDA environment).

    If an existing CSV is empty or corrupt (e.g. truncated by an interrupted training run),
    it is rebuilt in full, so pd.read_csv cannot raise EmptyDataError and abort a whole
    training batch.
    """
    path = data_dir(env) / f"{instrument}_{granularity}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)

    df_exist = None
    if path.exists() and path.stat().st_size > 0:
        try:
            df_exist = pd.read_csv(path, index_col="time", parse_dates=["time"])
            df_exist.index = pd.DatetimeIndex(df_exist.index).tz_convert(TZ)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, ValueError) as e:
            log.warning(f"⚠️ {path.name} cannot be parsed ({e}); rebuilding in full")
            df_exist = None

    if df_exist is not None and len(df_exist) > 0:
        df_new = fetch_candles(instrument, granularity, since=df_exist.index[-1])
        df = pd.concat([df_exist, df_new])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    else:
        if path.exists():
            log.warning(f"⚠️ {path.name} is empty; rebuilding in full")
        df = fetch_candles(instrument, granularity, lookback_months=lookback_months)

    # Atomic write: write to a temp file then replace, so an interruption cannot leave a
    # 0-byte CSV behind
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp)
    os.replace(tmp, path)
    return df
