import pandas as pd

# Load behavior data
df = pd.read_csv("data/behavior_events.csv")

# Convert date column
df["Date"] = pd.to_datetime(df["Date"])

# Create future return columns
df["FutureClose5D"] = df.groupby("Ticker")["Close"].shift(-5)
df["Return5D"] = (df["FutureClose5D"] - df["Close"]) / df["Close"]

# Win = future return is positive
df["Win5D"] = df["Return5D"] > 0

# ---------- FEAR_EVENT ----------
fear_df = df[df["BehaviorLabel"] == "FEAR_EVENT"]
fear_count = len(fear_df)
fear_win_rate = fear_df["Win5D"].mean() if not fear_df.empty else 0
fear_avg_return = fear_df["Return5D"].mean() if not fear_df.empty else 0

# ---------- GREED_EVENT ----------
greed_df = df[df["BehaviorLabel"] == "GREED_EVENT"]
greed_count = len(greed_df)
greed_win_rate = greed_df["Win5D"].mean()
greed_avg_return = greed_df["Return5D"].mean()

# ---------- PRICE_PANIC_ONLY ----------
panic_df = df[df["BehaviorLabel"] == "PANIC"]
panic_count = len(panic_df)
panic_win_rate = panic_df["Win5D"].mean()
panic_avg_return = panic_df["Return5D"].mean()

# ---------- EXTREME_PANIC ----------
extreme_panic_df = df[df["RareEventLabel"] == "EXTREME_PANIC"]
extreme_panic_count = len(extreme_panic_df)
extreme_panic_win_rate = extreme_panic_df["Win5D"].mean()
extreme_panic_avg_return = extreme_panic_df["Return5D"].mean()

# Build results table
results = pd.DataFrame([
    {
        "Signal": "FEAR_EVENT",
        "Count": fear_count,
        "WinRate5D": fear_win_rate,
        "AvgReturn5D": fear_avg_return
    },
    {
        "Signal": "GREED_EVENT",
        "Count": greed_count,
        "WinRate5D": greed_win_rate,
        "AvgReturn5D": greed_avg_return
    },
    {
        "Signal": "PRICE_PANIC_ONLY",
        "Count": panic_count,
        "WinRate5D": panic_win_rate,
        "AvgReturn5D": panic_avg_return
    },
    {
        "Signal": "EXTREME_PANIC",
        "Count": extreme_panic_count,
        "WinRate5D": extreme_panic_win_rate,
        "AvgReturn5D": extreme_panic_avg_return
    }
])

# Save results
results.to_csv("data/research_results.csv", index=False)

# Print results
print(results)
print("Research analysis saved to data/research_results.csv")