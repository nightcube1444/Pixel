import pandas as pd
from pathlib import Path

INPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)

OUTPUT_FILE = Path(
    "data/regime_pattern_survival.csv"
)


def calc_winrate(df):

    if len(df) == 0:
        return None

    return round(
        df["Win10D"].mean() * 100,
        2
    )


def classify_survival(score):

    if score >= 55:
        return "INSTITUTIONAL"

    if score >= 50:
        return "ROBUST"

    return "WEAK"


def main():

    print(
        "\nREGIME PATTERN SURVIVAL ENGINE V2\n"
    )

    df = pd.read_csv(
        INPUT_FILE
    )

    required = [
        "CrossAssetPattern",
        "MarketRegime",
        "Win10D",
        "ForwardReturn10D"
    ]

    missing = [
        c for c in required
        if c not in df.columns
    ]

    if missing:

        print(
            f"Missing columns: {missing}"
        )
        return

    df = df.dropna(
        subset=[
            "CrossAssetPattern",
            "MarketRegime",
            "ForwardReturn10D"
        ]
    )

    print(
        f"Rows analyzed: {len(df):,}"
    )

    rows = []

    for pattern, group in df.groupby(
        "CrossAssetPattern"
    ):

        appearances = len(group)

        avg_return = round(
            group["ForwardReturn10D"].mean(),
            2
        )

        regime_rates = {}

        for regime in sorted(
            group["MarketRegime"]
            .dropna()
            .unique()
        ):

            sub = group[
                group["MarketRegime"] == regime
            ]

            wr = calc_winrate(sub)

            regime_rates[regime] = wr

        valid_rates = [
            x
            for x in regime_rates.values()
            if x is not None
        ]

        if appearances < 500:

            survival_score = 0
            regime_class = "INSUFFICIENT"

        elif len(valid_rates) == 0:

            survival_score = 0
            regime_class = "NO_REGIME_DATA"

        else:

            survival_score = round(
                sum(valid_rates)
                / len(valid_rates),
                2
            )

            regime_class = classify_survival(
                survival_score
            )

        row = {
            "Pattern": pattern,
            "Appearances": appearances,
            "AvgReturn10D": avg_return,
            "RegimeCount": len(
                regime_rates
            ),
            "SurvivalScore": survival_score,
            "RegimeClass": regime_class
        }

        for regime, wr in regime_rates.items():

            col = (
                regime
                .replace(" ", "_")
                .upper()
                + "_WR"
            )

            row[col] = wr

        rows.append(row)

    result = pd.DataFrame(rows)

    result = result.sort_values(
        by=[
            "SurvivalScore",
            "Appearances"
        ],
        ascending=[
            False,
            False
        ]
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        "\nTOP SURVIVING PATTERNS\n"
    )

    display_cols = [
        "Pattern",
        "Appearances",
        "AvgReturn10D",
        "RegimeCount",
        "SurvivalScore",
        "RegimeClass"
    ]

    print(
        result[
            display_cols
        ]
        .head(25)
        .to_string(index=False)
    )

    print(
        "\nREGIME CLASS SUMMARY\n"
    )

    print(
        result[
            "RegimeClass"
        ].value_counts()
    )

    print(
        f"\nPatterns analyzed: "
        f"{len(result)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()