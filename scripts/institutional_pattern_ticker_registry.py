from pathlib import Path
import pandas as pd

PATTERN_FILE = Path("data/institutional_patterns.csv")
TICKER_HISTORY_FILE = Path("data/ticker_pattern_history.csv")
OUTPUT_FILE = Path("data/institutional_pattern_tickers.csv")


def main():
    print("\nINSTITUTIONAL PATTERN TICKER REGISTRY\n")

    patterns = pd.read_csv(PATTERN_FILE)
    history = pd.read_csv(TICKER_HISTORY_FILE)

    history = history.rename(
        columns={
            "CrossAssetPattern": "Pattern",
            "Appearances": "TickerAppearances",
            "AvgReturn10D": "TickerAvgReturn10D",
            "WinRate": "TickerWinRate",
        }
    )

    merged = patterns.merge(
        history,
        on="Pattern",
        how="left"
    )

    keep_cols = [
        "InstitutionalRank",
        "Pattern",
        "Ticker",
        "Appearances",
        "AvgReturn10D",
        "SurvivalScore",
        "TickerAppearances",
        "TickerAvgReturn10D",
        "TickerWinRate",
        "TickerPatternScore",
    ]

    for col in keep_cols:
        if col not in merged.columns:
            merged[col] = None

    merged = merged[keep_cols]

    merged = merged.sort_values(
        by=["InstitutionalRank", "TickerPatternScore"],
        ascending=[True, False]
    )

    merged.to_csv(OUTPUT_FILE, index=False)

    print(merged.head(50).to_string(index=False))
    print(f"\nRows: {len(merged)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()