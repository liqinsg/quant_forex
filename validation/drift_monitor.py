import os, yaml, numpy as np, pandas as pd, pickle
from config import load_config, model_dir
CFG = load_config()

def psi_score(exp_arr, act_arr, bins=10, eps=1e-10):
    e_pdf = np.clip(np.histogram(exp_arr, bins=bins, density=True)[0], eps, None)
    a_pdf = np.clip(np.histogram(act_arr, bins=bins, density=True)[0], eps, None)
    e_pdf /= e_pdf.sum(); a_pdf /= a_pdf.sum()
    return np.sum((a_pdf-e_pdf)*np.log(a_pdf/e_pdf))

def check_drift(instrument, features, probs):
    ref_path = model_dir() / f"ref_{instrument}.pkl"
    if not ref_path.exists():
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ref_path, "wb") as f: pickle.dump({"probs":probs}, f)
        return {"status":"baseline_saved","psi":0.0}
    with open(ref_path, "rb") as f: ref = pickle.load(f)
    psi = psi_score(ref["probs"], probs)
    status = "ok"
    if psi > CFG["monitor"]["psi_critical"]: status = "CRITICAL"
    elif psi > CFG["monitor"]["psi_warning"]: status = "WARNING"
    return {"psi":round(psi,4),"status":status}