import yfinance as yf
import pandas as pd
from pathlib import Path

UNIVERSE_PATH = Path("config/asset_universe.csv")
OUTPUT_PATH = Path("data/market_data.csv")

universe = pd.read_csv(UNIVERSE_PATH)

tickers = (
    universe["Ticker"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

print(f"Loaded {len(tickers)} assets")
print(tickers[:10])
print(f"Downloading data for {len(tickers)} tickers:")
print(tickers)

frames = []

for ticker in tickers:
    print(f"Downloading {ticker}...")

    df = yf.download(
        ticker,
        start="2010-01-01",
        auto_adjust=False,
        progress=False
    )

    if df.empty:
        print(f"WARNING: No data for {ticker}")
        continue

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()

    df["Ticker"] = ticker.replace(".NS", "")

    required_cols = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Adj Close",
        "Volume",
        "Ticker",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df = df[required_cols]

    frames.append(df)

if not frames:
    print("No market data downloaded.")
    raise SystemExit(1)

market_data = pd.concat(frames, ignore_index=True)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
market_data.to_csv(OUTPUT_PATH, index=False)

print(f"Market data downloaded and saved to {OUTPUT_PATH}")
print(f"Rows saved: {len(market_data)}")
print(f"Assets saved: {market_data['Ticker'].nunique()}")