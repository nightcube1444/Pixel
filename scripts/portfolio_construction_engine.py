from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data/context_aware_recommendations.csv"
OUTPUT_FILE = BASE_DIR / "data/model_portfolio.csv"

if not INPUT_FILE.exists():
    raise FileNotFoundError(INPUT_FILE)

df = pd.read_csv(INPUT_FILE)

required = [
    "Ticker",
    "AdjustedAlphaScore",
    "WinRate"
]

for col in required:
    if col not in df.columns:
        raise ValueError(f"Missing column: {col}")

# -------------------------
# Keep strongest candidates
# -------------------------

portfolio = df[
    df["Recommendation"].isin(["BUY", "WATCH"])
].copy()

if portfolio.empty:
    print("No BUY/WATCH candidates found")
    portfolio.to_csv(OUTPUT_FILE, index=False)
    raise SystemExit

# -------------------------
# Weight formula
# -------------------------

portfolio["WeightScore"] = (
    portfolio["AdjustedAlphaScore"]
    * (portfolio["WinRate"] / 100)
)

portfolio["WeightScore"] = portfolio["WeightScore"].clip(lower=0)

total = portfolio["WeightScore"].sum()

if total > 0:
    portfolio["WeightPct"] = (
        portfolio["WeightScore"] / total
    ) * 100
else:
    portfolio["WeightPct"] = 0

portfolio = portfolio.sort_values(
    "WeightPct",
    ascending=False
)

portfolio["WeightPct"] = (
    portfolio["WeightPct"]
    .round(2)
)

portfolio = portfolio[
    [
        "Ticker",
        "Recommendation",
        "AdjustedAlphaScore",
        "WinRate",
        "WeightPct"
    ]
]

portfolio.to_csv(
    OUTPUT_FILE,
    index=False
)

print("\n===================================")
print(" MINI CUBE MODEL PORTFOLIO")
print("===================================\n")

print(portfolio)

print(
    f"\nSaved to {OUTPUT_FILE}"
)