import pandas as pd
from pathlib import Path

INPUT_FILE = Path(
    "data/regime_pattern_survival.csv"
)

OUTPUT_FILE = Path(
    "data/institutional_patterns.csv"
)

MIN_APPEARANCES = 500
MIN_SURVIVAL = 55
MIN_RETURN = 0


def main():

    print(
        "\nINSTITUTIONAL PATTERN REGISTRY\n"
    )

    df = pd.read_csv(INPUT_FILE)

    institutional = df[
        (df["Appearances"] >= MIN_APPEARANCES)
        &
        (df["SurvivalScore"] >= MIN_SURVIVAL)
        &
        (df["AvgReturn10D"] > MIN_RETURN)
    ].copy()

    institutional = institutional.sort_values(
        [
            "SurvivalScore",
            "Appearances"
        ],
        ascending=False
    )

    institutional["InstitutionalRank"] = (
        range(
            1,
            len(institutional) + 1
        )
    )

    institutional.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        institutional[
            [
                "InstitutionalRank",
                "Pattern",
                "Appearances",
                "AvgReturn10D",
                "SurvivalScore"
            ]
        ]
        .head(25)
        .to_string(index=False)
    )

    print(
        f"\nInstitutional Patterns: "
        f"{len(institutional)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()