from pathlib import Path
import pandas as pd

MARKET_DATA = Path("data/market_data.csv")
SIGNALS_DATA = Path("data/all_stock_signals_with_context.csv")
VALIDATION_DATA = Path("data/pattern_validation_results.csv")

OUTPUT_REPORT = Path("data/research_audit_v2_report.txt")


def confidence_score(trades, tickers, pvalue, winrate):

    sample_component = min(trades / 500, 1.0) * 40

    diversity_component = min(tickers / 20, 1.0) * 30

    p_component = max(0, (1 - min(pvalue, 1))) * 20

    win_component = (winrate / 100) * 10

    return round(
        sample_component +
        diversity_component +
        p_component +
        win_component,
        2
    )


def main():

    print("\nRESEARCH AUDIT V2\n")

    report = []

    # ==========================
    # LOAD DATA
    # ==========================

    market = pd.read_csv(MARKET_DATA)
    signals = pd.read_csv(SIGNALS_DATA)
    validation = pd.read_csv(VALIDATION_DATA)

    # ==========================
    # DUPLICATE CHECK
    # ==========================

    duplicates = market.duplicated(
        subset=["Date", "Ticker"]
    ).sum()

    report.append("DUPLICATE AUDIT")
    report.append("--------------------")
    report.append(f"Duplicate Date/Ticker rows: {duplicates}")
    report.append("")

    # ==========================
    # TICKER BALANCE
    # ==========================

    report.append("TOP TICKERS")
    report.append("--------------------")

    ticker_counts = (
        market.groupby("Ticker")
        .size()
        .sort_values(ascending=False)
    )

    total_rows = len(market)

    for ticker, count in ticker_counts.head(20).items():

        pct = round(count / total_rows * 100, 2)

        report.append(
            f"{ticker} | Rows={count} | {pct}%"
        )

    report.append("")

    # ==========================
    # PATTERN DIVERSITY
    # ==========================

    report.append("VALIDATED PATTERN QUALITY")
    report.append("--------------------")

    validated = validation[
        validation["ValidationStatus"] == "VALIDATED"
    ].copy()

    results = []

    for _, row in validated.iterrows():

        pattern = row["Pattern"]

        subset = signals[
            signals["CrossAssetPattern"] == pattern
        ]

        unique_tickers = subset["Ticker"].nunique()

        top_ticker = "NONE"
        top_pct = 0

        if not subset.empty:

            counts = (
                subset["Ticker"]
                .value_counts()
            )

            top_ticker = counts.index[0]

            top_pct = round(
                counts.iloc[0] /
                len(subset) * 100,
                2
            )

        score = confidence_score(
            row["Trades"],
            unique_tickers,
            row["PValue"],
            row["WinRate10D"]
        )

        results.append({
            "Pattern": pattern,
            "Trades": row["Trades"],
            "UniqueTickers": unique_tickers,
            "TopTicker": top_ticker,
            "TopTickerPct": top_pct,
            "ConfidenceScore": score
        })

    quality = pd.DataFrame(results)

    quality = quality.sort_values(
        "ConfidenceScore",
        ascending=False
    )

    quality.to_csv(
        "data/pattern_quality_scores.csv",
        index=False
    )

    for _, row in quality.head(20).iterrows():

        report.append(
            f"{row['ConfidenceScore']} | "
            f"{row['Pattern']} | "
            f"Trades={int(row['Trades'])} | "
            f"Tickers={row['UniqueTickers']} | "
            f"Top={row['TopTicker']} "
            f"({row['TopTickerPct']}%)"
        )

    report.append("")

    OUTPUT_REPORT.write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    print("\n".join(report))

    print("\nSaved:")
    print(OUTPUT_REPORT)

    print("\nSaved:")
    print("data/pattern_quality_scores.csv")


if __name__ == "__main__":
    main()