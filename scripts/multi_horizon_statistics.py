import pandas as pd
from pathlib import Path

file_path = Path("data/forward_validation_results.csv")

if not file_path.exists():
    print("forward_validation_results.csv not found.")
    exit()

df = pd.read_csv(file_path)

if df.empty:
    print("No forward validation results found.")
    exit()

signals = df["Signal"].dropna().unique()

results = []

for signal in signals:
    signal_df = df[df["Signal"] == signal]

    trades = len(signal_df)

    if trades == 0:
        continue

    results.append({
        "Signal": signal,
        "Trades": trades,

        "WinRate1D": round(signal_df["Win1D"].dropna().mean() * 100, 2) if signal_df["Win1D"].dropna().shape[0] > 0 else None,
        "AvgReturn1D": round(signal_df["Return1D"].dropna().mean() * 100, 3) if signal_df["Return1D"].dropna().shape[0] > 0 else None,

        "WinRate3D": round(signal_df["Win3D"].dropna().mean() * 100, 2) if signal_df["Win3D"].dropna().shape[0] > 0 else None,
        "AvgReturn3D": round(signal_df["Return3D"].dropna().mean() * 100, 3) if signal_df["Return3D"].dropna().shape[0] > 0 else None,

        "WinRate5D": round(signal_df["Win5D"].dropna().mean() * 100, 2) if signal_df["Win5D"].dropna().shape[0] > 0 else None,
        "AvgReturn5D": round(signal_df["Return5D"].dropna().mean() * 100, 3) if signal_df["Return5D"].dropna().shape[0] > 0 else None,

        "WinRate10D": round(signal_df["Win10D"].dropna().mean() * 100, 2) if signal_df["Win10D"].dropna().shape[0] > 0 else None,
        "AvgReturn10D": round(signal_df["Return10D"].dropna().mean() * 100, 3) if signal_df["Return10D"].dropna().shape[0] > 0 else None
    })

stats_df = pd.DataFrame(results)

if stats_df.empty:
    print("No statistics could be generated.")
    exit()

stats_df = stats_df.sort_values(
    by=["AvgReturn10D", "WinRate10D", "Trades"],
    ascending=[False, False, False],
    na_position="last"
)

print("\nMULTI-HORIZON SIGNAL STATISTICS\n")
print(stats_df)

stats_df.to_csv("data/multi_horizon_statistics.csv", index=False)

print("\nSaved to data/multi_horizon_statistics.csv") 