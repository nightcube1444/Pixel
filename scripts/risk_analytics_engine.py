from pathlib import Path
import pandas as pd
import numpy as np

TRADE_LOG_PATH = Path("data/paper_trade_log.csv")
OUTPUT_PATH = Path("data/risk_analytics.csv")

if not TRADE_LOG_PATH.exists():
    print("Trade log not found.")
    raise SystemExit

df = pd.read_csv(TRADE_LOG_PATH)

if df.empty:
    print("No completed trades yet.")
    raise SystemExit

df["ReturnPct"] = pd.to_numeric(
    df["ReturnPct"],
    errors="coerce"
).fillna(0)

total_trades = len(df)

wins = df[df["ReturnPct"] > 0]
losses = df[df["ReturnPct"] <= 0]

win_rate = round(
    len(wins) / total_trades * 100,
    2
)

avg_win = round(
    wins["ReturnPct"].mean(),
    2
) if len(wins) else 0

avg_loss = round(
    losses["ReturnPct"].mean(),
    2
) if len(losses) else 0

expectancy = round(
    df["ReturnPct"].mean(),
    2
)

gross_profit = wins["ReturnPct"].sum()
gross_loss = abs(losses["ReturnPct"].sum())

profit_factor = round(
    gross_profit / gross_loss,
    2
) if gross_loss > 0 else np.inf

std_return = df["ReturnPct"].std()

sharpe = round(
    expectancy / std_return,
    2
) if std_return and std_return > 0 else 0

results = pd.DataFrame([{
    "TotalTrades": total_trades,
    "WinRate": win_rate,
    "AverageWin": avg_win,
    "AverageLoss": avg_loss,
    "Expectancy": expectancy,
    "ProfitFactor": profit_factor,
    "SharpeRatio": sharpe
}])

results.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\n===================================")
print(" MINI CUBE RISK ANALYTICS")
print("===================================\n")

print(results)

print(f"\nSaved to {OUTPUT_PATH}")