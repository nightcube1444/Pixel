from pathlib import Path
import pandas as pd

MARKET_DATA = Path("data/market_data.csv")
VALIDATION_DATA = Path("data/pattern_validation_results.csv")
REPORT_FILE = Path("data/research_audit_report.txt")


def main():

    print("\nRESEARCH AUDIT ENGINE\n")

    report = []

    # ==========================
    # MARKET DATA AUDIT
    # ==========================

    market = pd.read_csv(MARKET_DATA)

    total_rows = len(market)

    unique_tickers = market["Ticker"].nunique()

    start_date = market["Date"].min()
    end_date = market["Date"].max()

    report.append("MARKET DATA")
    report.append("--------------------")
    report.append(f"Rows: {total_rows:,}")
    report.append(f"Unique Tickers: {unique_tickers}")
    report.append(f"Start Date: {start_date}")
    report.append(f"End Date: {end_date}")
    report.append("")

    # ==========================
    # VALIDATION AUDIT
    # ==========================

    validation = pd.read_csv(VALIDATION_DATA)

    validated = validation[
        validation["ValidationStatus"] == "VALIDATED"
    ]

    report.append("PATTERN VALIDATION")
    report.append("--------------------")
    report.append(f"Total Patterns: {len(validation)}")
    report.append(f"Validated Patterns: {len(validated)}")
    report.append("")

    # ==========================
    # TOP SAMPLE SIZE
    # ==========================

    biggest = validation.sort_values(
        "Trades",
        ascending=False
    ).head(10)

    report.append("TOP SAMPLE SIZE PATTERNS")
    report.append("--------------------")

    for _, row in biggest.iterrows():

        report.append(
            f"{row['Pattern']} | "
            f"Trades={int(row['Trades'])} | "
            f"WinRate={row['WinRate10D']:.2f}% | "
            f"Avg10D={row['AvgReturn10D']:.2f}%"
        )

    report.append("")

    # ==========================
    # BEST VALIDATED
    # ==========================

    best = validated.sort_values(
        "AvgReturn10D",
        ascending=False
    ).head(10)

    report.append("BEST VALIDATED PATTERNS")
    report.append("--------------------")

    for _, row in best.iterrows():

        report.append(
            f"{row['Pattern']} | "
            f"Trades={int(row['Trades'])} | "
            f"Avg10D={row['AvgReturn10D']:.2f}% | "
            f"PValue={row['PValue']:.5f}"
        )

    report.append("")

    text = "\n".join(report)

    REPORT_FILE.write_text(text)

    print(text)

    print("\nSaved to:")
    print(REPORT_FILE)


if __name__ == "__main__":
    main()