import pandas as pd
from pathlib import Path

LIVE_FILE = Path("data/institutional_opportunities.csv")
UNIVERSE_FILE = Path("config/asset_universe.csv")
OUTPUT_FILE = Path("data/institutional_recommendations.csv")


def clean_ticker(ticker):
    return (
        str(ticker)
        .replace(".NS", "")
        .replace(".BO", "")
        .strip()
        .upper()
    )


def main():

    print("\nINSTITUTIONAL RECOMMENDATION ENGINE\n")

    live = pd.read_csv(LIVE_FILE)
    universe = pd.read_csv(UNIVERSE_FILE)

    # -------------------------
    # Normalize tickers
    # -------------------------

    live["TickerClean"] = live["Ticker"].apply(clean_ticker)

    universe["TickerClean"] = (
        universe["Ticker"]
        .astype(str)
        .apply(clean_ticker)
    )

    # -------------------------
    # Merge sector information
    # -------------------------

    live = live.merge(
        universe[
            [
                "TickerClean",
                "Sector",
                "Market",
                "AssetType",
            ]
        ],
        on="TickerClean",
        how="left",
    )

    # -------------------------
    # Opportunity Score
    # -------------------------

    live["OpportunityScore"] = (
        live["AlphaScore"] * 0.5
        + live["SurvivalScore"] * 0.5
    )

    live = live.sort_values(
        "OpportunityScore",
        ascending=False,
    )

    live["RecommendationRank"] = (
        range(1, len(live) + 1)
    )

    output = live[
        [
            "RecommendationRank",
            "Ticker",
            "Sector",
            "Market",
            "AssetType",
            "OpportunityScore",
            "AlphaScore",
            "SurvivalScore",
        ]
    ]

    print(
        output.head(25).to_string(index=False)
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"\nRecommendations: {len(output)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()