import pandas as pd

signals = pd.read_csv("data/all_stock_signals.csv")
context = pd.read_csv("data/benchmark_context.csv")

signals["Date"] = pd.to_datetime(signals["Date"], errors="coerce")
context["Date"] = pd.to_datetime(context["Date"], errors="coerce")

merged = pd.merge(signals, context, on="Date", how="left")

# Cleaner labels

merged["PatternBase"] = (
    merged["PatternBase"]
    .fillna("NONE|INSUFFICIENT_HISTORY|NORMAL")
)

merged["SPY_Regime"] = (
    merged["SPY_Regime"]
    .fillna("SPY_INSUFFICIENT_HISTORY")
    .replace("UNKNOWN", "SPY_INSUFFICIENT_HISTORY")
)

merged["VIX_State"] = (
    merged["VIX_State"]
    .fillna("VIX_UNAVAILABLE")
)

merged["CrossAssetPattern"] = (
    merged["PatternBase"].astype(str)
    + "|"
    + merged["SPY_Regime"].astype(str)
    + "|"
    + merged["VIX_State"].astype(str)
)

merged.to_csv(
    "data/all_stock_signals_with_context.csv",
    index=False
)

print("Saved to data/all_stock_signals_with_context.csv")

print(
    merged[
        [
            "Date",
            "Ticker",
            "PatternBase",
            "SPY_Regime",
            "VIX_State",
            "CrossAssetPattern",
        ]
    ].tail(20)
)