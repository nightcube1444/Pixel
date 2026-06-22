import pandas as pd
import numpy as np

print("\nBOUNCE PROBABILITY ENGINE\n")

try:
    df = pd.read_csv("data/forward_validation_results.csv")
except Exception as e:
    print(f"Could not load file: {e}")
    exit()

required_cols = [
    "Signal",
    "Return1D",
    "Return5D",
    "Return10D"
]

missing = [c for c in required_cols if c not in df.columns]

if missing:
    print("Missing columns:", missing)
    exit()

# -------------------------
# Bounce Definition
# -------------------------

# Day 1 must be negative
bounce_df = df[df["Return1D"] < 0].copy()

if bounce_df.empty:
    print("No bounce candidates found.")
    exit()

# 5D recovery
bounce_df["Recovered5D"] = (
    bounce_df["Return5D"] > 0
).astype(int)

# 10D recovery
bounce_df["Recovered10D"] = (
    bounce_df["Return10D"] > 0
).astype(int)

# strength score
bounce_df["BounceStrength"] = (
    bounce_df["Return10D"]
)

summary = (
    bounce_df
    .groupby("Signal")
    .agg(
        Events=("Signal", "count"),
        AvgDrop1D=("Return1D", "mean"),
        AvgBounce5D=("Return5D", "mean"),
        AvgBounce10D=("Return10D", "mean"),
        RecoveryRate5D=("Recovered5D", "mean"),
        RecoveryRate10D=("Recovered10D", "mean")
    )
    .reset_index()
)

summary["RecoveryRate5D"] *= 100
summary["RecoveryRate10D"] *= 100

# -------------------------
# Probability Score
# -------------------------

summary["BounceProbability"] = (
    summary["RecoveryRate10D"] * 0.60
    +
    summary["RecoveryRate5D"] * 0.25
    +
    np.clip(summary["AvgBounce10D"], 0, None) * 5
    +
    np.clip(summary["AvgBounce5D"], 0, None) * 2
)

summary["BounceProbability"] = (
    summary["BounceProbability"]
    .round(2)
)

# -------------------------
# Classification
# -------------------------

def classify(prob):

    if prob >= 85:
        return "ELITE"

    if prob >= 70:
        return "HIGH"

    if prob >= 55:
        return "MEDIUM"

    return "LOW"

summary["Classification"] = (
    summary["BounceProbability"]
    .apply(classify)
)

summary = summary.sort_values(
    "BounceProbability",
    ascending=False
)

summary = summary.round({
    "AvgDrop1D": 2,
    "AvgBounce5D": 2,
    "AvgBounce10D": 2,
    "RecoveryRate5D": 2,
    "RecoveryRate10D": 2
})

print(summary.head(20))

summary.to_csv(
    "data/bounce_probability_rankings.csv",
    index=False
)

print(
    f"\nSignals analyzed: {len(summary)}"
)

print(
    "Saved -> data/bounce_probability_rankings.csv"
)