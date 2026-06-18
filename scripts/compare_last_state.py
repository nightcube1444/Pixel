from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_LOG_PATH = BASE_DIR / "data/mini_cube_state_log.csv"


def load_state_log() -> pd.DataFrame | None:
    if not STATE_LOG_PATH.exists():
        print(f"Missing file: {STATE_LOG_PATH}")
        return None

    try:
        df = pd.read_csv(STATE_LOG_PATH)
    except Exception as e:
        print(f"Failed to read state log: {e}")
        return None

    if df.empty or len(df) < 2:
        print("Not enough state history to compare. Need at least 2 rows.")
        return None

    return df


def compare_rows(old_row: dict, new_row: dict) -> list[str]:
    changes = []

    keys_to_compare = [
        "MarketState",
        "TopTicker",
        "TopPrimarySignal",
        "TopMarketRegime",
        "TopVolatility",
        "TopScore",
        "TopPriorityScore",
        "BullCount",
        "BearCount",
        "SidewaysCount",
        "HighVolCount",
        "PanicCount",
        "MomentumCount",
        "OversoldCount",
        "OverboughtCount",
    ]

    for key in keys_to_compare:
        old_value = str(old_row.get(key, "")).strip()
        new_value = str(new_row.get(key, "")).strip()

        if old_value != new_value:
            changes.append(f"{key}: {old_value} -> {new_value}")

    return changes


def main() -> None:
    df = load_state_log()
    if df is None:
        return

    old_row = df.iloc[-2].to_dict()
    new_row = df.iloc[-1].to_dict()

    print("MINI CUBE STATE COMPARISON")
    print(f"Previous Time: {old_row.get('Timestamp', 'UNKNOWN')}")
    print(f"Current Time : {new_row.get('Timestamp', 'UNKNOWN')}")
    print()

    changes = compare_rows(old_row, new_row)

    if not changes:
        print("No state changes found.")
        return

    print("Changes detected:")
    for change in changes:
        print(f"- {change}")


if __name__ == "__main__":
    main()