from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)

UNIVERSE_FILE = Path(
    "config/asset_universe.csv"
)

OUTPUT_FILE = Path(
    "data/sector_alpha_rankings.csv"
)


def main():

    print("\nSECTOR ALPHA ENGINE\n")

    signals = pd.read_csv(INPUT_FILE)
    universe = pd.read_csv(UNIVERSE_FILE)

    signals = signals.merge(
        universe[
            [
                "Ticker",
                "Sector"
            ]
        ],
        on="Ticker",
        how="left"
    )

    signals["ForwardReturn10D"] = pd.to_numeric(
        signals["ForwardReturn10D"],
        errors="coerce"
    )

    signals["Win10D"] = pd.to_numeric(
        signals["Win10D"],
        errors="coerce"
    )

    sector_stats = (
        signals
        .groupby("Sector")
        .agg(
            Opportunities=("Ticker", "count"),
            AvgReturn10D=("ForwardReturn10D", "mean"),
            WinRate=("Win10D", "mean")
        )
        .reset_index()
    )

    sector_stats["AvgReturn10D"] = (
        sector_stats["AvgReturn10D"]
        .round(2)
    )

    sector_stats["WinRate"] = (
        sector_stats["WinRate"] * 100
    ).round(2)

    sector_stats["SectorAlphaScore"] = (
        sector_stats["AvgReturn10D"] * 10
        + sector_stats["WinRate"]
    ).round(2)

    sector_stats = sector_stats.sort_values(
        by="SectorAlphaScore",
        ascending=False
    )

    sector_stats.insert(
        0,
        "SectorRank",
        range(
            1,
            len(sector_stats) + 1
        )
    )

    sector_stats.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        sector_stats.head(25)
        .to_string(index=False)
    )

    print(
        f"\nSectors analyzed: "
        f"{len(sector_stats)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()