from pathlib import Path
import pandas as pd
import numpy as np
from math import sqrt, erf

DISCOVERY_PATH = Path("data/signal_discovery_results.csv")
OUTPUT_PATH = Path("data/pattern_validation_results.csv")

MIN_TRADES = 30
P_VALUE_LIMIT = 0.05


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


def normal_cdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def p_value_from_mean(avg_return, std_return, trades):
    if trades <= 1 or std_return <= 0:
        return 1.0

    standard_error = std_return / sqrt(trades)
    z_score = avg_return / standard_error

    p_value = 2 * (1 - normal_cdf(abs(z_score)))

    return max(0.0, min(1.0, p_value))


def main():
    df = safe_read_csv(DISCOVERY_PATH)

    if df is None:
        print("Missing signal_discovery_results.csv")
        return

    df = df.copy()

    for col in ["Trades", "AvgReturn5D", "AvgReturn10D", "WinRate5D", "WinRate10D"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    rows = []

    for _, row in df.iterrows():
        pattern = row.get("Pattern", row.get("SignalSetup", ""))

        trades = float(row.get("Trades", 0))
        avg_return_5d = float(row.get("AvgReturn5D", 0))
        avg_return_10d = float(row.get("AvgReturn10D", 0))
        winrate_5d = float(row.get("WinRate5D", 0))
        winrate_10d = float(row.get("WinRate10D", 0))

        # Temporary estimated volatility.
        # Later we will replace this with real return distribution from raw events.
        estimated_std = max(abs(avg_return_10d) * 2, 5.0)

        p_value = p_value_from_mean(
            avg_return_10d,
            estimated_std,
            trades
        )

        if trades < MIN_TRADES:
            validation = "INSUFFICIENT_SAMPLE"
        elif p_value <= P_VALUE_LIMIT and avg_return_10d > 0:
            validation = "VALIDATED"
        elif avg_return_10d > 0 and winrate_10d >= 50:
            validation = "WATCHLIST_ONLY"
        else:
            validation = "NOT_VALIDATED"

        rows.append({
            "Pattern": pattern,
            "Trades": trades,
            "AvgReturn5D": avg_return_5d,
            "AvgReturn10D": avg_return_10d,
            "WinRate5D": winrate_5d,
            "WinRate10D": winrate_10d,
            "EstimatedStd": round(estimated_std, 4),
            "PValue": round(p_value, 6),
            "ValidationStatus": validation,
        })

    result = pd.DataFrame(rows)

    result = result.sort_values(
        by=["ValidationStatus", "PValue", "AvgReturn10D"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    print("\nPATTERN VALIDATION ENGINE\n")
    print(result.head(30).to_string(index=False))
    print()
    print(f"Rows: {len(result)}")
    print(f"Saved to {OUTPUT_PATH}")
    print()
    print("Validation counts:")
    print(result["ValidationStatus"].value_counts().to_string())


if __name__ == "__main__":
    main()