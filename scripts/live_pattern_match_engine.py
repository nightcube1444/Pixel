from pathlib import Path
import pandas as pd

LIVE_MATCHES_FILE = Path(
    "data/live_pattern_matches.csv"
)

TRUST_FILE = Path(
    "data/trusted_patterns.csv"
)

OUTPUT_FILE = Path(
    "data/live_pattern_matches.csv"
)


def main():

    print("\nLIVE PATTERN MATCH ENGINE\n")

    live_matches = pd.read_csv(
        LIVE_MATCHES_FILE
    )

    trust_df = pd.read_csv(
        TRUST_FILE
    )

    trust_df = trust_df[
        [
            "Pattern",
            "TrustLevel",
            "ConfidenceScore",
            "PValue",
            "ValidationStatus"
        ]
    ]

    # Remove old trust columns if they exist
    columns_to_remove = [
        "TrustLevel",
        "ConfidenceScore",
        "PValue",
        "ValidationStatus",
        "TrustRank"
    ]

    live_matches = live_matches.drop(
        columns=[
            col
            for col in columns_to_remove
            if col in live_matches.columns
        ],
        errors="ignore"
    )

    # Merge trust data
    live_matches = live_matches.merge(
        trust_df,
        on="Pattern",
        how="left",
        validate="many_to_one"
    )

    # Fill missing values
    live_matches["TrustLevel"] = (
        live_matches["TrustLevel"]
        .fillna("UNTRUSTED")
    )

    live_matches["ConfidenceScore"] = (
        pd.to_numeric(
            live_matches["ConfidenceScore"],
            errors="coerce"
        )
        .fillna(0)
    )

    live_matches["PValue"] = (
        pd.to_numeric(
            live_matches["PValue"],
            errors="coerce"
        )
        .fillna(1)
    )

    live_matches["ValidationStatus"] = (
        live_matches["ValidationStatus"]
        .fillna("NOT_VALIDATED")
    )

    trust_rank_map = {
        "INSTITUTIONAL": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "UNTRUSTED": 1
    }

    live_matches["TrustRank"] = (
        live_matches["TrustLevel"]
        .map(trust_rank_map)
        .fillna(1)
    )

    live_matches = live_matches.sort_values(
        by=[
            "TrustRank",
            "AlphaScore"
        ],
        ascending=[False, False]
    )

    live_matches.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        live_matches[
            [
                "Ticker",
                "Pattern",
                "TrustLevel",
                "ConfidenceScore",
                "WinRate",
                "AlphaScore"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    print("\nTrust Summary")

    print(
        live_matches["TrustLevel"]
        .value_counts()
    )

    print(
        f"\nMatches found: {len(live_matches)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()