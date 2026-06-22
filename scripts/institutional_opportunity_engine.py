from pathlib import Path
import pandas as pd

LIVE_FILE = Path(
    "data/live_pattern_matches.csv"
)

INSTITUTIONAL_FILE = Path(
    "data/institutional_patterns.csv"
)

OUTPUT_FILE = Path(
    "data/institutional_opportunities.csv"
)
DIVERSITY_PATH = Path("data/pattern_ticker_diversity.csv")
def load_diversity():
    if not DIVERSITY_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(DIVERSITY_PATH)
    df["Pattern"] = df["Pattern"].astype(str).str.strip()
    return df

def main():

    print("\nINSTITUTIONAL OPPORTUNITY ENGINE\n")

    live_df = pd.read_csv(LIVE_FILE)

    inst_df = pd.read_csv(INSTITUTIONAL_FILE)

    pattern_counts = (
        live_df.groupby("Pattern")
        .size()
        .reset_index(name="CurrentTickerCount")
    )

    opportunities = (
        live_df.merge(
            inst_df,
            on="Pattern",
            how="inner"
        )
        .merge(
            pattern_counts,
            on="Pattern",
            how="left"
        )
    )

    # -----------------------------
    # Merge ticker diversity data
    # -----------------------------
     

    opportunities = opportunities[
        [
            "Ticker",
            "Pattern",
            "InstitutionalRank",
            "Appearances",
            "AvgReturn10D",
            "SurvivalScore",
            "AlphaScore",
            "CurrentTickerCount",
            "DistinctTickers",
            "TopTickerSharePct",
            "DiversityStatus",
        ]
    ]

    opportunities = opportunities.sort_values(
        by=[
            "InstitutionalRank",
            "AlphaScore"
        ],
        ascending=[
            True,
            False
        ]
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    opportunities.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        opportunities.head(30).to_string(
            index=False
        )
    )

    print(
        f"\nInstitutional Opportunities: "
        f"{len(opportunities)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )
if __name__ == "__main__":
    main()