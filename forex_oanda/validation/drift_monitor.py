import os, yaml, numpy as np, pandas as pd, pickle
with open("config/config.yaml") as f: CFG = yaml.safe_load(f)

def psi_score(exp_arr, act_arr, bins=10, eps=1e-10):
    e_pdf = np.clip(np.histogram(exp_arr, bins=bins, density=True)[0], eps, None)
    a_pdf = np.clip(np.histogram(act_arr, bins=bins, density=True)[0], eps, None)
    e_pdf /= e_pdf.sum(); a_pdf /= a_pdf.sum()
    return np.sum((a_pdf-e_pdf)*np.log(a_pdf/e_pdf))

def check_drift(instrument, features, probs):
    ref_path = f"models/model_store/ref_{instrument}.pkl"
    if not os.path.exists(ref_path):
        with open(ref_path, "wb") as f: pickle.dump({"probs":probs}, f)
        return {"status":"baseline_saved","psi":0.0}
    with open(ref_path, "rb") as f: ref = pickle.load(f)
    psi = psi_score(ref["probs"], probs)
    status = "ok"
    if psi > CFG["monitor"]["psi_critical"]: status = "CRITICAL"
    elif psi > CFG["monitor"]["psi_warning"]: status = "WARNING"
    return {"psi":round(psi,4),"status":status}