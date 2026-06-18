import pandas as pd
from pathlib import Path

# -----------------------------
# File paths
# -----------------------------
market_path = Path("data/market_data.csv")
news_path = Path("data/news_signals.csv")
output_path = Path("data/behavior_events.csv")

# -----------------------------
# Check files exist
# -----------------------------
if not market_path.exists():
    print("market_data.csv not found.")
    exit()

if not news_path.exists():
    print("news_signals.csv not found.")
    exit()

if market_path.stat().st_size == 0:
    print("market_data.csv is empty.")
    exit()

if news_path.stat().st_size == 0:
    print("news_signals.csv is empty.")
    exit()

# -----------------------------
# Load data
# -----------------------------
market_df = pd.read_csv(market_path)
news_df = pd.read_csv(news_path)

if market_df.empty:
    print("market_data.csv has no rows.")
    exit()

if news_df.empty:
    print("news_signals.csv has no rows.")
    exit()

# -----------------------------
# Normalize required columns
# -----------------------------
required_market_cols = ["Date", "Ticker", "Close"]
missing_market = [col for col in required_market_cols if col not in market_df.columns]

if missing_market:
    print("market_data.csv is missing columns:", missing_market)
    exit()

required_news_cols = ["Date"]
missing_news = [col for col in required_news_cols if col not in news_df.columns]

if missing_news:
    print("news_signals.csv is missing columns:", missing_news)
    exit()

# If ticker column is missing in news, apply news to all stocks on that date
if "Ticker" not in news_df.columns:
    print("Ticker column missing — applying signals to ALL stocks")
    news_df["Ticker"] = "ALL"

# -----------------------------
# Normalize dates
# -----------------------------
market_df["Date"] = pd.to_datetime(market_df["Date"], errors="coerce")
news_df["Date"] = pd.to_datetime(news_df["Date"], errors="coerce")

market_df = market_df.dropna(subset=["Date", "Ticker", "Close"]).copy()
news_df = news_df.dropna(subset=["Date"]).copy()

market_df["Date"] = market_df["Date"].dt.normalize()
news_df["Date"] = news_df["Date"].dt.normalize()

# -----------------------------
# Normalize tickers
# -----------------------------
market_df["Ticker"] = (
    market_df["Ticker"]
    .astype(str)
    .str.replace(".NS", "", regex=False)
    .str.strip()
    .str.upper()
)

news_df["Ticker"] = (
    news_df["Ticker"]
    .astype(str)
    .str.replace(".NS", "", regex=False)
    .str.strip()
    .str.upper()
)

# -----------------------------
# Sort market data
# -----------------------------
market_df = market_df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

# -----------------------------
# Create moving averages
# -----------------------------
market_df["MA20"] = (
    market_df.groupby("Ticker")["Close"]
    .transform(lambda s: s.rolling(20, min_periods=20).mean())
)

market_df["MA50"] = (
    market_df.groupby("Ticker")["Close"]
    .transform(lambda s: s.rolling(50, min_periods=50).mean())
)

# -----------------------------
# Create daily returns
# -----------------------------
market_df["DailyReturn"] = (
    market_df.groupby("Ticker")["Close"]
    .pct_change()
)

# -----------------------------
# Create rolling volatility
# -----------------------------
market_df["Volatility20"] = (
    market_df.groupby("Ticker")["DailyReturn"]
    .transform(lambda s: s.rolling(20, min_periods=20).std())
)

# -----------------------------
# Build volatility thresholds
# -----------------------------
ticker_thresholds = {}

for ticker, group in market_df.groupby("Ticker"):
    vols = group["Volatility20"].dropna()

    if vols.empty:
        ticker_thresholds[ticker] = {
            "low": None,
            "high": None
        }
    else:
        ticker_thresholds[ticker] = {
            "low": vols.quantile(0.33),
            "high": vols.quantile(0.67)
        }

# -----------------------------
# Label functions
# -----------------------------
def label_trend(row):
    ma20 = row["MA20"]
    ma50 = row["MA50"]
    close = row["Close"]

    if pd.isna(ma20) or pd.isna(ma50) or pd.isna(close):
        return "UNKNOWN_TREND"

    if close > ma20 and ma20 > ma50:
        return "UPTREND"
    elif close < ma20 and ma20 < ma50:
        return "DOWNTREND"
    else:
        return "SIDEWAYS"


