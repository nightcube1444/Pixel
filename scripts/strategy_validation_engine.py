from pathlib import Path
import pandas as pd

MARKET_DATA = Path("data/market_data.csv")
OPPORTUNITIES = Path("data/institutional_opportunities.csv")
OUTPUT = Path("data/strategy_validation_results.csv")

HORIZONS = [5, 10, 20]


def main():
    print("\nSTRATEGY VALIDATION ENGINE\n")

    market = pd.read_csv(MARKET_DATA)
    opps = pd.read_csv(OPPORTUNITIES)

    market["Ticker"] = market["Ticker"].astype(str).str.upper().str.strip()
    market["Date"] = pd.to_datetime(market["Date"], errors="coerce")
    market["Close"] = pd.to_numeric(market["Close"], errors="coerce")

    opps["Ticker"] = opps["Ticker"].astype(str).str.upper().str.strip()

    rows = []

    for _, opp in opps.iterrows():
        ticker = opp["Ticker"]
        pattern = opp["Pattern"]

        df = market[market["Ticker"] == ticker].copy()
        df = df.sort_values("Date").reset_index(drop=True)

        if df.empty:
            continue

        latest_close = df.iloc[-1]["Close"]

        result = {
            "Ticker": ticker,
            "Pattern": pattern,
            "Appearances": opp.get("Appearances", ""),
            "SurvivalScore": opp.get("SurvivalScore", ""),
            "AlphaScore": opp.get("AlphaScore", ""),
            "DistinctTickers": opp.get("DistinctTickers", ""),
            "DiversityStatus": opp.get("DiversityStatus", ""),
            "LatestClose": latest_close,
        }

        for h in HORIZONS:
            returns = []

            for i in range(len(df) - h):
                entry = df.iloc[i]["Close"]
                exit_price = df.iloc[i + h]["Close"]

                if pd.isna(entry) or pd.isna(exit_price) or entry == 0:
                    continue

                ret = ((exit_price - entry) / entry) * 100
                returns.append(ret)

            if returns:
                s = pd.Series(returns)

                result[f"AvgReturn{h}D"] = round(s.mean(), 2)
                result[f"WinRate{h}D"] = round((s > 0).mean() * 100, 2)
                result[f"MedianReturn{h}D"] = round(s.median(), 2)
                result[f"Trades{h}D"] = len(s)
            else:
                result[f"AvgReturn{h}D"] = 0
                result[f"WinRate{h}D"] = 0
                result[f"MedianReturn{h}D"] = 0
                result[f"Trades{h}D"] = 0

        rows.append(result)

    out = pd.DataFrame(rows)

    if out.empty:
        print("No validation results generated.")
        return

    out = out.sort_values(
        by=["AvgReturn10D", "WinRate10D"],
        ascending=[False, False],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)

    print(out.to_string(index=False))
    print(f"\nSaved to {OUTPUT}")


if __name__ == "__main__":
    main()