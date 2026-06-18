from pathlib import Path
import pandas as pd

MARKET_DATA_PATH = Path("data/market_data.csv")
OUTPUT_PATH = Path("data/approved_universe.csv")
REPORT_PATH = Path("data/universe_quality_report.csv")


def main():
    if not MARKET_DATA_PATH.exists():
        print("market_data.csv missing. Run download_data.py first.")
        return

    df = pd.read_csv(MARKET_DATA_PATH)

    required = ["Ticker", "Date", "Close"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        print(f"market_data.csv missing columns: {missing}")
        return

    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    rows = []

    for ticker in sorted(df["Ticker"].dropna().unique()):
        stock = df[df["Ticker"] == ticker].copy()

        total_rows = len(stock)
        valid_close_rows = int(stock["Close"].notna().sum())
        missing_close_rows = int(stock["Close"].isna().sum())

        missing_pct = round((missing_close_rows / total_rows) * 100, 2) if total_rows else 100

        valid_stock = stock.dropna(subset=["Date", "Close"]).copy()

        if valid_stock.empty:
            first_date = ""
            last_date = ""
            years = 0
        else:
            first_date = valid_stock["Date"].min().strftime("%Y-%m-%d")
            last_date = valid_stock["Date"].max().strftime("%Y-%m-%d")
            years = round((valid_stock["Date"].max() - valid_stock["Date"].min()).days / 365.25, 2)

        status = "PASS"
        reason = []

        if valid_close_rows < 200:
            status = "FAIL"
            reason.append("Less than 200 valid price rows")

        if years < 1:
            status = "FAIL"
            reason.append("Less than 1 year of valid history")

        if valid_close_rows >= 200 and years >= 1:
            reason.append("Enough valid history")

        quality_score = 0

        if valid_close_rows >= 1000:
            quality_score += 40
        elif valid_close_rows >= 500:
            quality_score += 30
        elif valid_close_rows >= 200:
            quality_score += 20

        if years >= 5:
            quality_score += 30
        elif years >= 2:
            quality_score += 20
        elif years >= 1:
            quality_score += 10

        if missing_pct <= 5:
            quality_score += 30
        elif missing_pct <= 20:
            quality_score += 20
        elif missing_pct <= 40:
            quality_score += 10

        rows.append({
            "Ticker": ticker,
            "TotalRows": total_rows,
            "ValidCloseRows": valid_close_rows,
            "MissingCloseRows": missing_close_rows,
            "MissingPct": missing_pct,
            "FirstDate": first_date,
            "LastDate": last_date,
            "Years": years,
            "QualityScore": quality_score,
            "Status": status,
            "Reason": "; ".join(reason),
        })

    report = pd.DataFrame(rows)

    approved = report[report["Status"] == "PASS"].copy()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report.to_csv(REPORT_PATH, index=False)
    approved.to_csv(OUTPUT_PATH, index=False)

    print("\nUNIVERSE QUALITY REPORT\n")
    print(report.head(30))

    print()
    print(f"Approved assets: {len(approved)} / {len(report)}")
    print(f"Saved report to {REPORT_PATH}")
    print(f"Saved approved universe to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()