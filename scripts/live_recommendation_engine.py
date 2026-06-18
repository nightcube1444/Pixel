from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

match_file = BASE_DIR / "data/live_pattern_matches.csv"
output_file = BASE_DIR / "data/live_recommendations.csv"

if not match_file.exists():
    raise FileNotFoundError(match_file)

df = pd.read_csv(match_file)

if df.empty:
    raise ValueError("No pattern matches found")

# --------------------------
# Confidence Classification
# --------------------------

def confidence_level(alpha_score, win_rate, trades):

    if alpha_score >= 20 and win_rate >= 60 and trades >= 100:
        return "VERY_HIGH"

    if alpha_score >= 10 and win_rate >= 55 and trades >= 50:
        return "HIGH"

    if alpha_score >= 3 and trades >= 50:
        return "MEDIUM"

    if alpha_score >= 0:
        return "LOW"

    return "AVOID"


df["Confidence"] = df.apply(
    lambda row: confidence_level(
        row["AlphaScore"],
        row["WinRate"],
        row["Trades"]
    ),
    axis=1
)

# --------------------------
# Recommendation
# --------------------------

def recommendation(row):

    if row["Confidence"] == "VERY_HIGH":
        return "STRONG_BUY"

    if row["Confidence"] == "HIGH":
        return "BUY"

    if row["Confidence"] == "MEDIUM":
        return "WATCH"

    if row["Confidence"] == "LOW":
        return "NEUTRAL"

    return "AVOID"


df["Recommendation"] = df.apply(
    recommendation,
    axis=1
)

# --------------------------
# Sort
# --------------------------

df = df.sort_values(
    ["AlphaScore", "WinRate"],
    ascending=False
)

# --------------------------
# Save
# --------------------------

df.to_csv(output_file, index=False)

print("\n===================================")
print(" MINI CUBE RECOMMENDATION ENGINE")
print("===================================\n")

buy = df[df["Recommendation"].isin(["STRONG_BUY", "BUY"])]
watch = df[df["Recommendation"] == "WATCH"]
avoid = df[df["Recommendation"] == "AVOID"]

print("BUY CANDIDATES")
print("-----------------------------------")

if buy.empty:
    print("None")
else:
    print(
        buy[
            [
                "Ticker",
                "Recommendation",
                "Confidence",
                "AlphaScore",
                "WinRate"
            ]
        ]
    )

print("\nWATCHLIST")
print("-----------------------------------")

if watch.empty:
    print("None")
else:
    print(
        watch[
            [
                "Ticker",
                "Confidence",
                "AlphaScore",
                "WinRate"
            ]
        ]
    )

print("\nAVOID")
print("-----------------------------------")

if avoid.empty:
    print("None")
else:
    print(
        avoid[
            [
                "Ticker",
                "AlphaScore",
                "WinRate"
            ]
        ]
    )

print()
print(f"Saved to {output_file}")