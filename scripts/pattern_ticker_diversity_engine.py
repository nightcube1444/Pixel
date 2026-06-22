from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/institutional_pattern_tickers.csv")
OUTPUT_PATH = Path("data/pattern_ticker_diversity.csv")

MIN_DISTINCT_TICKERS = 5
MAX_TOP_TICKER_SHARE = 40.0


def main():
    if not INPUT_PATH.exists():
        print(f"Missing file: {INPUT_PATH}")
        return

    df = pd.read_csv(INPUT_PATH)

    required = ["Pattern", "Ticker", "TickerAppearances"]

    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"Missing columns: {missing}")
        print(df.columns.tolist())
        return

    df = df.copy()
    df["Pattern"] = df["Pattern"].astype(str).str.strip()
    df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
    df["TickerAppearances"] = pd.to_numeric(
        df["TickerAppearances"],
        errors="coerce"
    ).fillna(0)

    rows = []

    for pattern, group in df.groupby("Pattern"):
        total_appearances = group["TickerAppearances"].sum()
        distinct_tickers = group["Ticker"].nunique()

        top_row = group.sort_values(
            "TickerAppearances",
            ascending=False
        ).iloc[0]

        top_ticker = top_row["Ticker"]
        top_ticker_appearances = top_row["TickerAppearances"]

        top_share = 0
        if total_appearances > 0:
            top_share = round(
                (top_ticker_appearances / total_appearances) * 100,
                2
            )

        if distinct_tickers >= MIN_DISTINCT_TICKERS and top_share <= MAX_TOP_TICKER_SHARE:
            status = "BROAD"
        elif distinct_tickers < MIN_DISTINCT_TICKERS:
            status = "LOW_DIVERSITY"
        elif top_share > MAX_TOP_TICKER_SHARE:
            status = "CONCENTRATED"
        else:
            status = "REVIEW"

        rows.append({
            "Pattern": pattern,
            "TotalTickerAppearances": int(total_appearances),
            "DistinctTickers": int(distinct_tickers),
            "TopTicker": top_ticker,
            "TopTickerAppearances": int(top_ticker_appearances),
            "TopTickerSharePct": top_share,
            "DiversityStatus": status,
        })

    out = pd.DataFrame(rows)

    out = out.sort_values(
        by=["DiversityStatus", "DistinctTickers", "TotalTickerAppearances"],
        ascending=[True, False, False],
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    print("\nPATTERN TICKER DIVERSITY ENGINE")
    print(out.head(20).to_string(index=False))
    print(f"\nRows: {len(out)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()