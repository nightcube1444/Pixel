import pandas as pd

df = pd.read_csv("data/forward_validation_results.csv")

signals = df["Signal"].unique()

results = []

for signal in signals:

    signal_df = df[df["Signal"] == signal]

    trades = len(signal_df)

    if trades == 0:
        continue

    win_rate = (signal_df["Win1D"] == True).mean()
    avg_return = signal_df["Return1D"].mean()

    results.append({
        "Signal": signal,
        "Trades": trades,
        "WinRate": round(win_rate * 100, 2),
        "AverageReturn": round(avg_return * 100, 3)
    })

stats_df = pd.DataFrame(results)

stats_df = stats_df.sort_values("WinRate", ascending=False)

print("\nSignal Performance\n")
print(stats_df)

stats_df.to_csv("data/signal_statistics.csv", index=False)

print("\nSaved to data/signal_statistics.csv")