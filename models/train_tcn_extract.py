# 文件顶部改导入路径
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.fetch_oanda import update_csv
from features.build_features import add_ta_features
import os, pandas as pd, numpy as np, pickle, yaml, torch, torch.nn as nn
with open("config/config.yaml") as f: CFG = yaml.safe_load(f)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEQ_LEN = CFG.get("lookback_seq_len", 64)

class TemporalConvNet(nn.Module):
    def __init__(self, in_dim=5, out_dim=32, ch=[32,48,64], k=3, drop=0.2):
        super().__init__()
        layers, prev = [], in_dim
        for i,c in enumerate(ch):
            d=2**i; p=(k-1)*d
            layers.append(nn.Sequential(
                nn.Conv1d(prev,c,k,1,p,dilation=d), nn.ReLU(), nn.Dropout(drop),
                nn.Conv1d(c,c,k,1,p,dilation=d), nn.ReLU(), nn.Dropout(drop)))
            prev=c
        self.net = nn.Sequential(*layers)
        self.head = nn.Linear(prev, out_dim)
    def forward(self, x):
        return self.head(self.net(x)[:,:,-1])

def train_tcn_encoder(instrument, df):
    from sklearn.preprocessing import StandardScaler
    cols = ["open","high","low","close","ta_return_1"]
    scaler = StandardScaler()
    arr = scaler.fit_transform(df[cols].dropna())
    if len(arr) < SEQ_LEN+500: return None, None
    
    X = np.stack([arr[i:i+SEQ_LEN].T for i in range(len(arr)-SEQ_LEN)]).astype(np.float32)
    Xt = torch.from_numpy(X).to(DEVICE)
    
    model = TemporalConvNet().to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    for ep in range(30):
        model.train()
        loss = nn.MSELoss()(model(Xt[:,:,-32:]), Xt[:,:,-32:].mean(dim=-1))
        opt.zero_grad(); loss.backward(); opt.step()
        if (ep+1)%10==0: print(f"TCN Epoch {ep+1}: {loss.item():.6f}")
    
    model.eval()
    with torch.no_grad(): feats = model(Xt).cpu().numpy()
    idx = df.index[SEQ_LEN:]
    seq_df = pd.DataFrame(feats, index=idx, columns=[f"seq_{i:02d}" for i in range(32)])
    
    pkg = {"state": model.state_dict(), "scaler": scaler, "seq_len": SEQ_LEN}
    with open(f"models/model_store/tcn_{instrument}.pkl", "wb") as f: pickle.dump(pkg, f)
    return pkg, seq_df

def get_latest_seq_feature(instrument, df):
    with open(f"models/model_store/tcn_{instrument}.pkl", "rb") as f: pkg = pickle.load(f)
    model = TemporalConvNet(); model.load_state_dict(pkg["state"])
    model.to(DEVICE).eval()
    cols = ["open","high","low","close","ta_return_1"]
    arr = pkg["scaler"].transform(df[cols].iloc[-pkg["seq_len"]:].values.astype(np.float32))
    x = torch.from_numpy(arr.T).unsqueeze(0).to(DEVICE)
    with torch.no_grad(): fv = model(x).cpu().numpy()[0]
    return {f"seq_{i:02d}": float(fv[i]) for i in range(len(fv))}

if __name__ == "__main__":
    import sys
    inst = sys.argv[1] if len(sys.argv)>1 else "EUR_USD"
    from data.fetch_oanda import update_csv
    from features.build_features import add_ta_features
    df = update_csv(inst)
    df = add_ta_features(df)
    _, sdf = train_tcn_encoder(inst, df)
    if sdf is not None: sdf.to_csv(f"reports/seq_{inst}.csv")