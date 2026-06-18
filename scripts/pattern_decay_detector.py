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

# Make sure date column is proper datetime
df["SnapshotDate"] = pd.to_datetime(df["SnapshotDate"], format="mixed", errors="coerce")
df = df.dropna(subset=["SnapshotDate"])

if df.empty:
    print("No valid dated memory data found.")
    exit()

results = []

for pattern, group in df.groupby("Pattern"):
    group = group.sort_values("SnapshotDate").copy()

    first_seen = group["SnapshotDate"].min()
    last_seen = group["SnapshotDate"].max()

    first_return = group.iloc[0]["AvgReturn10D"]
    latest_return = group.iloc[-1]["AvgReturn10D"]

    appearances = len(group)
    change_in_return = latest_return - first_return

    if change_in_return > 0.2:
        decay_label = "IMPROVING"
    elif change_in_return < -0.2:
        decay_label = "DECAYING"
    else:
        decay_label = "STABLE"

    results.append({
        "Pattern": pattern,
        "Appearances": appearances,
        "FirstSeen": first_seen,
        "LastSeen": last_seen,
        "FirstAvgReturn": round(first_return, 3),
        "LatestAvgReturn": round(latest_return, 3),
        "ReturnChange": round(change_in_return, 3),
        "DecayLabel": decay_label
    })

decay_df = pd.DataFrame(results)

if decay_df.empty:
    print("No pattern decay results could be generated.")
    exit()

# Sort by most appearances, then strongest latest return
decay_df = decay_df.sort_values(
    by=["Appearances", "LatestAvgReturn"],
    ascending=[False, False]
).reset_index(drop=True)

decay_df["DecayRank"] = range(1, len(decay_df) + 1)

# Move rank to front
cols = ["DecayRank"] + [col for col in decay_df.columns if col != "DecayRank"]
decay_df = decay_df[cols]

print("\nPATTERN DECAY DETECTOR RESULTS\n")
print(decay_df)

decay_df.to_csv("data/pattern_decay_results.csv", index=False)

print("\nSaved to data/pattern_decay_results.csv")