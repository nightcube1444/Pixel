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
SURVIVAL_PATH = Path("data/pattern_survival_results.csv")
CONFIDENCE_PATH = Path("data/confidence_score_results.csv")
MEMORY_PATH = Path("data/research_memory.csv")

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


def memory_status(times_seen, survival_label, long_avg_return):
    label = str(survival_label).upper()

    if times_seen >= 20 and label in ["IMPROVING", "STABLE"] and long_avg_return > 0:
        return "TRUSTED"
    if times_seen >= 10 and long_avg_return > 0:
        return "WATCHLIST"
    if label in ["DECAYING", "DEAD"]:
        return "WEAKENING"
    return "EARLY"


# -----------------------------------
# Load best available ranking source
# -----------------------------------
base_df = None

if ALPHA_PATH.exists() and ALPHA_PATH.stat().st_size > 0:
    base_df = safe_read_csv(ALPHA_PATH)
elif DISCOVERY_PATH.exists() and DISCOVERY_PATH.stat().st_size > 0:
    base_df = safe_read_csv(DISCOVERY_PATH)

if base_df is None:
    raise FileNotFoundError("No usable alpha/discovery file found for memory update.")

base_df = normalize_pattern_column(base_df)

# -----------------------------------
# Load optional supporting files
# -----------------------------------
survival_df = safe_read_csv(SURVIVAL_PATH)
confidence_df = safe_read_csv(CONFIDENCE_PATH)
old_memory = safe_read_csv(MEMORY_PATH)

if survival_df is not None:
    survival_df = normalize_pattern_column(survival_df)

if confidence_df is not None:
    confidence_df = normalize_pattern_column(confidence_df)

if old_memory is not None:
    old_memory = normalize_pattern_column(old_memory)

# -----------------------------------
# Build today's snapshot table
# -----------------------------------
today_df = pd.DataFrame()
today_df["Pattern"] = base_df["Pattern"]

today_df["TodayRank"] = get_col(base_df, ["AlphaRank", "Rank"], default_value=np.nan)
today_df["TodayTrades"] = get_col(base_df, ["Trades", "Count", "Appearances"], default_value=0)
today_df["TodayWinRate5D"] = get_col(base_df, ["WinRate", "WinRate5D", "AvgWinRate"], default_value=np.nan)
today_df["TodayAvgReturn5D"] = get_col(base_df, ["AvgReturn", "AvgReturn5D"], default_value=np.nan)
today_df["TodayAlphaScore"] = get_col(base_df, ["AlphaScore"], default_value=np.nan)
today_df["TodayConfidenceScore"] = get_col(base_df, ["ConfidenceScore"], default_value=np.nan)

# Merge in survival if available
if survival_df is not None:
    keep_cols = ["Pattern"]
    for c in ["SurvivalLabel", "RecentAvgReturn5D", "RecentWinRate5D", "DeltaReturn5D"]:
        if c in survival_df.columns:
            keep_cols.append(c)
    today_df = pd.merge(today_df, survival_df[keep_cols], on="Pattern", how="left")
else:
    today_df["SurvivalLabel"] = "UNKNOWN"
    today_df["RecentAvgReturn5D"] = np.nan
    today_df["RecentWinRate5D"] = np.nan
    today_df["DeltaReturn5D"] = np.nan

# Merge in confidence if missing
if confidence_df is not None and "TodayConfidenceScore" in today_df.columns:
    if today_df["TodayConfidenceScore"].isna().all():
        keep_cols = ["Pattern"]
        for c in ["ConfidenceScore"]:
            if c in confidence_df.columns:
                keep_cols.append(c)
        tmp = confidence_df[keep_cols].rename(columns={"ConfidenceScore": "TodayConfidenceScore_conf"})
        today_df = pd.merge(today_df, tmp, on="Pattern", how="left")
        today_df["TodayConfidenceScore"] = today_df["TodayConfidenceScore"].fillna(today_df["TodayConfidenceScore_conf"])
        today_df = today_df.drop(columns=["TodayConfidenceScore_conf"], errors="ignore")

today_df["LastSeen"] = TODAY

# Clean numeric fields
numeric_cols = [
    "TodayRank", "TodayTrades", "TodayWinRate5D", "TodayAvgReturn5D",
    "TodayAlphaScore", "TodayConfidenceScore", "RecentAvgReturn5D",
    "RecentWinRate5D", "DeltaReturn5D"
]

for c in numeric_cols:
    if c in today_df.columns:
        today_df[c] = pd.to_numeric(today_df[c], errors="coerce")

today_df["SurvivalLabel"] = today_df["SurvivalLabel"].fillna("UNKNOWN")

# Remove duplicate patterns if any
today_df = today_df.drop_duplicates(subset=["Pattern"]).reset_index(drop=True)

# -----------------------------------
# Create fresh memory if none exists
# -----------------------------------
if old_memory is None:
    memory = today_df.copy()

    memory["FirstSeen"] = TODAY
    memory["TimesSeen"] = 1
    memory["LongAvgReturn5D"] = memory["TodayAvgReturn5D"]
    memory["RecentAvgReturn5D_Memory"] = memory["RecentAvgReturn5D"].fillna(memory["TodayAvgReturn5D"])
    memory["BestRank"] = memory["TodayRank"]
    memory["WorstRank"] = memory["TodayRank"]
    memory["LatestWinRate5D"] = memory["TodayWinRate5D"]
    memory["LatestConfidenceScore"] = memory["TodayConfidenceScore"]
    memory["LatestSurvivalLabel"] = memory["SurvivalLabel"]

