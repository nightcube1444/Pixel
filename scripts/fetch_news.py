import os
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import requests

# ---------------------------------------------------
# Configuration
# ---------------------------------------------------

OUTPUT_PATH = Path("data/news_data.csv")
API_KEY = os.getenv("FINNHUB_API_KEY", "d6qf52hr01qhcrmjv5d0d6qf52hr01qhcrmjv5dg").strip()

# ---------------------------------------------------
# Check API key
# ---------------------------------------------------

if not API_KEY:
    raise ValueError(
        "Missing FINNHUB_API_KEY environment variable. "
        "Set it before running fetch_news.py"
    )

# ---------------------------------------------------
# Finnhub API request
# ---------------------------------------------------

url = "https://finnhub.io/api/v1/news"

params = {
    "category": "general",
    "token": API_KEY,
}

print("Fetching news from Finnhub...")

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    print("HTTP error while calling Finnhub API:", e)
    print("Check if your API key is valid.")
    exit()

except requests.exceptions.RequestException as e:
    print("Network error while calling Finnhub API:", e)
    exit()

# ---------------------------------------------------
# Parse response
# ---------------------------------------------------

data = response.json()

rows = []

for item in data:

    ts = item.get("datetime")

    dt = pd.to_datetime(
        ts,
        unit="s",
        errors="coerce",
        utc=True
    )

    rows.append({
        "Date": dt.date() if pd.notna(dt) else None,
        "Ticker": "MARKET",
        "Headline": item.get("headline"),
        "Source": item.get("source"),
        "Summary": item.get("summary"),
        "URL": item.get("url"),
        "FetchedAtUTC": datetime.now(timezone.utc).isoformat()
    })

# ---------------------------------------------------
# Build dataframe
# ---------------------------------------------------

df = pd.DataFrame(rows)

if df.empty:
    print("No news returned from API.")
    exit()

# ---------------------------------------------------
# Clean data
# ---------------------------------------------------

df = df.dropna(subset=["Date", "Headline"]).copy()

df["Headline"] = df["Headline"].astype(str).str.strip()

df = df[df["Headline"] != ""]

df = df.drop_duplicates(
    subset=["Date", "Headline"]
).reset_index(drop=True)

# ---------------------------------------------------
# Save output
# ---------------------------------------------------

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    OUTPUT_PATH,
    index=False
)

# ---------------------------------------------------
# Output
# ---------------------------------------------------

print(f"\nSaved {len(df)} news rows to {OUTPUT_PATH}\n")

print("Sample rows:")
print(df.head(10))