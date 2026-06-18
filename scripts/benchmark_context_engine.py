import pandas as pd

df = pd.read_csv("data/market_data.csv")

print("Columns detected:", df.columns)

# Ensure correct column names
df.columns = [c.strip() for c in df.columns]

if "Ticker" not in df.columns:
    df = df.rename(columns={df.columns[-1]: "Ticker"})

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date", "Ticker", "Close"]).copy()

print(df[["Date", "Ticker", "Close"]].head(10))

# Keep only benchmark assets
bench = df[df["Ticker"].isin(["SPY", "^VIX"])].copy()
bench = bench.sort_values(["Ticker", "Date"])

# Build SPY regime helper columns
spy = bench[bench["Ticker"] == "SPY"].copy()
spy["SPY_MA50"] = spy["Close"].rolling(50).mean()
spy["SPY_MA200"] = spy["Close"].rolling(200).mean()
spy["SPY_Return"] = spy["Close"].pct_change()
spy["SPY_Vol20"] = spy["SPY_Return"].rolling(20).std()

def classify_spy_regime(row):
    c = row["Close"]
    ma50 = row["SPY_MA50"]
    ma200 = row["SPY_MA200"]
    vol20 = row["SPY_Vol20"]

    if pd.isna(c) or pd.isna(ma50) or pd.isna(ma200) or pd.isna(vol20):
        return "UNKNOWN"
    if vol20 >= 0.02:
        return "HIGH_VOL"
    if c > ma50 and ma50 > ma200:
        return "BULL"
    if c < ma50 and ma50 < ma200:
        return "BEAR"
    return "SIDEWAYS"

spy["SPY_Regime"] = spy.apply(classify_spy_regime, axis=1)
spy = spy[["Date", "SPY_Regime"]]

# Build VIX state
vix = bench[bench["Ticker"] == "^VIX"].copy()

def classify_vix_state(x):
    if pd.isna(x):
        return "UNKNOWN"
    if x >= 30:
        return "VIX_EXTREME"
    if x >= 20:
        return "VIX_HIGH"
    if x >= 15:
        return "VIX_ELEVATED"
    return "VIX_LOW"

vix["VIX_State"] = vix["Close"].apply(classify_vix_state)
vix = vix[["Date", "VIX_State"]]

# Merge benchmark states by date
context = pd.merge(spy, vix, on="Date", how="outer").sort_values("Date")

print(context.tail(20))

context.to_csv("data/benchmark_context.csv", index=False)
print("Saved to data/benchmark_context.csv")