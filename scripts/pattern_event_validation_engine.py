from pathlib import Path
import pandas as pd

HISTORICAL_FILE = Path("data/historical_forward_returns.csv")
OPPORTUNITIES_FILE = Path("data/institutional_opportunities.csv")
OUTPUT_FILE = Path("data/pattern_event_validation_results.csv")


def main():
    print("\nPATTERN EVENT VALIDATION ENGINE\n")

    hist = pd.read_csv(HISTORICAL_FILE)
    opps = pd.read_csv(OPPORTUNITIES_FILE)

    hist["Ticker"] = hist["Ticker"].astype(str).str.upper().str.strip()
    opps["Ticker"] = opps["Ticker"].astype(str).str.upper().str.strip()

    hist["CrossAssetPattern"] = hist["CrossAssetPattern"].astype(str).str.strip()
    opps["Pattern"] = opps["Pattern"].astype(str).str.strip()

    hist["ForwardReturn5D"] = pd.to_numeric(hist["ForwardReturn5D"], errors="coerce")
    hist["ForwardReturn10D"] = pd.to_numeric(hist["ForwardReturn10D"], errors="coerce")

    rows = []

    for _, opp in opps.iterrows():
        ticker = opp["Ticker"]
        pattern = opp["Pattern"]

        events = hist[
            (hist["Ticker"] == ticker)
            &
            (hist["CrossAssetPattern"] == pattern)
        ].copy()

        if events.empty:
            continue

        result = {
            "Ticker": ticker,
            "Pattern": pattern,
            "Events": len(events),
            "Appearances": opp.get("Appearances", ""),
            "SurvivalScore": opp.get("SurvivalScore", ""),
            "AlphaScore": opp.get("AlphaScore", ""),
            "DistinctTickers": opp.get("DistinctTickers", ""),
            "TopTickerSharePct": opp.get("TopTickerSharePct", ""),
            "DiversityStatus": opp.get("DiversityStatus", ""),
        }

        valid_5d = events["ForwardReturn5D"].dropna()
        valid_10d = events["ForwardReturn10D"].dropna()

        if len(valid_5d) > 0:
            result["AvgReturn5D"] = round(valid_5d.mean(), 2)
            result["MedianReturn5D"] = round(valid_5d.median(), 2)
            result["WinRate5D"] = round((valid_5d > 0).mean() * 100, 2)
            result["WorstReturn5D"] = round(valid_5d.min(), 2)
            result["BestReturn5D"] = round(valid_5d.max(), 2)
        else:
            result["AvgReturn5D"] = 0
            result["MedianReturn5D"] = 0
            result["WinRate5D"] = 0
            result["WorstReturn5D"] = 0
            result["BestReturn5D"] = 0

        if len(valid_10d) > 0:
            result["AvgReturn10D"] = round(valid_10d.mean(), 2)
            result["MedianReturn10D"] = round(valid_10d.median(), 2)
            result["WinRate10D"] = round((valid_10d > 0).mean() * 100, 2)
            result["WorstReturn10D"] = round(valid_10d.min(), 2)
            result["BestReturn10D"] = round(valid_10d.max(), 2)
        else:
            result["AvgReturn10D"] = 0
            result["MedianReturn10D"] = 0
            result["WinRate10D"] = 0
            result["WorstReturn10D"] = 0
            result["BestReturn10D"] = 0

        rows.append(result)

    out = pd.DataFrame(rows)

    if out.empty:
        print("No pattern event validation results generated.")
        return

    out = out.sort_values(
        by=["AvgReturn10D", "WinRate10D"],
        ascending=[False, False],
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)

    print(out.to_string(index=False))
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()