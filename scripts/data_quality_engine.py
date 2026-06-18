from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PATH = DATA_DIR / "data_quality_report.csv"

CHECK_FILES = {
    "market_data.csv": ["Date", "Ticker", "Close"],
    "latest_stock_signals.csv": ["Date", "Ticker", "FinalScore"],
    "all_stock_signals.csv": ["Date", "Ticker", "FinalScore"],
    "sector_strength.csv": ["Sector", "AvgScore", "StockCount"],
    "signal_discovery_results.csv": ["Pattern", "WinRate10D", "AvgReturn10D"],
    "confidence_score_results.csv": ["ConfidenceScore"],
    "market_state.csv": ["Date", "MarketState"],
}


def file_size_mb(path: Path) -> float:
    return round(path.stat().st_size / (1024 * 1024), 2)


def check_file(filename: str, required_columns: list[str]) -> dict:
    path = DATA_DIR / filename

    result = {
        "File": filename,
        "Exists": False,
        "Rows": 0,
        "Columns": 0,
        "SizeMB": 0,
        "DuplicateRows": 0,
        "MissingColumns": "",
        "NaNCells": 0,
        "Status": "MISSING",
        "Issue": "",
    }

    if not path.exists():
        result["Issue"] = "File missing"
        return result

    result["Exists"] = True
    result["SizeMB"] = file_size_mb(path)

    try:
        df = pd.read_csv(path)
    except Exception as e:
        result["Status"] = "ERROR"
        result["Issue"] = str(e)
        return result

    result["Rows"] = len(df)
    result["Columns"] = len(df.columns)
    result["DuplicateRows"] = int(df.duplicated().sum())
    result["NaNCells"] = int(df.isna().sum().sum())

    missing = [col for col in required_columns if col not in df.columns]
    result["MissingColumns"] = ", ".join(missing)

    issues = []

    if missing:
        issues.append("Missing required columns")

    if result["DuplicateRows"] > 0:
        issues.append("Duplicate rows found")

    if result["NaNCells"] > 0:
        issues.append("NaN values found")

    if result["SizeMB"] > 100:
        issues.append("File too large")

    if result["Rows"] == 0:
        issues.append("Empty file")

    if issues:
        result["Status"] = "WARNING"
        result["Issue"] = " | ".join(issues)
    else:
        result["Status"] = "OK"
        result["Issue"] = "No major issue"

    return result


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for filename, columns in CHECK_FILES.items():
        results.append(check_file(filename, columns))

    report = pd.DataFrame(results)
    report.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE DATA QUALITY REPORT")
    print("===================================\n")

    print(report.to_string(index=False))

    warning_count = (report["Status"] != "OK").sum()

    print("\nSummary")
    print("-------------------")
    print(f"Files checked: {len(report)}")
    print(f"Warnings/errors: {warning_count}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()