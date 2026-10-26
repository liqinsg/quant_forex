import pandas as pd
from datetime import datetime

def log_equity(balance, floating=0.0):
    path = "reports/equity.csv"
    row = {"time":datetime.now(),"balance":balance,"floating_pnl":floating,"equity":balance+floating}
    try:
        df = pd.read_csv(path)
        pd.DataFrame([row]).to_csv(path, mode="a", header=False, index=False)
    except:
        pd.DataFrame([row]).to_csv(path, index=False)