else:
    old_memory["Pattern"] = old_memory["Pattern"].astype(str)

    memory = pd.merge(
        old_memory,
        today_df,
        on="Pattern",
        how="outer",
        suffixes=("_old", "")
    )

    # Seen flags
    seen_before = memory["FirstSeen"].notna()
    seen_today = memory["LastSeen"].notna()

    # FirstSeen
    memory["FirstSeen"] = memory["FirstSeen"].fillna(TODAY)

    # LastSeen
    memory["LastSeen"] = memory["LastSeen"].fillna(memory.get("LastSeen_old", TODAY)).fillna(TODAY)

    # TimesSeen
    old_times = pd.to_numeric(memory.get("TimesSeen", 0), errors="coerce").fillna(0)
    appeared_today = memory["TodayTrades"].notna().astype(int)
    memory["TimesSeen"] = old_times + appeared_today

    # LongAvgReturn5D
    old_long = pd.to_numeric(memory.get("LongAvgReturn5D", np.nan), errors="coerce")
    today_avg = pd.to_numeric(memory.get("TodayAvgReturn5D", np.nan), errors="coerce")

    memory["LongAvgReturn5D"] = np.where(
        old_long.notna() & today_avg.notna() & (memory["TimesSeen"] > 0),
        ((old_long * (memory["TimesSeen"] - 1)) + today_avg) / memory["TimesSeen"],
        old_long.fillna(today_avg)
    )

    # RecentAvgReturn5D_Memory
    old_recent = pd.to_numeric(memory.get("RecentAvgReturn5D_Memory", np.nan), errors="coerce")
    current_recent = pd.to_numeric(memory.get("RecentAvgReturn5D", np.nan), errors="coerce")
    memory["RecentAvgReturn5D_Memory"] = np.where(
        current_recent.notna(),
        current_recent,
        old_recent
    )

    # BestRank / WorstRank
    old_best = pd.to_numeric(memory.get("BestRank", np.nan), errors="coerce")
    old_worst = pd.to_numeric(memory.get("WorstRank", np.nan), errors="coerce")
    today_rank = pd.to_numeric(memory.get("TodayRank", np.nan), errors="coerce")

    memory["BestRank"] = np.where(
        old_best.notna() & today_rank.notna(),
        np.minimum(old_best, today_rank),
        old_best.fillna(today_rank)
    )

    memory["WorstRank"] = np.where(
        old_worst.notna() & today_rank.notna(),
        np.maximum(old_worst, today_rank),
        old_worst.fillna(today_rank)
    )

    # Latest values
    memory["LatestWinRate5D"] = pd.to_numeric(memory.get("TodayWinRate5D", np.nan), errors="coerce").fillna(
        pd.to_numeric(memory.get("LatestWinRate5D", np.nan), errors="coerce")
    )

    memory["LatestConfidenceScore"] = pd.to_numeric(memory.get("TodayConfidenceScore", np.nan), errors="coerce").fillna(
        pd.to_numeric(memory.get("LatestConfidenceScore", np.nan), errors="coerce")
    )

    memory["LatestSurvivalLabel"] = memory.get("SurvivalLabel", pd.Series(["UNKNOWN"] * len(memory))).fillna(
        memory.get("LatestSurvivalLabel", "UNKNOWN")
    )

# -----------------------------------
# Final derived status
# -----------------------------------
memory["LongAvgReturn5D"] = pd.to_numeric(memory["LongAvgReturn5D"], errors="coerce").fillna(0)
memory["LatestConfidenceScore"] = pd.to_numeric(memory["LatestConfidenceScore"], errors="coerce").fillna(0)
memory["LatestWinRate5D"] = pd.to_numeric(memory["LatestWinRate5D"], errors="coerce").fillna(0)
memory["TimesSeen"] = pd.to_numeric(memory["TimesSeen"], errors="coerce").fillna(0).astype(int)

memory["MemoryStatus"] = memory.apply(
    lambda row: memory_status(
        row["TimesSeen"],
        row["LatestSurvivalLabel"],
        row["LongAvgReturn5D"]
    ),
    axis=1
)

# -----------------------------------
# Human-readable summary
# -----------------------------------
def build_summary(row):
    return (
        f"Pattern {row['Pattern']} has memory status {row['MemoryStatus']}; "
        f"seen {row['TimesSeen']} times; "
        f"latest win rate {round(row['LatestWinRate5D'], 2)}; "
        f"long avg return {round(row['LongAvgReturn5D'], 3)}; "
        f"confidence score {round(row['LatestConfidenceScore'], 4)}; "
        f"survival {row['LatestSurvivalLabel']}."
    )

memory["Summary"] = memory.apply(build_summary, axis=1)

# -----------------------------------
# Choose final columns
# -----------------------------------
final_cols = [
    "Pattern",
    "FirstSeen",
    "LastSeen",
    "TimesSeen",
    "BestRank",
    "WorstRank",
    "LongAvgReturn5D",
    "RecentAvgReturn5D_Memory",
    "LatestWinRate5D",
    "LatestConfidenceScore",
    "LatestSurvivalLabel",
    "MemoryStatus",
    "Summary"
]

for col in final_cols:
    if col not in memory.columns:
        memory[col] = np.nan

memory = memory[final_cols].copy()

# Sort strongest memory patterns first
memory = memory.sort_values(
    by=["TimesSeen", "LatestConfidenceScore", "LongAvgReturn5D"],
    ascending=[False, False, False]
).reset_index(drop=True)

# -----------------------------------
# Save
# -----------------------------------
MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
memory.to_csv(MEMORY_PATH, index=False)

print("\nRESEARCH MEMORY ENGINE RESULTS\n")
print(memory.head(20))
print(f"\nSaved to {MEMORY_PATH}")
print(f"Patterns stored: {len(memory)}")