from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PATH = DATA_DIR / "nan_inspection_report.csv"

FILES_TO_CHECK = [
    "market_data.csv",
    "latest_stock_signals.csv",
    "all_stock_signals.csv",
    "market_state.csv",
]


def inspect_file(filename):
    path = DATA_DIR / filename
    rows = []

    if not path.exists():
        return [{
            "File": filename,
            "Column": "ALL",
            "NaNCount": 0,
            "NaNPct": 0,
            "Status": "MISSING",
        }]

    df = pd.read_csv(path)

    total_rows = len(df)

    for col in df.columns:
        nan_count = int(df[col].isna().sum())
        nan_pct = round((nan_count / total_rows) * 100, 2) if total_rows else 0

        if nan_count == 0:
            continue

        if nan_pct > 50:
            status = "HIGH_NAN"
        elif nan_pct > 10:
            status = "MEDIUM_NAN"
        else:
            status = "LOW_NAN"

        rows.append({
            "File": filename,
            "Column": col,
            "NaNCount": nan_count,
            "NaNPct": nan_pct,
            "Status": status,
        })

    return rows


def main():
    all_rows = []

    for filename in FILES_TO_CHECK:
        all_rows.extend(inspect_file(filename))

    if not all_rows:
        all_rows.append({
            "File": "ALL",
            "Column": "ALL",
            "NaNCount": 0,
            "NaNPct": 0,
            "Status": "NO_NAN_FOUND",
        })

    report = pd.DataFrame(all_rows)
    report = report.sort_values(["File", "NaNCount"], ascending=[True, False])
    report.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE NAN INSPECTION REPORT")
    print("===================================\n")
    print(report.to_string(index=False))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()