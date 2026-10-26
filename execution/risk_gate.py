class CircuitBreaker:
    def __init__(self): self.halt_until = None
    def is_halted(self): from datetime import datetime; return self.halt_until and datetime.now() < self.halt_until
    def trigger(self, mins=60): from pandas import Timestamp; self.halt_until = Timestamp.now() + pd.Timedelta(minutes=mins)
    def lift(self): self.halt_until = None
circuit = CircuitBreaker()

def enhanced_risk_check(ann_vol, dd, daily_pnl, trade_count, cfg):
    if circuit.is_halted(): return False, "circuit_breaker"
    r = cfg["risk"]
    reas = []
    if ann_vol > r["vol_threshold_annual"]: reas.append("vol_too_high")
    if dd > r["max_total_drawdown_pct"]/100: reas.append("max_dd"); circuit.trigger(120)
    if daily_pnl < -r["max_daily_drawdown_pct"]/100: reas.append("daily_limit"); circuit.trigger(240)
    if trade_count > 12: reas.append("too_many_trades")
    return len(reas)==0, ",".join(reas) if reas else "ok"