import oandapyV20.endpoints.orders as orders, oandapyV20.endpoints.positions as positions
from config.config_oanda import get_oanda_profile

def get_client():
    return get_oanda_profile()["oanda_client"]

def _account_id():
    ids = get_oanda_profile()["account_ids"]
    return ids[0] if ids else None

def place_market_order(instrument, units, sl=None, tp=None):
    client = get_client()
    data = {"order":{"type":"MARKET","instrument":instrument,"units":str(units),"positionFill":"DEFAULT"}}
    if sl: data["order"]["stopLossOnFill"] = {"price":f"{sl:.5f}","timeInForce":"GTC"}
    if tp: data["order"]["takeProfitOnFill"] = {"price":f"{tp:.5f}","timeInForce":"GTC"}
    return client.request(orders.OrderCreate(_account_id(), data=data))

def close_position(instrument):
    client = get_client()
    return client.request(positions.PositionClose(_account_id(), instrument=instrument,
        data={"longUnits":"ALL","shortUnits":"ALL"}))

def get_open_position(instrument):
    try:
        pos = get_client().request(positions.PositionDetails(_account_id(), instrument))["position"]
        return {"has_position":float(pos["netUnits"])!=0, "units":float(pos["netUnits"]),
                "unrealizedPL":float(pos["unrealizedPL"])}
    except: return {"has_position":False, "units":0, "unrealizedPL":0.0}
