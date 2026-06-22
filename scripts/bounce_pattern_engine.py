import pandas as pd

print("\nBOUNCE PATTERN ENGINE\n")

try:
    df = pd.read_csv("data/bounce_back_results.csv")
except FileNotFoundError:
    print("Missing: data/bounce_back_results.csv")
    raise SystemExit

required = [
    "CrossAssetPattern",
    "Bounce5D",
    "Bounce10D",
    "Recovered5D",
    "Recovered10D",
]

missing = [c for c in required if c not in df.columns]

if missing:
    print(f"Missing columns: {missing}")
    raise SystemExit

df = df.dropna(subset=["CrossAssetPattern"])

summary = (
    df.groupby("CrossAssetPattern")
    .agg(
        Events=("Ticker", "count"),
        AvgBounce5D=("Bounce5D", "mean"),
        AvgBounce10D=("Bounce10D", "mean"),
        RecoveryRate5D=("Recovered5D", "mean"),
        RecoveryRate10D=("Recovered10D", "mean"),
    )
    .reset_index()
)

summary["RecoveryRate5D"] *= 100
summary["RecoveryRate10D"] *= 100

summary["BounceScore"] = (
    summary["AvgBounce10D"] * 10
    + summary["RecoveryRate10D"]
)

summary = summary.round(2)

summary = summary.sort_values(
    "BounceScore",
    ascending=False
)

print(
    summary.head(30).to_string(index=False)
)

summary.to_csv(
    "data/bounce_pattern_rankings.csv",
    index=False
)

print(f"\nPatterns analyzed: {len(summary)}")
print(
    "Saved -> data/bounce_pattern_rankings.csv"
)