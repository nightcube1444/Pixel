from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

recommendation_file = BASE_DIR / "data/live_recommendations.csv"
market_file = BASE_DIR / "data/market_state.csv"
output_file = BASE_DIR / "data/context_aware_recommendations.csv"

# ----------------------------------
# Load data
# ----------------------------------

recommendations = pd.read_csv(recommendation_file)
market = pd.read_csv(market_file)

if recommendations.empty:
    raise ValueError("No recommendations found")

if market.empty:
    raise ValueError("No market state found")

latest_market = market.iloc[-1]
market_state = str(latest_market["MarketState"]).upper()

print("\n===================================")
print(" CONTEXT AWARE RECOMMENDATION ENGINE")
print("===================================\n")

print("Current Market State:", market_state)
print()

# ----------------------------------
# Market Context Score
# ----------------------------------

def context_adjustment(row):

    signal = str(row["PrimarySignal"]).upper()

    adjustment = 0

    # Bullish environments
    if market_state in ["RISK_ON", "POSITIVE_BIAS", "TENSE_BULL"]:

        if signal == "MOMENTUM":
            adjustment += 2

        elif signal == "PANIC":
            adjustment -= 2

    # Defensive environments
    elif market_state in ["RISK_OFF", "RISK_OFF_WARNING"]:

        if signal == "PANIC":
            adjustment += 2

        elif signal == "OVERSOLD":
            adjustment += 2

        elif signal == "MOMENTUM":
            adjustment -= 2

    return adjustment


recommendations["ContextAdjustment"] = recommendations.apply(
    context_adjustment,
    axis=1
)

recommendations["AdjustedAlphaScore"] = (
    recommendations["AlphaScore"]
    + recommendations["ContextAdjustment"]
)

# ----------------------------------
# Reclassify confidence
# ----------------------------------

def classify(score):

    if score >= 20:
        return "STRONG_BUY"

    if score >= 10:
        return "BUY"

    if score >= 3:
        return "WATCH"

    if score >= 0:
        return "NEUTRAL"

    return "AVOID"


recommendations["Recommendation"] = (
    recommendations["AdjustedAlphaScore"]
    .apply(classify)
)

# ----------------------------------
# Sort
# ----------------------------------

recommendations = recommendations.sort_values(
    "AdjustedAlphaScore",
    ascending=False
)

# ----------------------------------
# Save
# ----------------------------------

recommendations.to_csv(output_file, index=False)

print(
    recommendations[
        [
            "Ticker",
            "PrimarySignal",
            "AlphaScore",
            "ContextAdjustment",
            "AdjustedAlphaScore",
            "Recommendation"
        ]
    ]
)

print()
print(f"Saved to {output_file}")