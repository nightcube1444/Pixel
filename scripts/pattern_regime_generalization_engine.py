import pandas as pd
from pathlib import Path

INPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)

OUTPUT_FILE = Path(
    "data/pattern_regime_generalization.csv"
)


def winrate(df):

    if len(df) == 0:
        return None

    return round(
        df["Win10D"].mean() * 100,
        2
    )


def classify(score):

    if score >= 60:
        return "UNIVERSAL"

    if score >= 55:
        return "ROBUST"

    if score >= 50:
        return "MIXED"

    return "WEAK"


def main():

    print(
        "\nPATTERN REGIME GENERALIZATION ENGINE\n"
    )

    df = pd.read_csv(INPUT_FILE)

    df = df.dropna(
        subset=[
            "PrimarySignal",
            "MarketRegime",
            "ForwardReturn10D"
        ]
    )

    rows = []

    for signal, group in df.groupby(
        "PrimarySignal"
    ):

        appearances = len(group)

        regime_stats = {}

        for regime in sorted(
            group["MarketRegime"]
            .dropna()
            .unique()
        ):

            sub = group[
                group["MarketRegime"] == regime
            ]

            wr = winrate(sub)

            regime_stats[regime] = wr

        valid_rates = [
            x
            for x in regime_stats.values()
            if x is not None
        ]

        if len(valid_rates) == 0:
            continue

        robustness = round(
            sum(valid_rates)
            / len(valid_rates),
            2
        )

        avg_return = round(
            group["ForwardReturn10D"].mean(),
            2
        )

        row = {
            "Signal": signal,
            "Appearances": appearances,
            "AvgReturn10D": avg_return,
            "RegimeCount": len(regime_stats),
            "RobustnessScore": robustness,
            "Classification": classify(
                robustness
            )
        }

        for regime, wr in regime_stats.items():

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
        [
            "RobustnessScore",
            "Appearances"
        ],
        ascending=False
    )

    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        result.head(20).to_string(
            index=False
        )
    )

    print("\nClassification Summary\n")

    print(
        result["Classification"]
        .value_counts()
    )

    print(
        f"\nSignals analyzed: {len(result)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()