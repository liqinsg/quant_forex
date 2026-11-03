import pandas as pd
import numpy as np

df = pd.read_json("reports/lifecycle.jsonl", lines=True)
if "aligned" not in df.columns:
    df["aligned"] = pd.NA
df["trend_age"] = pd.to_numeric(df["trend_age"], errors="coerce")
df["prob"] = pd.to_numeric(df["prob"], errors="coerce")

print("="*60)
print("📊 Age Bins vs Probability")
print("="*60)

df["age_bin"] = pd.qcut(df["trend_age"], 5, labels=[
    "0–20% (Youngest)",
    "20–40%",
    "40–60%",
    "60–80%",
    "80–100% (Oldest)"
])

age_summary = df.groupby("age_bin", observed=True).agg({
    "prob": ["mean", "std", "count"],
    "trend_disp_atr": "mean"
}).round(4)
print(age_summary)
print()

print("="*60)
print("📊 Stage vs Prob Distribution")
print("="*60)
stage_prob = df.groupby("trend_stage")["prob"].agg([
    "mean", "std", "min", "max", "count"
]).round(4)
print(stage_prob.sort_values("mean", ascending=False))
print()

print("="*60)
print("📊 Aligned vs Not Aligned (once data accumulates)")
print("="*60)
if df["aligned"].notna().sum() > 0:
    align_grp = df.dropna(subset=["aligned"]).groupby("aligned")["prob"].agg(["mean", "count"])
    print(align_grp)
else:
    print("Waiting for aligned field to populate...")