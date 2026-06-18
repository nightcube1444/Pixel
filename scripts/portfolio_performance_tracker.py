from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

portfolio_file = BASE_DIR / "data/model_portfolio.csv"
signals_file = BASE_DIR / "data/latest_stock_signals.csv"

if not portfolio_file.exists():
    raise FileNotFoundError(portfolio_file)

if not signals_file.exists():
    raise FileNotFoundError(signals_file)

portfolio = pd.read_csv(portfolio_file)
signals = pd.read_csv(signals_file)

merged = portfolio.merge(
    signals[["Ticker", "Close"]],
    on="Ticker",
    how="left"
)

merged["PortfolioValue"] = (
    100000 *
    merged["WeightPct"] / 100
)

merged["Shares"] = (
    merged["PortfolioValue"] /
    merged["Close"]
)

merged["Shares"] = merged["Shares"].round(2)

merged.to_csv(
    BASE_DIR / "data/portfolio_positions.csv",
    index=False
)

print("\n===================================")
print(" MINI CUBE PORTFOLIO TRACKER")
print("===================================\n")

print(
    merged[
        [
            "Ticker",
            "WeightPct",
            "Close",
            "PortfolioValue",
            "Shares"
        ]
    ]
)

print(
    "\nSaved to data/portfolio_positions.csv"
)