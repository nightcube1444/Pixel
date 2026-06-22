from pathlib import Path
import pandas as pd

INPUT_FILE = Path(
    "data/pattern_event_validation_results.csv"
)

OUTPUT_FILE = Path(
    "data/final_trade_candidates.csv"
)

MIN_EVENTS = 50
MIN_WINRATE = 60
MIN_RETURN = 0.50


def main():

    print("\nFINAL CANDIDATE ENGINE\n")

    df = pd.read_csv(INPUT_FILE)

    candidates = df[
        (df["Events"] >= MIN_EVENTS)
        &
        (df["WinRate10D"] >= MIN_WINRATE)
        &
        (df["AvgReturn10D"] >= MIN_RETURN)
    ].copy()

    candidates = candidates.sort_values(
        [
            "WinRate10D",
            "AvgReturn10D"
        ],
        ascending=False
    )

    candidates.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        candidates[
            [
                "Ticker",
                "Events",
                "WinRate10D",
                "AvgReturn10D",
                "SurvivalScore",
                "AlphaScore",
            ]
        ].to_string(index=False)
    )

    print(
        f"\nFinal Candidates: {len(candidates)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()