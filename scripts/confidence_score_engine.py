import pandas as pd
import math
from pathlib import Path

file_path = Path("data/pattern_stability_results.csv")

if not file_path.exists():
    print("pattern_stability_results.csv not found.")
    exit()

df = pd.read_csv(file_path)

if df.empty:
    print("No pattern stability data found.")
    exit()

# Make sure required columns exist
required_cols = ["Pattern", "Appearances", "AvgTrades", "AvgWinRate", "AvgReturn"]

for col in required_cols:
    if col not in df.columns:
        print(f"Missing required column: {col}")
        exit()

# Safe confidence score calculation
def calculate_confidence_score(row):
    appearances = row["Appearances"]
    avg_trades = row["AvgTrades"]
    avg_win_rate = row["AvgWinRate"]
    avg_return = row["AvgReturn"]

    if pd.isna(appearances) or pd.isna(avg_trades) or pd.isna(avg_win_rate) or pd.isna(avg_return):
        return None

    if appearances <= 0 or avg_trades <= 0:
        return None

    score = avg_return * math.sqrt(appearances) * (avg_win_rate / 100) * math.sqrt(avg_trades)
    return round(score, 4)

df["ConfidenceScore"] = df.apply(calculate_confidence_score, axis=1)

# Sort strongest confidence first
df = df.sort_values(
    by=["ConfidenceScore", "AvgReturn", "AvgWinRate"],
    ascending=[False, False, False],
    na_position="last"
).reset_index(drop=True)

# Add confidence rank
df["ConfidenceRank"] = range(1, len(df) + 1)

# Move rank column to front
cols = ["ConfidenceRank"] + [col for col in df.columns if col != "ConfidenceRank"]
df = df[cols]

print("\nCONFIDENCE SCORE ENGINE RESULTS\n")
print(df)

df.to_csv("data/confidence_score_results.csv", index=False)

print("\nSaved to data/confidence_score_results.csv")