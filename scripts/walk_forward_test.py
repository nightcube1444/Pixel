 from pathlib import Path
import pandas as pd

INPUT_FILE = Path("data/forward_validation_results.csv")
OUTPUT_FILE = Path("data/walk_forward_results.csv")

MIN_TRADES = 30


def summarize(dataframe, label, train_end_year=None, test_year=None):
    if dataframe.empty:
        return pd.DataFrame()

    summary = dataframe.groupby("Signal").agg(
        Trades=("Ticker", "count"),
        WinRate=("Win1D", "mean"),
        AvgReturn=("Return1D", "mean"),
    ).reset_index()

    summary["WinRate"] = summary["WinRate"] * 100
    summary["AvgReturn"] = summary["AvgReturn"] * 100
    summary["Period"] = label
    summary["TrainEndYear"] = train_end_year
    summary["TestYear"] = test_year

    summary["Status"] = summary.apply(
        lambda row: "VALID"
        if row["Trades"] >= MIN_TRADES and row["WinRate"] >= 55 and row["AvgReturn"] > 0
        else "WEAK",
        axis=1,
    )

    return summary.round({
        "WinRate": 2,
        "AvgReturn": 3,
    })


def main():
    df = pd.read_csv(INPUT_FILE)

    df["SignalDate"] = pd.to_datetime(
        df["SignalDate"],
        format="mixed",
        errors="coerce",
    )

    df = df.dropna(subset=["SignalDate"]).copy()

    if df.empty:
        print("No forward validation data available.")
        return

    df["Year"] = df["SignalDate"].dt.year

    years = sorted(df["Year"].unique())

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

    results = pd.concat(all_results, ignore_index=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_FILE, index=False)

    print("\nWALK-FORWARD TEST RESULTS\n")
    print(results.head(50).to_string(index=False))
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()