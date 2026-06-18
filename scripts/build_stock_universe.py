import pandas as pd
from pathlib import Path

# File paths for your exported spreadsheet CSV files
sheet1_path = Path("data/Stock Tracker - Sheet1.csv")
sheet2_path = Path("data/Stock Tracker - Sheet2.csv")

if not sheet1_path.exists():
    print("Sheet1 CSV not found.")
    exit()

if not sheet2_path.exists():
    print("Sheet2 CSV not found.")
    exit()

# Read both sheets
sheet1 = pd.read_csv(sheet1_path)
sheet2 = pd.read_csv(sheet2_path)

all_tickers = []

# -----------------------------
# Sheet1: India watchlist
# -----------------------------
if "Ticker" in sheet1.columns:
    india_tickers = (
        sheet1["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    # Add .NS suffix if not already present
    india_tickers = [
        ticker if ticker.endswith(".NS") else f"{ticker}.NS"
        for ticker in india_tickers
        if ticker and ticker.lower() != "nan"
    ]

    all_tickers.extend(india_tickers)

# -----------------------------
# Sheet2: US watchlist
# -----------------------------
if "TICKER" in sheet2.columns:
    us_tickers = (
        sheet2["TICKER"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
elif "Ticker" in sheet2.columns:
    us_tickers = (
        sheet2["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
else:
    us_tickers = []

us_tickers = [
    ticker for ticker in us_tickers
    if ticker and ticker.lower() != "nan"
]

all_tickers.extend(us_tickers)

# Remove duplicates and sort
unique_tickers = sorted(set(all_tickers))

# Save final stock universe
stock_df = pd.DataFrame({"Ticker": unique_tickers})
stock_df.to_csv("data/stock.csv", index=False)

print("Stock universe built successfully.")
print(stock_df.head(20))
print(f"Total tickers: {len(stock_df)}")