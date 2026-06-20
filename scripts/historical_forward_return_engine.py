import pandas as pd
from pathlib import Path

INPUT_FILE = Path(
    "data/all_stock_signals_with_context.csv"
)

OUTPUT_FILE = Path(
    "data/historical_forward_returns.csv"
)


def main():

    print("\nHISTORICAL FORWARD RETURN ENGINE\n")

    df = pd.read_csv(
        INPUT_FILE
    )

    df["Date"] = pd.to_datetime(
        df["Date"]
    )

    df = df.sort_values(
        ["Ticker", "Date"]
    )

    results = []

    for ticker, group in df.groupby("Ticker"):

        group = group.copy()

        group["Price5D"] = (
            group["Close"].shift(-5)
        )

        group["Price10D"] = (
            group["Close"].shift(-10)
        )

        group["ForwardReturn5D"] = (
            (
                group["Price5D"]
                - group["Close"]
            )
            / group["Close"]
            * 100
        )

        group["ForwardReturn10D"] = (
            (
                group["Price10D"]
                - group["Close"]
            )
            / group["Close"]
            * 100
        )

        group["Win5D"] = (
            group["ForwardReturn5D"] > 0
        ).astype(int)

        group["Win10D"] = (
            group["ForwardReturn10D"] > 0
        ).astype(int)

        results.append(group)

    output = pd.concat(
        results,
        ignore_index=True
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print(
        output[
            [
                "Date",
                "Ticker",
                "Close",
                "Price5D",
                "ForwardReturn5D",
                "Price10D",
                "ForwardReturn10D"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print(
        f"\nRows: {len(output)}"
    )

    print(
        f"Saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()