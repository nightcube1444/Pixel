from pathlib import Path
import pandas as pd

CHANGE_PATH = Path("data/change_detection_results.csv")
ALPHA_PATH = Path("data/alpha_ranking_results.csv")
SIGNALS_PATH = Path("data/latest_stock_signals.csv")
OUTPUT_PATH = Path("data/root_cause_report.csv")


def main():

    if not CHANGE_PATH.exists():
        print("Missing change_detection_results.csv")
        return

    if not ALPHA_PATH.exists():
        print("Missing alpha_ranking_results.csv")
        return

    if not SIGNALS_PATH.exists():
        print("Missing latest_stock_signals.csv")
        return

    changes = pd.read_csv(CHANGE_PATH)
    alpha = pd.read_csv(ALPHA_PATH)
    signals = pd.read_csv(SIGNALS_PATH)

    rows = []

    for _, event in changes.iterrows():

        pattern = str(event.get("Item", "")).strip()

        if event.get("Category") != "ALPHA":
            continue

        match = alpha[
            alpha["Pattern"].astype(str).str.strip() == pattern
        ]

        if match.empty:
            continue

        row = match.iloc[0]

        trades = float(row.get("Trades", 0))
        winrate = float(row.get("WinRate", 0))
        alpha_score = float(row.get("AlphaScore", 0))

        matching_stocks = []

        for _, stock in signals.iterrows():

            stock_pattern = (
                str(stock.get("PrimarySignal", "NONE"))
                + "|"
                + str(stock.get("MarketRegime", "UNKNOWN"))
                + "|"
                + str(stock.get("Volatility", "NORMAL"))
            )

            if stock_pattern == pattern:
                matching_stocks.append(
                    str(stock.get("Ticker"))
                )

        if trades >= 500:
            evidence = "STRONG"
        elif trades >= 100:
            evidence = "MODERATE"
        else:
            evidence = "WEAK"

        reason = []

        if alpha_score >= 100:
            reason.append("Exceptional alpha score")
        elif alpha_score >= 50:
            reason.append("High alpha score")

        if winrate >= 60:
            reason.append("Strong win rate")
        elif winrate >= 50:
            reason.append("Positive win rate")

        if trades >= 1000:
            reason.append("Very large sample size")
        elif trades >= 500:
            reason.append("Large sample size")
        elif trades >= 100:
            reason.append("Moderate sample size")

        if not reason:
            reason.append("Limited evidence")

        if evidence == "STRONG" and winrate >= 55:
            action = "Monitor closely"
        elif evidence == "MODERATE":
            action = "Needs more validation"
        else:
            action = "Treat cautiously"

        rows.append({
            "Pattern": pattern,
            "Stocks": ", ".join(matching_stocks),
            "ChangeType": event["ChangeType"],
            "AlphaRank": row.get("AlphaRank"),
            "AlphaScore": alpha_score,
            "WinRate": winrate,
            "Trades": trades,
            "EvidenceLevel": evidence,
            "Reason": "; ".join(reason),
            "SuggestedAction": action
        })

    result = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\nROOT CAUSE REPORT\n")
    print(result.head(20))

    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()