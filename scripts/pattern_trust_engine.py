from pathlib import Path
import pandas as pd

VALIDATION_FILE = Path(
    "data/pattern_validation_results.csv"
)

QUALITY_FILE = Path(
    "data/pattern_quality_scores.csv"
)

OUTPUT_FILE = Path(
    "data/trusted_patterns.csv"
)


def determine_trust(
    trades,
    pvalue,
    confidence
):
    """
    Trust hierarchy:

    INSTITUTIONAL
    HIGH
    MEDIUM
    LOW
    UNTRUSTED
    """

    if trades >= 1000 and pvalue < 0.01 and confidence >= 95:
        return "INSTITUTIONAL"

    elif trades >= 300 and pvalue < 0.05 and confidence >= 90:
        return "HIGH"

    elif trades >= 100 and pvalue < 0.05:
        return "MEDIUM"

    elif trades >= 30:
        return "LOW"

    return "UNTRUSTED"


def main():

    print("\nPATTERN TRUST ENGINE\n")

    validation = pd.read_csv(
        VALIDATION_FILE
    )

    quality = pd.read_csv(
        QUALITY_FILE
    )

    merged = validation.merge(
        quality,
        on="Pattern",
        how="left"
    )

    # ----------------------------------
    # Clean duplicate column names
    # ----------------------------------

    merged = merged.rename(
        columns={
            "Trades_x": "Trades",
            "Trades_y": "QualityTrades"
        }
    )

    # ----------------------------------
    # Type Safety
    # ----------------------------------

    merged["Trades"] = pd.to_numeric(
        merged["Trades"],
        errors="coerce"
    ).fillna(0)

    merged["PValue"] = pd.to_numeric(
        merged["PValue"],
        errors="coerce"
    ).fillna(1)

    merged["ConfidenceScore"] = pd.to_numeric(
        merged["ConfidenceScore"],
        errors="coerce"
    ).fillna(0)

    # ----------------------------------
    # Calculate Trust
    # ----------------------------------

    merged["TrustLevel"] = merged.apply(
        lambda row: determine_trust(
            row["Trades"],
            row["PValue"],
            row["ConfidenceScore"]
        ),
        axis=1
    )

    # ----------------------------------
    # Sort Results
    # ----------------------------------

    trust_order = {
        "INSTITUTIONAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "UNTRUSTED": 1
    }

    merged["TrustRank"] = merged["TrustLevel"].map(
        trust_order
    )

    trusted = merged.sort_values(
        by=[
            "TrustRank",
            "ConfidenceScore"
        ],
        ascending=[False, False]
    )

    trusted.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        trusted[
            [
                "Pattern",
                "Trades",
                "ConfidenceScore",
                "PValue",
                "TrustLevel"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    print("\nTrust Counts")
    print(
        trusted["TrustLevel"]
        .value_counts()
    )

    print(
        "\nTop Institutional Patterns"
    )

    institutional = trusted[
        trusted["TrustLevel"] == "INSTITUTIONAL"
    ]

    if not institutional.empty:
        print(
            institutional[
                [
                    "Pattern",
                    "Trades",
                    "ConfidenceScore",
                    "PValue"
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()