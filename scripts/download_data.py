import time
from pathlib import Path

import pandas as pd
import yfinance as yf

UNIVERSE_PATH = Path("config/asset_universe.csv")
OUTPUT_PATH = Path("data/market_data.csv")
FAILED_OUTPUT = Path("data/failed_downloads.csv")

universe = pd.read_csv(UNIVERSE_PATH)

tickers = (
    universe["Ticker"]
    .dropna()
    .astype(str)
    .str.upper()
    .str.strip()
    .str.replace("$", "", regex=False)
    .drop_duplicates()
    .tolist()
)

print(f"\nLoaded {len(tickers)} assets")
print("First 10 tickers:")
print(tickers[:10])

frames = []
failed_tickers = []

for i, ticker in enumerate(tickers, start=1):

    print(f"\n[{i}/{len(tickers)}] Downloading {ticker}...")

    success = False

    for attempt in range(1, 4):

        try:

            df = yf.download(
                ticker,
                start="2010-01-01",
                auto_adjust=False,
                progress=False,
                threads=False
            )

            if not df.empty:

                success = True
                break

            print(
                f"Attempt {attempt}: empty dataset for {ticker}"
            )

        except Exception as e:

            print(
                f"Attempt {attempt} failed for {ticker}: {e}"
            )

        time.sleep(2)

    if not success:

        print(f"FAILED: {ticker}")

        failed_tickers.append(ticker)

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

    time.sleep(0.25)

if not frames:

    print("\nERROR: No market data downloaded.")

    raise SystemExit(1)

market_data = pd.concat(
    frames,
    ignore_index=True
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

market_data.to_csv(
    OUTPUT_PATH,
    index=False
)

pd.DataFrame(
    {"Ticker": failed_tickers}
).to_csv(
    FAILED_OUTPUT,
    index=False
)

print("\n===================================")
print("DOWNLOAD COMPLETE")
print("===================================")

print(f"Rows saved: {len(market_data):,}")
print(
    f"Assets saved: "
    f"{market_data['Ticker'].nunique()}"
)

print(
    f"Failed tickers: "
    f"{len(failed_tickers)}"
)

if failed_tickers:

    print("\nFailed list:")
    print(failed_tickers)

print(f"\nMarket data saved to:")
print(OUTPUT_PATH)

print(f"\nFailed downloads saved to:")
print(FAILED_OUTPUT)