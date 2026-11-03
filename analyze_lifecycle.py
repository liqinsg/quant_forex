import pandas as pd
import numpy as np

# Load data
df = pd.read_json("reports/lifecycle.jsonl", lines=True)
df["timestamp"] = pd.to_datetime(df["timestamp"])

print("="*60)
print("📊 Lifecycle v1 — Data Report")
print("="*60)
print(f"Records: {len(df)} | Instruments: {df['instrument'].nunique()}")
print(f"Time range: {df['timestamp'].min().strftime('%m-%d %H:%M')} → {df['timestamp'].max().strftime('%m-%d %H:%M')}")
print()

# 1. Stage distribution
print("--- 1. Trend stage distribution ---")
stage_counts = df.groupby(["trend_stage", "instrument"]).size().unstack(fill_value=0)
print(stage_counts)
print("\nOverall distribution:")
print(df["trend_stage"].value_counts().to_string())
print()

# 2. Stage vs probability
print("--- 2. Average probability per stage ---")
stage_prob = df.groupby("trend_stage")["prob"].agg(["mean", "std", "count"])
print(stage_prob.round(4))
print()

# 3. Trend age vs probability correlation
print("--- 3. Correlation matrix ---")
corr = df[["trend_age", "trend_strength", "trend_disp_atr", "prob"]].corr()
print(corr.round(3))
print()

# 4. High/low strength comparison
print("--- 4. FADING breakdown ---")
fading = df[df["trend_stage"] == "FADING"]
others = df[df["trend_stage"] != "FADING"]
print(f"FADING    : mean prob={fading['prob'].mean():.4f} | samples={len(fading)}")
print(f"Non-FADING: mean prob={others['prob'].mean():.4f} | samples={len(others)}")
print()

# 5. Strongest/weakest trends
print("--- 5. Trend strength TOP5 ---")
print(df.nlargest(5, "trend_strength")[["instrument", "trend_stage", "trend_strength", "prob"]].to_string(index=False))
print()
print("--- 6. Largest displacement TOP5 (disp_atr) ---")
print(df.nlargest(5, "trend_disp_atr")[["instrument", "trend_stage", "trend_disp_atr", "prob"]].to_string(index=False))
