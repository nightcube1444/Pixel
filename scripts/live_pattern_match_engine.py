from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

signals_file = BASE_DIR / "data/all_stock_signals_with_context.csv"
alpha_file = BASE_DIR / "data/alpha_ranking_results.csv"
output_file = BASE_DIR / "data/live_pattern_matches.csv"

# -------------------------
# Load files
# -------------------------

signals = pd.read_csv(signals_file)
alpha = pd.read_csv(alpha_file)

if signals.empty:
    raise ValueError("No signal data found")

if alpha.empty:
    raise ValueError("No alpha ranking data found")

# -------------------------
# Latest signal per ticker
# -------------------------

signals["Date"] = pd.to_datetime(signals["Date"])

latest_signals = (
    signals
    .sort_values("Date")
    .groupby("Ticker")
    .tail(1)
    .copy()
)

# -------------------------
# Match patterns
# -------------------------

matches = []

for _, row in latest_signals.iterrows():

    pattern = str(row.get("CrossAssetPattern", "")).strip()

    if pattern == "":
        continue

    alpha_match = alpha[
        alpha["Pattern"].astype(str).str.strip() == pattern
    ]

    if alpha_match.empty:
        continue

    alpha_row = alpha_match.iloc[0]

    matches.append({
        "Ticker": row["Ticker"],
        "Date": row["Date"],
        "Pattern": pattern,
        "PrimarySignal": row.get("PrimarySignal", "NONE"),
        "MarketRegime": row.get("MarketRegime", "UNKNOWN"),
        "AlphaRank": alpha_row["AlphaRank"],
        "Trades": alpha_row["Trades"],
        "WinRate": alpha_row["WinRate"],
        "AlphaScore": alpha_row["AlphaScore"]
    })

# -------------------------
# Output
# -------------------------

results = pd.DataFrame(matches)

if results.empty:
    print("No historical alpha matches found.")
else:

    results = results.sort_values(
        ["AlphaScore", "WinRate"],
        ascending=False
    )

    results.to_csv(output_file, index=False)

    print("\nLIVE PATTERN MATCHES\n")

    print(
        results[
            [
                "Ticker",
                "PrimarySignal",
                "Pattern",
                "Trades",
                "WinRate",
                "AlphaScore"
            ]
        ].head(20)
    )

    print()
    print(f"Matches found: {len(results)}")
    print(f"Saved to {output_file}")