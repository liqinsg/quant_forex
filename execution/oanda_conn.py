import oandapyV20.endpoints.orders as orders, oandapyV20.endpoints.positions as positions
from config.config_oanda import get_oanda_profile

# 全局 dry-run 开关：开启后所有下单/平仓调用只返回空响应，不向 OANDA 发送
_DRY_RUN = False


def set_dry_run(enabled: bool) -> None:
    global _DRY_RUN
    _DRY_RUN = bool(enabled)


def is_dry_run() -> bool:
    return _DRY_RUN


def get_client():
    return get_oanda_profile()["oanda_client"]

def _account_id():
    return get_oanda_profile()["account_id"]

def place_market_order(instrument, units, sl=None, tp=None):
    if _DRY_RUN:
        return {}
    client = get_client()
    data = {"order":{"type":"MARKET","instrument":instrument,"units":str(units),"positionFill":"DEFAULT"}}
    if sl: data["order"]["stopLossOnFill"] = {"price":f"{sl:.5f}","timeInForce":"GTC"}
    if tp: data["order"]["takeProfitOnFill"] = {"price":f"{tp:.5f}","timeInForce":"GTC"}
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
