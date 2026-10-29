import oandapyV20.endpoints.orders as orders, oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.trades as trades
from config.config_oanda import get_oanda_profile

# 全局 dry-run 开关：开启后所有下单/平仓调用只返回空响应，不向 OANDA 发送
_DRY_RUN = False

# 价格精度缓存：品种 -> displayPrecision（成功查询才缓存）
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
    """OANDA 价格精度：优先实时查询该品种的 displayPrecision 并缓存。

    覆盖外汇（非日元 5 / 日元 3）与加密（BTC_USD 1 / ETH_USD 2）等所有品种；
    查询失败时回退到 JPY 启发式（日元 3 位，其余 5 位），且不写入缓存以便下次重试。
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
    # 单位数归一化：整数值发 "10000"/"1"，小数（加密）保留原值如 "0.01"
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
    """按品种聚合当前 bot（tag=fx_bot_v7*）的净持仓方向与数量。

    返回 {instrument: {"direction": "LONG"/"SHORT", "units": 绝对净单位数}}；
    同一品种多笔 trade 先按 currentUnits 求和再定方向，净额为 0 的品种不返回。
    查询失败返回 None，调用方据此跳过本轮开仓（fail-closed）。
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
    """检查是否已存在当前 bot 打开的同品种同方向 open trade。"""
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
