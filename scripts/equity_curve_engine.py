from pathlib import Path
import pandas as pd

TRADE_LOG_PATH = Path("data/paper_trade_log.csv")
OUTPUT_PATH = Path("data/equity_curve.csv")

STARTING_CAPITAL = 100000

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

capital = STARTING_CAPITAL

rows = []

for _, trade in df.iterrows():

    pnl = capital * (trade["ReturnPct"] / 100)

    capital += pnl

    rows.append({
        "Timestamp": trade["Timestamp"],
        "Ticker": trade["Ticker"],
        "ReturnPct": trade["ReturnPct"],
        "Equity": round(capital, 2)
    })

equity_df = pd.DataFrame(rows)

equity_df["PeakEquity"] = equity_df["Equity"].cummax()

equity_df["DrawdownPct"] = (
    (equity_df["Equity"] -
     equity_df["PeakEquity"])
    /
    equity_df["PeakEquity"]
) * 100

equity_df.to_csv(
    OUTPUT_PATH,
    index=False
)

print("\n===================================")
print(" MINI CUBE EQUITY CURVE")
print("===================================\n")

print(equity_df.tail())

print("\nFinal Equity:",
      round(capital, 2))

print("Total Return:",
      round(
          ((capital - STARTING_CAPITAL)
           / STARTING_CAPITAL) * 100,
          2
      ),
      "%")

print("Max Drawdown:",
      round(
          equity_df["DrawdownPct"].min(),
          2
      ),
      "%")

print(f"\nSaved to {OUTPUT_PATH}")