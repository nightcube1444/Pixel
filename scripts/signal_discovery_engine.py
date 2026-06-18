import pandas as pd

# ---------------------------------
# Load full signal dataset
# ---------------------------------
df = pd.read_csv("data/all_stock_signals_with_context.csv")

# ---------------------------------
# Convert dates
# ---------------------------------
df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")

# ---------------------------------
# Validate required columns
# ---------------------------------
required_cols = ["Date", "Ticker", "Close"]
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")

# ---------------------------------
# Choose pattern source
# ---------------------------------
if "CrossAssetPattern" in df.columns:
    pattern_col = "CrossAssetPattern"
elif "PatternBase" in df.columns:
    pattern_col = "PatternBase"
else:
    raise ValueError("Neither CrossAssetPattern nor PatternBase exists in the dataset.")

# ---------------------------------
# Sort data properly
# ---------------------------------
df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

# ---------------------------------
# Compute future prices and returns
# ---------------------------------
df["Price1D"] = df.groupby("Ticker")["Close"].shift(-1)
df["Price3D"] = df.groupby("Ticker")["Close"].shift(-3)
df["Price5D"] = df.groupby("Ticker")["Close"].shift(-5)
df["Price10D"] = df.groupby("Ticker")["Close"].shift(-10)

df["Return1D"] = (df["Price1D"] / df["Close"]) - 1
df["Return3D"] = (df["Price3D"] / df["Close"]) - 1
df["Return5D"] = (df["Price5D"] / df["Close"]) - 1
df["Return10D"] = (df["Price10D"] / df["Close"]) - 1

df["Win1D"] = df["Return1D"] > 0
df["Win3D"] = df["Return3D"] > 0
df["Win5D"] = df["Return5D"] > 0
df["Win10D"] = df["Return10D"] > 0

# ---------------------------------
# Keep only rows with real signals
# ---------------------------------
if "PrimarySignal" in df.columns:
    df = df[df["PrimarySignal"].fillna("NONE") != "NONE"].copy()

# Keep only real patterns
df["Pattern"] = df[pattern_col].fillna("UNKNOWN")
df = df[df["Pattern"] != "UNKNOWN"].copy()

# ---------------------------------
# Group and summarize patterns
# ---------------------------------
discovery = df.groupby("Pattern").agg(
    Trades=("Ticker", "count"),

    WinRate1D=("Win1D", "mean"),
    AvgReturn1D=("Return1D", "mean"),

    WinRate3D=("Win3D", "mean"),
    AvgReturn3D=("Return3D", "mean"),

    WinRate5D=("Win5D", "mean"),
    AvgReturn5D=("Return5D", "mean"),

    WinRate10D=("Win10D", "mean"),
    AvgReturn10D=("Return10D", "mean")
).reset_index()

# ---------------------------------
# Convert win rates / returns to %
# ---------------------------------
for col in [
    "WinRate1D", "AvgReturn1D",
    "WinRate3D", "AvgReturn3D",
    "WinRate5D", "AvgReturn5D",
    "WinRate10D", "AvgReturn10D"
]:
    discovery[col] = discovery[col] * 100

# ---------------------------------
# Round values
# ---------------------------------
discovery = discovery.round({
    "WinRate1D": 2, "AvgReturn1D": 3,
    "WinRate3D": 2, "AvgReturn3D": 3,
    "WinRate5D": 2, "AvgReturn5D": 3,
    "WinRate10D": 2, "AvgReturn10D": 3
})

# ---------------------------------
# Filter tiny sample sizes
# ---------------------------------
discovery = discovery[discovery["Trades"] >= 5].copy()

# ---------------------------------
# Sort strongest patterns first
# You can change this ranking logic later
# ---------------------------------
discovery = discovery.sort_values(
    by=["AvgReturn5D", "WinRate5D", "Trades"],
    ascending=[False, False, False]
).reset_index(drop=True)

# ---------------------------------
# Add rank
# ---------------------------------
discovery["Rank"] = discovery.index + 1

# ---------------------------------
# Reorder columns
# ---------------------------------
discovery = discovery[[
    "Rank",
    "Pattern",
    "Trades",
    "WinRate1D", "AvgReturn1D",
    "WinRate3D", "AvgReturn3D",
    "WinRate5D", "AvgReturn5D",
    "WinRate10D", "AvgReturn10D"
]]

# ---------------------------------
# Print and save
# ---------------------------------
print("\nSIGNAL DISCOVERY ENGINE RESULTS\n")
print(discovery.head(30))

discovery.to_csv("data/signal_discovery_results.csv", index=False)

print("\nSaved to data/signal_discovery_results.csv")
print(f"Pattern source used: {pattern_col}")
print(f"Rows studied: {len(df)}")
print(f"Patterns found: {len(discovery)}")