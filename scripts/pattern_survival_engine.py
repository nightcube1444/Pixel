import os
from pathlib import Path
import pandas as pd
import numpy as np

INPUT_PATH = Path("data/daily_pattern_snapshots.csv")
OUTPUT_PATH = Path("data/pattern_survival_results.csv")


def safe_read_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"File is empty: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"No rows found in: {path}")
    return df


df = safe_read_csv(INPUT_PATH)

required_cols = ["SnapshotDate", "Pattern"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["SnapshotDate"] = pd.to_datetime(df["SnapshotDate"], errors="coerce")
df = df.dropna(subset=["SnapshotDate", "Pattern"]).copy()

# Numeric cleanup
for col in ["Rank", "Trades", "WinRate5D", "AvgReturn5D", "AlphaScore", "ConfidenceScore"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.sort_values(["Pattern", "SnapshotDate"]).reset_index(drop=True)

results = []

for pattern, group in df.groupby("Pattern"):
    group = group.sort_values("SnapshotDate").copy()

    # Need at least 2 historical snapshots to compare old vs recent
    if len(group) < 2:
        continue

    split_idx = len(group) // 2
    old = group.iloc[:split_idx]
    recent = group.iloc[split_idx:]

    if len(old) == 0 or len(recent) == 0:
        continue

    old_avg_return = old["AvgReturn5D"].mean() if "AvgReturn5D" in old.columns else np.nan
    recent_avg_return = recent["AvgReturn5D"].mean() if "AvgReturn5D" in recent.columns else np.nan

    old_winrate = old["WinRate5D"].mean() if "WinRate5D" in old.columns else np.nan
    recent_winrate = recent["WinRate5D"].mean() if "WinRate5D" in recent.columns else np.nan

    old_alpha = old["AlphaScore"].mean() if "AlphaScore" in old.columns else np.nan
    recent_alpha = recent["AlphaScore"].mean() if "AlphaScore" in recent.columns else np.nan

    appearances = len(group)
    delta_return = recent_avg_return - old_avg_return if pd.notna(old_avg_return) and pd.notna(recent_avg_return) else np.nan
    delta_winrate = recent_winrate - old_winrate if pd.notna(old_winrate) and pd.notna(recent_winrate) else np.nan
    delta_alpha = recent_alpha - old_alpha if pd.notna(old_alpha) and pd.notna(recent_alpha) else np.nan

    # Survival logic
    survival_label = "UNKNOWN"

    if pd.notna(recent_avg_return) and pd.notna(old_avg_return):
        if recent_avg_return < 0 and old_avg_return > 0:
            survival_label = "DEAD"
        elif pd.notna(delta_return) and delta_return <= -0.5:
            survival_label = "DECAYING"
        elif pd.notna(delta_return) and delta_return >= 0.5:
            survival_label = "IMPROVING"
        else:
            survival_label = "STABLE"

    results.append({
        "Pattern": pattern,
        "Appearances": appearances,
        "FirstSeen": group["SnapshotDate"].min().strftime("%Y-%m-%d"),
        "LastSeen": group["SnapshotDate"].max().strftime("%Y-%m-%d"),
        "OldAvgReturn5D": round(old_avg_return, 3) if pd.notna(old_avg_return) else np.nan,
        "RecentAvgReturn5D": round(recent_avg_return, 3) if pd.notna(recent_avg_return) else np.nan,
        "DeltaReturn5D": round(delta_return, 3) if pd.notna(delta_return) else np.nan,
        "OldWinRate5D": round(old_winrate, 2) if pd.notna(old_winrate) else np.nan,
        "RecentWinRate5D": round(recent_winrate, 2) if pd.notna(recent_winrate) else np.nan,
        "DeltaWinRate5D": round(delta_winrate, 2) if pd.notna(delta_winrate) else np.nan,
        "OldAlphaScore": round(old_alpha, 4) if pd.notna(old_alpha) else np.nan,
        "RecentAlphaScore": round(recent_alpha, 4) if pd.notna(recent_alpha) else np.nan,
        "DeltaAlphaScore": round(delta_alpha, 4) if pd.notna(delta_alpha) else np.nan,
        "SurvivalLabel": survival_label
    })

survival_df = pd.DataFrame(results)

if survival_df.empty:
    print("No survival results generated yet.")
else:
    survival_df = survival_df.sort_values(
        by=["DeltaAlphaScore", "RecentAvgReturn5D", "Appearances"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    print("\nPATTERN SURVIVAL ENGINE RESULTS\n")
    print(survival_df.head(20))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    survival_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nSaved to {OUTPUT_PATH}")
    print(f"Patterns evaluated: {len(survival_df)}")