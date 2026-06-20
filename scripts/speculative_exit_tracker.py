from pathlib import Path
from datetime import datetime
import pandas as pd

JOURNAL_PATH = Path("data/speculative_trade_journal.csv")
LATEST_SIGNALS_PATH = Path("data/latest_stock_signals.csv")
OUTPUT_PATH = Path("data/speculative_trade_journal.csv")

TARGET_PCT = 15.0
STOP_LOSS_PCT = 7.0


def safe_read_csv(path):
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        df = pd.read_csv(path)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"Could not read {path}: {e}")
        return None


def main():
    journal = safe_read_csv(JOURNAL_PATH)
    latest = safe_read_csv(LATEST_SIGNALS_PATH)

    if journal is None:
        print("Missing speculative_trade_journal.csv")
        return

    if latest is None:
        print("Missing latest_stock_signals.csv")
        return

    latest_prices = {
        str(row["Ticker"]).strip(): float(row["Close"])
        for _, row in latest.iterrows()
        if pd.notna(row.get("Close"))
    }

    journal = journal.copy()

    # Force these columns to allow text values like OPEN, TARGET_HIT, STOP_LOSS_HIT
    text_cols = ["Status", "ExitDate", "ExitPrice", "ReturnPct", "Result", "Notes"]

    for col in text_cols:
        if col not in journal.columns:
            journal[col] = ""
        journal[col] = journal[col].astype("object").fillna("")

    updated_count = 0
    closed_count = 0

    for i, row in journal.iterrows():
        status = str(row.get("Status", "")).strip().upper()

        if status != "OPEN":
            continue

        ticker = str(row.get("Ticker", "")).strip()

        if ticker not in latest_prices:
            continue

        entry_price = pd.to_numeric(row.get("EntryPrice"), errors="coerce")

        if pd.isna(entry_price) or entry_price <= 0:
            continue

        current_price = latest_prices[ticker]

        target_price = entry_price * (1 + TARGET_PCT / 100)
        stop_price = entry_price * (1 - STOP_LOSS_PCT / 100)

        return_pct = ((current_price - entry_price) / entry_price) * 100

        updated_count += 1

        if current_price >= target_price:
            journal.at[i, "Status"] = "CLOSED"
            journal.at[i, "ExitDate"] = datetime.now().strftime("%Y-%m-%d")
            journal.at[i, "ExitPrice"] = round(current_price, 2)
            journal.at[i, "ReturnPct"] = round(return_pct, 2)
            journal.at[i, "Result"] = "TARGET_HIT"
            journal.at[i, "Notes"] = "Target profit reached"
            closed_count += 1

        elif current_price <= stop_price:
            journal.at[i, "Status"] = "CLOSED"
            journal.at[i, "ExitDate"] = datetime.now().strftime("%Y-%m-%d")
            journal.at[i, "ExitPrice"] = round(current_price, 2)
            journal.at[i, "ReturnPct"] = round(return_pct, 2)
            journal.at[i, "Result"] = "STOP_LOSS_HIT"
            journal.at[i, "Notes"] = "Stop loss reached"
            closed_count += 1

        else:
            journal.at[i, "ReturnPct"] = round(return_pct, 2)
            journal.at[i, "Result"] = "OPEN"
            journal.at[i, "Notes"] = "Still open"

    journal.to_csv(OUTPUT_PATH, index=False)

    print("\nSPECULATIVE EXIT TRACKER\n")
    print(journal.tail(20).to_string(index=False))
    print()
    print(f"Open trades checked: {updated_count}")
    print(f"Trades closed: {closed_count}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()