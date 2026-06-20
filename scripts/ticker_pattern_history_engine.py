from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)

OUTPUT_FILE = Path(
    "data/ticker_pattern_history.csv"
)


def main():

    print("\nTICKER PATTERN HISTORY ENGINE\n")

    df = pd.read_csv(INPUT_FILE)

    df["ForwardReturn10D"] = pd.to_numeric(
        df["ForwardReturn10D"],
        errors="coerce"
    )

    df["Win10D"] = pd.to_numeric(
        df["Win10D"],
        errors="coerce"
    )

    results = (
        df.groupby(
            [
                "Ticker",
                "CrossAssetPattern"
            ]
        )
        .agg(
            Appearances=(
                "Ticker",
                "count"
            ),
            AvgReturn10D=(
                "ForwardReturn10D",
                "mean"
            ),
            WinRate=(
                "Win10D",
                "mean"
            )
        )
        .reset_index()
    )

    results["WinRate"] = (
        results["WinRate"] * 100
    ).round(2)

    results["AvgReturn10D"] = (
        results["AvgReturn10D"]
        .round(2)
    )

    results["TickerPatternScore"] = (
        results["AvgReturn10D"] * 10
        + results["WinRate"]
    ).round(2)

    results = results.sort_values(
        by=[
            "Ticker",
            "TickerPatternScore"
        ],
        ascending=[
            True,
            False
        ]
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        results.head(30)
        .to_string(index=False)
    )

    print(
        f"\nRows: {len(results)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()