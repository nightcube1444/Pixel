from pathlib import Path
import pandas as pd

MARKET_DATA = Path("data/market_data.csv")
OUTPUT = Path("data/liquidity_report.csv")

MIN_AVG_VOLUME = 500_000
MIN_AVG_DOLLAR_VOLUME = 1_000_000
LOOKBACK_DAYS = 60


def main():
    print("\nLIQUIDITY FILTER ENGINE\n")

    df = pd.read_csv(MARKET_DATA)

    required = ["Date", "Ticker", "Close", "Volume"]
    missing = [c for c in required if c not in df.columns]

    if missing:
        print(f"Missing columns: {missing}")
        return

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Ticker"] = df["Ticker"].astype(str).str.upper().str.strip()
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce")

    df = df.dropna(subset=["Date", "Ticker", "Close", "Volume"])

    rows = []

    for ticker, group in df.groupby("Ticker"):
        group = group.sort_values("Date").tail(LOOKBACK_DAYS)

        if group.empty:
            continue

        avg_volume = group["Volume"].mean()
        avg_dollar_volume = (group["Close"] * group["Volume"]).mean()
        last_close = group.iloc[-1]["Close"]

        if avg_volume >= MIN_AVG_VOLUME and avg_dollar_volume >= MIN_AVG_DOLLAR_VOLUME:
            status = "LIQUID"
        else:
            status = "ILLQUID"

        rows.append({
            "Ticker": ticker,
            "LastClose": round(last_close, 2),
            "AvgVolume60D": round(avg_volume, 0),
            "AvgDollarVolume60D": round(avg_dollar_volume, 0),
            "LiquidityStatus": status,
        })

    out = pd.DataFrame(rows)

    out = out.sort_values(
        by=["LiquidityStatus", "AvgDollarVolume60D"],
        ascending=[True, False],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)

    print(out.to_string(index=False))
    print(f"\nSaved to {OUTPUT}")


if __name__ == "__main__":
    main()