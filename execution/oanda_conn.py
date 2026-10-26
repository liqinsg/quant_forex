import os, oandapyV20
import oandapyV20.endpoints.orders as orders, oandapyV20.endpoints.positions as positions
from dotenv import load_dotenv
load_dotenv()

def get_client():
    env = "practice" if os.getenv("OANDA_ENV")=="practice" else "live"
    return oandapyV20.API(access_token=os.getenv("OANDA_TOKEN"), environment=env)

def place_market_order(instrument, units, sl=None, tp=None):
    client = get_client()
    data = {"order":{"type":"MARKET","instrument":instrument,"units":str(units),"positionFill":"DEFAULT"}}
    if sl: data["order"]["stopLossOnFill"] = {"price":f"{sl:.5f}","timeInForce":"GTC"}
    if tp: data["order"]["takeProfitOnFill"] = {"price":f"{tp:.5f}","timeInForce":"GTC"}
    return client.request(orders.OrderCreate(os.getenv("OANDA_ACCOUNT_ID"), data=data))

def close_position(instrument):
    client = get_client()
    return client.request(positions.PositionClose(os.getenv("OANDA_ACCOUNT_ID"), instrument=instrument,
        data={"longUnits":"ALL","shortUnits":"ALL"}))

def get_open_position(instrument):
    try:
        pos = get_client().request(positions.PositionDetails(os.getenv("OANDA_ACCOUNT_ID"), instrument))["position"]
        return {"has_position":float(pos["netUnits"])!=0, "units":float(pos["netUnits"]),
                "unrealizedPL":float(pos["unrealizedPL"])}
    except: return {"has_position":False, "units":0, "unrealizedPL":0.0}