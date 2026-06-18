import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# -----------------------------------
# File paths
# -----------------------------------
ALPHA_PATH = Path("data/alpha_ranking_results.csv")
DISCOVERY_PATH = Path("data/signal_discovery_results.csv")
CONFIDENCE_PATH = Path("data/confidence_score_results.csv")
HISTORY_DIR = Path("data/pattern_history")
SNAPSHOT_PATH = Path("data/daily_pattern_snapshots.csv")

TODAY = pd.Timestamp.today().normalize().strftime("%Y-%m-%d")


# -----------------------------------
# Helpers
# -----------------------------------
def safe_read_csv(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except Exception:
        return None


def detect_pattern_column(df: pd.DataFrame):
    for col in ["Pattern", "SignalSetup", "Signal"]:
        if col in df.columns:
            return col
    return None


def normalize_pattern_column(df: pd.DataFrame):
    pattern_col = detect_pattern_column(df)
    if pattern_col is None:
        raise ValueError(f"No usable pattern column found in columns: {list(df.columns)}")
    df = df.copy()
    df["Pattern"] = df[pattern_col].astype(str)
    return df


def get_col(df: pd.DataFrame, possible_names, default_value=np.nan):
    for c in possible_names:
        if c in df.columns:
            return df[c]
    return pd.Series([default_value] * len(df), index=df.index)


# -----------------------------------
# Load best available source
# -----------------------------------
base_df = None
source_used = None

if ALPHA_PATH.exists() and ALPHA_PATH.stat().st_size > 0:
    base_df = safe_read_csv(ALPHA_PATH)
    source_used = "alpha_ranking_results.csv"
elif DISCOVERY_PATH.exists() and DISCOVERY_PATH.stat().st_size > 0:
    base_df = safe_read_csv(DISCOVERY_PATH)
    source_used = "signal_discovery_results.csv"

if base_df is None:
    raise FileNotFoundError("No usable alpha/discovery file found for snapshot update.")

base_df = normalize_pattern_column(base_df)

confidence_df = safe_read_csv(CONFIDENCE_PATH)
if confidence_df is not None:
    confidence_df = normalize_pattern_column(confidence_df)

# -----------------------------------
# Build today's snapshot rows
# -----------------------------------
snap = pd.DataFrame()
snap["SnapshotDate"] = [TODAY] * len(base_df)
snap["Pattern"] = base_df["Pattern"]

snap["Rank"] = get_col(base_df, ["AlphaRank", "Rank"], default_value=np.nan)
snap["Trades"] = get_col(base_df, ["Trades", "Count", "Appearances"], default_value=np.nan)
snap["WinRate5D"] = get_col(base_df, ["WinRate", "WinRate5D", "AvgWinRate"], default_value=np.nan)
snap["AvgReturn5D"] = get_col(base_df, ["AvgReturn", "AvgReturn5D"], default_value=np.nan)
snap["AlphaScore"] = get_col(base_df, ["AlphaScore"], default_value=np.nan)
snap["SourceFile"] = source_used

# Add confidence if present in base
snap["ConfidenceScore"] = get_col(base_df, ["ConfidenceScore"], default_value=np.nan)

# If base didn't have confidence, try merging from confidence file
if confidence_df is not None and snap["ConfidenceScore"].isna().all():
    conf_small = confidence_df[["Pattern"]].copy()
    if "ConfidenceScore" in confidence_df.columns:
        conf_small["ConfidenceScore"] = confidence_df["ConfidenceScore"]
        snap = pd.merge(snap, conf_small, on="Pattern", how="left", suffixes=("", "_conf"))
        snap["ConfidenceScore"] = snap["ConfidenceScore"].fillna(snap["ConfidenceScore_conf"])
        snap = snap.drop(columns=["ConfidenceScore_conf"], errors="ignore")

# Numeric cleanup
for c in ["Rank", "Trades", "WinRate5D", "AvgReturn5D", "AlphaScore", "ConfidenceScore"]:
    if c in snap.columns:
        snap[c] = pd.to_numeric(snap[c], errors="coerce")

# Drop duplicate patterns in today's run if any
snap = snap.drop_duplicates(subset=["SnapshotDate", "Pattern"]).reset_index(drop=True)

# -----------------------------------
# Load old snapshots
# -----------------------------------
old_snapshots = safe_read_csv(SNAPSHOT_PATH)

if old_snapshots is None:
    final_snapshots = snap.copy()
else:
    final_snapshots = pd.concat([old_snapshots, snap], ignore_index=True)

    # Remove exact duplicate day+pattern rows, keep latest appended one
    final_snapshots = final_snapshots.drop_duplicates(
        subset=["SnapshotDate", "Pattern"],
        keep="last"
    ).reset_index(drop=True)

# -----------------------------------
# Sort nicely
# -----------------------------------
sort_cols = [c for c in ["SnapshotDate", "Rank", "AlphaScore", "Trades"] if c in final_snapshots.columns]
ascending = []
for c in sort_cols:
    if c == "SnapshotDate":
        ascending.append(True)
    else:
        ascending.append(True if c == "Rank" else False)

final_snapshots = final_snapshots.sort_values(
    by=sort_cols,
    ascending=ascending
).reset_index(drop=True)

# -----------------------------------
# Save
# -----------------------------------
SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
final_snapshots.to_csv(SNAPSHOT_PATH, index=False)

print("\nPATTERN SNAPSHOT ENGINE RESULTS\n")
print(snap.head(20))
print(f"\nSaved to {SNAPSHOT_PATH}")
print(f"Rows added today: {len(snap)}")
print(f"Total historical snapshot rows: {len(final_snapshots)}")
print(f"Source used: {source_used}")

# -----------------------------------
# Save daily alpha snapshot
# -----------------------------------

HISTORY_DIR.mkdir(parents=True, exist_ok=True)

today_alpha_file = HISTORY_DIR / f"{TODAY}_alpha.csv"

base_df.to_csv(
    today_alpha_file,
    index=False
)

print(
    f"Historical snapshot saved: "
    f"{today_alpha_file}"
)