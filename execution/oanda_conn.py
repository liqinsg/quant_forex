import oandapyV20.endpoints.orders as orders, oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.trades as trades
from config.config_oanda import get_oanda_profile

# Global dry-run switch: when enabled, every order/close call returns an empty response and
# nothing is sent to OANDA
_DRY_RUN = False

# Price precision cache: instrument -> displayPrecision (cached only on a successful query)
_PRECISION_CACHE = {}
_BOT_TRADE_TAG = "fx_bot_v7"


def set_dry_run(enabled: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = bool(enabled)


def is_dry_run() -> bool:
    return _DRY_RUN


def get_client():
    return get_oanda_profile()["oanda_client"]

def _account_id():
    return get_oanda_profile()["account_id"]

def _price_precision(instrument):
    """OANDA price precision: query the instrument's displayPrecision live and cache it.

    Covers all instrument types: FX (5 decimals, JPY pairs 3) and crypto (BTC_USD 1,
    ETH_USD 2). On a failed query it falls back to the JPY heuristic (3 decimals for JPY,
    5 otherwise) and does not cache, so the next call retries.
    """
    inst = instrument.upper()
    if inst in _PRECISION_CACHE:
        return _PRECISION_CACHE[inst]
    try:
        resp = get_client().request(
            accounts.AccountInstruments(_account_id(), params={"instruments": inst})
        )
        for item in resp.get("instruments", []):
            if item.get("name") == inst and item.get("displayPrecision") is not None:
                prec = int(item["displayPrecision"])
                _PRECISION_CACHE[inst] = prec
                return prec
    except Exception:
        pass
    return 3 if inst.endswith("JPY") else 5


def _trade_comment(instrument, units):
    direction = "LONG" if float(units) > 0 else "SHORT"
    env = get_oanda_profile()["env"]
    return f"main_loop_v2:{env}:{instrument}:{direction}"

def place_market_order(instrument, units, sl=None, tp=None):
    if _DRY_RUN:
        return {}
    client = get_client()
    p = _price_precision(instrument)
    # Normalize units: integral values are sent as "10000"/"1", fractional (crypto) values keep
    # their original form, e.g. "0.01"
    u = int(units) if float(units).is_integer() else float(units)
    data = {
        "order": {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(u),
            "positionFill": "DEFAULT",
            "tradeClientExtensions": {
                "tag": _BOT_TRADE_TAG,
                "comment": _trade_comment(instrument, u),
            },
        }
    }
    if sl: data["order"]["stopLossOnFill"] = {"price":f"{sl:.{p}f}","timeInForce":"GTC"}
    if tp: data["order"]["takeProfitOnFill"] = {"price":f"{tp:.{p}f}","timeInForce":"GTC"}
    return client.request(orders.OrderCreate(_account_id(), data=data))

def close_position(instrument):
    if _DRY_RUN:
        return {}
    client = get_client()
    return client.request(positions.PositionClose(_account_id(), instrument=instrument,
        data={"longUnits":"ALL","shortUnits":"ALL"}))

def get_open_position(instrument):
    try:
        pos = get_client().request(positions.PositionDetails(_account_id(), instrument))["position"]
        return {"has_position":float(pos["netUnits"])!=0, "units":float(pos["netUnits"]),
                "unrealizedPL":float(pos["unrealizedPL"])}
    except: return {"has_position":False, "units":0, "unrealizedPL":0.0}


def get_open_position_snapshot():
    """Aggregate the net position direction and size of this bot (tag=fx_bot_v7*) per instrument.

    Returns {instrument: {"direction": "LONG"/"SHORT", "units": absolute net units}};
    multiple trades on the same instrument are summed by currentUnits before the direction is
    decided, and instruments netting to 0 are omitted.
    Returns None if the query fails, and the caller then skips opening this cycle (fail-closed).
    """
    try:
        resp = get_client().request(trades.OpenTrades(_account_id()))
    except Exception:
        return None
    net = {}
    for trade in resp.get("trades", []):
        tag = (trade.get("clientExtensions") or {}).get("tag") or ""
        if not tag.startswith(_BOT_TRADE_TAG):
            continue
        units = float(trade.get("currentUnits", 0) or 0)
        if units == 0:
            continue
        inst = trade.get("instrument")
        net[inst] = net.get(inst, 0.0) + units
    return {
        inst: {"direction": "LONG" if units > 0 else "SHORT", "units": abs(units)}
        for inst, units in net.items()
        if units != 0
    }


def has_open_bot_trade(instrument, units):
    """Check whether this bot already has an open trade of the same instrument and direction."""
    direction_sign = 1 if float(units) > 0 else -1
    try:
        resp = get_client().request(trades.OpenTrades(_account_id()))
        for trade in resp.get("trades", []):
            if trade.get("instrument") != instrument:
                continue
            tag = trade.get("clientExtensions", {}).get("tag")
            if tag != _BOT_TRADE_TAG:
                continue
            current_units = float(trade.get("currentUnits", 0))
            if current_units == 0:
                continue
            if (1 if current_units > 0 else -1) == direction_sign:
                return True
    except Exception:
        return False
    return False
