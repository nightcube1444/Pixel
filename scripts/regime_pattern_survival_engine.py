from pathlib import Path
import pandas as pd

SIGNALS_FILE = Path(
    "data/all_stock_signals_with_context.csv"
)

FORWARD_FILE = Path(
    "data/forward_validation_results.csv"
)

OUTPUT_FILE = Path(
    "data/regime_pattern_survival.csv"
)


def classify_regime(
    bull,
    bear,
    sideways
):

    values = [
        bull,
        bear,
        sideways
    ]

    values = [
        v for v in values
        if pd.notna(v)
    ]

    if len(values) < 2:
        return "INSUFFICIENT"

    spread = max(values) - min(values)

    avg = sum(values) / len(values)

    if avg >= 55 and spread <= 10:
        return "ALL_WEATHER"

    if spread <= 20:
        return "STABLE"

    return "REGIME_DEPENDENT"


def main():

    print(
        "\nREGIME PATTERN SURVIVAL ENGINE\n"
    )

    signals = pd.read_csv(
        SIGNALS_FILE
    )

    forward = pd.read_csv(
        FORWARD_FILE
    )

    print(
        f"Signals rows: {len(signals)}"
    )

    print(
        f"Forward rows: {len(forward)}"
    )

    print(
        "\nForward columns:"
    )

    print(
        forward.columns.tolist()
    )

    # ----------------------------------
    # Merge signal history with forward results
    # ----------------------------------

    merge_cols = [
        c
        for c in [
            "Ticker",
            "Date"
        ]
        if c in signals.columns
    ]

    if (
        "Ticker" not in forward.columns
        or "SignalDate" not in forward.columns
    ):
        print(
            "\nForward validation file missing required columns."
        )
        return

    forward = forward.rename(
        columns={
            "SignalDate": "Date"
        }
    )

    merged = signals.merge(
        forward[
            [
                "Ticker",
                "Date",
                "Return10D"
            ]
        ],
        on=[
            "Ticker",
            "Date"
        ],
        how="inner"
    )

    print(
        f"\nMerged rows: {len(merged)}"
    )

    if merged.empty:
        print(
            "No merged rows found."
        )
        return

    results = []

    patterns = (
        merged["CrossAssetPattern"]
        .dropna()
        .unique()
    )

    for pattern in patterns:

        subset = merged[
            merged["CrossAssetPattern"]
            == pattern
        ]

        bull = subset[
            subset["SPY_Regime"]
            == "BULL"
        ]

        bear = subset[
            subset["SPY_Regime"]
            == "BEAR"
        ]

        sideways = subset[
            subset["SPY_Regime"]
            == "SIDEWAYS"
        ]

        bull_wr = (
            (bull["Return10D"] > 0)
            .mean() * 100
            if len(bull)
            else None
        )

        bear_wr = (
            (bear["Return10D"] > 0)
            .mean() * 100
            if len(bear)
            else None
        )

        sideways_wr = (
            (sideways["Return10D"] > 0)
            .mean() * 100
            if len(sideways)
            else None
        )

        survival = classify_regime(
            bull_wr,
            bear_wr,
            sideways_wr
        )

        results.append(
            {
                "Pattern": pattern,
                "Appearances": len(subset),
                "BullWR": bull_wr,
                "BearWR": bear_wr,
                "SidewaysWR": sideways_wr,
                "RegimeClass": survival
            }
        )

    results = pd.DataFrame(
        results
    )

    results["SurvivalScore"] = (
        results[
            [
                "BullWR",
                "BearWR",
                "SidewaysWR"
            ]
        ]
        .mean(axis=1)
    )

    results = results.sort_values(
        by="SurvivalScore",
        ascending=False
    )

    results.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nTOP SURVIVING PATTERNS\n")

    print(
        results.head(20).to_string(
            index=False
        )
    )

    print(
        f"\nSaved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()