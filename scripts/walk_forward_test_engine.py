from pathlib import Path
import pandas as pd

INPUT_FILE = Path("data/historical_forward_returns.csv")
OUTPUT_FILE = Path("data/walk_forward_results.csv")

MIN_TRADES = 30
MIN_WINRATE = 55.0
MIN_RETURN = 0.0


def summarize(dataframe, label, train_end_year=None, test_year=None):
    if dataframe.empty:
        return pd.DataFrame()

    summary = dataframe.groupby("PrimarySignal").agg(
        Trades=("Ticker", "count"),
        WinRate5D=("Win5D", "mean"),
        AvgReturn5D=("ForwardReturn5D", "mean"),
        WinRate10D=("Win10D", "mean"),
        AvgReturn10D=("ForwardReturn10D", "mean"),
    ).reset_index()

    summary["WinRate5D"] = summary["WinRate5D"] * 100
    summary["WinRate10D"] = summary["WinRate10D"] * 100

    summary["Period"] = label
    summary["TrainEndYear"] = train_end_year
    summary["TestYear"] = test_year

    summary["Status"] = summary.apply(
        lambda row: "VALID"
        if (
            row["Trades"] >= MIN_TRADES
            and row["WinRate10D"] >= MIN_WINRATE
            and row["AvgReturn10D"] > MIN_RETURN
        )
        else "WEAK",
        axis=1,
    )

    return summary.round({
        "WinRate5D": 2,
        "AvgReturn5D": 3,
        "WinRate10D": 2,
        "AvgReturn10D": 3,
    })


def main():
    print("\nWALK-FORWARD TEST ENGINE\n")

    if not INPUT_FILE.exists():
        print(f"Missing file: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    required = [
        "Date",
        "Ticker",
        "PrimarySignal",
        "ForwardReturn5D",
        "ForwardReturn10D",
        "Win5D",
        "Win10D",
    ]

    missing = [c for c in required if c not in df.columns]

    if missing:
        print(f"Missing required columns: {missing}")
        return

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="mixed",
        errors="coerce",
    )

    df = df.dropna(subset=["Date"]).copy()

    if df.empty:
        print("No valid historical dates found.")
        return

    df["PrimarySignal"] = (
        df["PrimarySignal"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["Year"] = df["Date"].dt.year

    for col in [
        "ForwardReturn5D",
        "ForwardReturn10D",
        "Win5D",
        "Win10D",
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(
        subset=[
            "ForwardReturn5D",
            "ForwardReturn10D",
            "Win5D",
            "Win10D",
        ]
    ).copy()

    years = sorted(df["Year"].unique())

    if len(years) < 4:
        print("Not enough years for walk-forward testing.")
        print(f"Available years: {years}")
        return

    all_results = []

    for test_year in years[3:]:
        train_df = df[df["Year"] < test_year].copy()
        test_df = df[df["Year"] == test_year].copy()

        if train_df.empty or test_df.empty:
            continue

        train_summary = summarize(
            train_df,
            "TRAIN",
            train_end_year=test_year - 1,
            test_year=test_year,
        )

        test_summary = summarize(
            test_df,
            "TEST",
            train_end_year=test_year - 1,
            test_year=test_year,
        )

        combined = pd.concat(
            [train_summary, test_summary],
            ignore_index=True,
        )

        all_results.append(combined)

    if not all_results:
        print("No walk-forward results generated.")
        return

    results = pd.concat(
        all_results,
        ignore_index=True,
    )

    results = results.sort_values(
        by=[
            "TestYear",
            "Period",
            "Status",
            "WinRate10D",
            "AvgReturn10D",
        ],
        ascending=[
            True,
            True,
            True,
            False,
            False,
        ],
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(results.head(80).to_string(index=False))

    print(f"\nRows: {len(results)}")
    print(f"Years tested: {years[3]} - {years[-1]}")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()