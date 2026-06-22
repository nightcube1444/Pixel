from pathlib import Path
import pandas as pd

INPUT_PATH = Path(
    "data/pattern_families.csv"
)

OUTPUT_PATH = Path(
    "data/pattern_family_stats.csv"
)


def calculate_family_score(
    avg_winrate: float,
    avg_return: float,
    total_events: int,
) -> float:

    score = (
        avg_winrate * 0.60
        +
        avg_return * 15
        +
        min(total_events / 10, 20)
    )

    return round(score, 2)


def main():

    if not INPUT_PATH.exists():
        print("pattern_families.csv not found")
        return

    df = pd.read_csv(INPUT_PATH)

    if df.empty:
        print("No family data found")
        return

    grouped = (
        df.groupby("PatternFamily")
        .agg(
            Members=("Ticker", "count"),
            TotalEvents=("Events", "sum"),
            AvgWinRate=("WinRate10D", "mean"),
            AvgReturn10D=("AvgReturn10D", "mean"),
            BestReturn10D=("AvgReturn10D", "max"),
            WorstReturn10D=("AvgReturn10D", "min"),
        )
        .reset_index()
    )

    grouped["FamilyScore"] = grouped.apply(
        lambda row: calculate_family_score(
            row["AvgWinRate"],
            row["AvgReturn10D"],
            row["TotalEvents"],
        ),
        axis=1,
    )

    grouped["FamilyStrength"] = grouped[
        "FamilyScore"
    ].apply(
        lambda x:
        "ELITE"
        if x >= 70
        else
        "STRONG"
        if x >= 55
        else
        "MODERATE"
        if x >= 40
        else
        "WEAK"
    )

    grouped = grouped.sort_values(
        "FamilyScore",
        ascending=False,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    grouped.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print("\nPATTERN FAMILY STATS ENGINE\n")

    print(
        grouped.to_string(index=False)
    )

    print(
        f"\nSaved -> {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()