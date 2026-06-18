import pandas as pd
from pathlib import Path

file_path = Path("data/market_memory.csv")

if not file_path.exists():
    print("market_memory.csv not found.")
    exit()

df = pd.read_csv(file_path)

if df.empty:
    print("No market memory data found.")
    exit()

# Make sure SnapshotDate is a date
df["SnapshotDate"] = pd.to_datetime(df["SnapshotDate"], format="mixed", errors="coerce")
df = df.dropna(subset=["SnapshotDate"])

if df.empty:
    print("No valid dated memory data found.")
    exit()

# Group by SignalSetup and summarize stability
stability_df = df.groupby("Pattern").agg(
    Appearances=("SnapshotDate", "count"),
    FirstSeen=("SnapshotDate", "min"),
    LastSeen=("SnapshotDate", "max"),
    AvgRank=("Rank", "mean"),
    BestRank=("Rank", "min"),
    WorstRank=("Rank", "max"),
    AvgTrades=("Trades", "mean"),
    AvgWinRate=("WinRate10D", "mean"),
    AvgReturn=("AvgReturn10D", "mean")
).reset_index()

# Round values
stability_df = stability_df.round({
    "AvgRank": 2,
    "AvgTrades": 2,
    "AvgWinRate": 2,
    "AvgReturn": 3
})

# Sort stable and strong patterns first
stability_df = stability_df.sort_values(
    by=["Appearances", "AvgReturn", "AvgWinRate"],
    ascending=[False, False, False]
).reset_index(drop=True)

# Add stability rank
stability_df["StabilityRank"] = range(1, len(stability_df) + 1)

# Move rank column to front
cols = ["StabilityRank"] + [col for col in stability_df.columns if col != "StabilityRank"]
stability_df = stability_df[cols]

print("\nPATTERN STABILITY TRACKER RESULTS\n")
print(stability_df)

stability_df.to_csv("data/pattern_stability_results.csv", index=False)

print("\nSaved to data/pattern_stability_results.csv")