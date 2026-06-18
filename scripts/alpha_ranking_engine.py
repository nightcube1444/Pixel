import os
import pandas as pd
import numpy as np

DISCOVERY_PATH = "data/signal_discovery_results.csv"
SURVIVAL_PATH = "data/pattern_survival_results.csv"
CONFIDENCE_PATH = "data/confidence_score_results.csv"
MEMORY_PATH = "data/research_memory.csv"
OUTPUT_PATH = "data/alpha_ranking_results.csv"


def safe_read_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    if os.path.getsize(path) == 0:
        raise ValueError(f"File is empty: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"No rows found in: {path}")

    return df


def find_pattern_column(df):
    for col in ["Pattern", "SignalSetup", "Signal"]:
        if col in df.columns:
            return col
    raise ValueError(f"No usable pattern column found in columns: {list(df.columns)}")


def normalize_pattern_column(df, name="Pattern"):
    pattern_col = find_pattern_column(df)
    df = df.copy()
    df[name] = df[pattern_col].astype(str).fillna("UNKNOWN")
    return df


# -----------------------------
# Load required files
# -----------------------------
discovery = safe_read_csv(DISCOVERY_PATH)
confidence = safe_read_csv(CONFIDENCE_PATH)

# Optional files
survival = None
if os.path.exists(SURVIVAL_PATH) and os.path.getsize(SURVIVAL_PATH) > 0:
    temp_survival = pd.read_csv(SURVIVAL_PATH)
    if not temp_survival.empty:
        survival = temp_survival

memory = None
if os.path.exists(MEMORY_PATH) and os.path.getsize(MEMORY_PATH) > 0:
    try:
        temp_memory = pd.read_csv(MEMORY_PATH)
        if not temp_memory.empty:
            memory = temp_memory
    except Exception:
        memory = None

# -----------------------------
# Normalize pattern columns
# -----------------------------
discovery = normalize_pattern_column(discovery, "Pattern")
confidence = normalize_pattern_column(confidence, "Pattern")

if survival is not None:
    survival = normalize_pattern_column(survival, "Pattern")

if memory is not None:
    memory = normalize_pattern_column(memory, "Pattern")

# -----------------------------
# Validate discovery columns
# -----------------------------
required_discovery = ["Pattern", "Trades"]
missing_discovery = [c for c in required_discovery if c not in discovery.columns]
if missing_discovery:
    raise ValueError(f"Missing required discovery columns: {missing_discovery}")

# Find usable win-rate column
winrate_col = None
for c in ["WinRate5D", "WinRate", "AvgWinRate"]:
    if c in discovery.columns:
        winrate_col = c
        break

# Find usable average-return column
avgreturn_col = None
for c in ["AvgReturn5D", "AvgReturn"]:
    if c in discovery.columns:
        avgreturn_col = c
        break

if winrate_col is None:
    raise ValueError("No usable win-rate column found in signal_discovery_results.csv")

if avgreturn_col is None:
    raise ValueError("No usable average-return column found in signal_discovery_results.csv")

# -----------------------------
# Start with discovery
# -----------------------------
df = discovery.copy()

keep_cols = ["Pattern", "Trades", winrate_col, avgreturn_col]
extra_optional = [
    c for c in [
        "Rank",
        "WinRate1D", "AvgReturn1D",
        "WinRate3D", "AvgReturn3D",
        "WinRate10D", "AvgReturn10D"
    ] if c in df.columns
]
keep_cols += extra_optional
df = df[keep_cols].copy()

df = df.rename(columns={
    winrate_col: "WinRateUsed",
    avgreturn_col: "AvgReturnUsed"
})

# -----------------------------
# Merge survival if available
# -----------------------------
if survival is not None:
    survival_keep = ["Pattern"]
    for c in ["SurvivalLabel", "RecentAvgReturn5D", "RecentWinRate5D", "DeltaReturn5D", "Appearances"]:
        if c in survival.columns:
            survival_keep.append(c)

    survival_small = survival[survival_keep].drop_duplicates(subset=["Pattern"])
    df = pd.merge(df, survival_small, on="Pattern", how="left")
else:
    df["SurvivalLabel"] = "UNKNOWN"

# -----------------------------
# Merge confidence
# -----------------------------
confidence_keep = ["Pattern"]
for c in ["ConfidenceScore", "ConfidenceRank", "StabilityScore", "DecayScore"]:
    if c in confidence.columns:
        confidence_keep.append(c)

confidence_small = confidence[confidence_keep].drop_duplicates(subset=["Pattern"])
df = pd.merge(df, confidence_small, on="Pattern", how="left")

# -----------------------------
# Merge memory if available
# -----------------------------
if memory is not None:
    memory_keep = ["Pattern"]
    for c in [
        "TimesSeen",
        "LastSeen",
        "FirstSeen",
        "LongAvgReturn5D",
        "RecentAvgReturn5D",
        "SurvivalLabel",
        "ConfidenceScore"
    ]:
        if c in memory.columns:
            memory_keep.append(c)

    memory_small = memory[memory_keep].drop_duplicates(subset=["Pattern"])

    rename_map = {}
    for c in memory_small.columns:
        if c != "Pattern" and c in df.columns:
            rename_map[c] = f"{c}_mem"
    memory_small = memory_small.rename(columns=rename_map)

    df = pd.merge(df, memory_small, on="Pattern", how="left")

# -----------------------------
# Fill defaults
# -----------------------------
df["Trades"] = pd.to_numeric(df["Trades"], errors="coerce").fillna(0)
df["WinRateUsed"] = pd.to_numeric(df["WinRateUsed"], errors="coerce").fillna(0)
df["AvgReturnUsed"] = pd.to_numeric(df["AvgReturnUsed"], errors="coerce").fillna(0)

if "ConfidenceScore" not in df.columns:
    df["ConfidenceScore"] = 0.5
else:
    df["ConfidenceScore"] = pd.to_numeric(df["ConfidenceScore"], errors="coerce").fillna(0.5)

if "TimesSeen" not in df.columns:
    if "TimesSeen_mem" in df.columns:
        df["TimesSeen"] = pd.to_numeric(df["TimesSeen_mem"], errors="coerce").fillna(1)
    else:
        df["TimesSeen"] = 1
else:
    df["TimesSeen"] = pd.to_numeric(df["TimesSeen"], errors="coerce").fillna(1)

if "SurvivalLabel" not in df.columns:
    if "SurvivalLabel_mem" in df.columns:
        df["SurvivalLabel"] = df["SurvivalLabel_mem"].fillna("UNKNOWN")
    else:
        df["SurvivalLabel"] = "UNKNOWN"
else:
    df["SurvivalLabel"] = df["SurvivalLabel"].fillna("UNKNOWN")

# -----------------------------
# Multipliers
# -----------------------------
def survival_multiplier(label):
    label = str(label).upper()
    if label == "IMPROVING":
        return 1.15
    if label == "STABLE":
        return 1.00
    if label == "DECAYING":
        return 0.80
    if label == "DEAD":
        return 0.50
    return 0.90


df["SurvivalMultiplier"] = df["SurvivalLabel"].apply(survival_multiplier)

df["WinRateFactor"] = df["WinRateUsed"] / 100.0
df["TradeFactor"] = np.log1p(df["Trades"].clip(lower=1))
df["MemoryFactor"] = np.log1p(df["TimesSeen"].clip(lower=1))
df["ConfidenceFactor"] = 1 + (df["ConfidenceScore"] * 0.10)

# -----------------------------
# Alpha score
# -----------------------------
df["AlphaScore"] = (
    df["AvgReturnUsed"] *
    df["WinRateFactor"] *
    df["TradeFactor"] *
    df["SurvivalMultiplier"] *
    df["ConfidenceFactor"] *
    (1 + df["MemoryFactor"] * 0.05)
)

df["AlphaScore"] = df["AlphaScore"].round(4)

# -----------------------------
# Filter tiny patterns
# -----------------------------
df = df[df["Trades"] >= 25].copy()

# -----------------------------
# Sort best first
# -----------------------------
df = df.sort_values(
    by=["AlphaScore", "AvgReturnUsed", "WinRateUsed", "Trades"],
    ascending=[False, False, False, False]
).reset_index(drop=True)

df["AlphaRank"] = df.index + 1

# -----------------------------
# Final output
# -----------------------------
final_cols = [
    "AlphaRank",
    "Pattern",
    "Trades",
    "WinRateUsed",
    "AvgReturnUsed",
    "SurvivalLabel",
    "TimesSeen",
    "ConfidenceScore",
    "AlphaScore"
]

for optional_col in ["RecentAvgReturn5D", "RecentWinRate5D", "DeltaReturn5D", "ConfidenceRank"]:
    if optional_col in df.columns:
        final_cols.append(optional_col)

result = df[final_cols].copy()

result = result.rename(columns={
    "WinRateUsed": "WinRate",
    "AvgReturnUsed": "AvgReturn"
})

print("\nALPHA RANKING RESULTS\n")
print(result.head(20))

result.to_csv(OUTPUT_PATH, index=False)
print(f"\nSaved to {OUTPUT_PATH}")
print(f"Rows ranked: {len(result)}")
print(f"Survival file used: {'YES' if survival is not None else 'NO'}")
print(f"Memory file used: {'YES' if memory is not None else 'NO'}")