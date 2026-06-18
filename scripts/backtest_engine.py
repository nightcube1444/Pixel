import pandas as pd

# Load signal data
df = pd.read_csv("data/all_stock_signals.csv")

# Make sure data is sorted
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

# Calculate future 5-day return for each stock
df["Future Close 5D"] = df.groupby("Ticker")["Close"].shift(-5)
df["Future Return 5D"] = (df["Future Close 5D"] - df["Close"]) / df["Close"]

# Define success after PANIC:
# success = future return after 5 days is positive
panic_df = df[df["Panic"] == "PANIC"].copy()
panic_df["Success"] = panic_df["Future Return 5D"] > 0

# Summary stats
total_panic_signals = len(panic_df)
successful_panic_signals = panic_df["Success"].sum()

if total_panic_signals > 0:
    success_rate = successful_panic_signals / total_panic_signals
else:
    success_rate = 0

print("=== PANIC BACKTEST RESULTS ===")
 
print(f"Total PANIC signals: {total_panic_signals}")
print(f"Successful PANIC signals: {successful_panic_signals}")
avg_return = panic_df["Future Return 5D"].mean()

print(f"Average return after PANIC: {avg_return:.2%}")
print(f"Success rate: {success_rate:.2%}")

# Save detailed results
panic_df.to_csv("data/panic_backtest_results.csv", index=False)

print("Detailed results saved to data/panic_backtest_results.csv")