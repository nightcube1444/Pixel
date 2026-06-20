from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)

UNIVERSE_FILE = Path(
    "config/asset_universe.csv"
)

OUTPUT_FILE = Path(
    "data/pattern_sector_matrix.csv"
)


def main():

    print("\nPATTERN SECTOR MATRIX\n")

    df = pd.read_csv(INPUT_FILE)

    universe = pd.read_csv(
        UNIVERSE_FILE
    )

    df = df.merge(
        universe[
            [
                "Ticker",
                "Sector"
            ]
        ],
        on="Ticker",
        how="left"
    )

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
                "CrossAssetPattern",
                "Sector"
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
    )

    results["PatternSectorScore"] = (
        results["AvgReturn10D"] * 10
        + results["WinRate"]
    )

    results = results.sort_values(
        by=[
            "CrossAssetPattern",
            "PatternSectorScore"
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