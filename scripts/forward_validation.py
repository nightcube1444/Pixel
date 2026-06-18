import pandas as pd
from pathlib import Path

# -----------------------------
# File paths
# -----------------------------
log_path = Path("data/live_signal_log.csv")
market_path = Path("data/market_data.csv")
output_path = Path("data/forward_validation_results.csv")

# -----------------------------
# Check files exist
# -----------------------------
if not log_path.exists():
    print("live_signal_log.csv not found.")
    exit()

if not market_path.exists():
    print("market_data.csv not found.")
    exit()

if log_path.stat().st_size == 0:
    print("live_signal_log.csv is empty.")
    exit()

if market_path.stat().st_size == 0:
    print("market_data.csv is empty.")
    exit()

# -----------------------------
# Load signal log
# -----------------------------
log_df = pd.read_csv(log_path)

if log_df.empty:
    print("No logged signals found.")
    exit()

# Normalize date column in signal log
if "SignalDate" not in log_df.columns:
    print("SignalDate column not found in live_signal_log.csv")
    exit()

if "Ticker" not in log_df.columns:
    print("Ticker column not found in live_signal_log.csv")
    exit()

log_df["SignalDate"] = pd.to_datetime(log_df["SignalDate"], errors="coerce")
log_df = log_df.dropna(subset=["SignalDate", "Ticker"]).copy()
log_df["SignalDate"] = log_df["SignalDate"].dt.normalize()
log_df["Ticker"] = log_df["Ticker"].astype(str).str.replace(".NS", "", regex=False).str.strip().str.upper()

# -----------------------------
# Load market data
# -----------------------------
market_df = pd.read_csv(market_path)

if market_df.empty:
    print("No market data found.")
    exit()

required_market_cols = ["Date", "Close", "Ticker"]
missing_market = [c for c in required_market_cols if c not in market_df.columns]
if missing_market:
    print("market_data.csv missing columns:", missing_market)
    exit()

market_df["Date"] = pd.to_datetime(market_df["Date"], errors="coerce")
market_df = market_df.dropna(subset=["Date", "Close", "Ticker"]).copy()
market_df["Date"] = market_df["Date"].dt.normalize()
market_df["Ticker"] = market_df["Ticker"].astype(str).str.replace(".NS", "", regex=False).str.strip().str.upper()

# Keep only useful columns
market_df = market_df[["Date", "Ticker", "Close"]].sort_values(["Ticker", "Date"]).reset_index(drop=True)

# -----------------------------
# Helper function
# -----------------------------
def get_future_close(ticker_df: pd.DataFrame, signal_date: pd.Timestamp, days_ahead: int):
    """
    Return the close price N trading rows after the signal date.
    """
    future_rows = ticker_df[ticker_df["Date"] > signal_date].head(days_ahead)

    if len(future_rows) < days_ahead:
        return None

    return float(future_rows.iloc[-1]["Close"])

# -----------------------------
# Build forward validation results
# -----------------------------
results = []

for _, row in log_df.iterrows():
    ticker = row["Ticker"]
    signal_date = row["SignalDate"]

    ticker_df = market_df[market_df["Ticker"] == ticker].copy()

    if ticker_df.empty:
        continue

    # Find entry close on the signal date
    entry_row = ticker_df[ticker_df["Date"] == signal_date]

    if entry_row.empty:
        continue

    entry_price = float(entry_row.iloc[0]["Close"])

    price_1d = get_future_close(ticker_df, signal_date, 1)
    price_3d = get_future_close(ticker_df, signal_date, 3)
    price_5d = get_future_close(ticker_df, signal_date, 5)
    price_10d = get_future_close(ticker_df, signal_date, 10)

    ret_1d = (price_1d - entry_price) / entry_price if price_1d is not None else None
    ret_3d = (price_3d - entry_price) / entry_price if price_3d is not None else None
    ret_5d = (price_5d - entry_price) / entry_price if price_5d is not None else None
    ret_10d = (price_10d - entry_price) / entry_price if price_10d is not None else None

    # Choose signal label safely
    signal_label = None
    for possible_col in ["BehaviorLabel", "Signal", "SignalLabel"]:
        if possible_col in row.index:
            signal_label = row[possible_col]
            break

    if signal_label is None:
        signal_label = "UNKNOWN"

    results.append({
        "Ticker": ticker,
        "SignalDate": signal_date,
        "Signal": signal_label,
        "EntryPrice": entry_price,

        "Price1D": price_1d,
        "Return1D": ret_1d,
        "Win1D": ret_1d > 0 if ret_1d is not None else None,

        "Price3D": price_3d,
        "Return3D": ret_3d,
        "Win3D": ret_3d > 0 if ret_3d is not None else None,

        "Price5D": price_5d,
        "Return5D": ret_5d,
        "Win5D": ret_5d > 0 if ret_5d is not None else None,

        "Price10D": price_10d,
        "Return10D": ret_10d,
        "Win10D": ret_10d > 0 if ret_10d is not None else None
    })

# -----------------------------
# Save output
# -----------------------------
results_df = pd.DataFrame(results)

if results_df.empty:
    print("No forward validation rows could be created.")
    results_df.to_csv(output_path, index=False)
    print(f"Saved empty file to {output_path}")
    exit()

results_df.to_csv(output_path, index=False)

print(f"Forward validation saved to {output_path}")
print(results_df.head())