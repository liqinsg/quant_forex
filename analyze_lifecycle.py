import pandas as pd
import numpy as np

# 读取数据
df = pd.read_json("reports/lifecycle.jsonl", lines=True)
df["timestamp"] = pd.to_datetime(df["timestamp"])

print("="*60)
print("📊 Lifecycle v1 — 数据报告")
print("="*60)
print(f"记录数: {len(df)} | 品种数: {df['instrument'].nunique()}")
print(f"时间: {df['timestamp'].min().strftime('%m-%d %H:%M')} → {df['timestamp'].max().strftime('%m-%d %H:%M')}")
print()

# 1. 各阶段分布
print("--- 1. 趋势阶段分布 ---")
stage_counts = df.groupby(["trend_stage", "instrument"]).size().unstack(fill_value=0)
print(stage_counts)
print("\n总体分布:")
print(df["trend_stage"].value_counts().to_string())
print()

# 2. 阶段 vs 概率
print("--- 2. 各阶段平均概率 ---")
stage_prob = df.groupby("trend_stage")["prob"].agg(["mean", "std", "count"])
print(stage_prob.round(4))
print()

# 3. 趋势年龄 vs 概率相关
print("--- 3. 相关性矩阵 ---")
corr = df[["trend_age", "trend_strength", "trend_disp_atr", "prob"]].corr()
print(corr.round(3))
print()

# 4. 高/低强度对比
print("--- 4. FADING 专项 ---")
fading = df[df["trend_stage"] == "FADING"]
others = df[df["trend_stage"] != "FADING"]
print(f"FADING   : 平均概率={fading['prob'].mean():.4f} | 样本={len(fading)}")
print(f"非FADING : 平均概率={others['prob'].mean():.4f} | 样本={len(others)}")
print()

# 5. 最强/最弱趋势
print("--- 5. 趋势强度 TOP5 ---")
print(df.nlargest(5, "trend_strength")[["instrument", "trend_stage", "trend_strength", "prob"]].to_string(index=False))
print()
print("--- 6. 空间最大 TOP5 (disp_atr) ---")
print(df.nlargest(5, "trend_disp_atr")[["instrument", "trend_stage", "trend_disp_atr", "prob"]].to_string(index=False))