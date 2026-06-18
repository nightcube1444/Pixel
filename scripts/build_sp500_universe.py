import pandas as pd
from pathlib import Path

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
tables = pd.read_html(url)
sp500_df = tables[0]

us_df = sp500_df[["Symbol"]].copy()
us_df.columns = ["Ticker"]

us_df["Ticker"] = (
    us_df["Ticker"]
    .astype(str)
    .str.strip()
    .str.upper()
    .str.replace(".", "-", regex=False)
)

india_tickers = pd.DataFrame({
    "Ticker": [
        "RELIANCE.NS",
        "INFY.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "WIPRO.NS",
        "HDFCBANK.NS",
        "ITC.NS",
        "TCS.NS",
        "ADANIENT.NS",
        "LT.NS"
    ]
})

universe_df = pd.concat([us_df, india_tickers], ignore_index=True)
universe_df["Ticker"] = universe_df["Ticker"].astype(str).str.strip().str.upper()
universe_df = universe_df.drop_duplicates().reset_index(drop=True)

Path("data").mkdir(exist_ok=True)
universe_df.to_csv("data/universe.csv", index=False)

print(f"Combined universe saved with {len(universe_df)} tickers.")
print(universe_df.head(20))
print(universe_df.tail(20))