import pandas as pd

# Load forward validation results
df = pd.read_csv("data/forward_validation_results.csv")

# Parse dates
df["SignalDate"] = pd.to_datetime(df["SignalDate"], format="mixed", errors="coerce")
df = df.dropna(subset=["SignalDate"])

if df.empty:
    print("No forward validation data available.")
    exit()

# Sort by date
df = df.sort_values("SignalDate").reset_index(drop=True)

# Split into train and test halves
split_idx = int(len(df) * 0.7)

train_df = df.iloc[:split_idx].copy()
test_df = df.iloc[split_idx:].copy()

def summarize_by_signal(dataframe, label):
    if dataframe.empty:
        return pd.DataFrame()

    summary = dataframe.groupby("Signal").agg(
        Trades=("Ticker", "count"),
        WinRate=("Win1D", "mean"),
        AvgReturn=("Return1D", "mean")
    ).reset_index()

    summary["WinRate"] = summary["WinRate"] * 100
    summary["AvgReturn"] = summary["AvgReturn"] * 100
    summary["Period"] = label

    summary = summary.round({
        "WinRate": 2,
        "AvgReturn": 3
    })

    return summary

train_summary = summarize_by_signal(train_df, "TRAIN")
test_summary = summarize_by_signal(test_df, "TEST")

results = pd.concat([train_summary, test_summary], ignore_index=True)

print("\nWALK-FORWARD TEST RESULTS\n")
print(results)

results.to_csv("data/walk_forward_results.csv", index=False)

print("\nSaved to data/walk_forward_results.csv")