def label_ma_position(row):
    ma20 = row["MA20"]
    close = row["Close"]

    if pd.isna(ma20) or pd.isna(close):
        return "UNKNOWN_MA"

    if close > ma20:
        return "ABOVE_20MA"
    else:
        return "BELOW_20MA"


def label_volatility(row):
    ticker = row["Ticker"]
    vol = row["Volatility20"]

    if pd.isna(vol):
        return "UNKNOWN_VOL"

    low_threshold = ticker_thresholds[ticker]["low"]
    high_threshold = ticker_thresholds[ticker]["high"]

    if low_threshold is None or high_threshold is None:
        return "UNKNOWN_VOL"

    if vol < low_threshold:
        return "LOW_VOL"
    elif vol > high_threshold:
        return "HIGH_VOL"
    else:
        return "NORMAL_VOL"


def label_behavior(row):
    fear = row.get("FearScore", 0)
    positive = row.get("PositiveScore", 0)

    fear = 0 if pd.isna(fear) else fear
    positive = 0 if pd.isna(positive) else positive

    if fear > positive:
        return "UNCERTAINTY_EVENT"
    elif positive > fear:
        return "NORMAL"
    else:
        return "NORMAL"


def label_signal_strength(row):
    headline_count = row.get("HeadlineCount", 0)
    headline_count = 0 if pd.isna(headline_count) else headline_count

    if headline_count >= 4:
        return "STRONG"
    elif headline_count >= 2:
        return "MODERATE"
    elif headline_count >= 1:
        return "WEAK"
    else:
        return "NONE"


def label_rare_event(row):
    fear = row.get("FearScore", 0)
    positive = row.get("PositiveScore", 0)
    headline_count = row.get("HeadlineCount", 0)

    fear = 0 if pd.isna(fear) else fear
    positive = 0 if pd.isna(positive) else positive
    headline_count = 0 if pd.isna(headline_count) else headline_count

    if fear >= 4 and headline_count >= 2:
        return "EXTREME_PANIC"
    elif positive >= 4 and headline_count >= 2:
        return "EXTREME_EUPHORIA"
    else:
        return "NONE"

# -----------------------------
# Apply market labels
# -----------------------------
market_df["TrendLabel"] = market_df.apply(label_trend, axis=1)
market_df["MAPositionLabel"] = market_df.apply(label_ma_position, axis=1)
market_df["VolatilityLabel"] = market_df.apply(label_volatility, axis=1)

# -----------------------------
# Merge news into market data
# -----------------------------
if (news_df["Ticker"] == "ALL").all():
    merged_df = pd.merge(
        market_df,
        news_df.drop(columns=["Ticker"]),
        on="Date",
        how="left"
    )
else:
    merged_df = pd.merge(
        market_df,
        news_df,
        on=["Date", "Ticker"],
        how="left"
    )

# -----------------------------
# Fill missing news numeric fields
# -----------------------------
for col in ["FearScore", "PositiveScore", "HeadlineCount"]:
    if col not in merged_df.columns:
        merged_df[col] = 0
    merged_df[col] = merged_df[col].fillna(0)

# -----------------------------
# Build old label columns
# -----------------------------
merged_df["BehaviorLabel"] = merged_df.apply(label_behavior, axis=1)
merged_df["SignalStrengthLabel"] = merged_df.apply(label_signal_strength, axis=1)
merged_df["RareEventLabel"] = merged_df.apply(label_rare_event, axis=1)

# -----------------------------
# Build richer SignalSetup
# -----------------------------
merged_df["Pattern"] = (
    merged_df["BehaviorLabel"].astype(str) + " | " +
    merged_df["SignalStrengthLabel"].astype(str) + " | " +
    merged_df["RareEventLabel"].astype(str) + " | " +
    merged_df["TrendLabel"].astype(str) + " | " +
    merged_df["VolatilityLabel"].astype(str) + " | " +
    merged_df["MAPositionLabel"].astype(str)
) 
merged_df["SignalSetup"] = merged_df["Pattern"]

# -----------------------------
# Save output
# -----------------------------
merged_df.to_csv(output_path, index=False)

print("Behavior events created and saved to data/behavior_events.csv")
print(
    merged_df[
        [
            "Date",
            "Ticker",
            "FearScore",
            "PositiveScore",
            "HeadlineCount",
            "BehaviorLabel",
            "SignalStrengthLabel",
            "RareEventLabel",
            "TrendLabel",
            "VolatilityLabel",
            "MAPositionLabel",
            "SignalSetup"
        ]
    ].head()
)