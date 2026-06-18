from pathlib import Path
import pandas as pd

TRADE_LOG_PATH = Path("data/paper_trade_log.csv")
OUTPUT_PATH = Path("data/trade_performance_summary.csv")

if not TRADE_LOG_PATH.exists():
    print("No trade log found.")
    raise SystemExit

df = pd.read_csv(TRADE_LOG_PATH)

if df.empty:
    print("No completed trades yet.")
    raise SystemExit

total_trades = len(df)

wins = len(df[df["ReturnPct"] > 0])
losses = len(df[df["ReturnPct"] <= 0])

win_rate = round((wins / total_trades) * 100, 2)

avg_return = round(df["ReturnPct"].mean(), 2)

best_trade = round(df["ReturnPct"].max(), 2)
worst_trade = round(df["ReturnPct"].min(), 2)

summary = pd.DataFrame([{
    "TotalTrades": total_trades,
    "Wins": wins,
    "Losses": losses,
    "WinRate": win_rate,
    "AverageReturn": avg_return,
    "BestTrade": best_trade,
    "WorstTrade": worst_trade
}])

summary.to_csv(OUTPUT_PATH, index=False)

print("\n===================================")
print(" MINI CUBE TRADE PERFORMANCE")
print("===================================\n")

print(summary)

print(f"\nSaved to {OUTPUT_PATH}")