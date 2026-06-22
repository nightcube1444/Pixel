import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/regime_pattern_survival.csv")
DIVERSITY_FILE = Path("data/pattern_ticker_diversity.csv")
OUTPUT_FILE = Path("data/institutional_patterns.csv")

MIN_APPEARANCES = 500
MIN_SURVIVAL = 55
MIN_RETURN = 0
MIN_DISTINCT_TICKERS = 20
MAX_TOP_TICKER_SHARE = 20.0


def main():
    print("\nINSTITUTIONAL PATTERN REGISTRY\n")

    df = pd.read_csv(INPUT_FILE)

    diversity = pd.read_csv(DIVERSITY_FILE)

    df["Pattern"] = df["Pattern"].astype(str).str.strip()
    diversity["Pattern"] = diversity["Pattern"].astype(str).str.strip()

    df = df.merge(
        diversity[
            [
                "Pattern",
                "DistinctTickers",
                "TopTickerSharePct",
                "DiversityStatus",
            ]
        ],
        on="Pattern",
        how="left",
    )

    df["DistinctTickers"] = pd.to_numeric(
        df["DistinctTickers"],
        errors="coerce",
    ).fillna(0)

    df["TopTickerSharePct"] = pd.to_numeric(
        df["TopTickerSharePct"],
        errors="coerce",
    ).fillna(100)

    df["DiversityStatus"] = (
        df["DiversityStatus"]
        .fillna("UNKNOWN")
        .astype(str)
        .str.upper()
    )

    institutional = df[
        (df["Appearances"] >= MIN_APPEARANCES)
        &
        (df["SurvivalScore"] >= MIN_SURVIVAL)
        &
        (df["AvgReturn10D"] > MIN_RETURN)
        &
        (df["DistinctTickers"] >= MIN_DISTINCT_TICKERS)
        &
        (df["TopTickerSharePct"] <= MAX_TOP_TICKER_SHARE)
        &
        (df["DiversityStatus"] == "BROAD")
    ].copy()

    institutional = institutional.sort_values(
        [
            "SurvivalScore",
            "Appearances",
            "DistinctTickers",
        ],
        ascending=[False, False, False],
    )

    institutional["InstitutionalRank"] = range(
        1,
        len(institutional) + 1,
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    institutional.to_csv(OUTPUT_FILE, index=False)

    print(
        institutional[
            [
                "InstitutionalRank",
                "Pattern",
                "Appearances",
                "AvgReturn10D",
                "SurvivalScore",
                "DistinctTickers",
                "TopTickerSharePct",
                "DiversityStatus",
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    print(f"\nInstitutional Patterns: {len(institutional)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()