from pathlib import Path
import pandas as pd

INPUT_FILE = Path("data/historical_forward_returns.csv")
OUTPUT_FILE = Path("data/bounce_back_results.csv")

DROP_THRESHOLD_PCT = -3.0


def classify_bounce(row):
    if row["Bounce10D"] >= 5:
        return "STRONG_BOUNCE"
    if row["Bounce10D"] >= 2:
        return "BOUNCE"
    if row["Bounce10D"] > 0:
        return "WEAK_BOUNCE"
    return "NO_BOUNCE"


def main():
    print("\nBOUNCE BACK ENGINE\n")

    if not INPUT_FILE.exists():
        print(f"Missing file: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    required = [
        "Date",
        "Ticker",
        "Close",
        "Daily Return",
        "PrimarySignal",
        "MarketRegime",
        "Volatility",
        "CrossAssetPattern",
        "ForwardReturn5D",
        "ForwardReturn10D",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        print(f"Missing required columns: {missing}")
        return

    df = df.copy()

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="mixed",
        errors="coerce",
    )

    df["Ticker"] = (
        df["Ticker"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Daily Return"] = pd.to_numeric(
        df["Daily Return"],
        errors="coerce",
    ) * 100

    df["ForwardReturn5D"] = pd.to_numeric(
        df["ForwardReturn5D"],
        errors="coerce",
    )

    df["ForwardReturn10D"] = pd.to_numeric(
        df["ForwardReturn10D"],
        errors="coerce",
    )

    df = df.dropna(
        subset=[
            "Date",
            "Ticker",
            "Daily Return",
            "ForwardReturn5D",
            "ForwardReturn10D",
        ]
    ).copy()

    drops = df[
        df["Daily Return"] <= DROP_THRESHOLD_PCT
    ].copy()

    if drops.empty:
        print("No bounce-back events found.")
        return

    drops["DropPct"] = drops["Daily Return"]
    drops["Bounce5D"] = drops["ForwardReturn5D"]
    drops["Bounce10D"] = drops["ForwardReturn10D"]

    drops["Recovered5D"] = drops["Bounce5D"] > 0
    drops["Recovered10D"] = drops["Bounce10D"] > 0

    drops["BounceStrength"] = drops.apply(
        classify_bounce,
        axis=1,
    )

    output_cols = [
        "Date",
        "Ticker",
        "Close",
        "DropPct",
        "PrimarySignal",
        "MarketRegime",
        "Volatility",
        "CrossAssetPattern",
        "Bounce5D",
        "Recovered5D",
        "Bounce10D",
        "Recovered10D",
        "BounceStrength",
    ]

    results = drops[output_cols].copy()

    results = results.sort_values(
        by=["Date", "DropPct"],
        ascending=[False, True],
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    summary = (
        results.groupby("BounceStrength")
        .agg(
            Events=("Ticker", "count"),
            AvgDropPct=("DropPct", "mean"),
            AvgBounce5D=("Bounce5D", "mean"),
            RecoveryRate5D=("Recovered5D", "mean"),
            AvgBounce10D=("Bounce10D", "mean"),
            RecoveryRate10D=("Recovered10D", "mean"),
        )
        .reset_index()
    )

    summary["RecoveryRate5D"] *= 100
    summary["RecoveryRate10D"] *= 100

    summary = summary.round(
        {
            "AvgDropPct": 2,
            "AvgBounce5D": 2,
            "RecoveryRate5D": 2,
            "AvgBounce10D": 2,
            "RecoveryRate10D": 2,
        }
    )

    print(summary.to_string(index=False))

    print(f"\nBounce Events: {len(results)}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()