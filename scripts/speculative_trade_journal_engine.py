from pathlib import Path
from datetime import datetime
import pandas as pd

WATCHLIST_PATH = Path("data/speculative_watchlist.csv")
JOURNAL_PATH = Path("data/speculative_trade_journal.csv")


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
    watchlist = safe_read_csv(WATCHLIST_PATH)

    if watchlist is None:
        print("Missing speculative_watchlist.csv. Run speculative_watchlist_engine.py first.")
        return

    today = datetime.now().strftime("%Y-%m-%d")

    candidates = watchlist[
        watchlist["Action"].isin(["WATCH", "WATCH_CLOSELY", "PAPER_ONLY"])
    ].copy()

    if candidates.empty:
        print("No speculative paper trade candidates today.")
        return

    old_journal = safe_read_csv(JOURNAL_PATH)

    rows = []

    for _, row in candidates.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        action = str(row.get("Action", "")).strip()
        entry_price = row.get("Close", None)

        if not ticker:
            continue

        already_exists = False

        if old_journal is not None:
            same_trade = old_journal[
                (old_journal["Ticker"].astype(str) == ticker)
                & (old_journal["EntryDate"].astype(str) == today)
            ]

            if not same_trade.empty:
                already_exists = True

        if already_exists:
            continue

        rows.append({
            "EntryDate": today,
            "Ticker": ticker,
            "EntryPrice": entry_price,
            "Signal": row.get("PrimarySignal", ""),
            "MarketRegime": row.get("MarketRegime", ""),
            "Volatility": row.get("Volatility", ""),
            "FinalScore": row.get("FinalScore", 0),
            "Pattern": row.get("Pattern", ""),
            "AlphaScore": row.get("AlphaScore", 0),
            "WinRate": row.get("WinRate", 0),
            "Trades": row.get("Trades", 0),
            "RiskLevel": row.get("RiskLevel", ""),
            "Action": action,
            "Status": "OPEN",
            "ExitDate": "",
            "ExitPrice": "",
            "ReturnPct": "",
            "Result": "",
            "Notes": "Auto-added from speculative watchlist"
        })

    new_entries = pd.DataFrame(rows)

    if old_journal is None:
        final = new_entries
    else:
        final = pd.concat([old_journal, new_entries], ignore_index=True)

    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(JOURNAL_PATH, index=False)

    print("\nSPECULATIVE TRADE JOURNAL ENGINE\n")

    if new_entries.empty:
        print("No new journal entries added.")
    else:
        print("New entries:")
        print(new_entries[[
            "EntryDate",
            "Ticker",
            "EntryPrice",
            "Signal",
            "FinalScore",
            "RiskLevel",
            "Action",
            "Status"
        ]].to_string(index=False))

    print()
    print(f"Total journal rows: {len(final)}")
    print(f"Saved to {JOURNAL_PATH}")


if __name__ == "__main__":
    main()