from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_LOG_PATH = BASE_DIR / "data/mini_cube_state_log.csv"
OUTPUT_PATH = BASE_DIR / "data/state_change_history.csv"
SUMMARY_PATH = BASE_DIR / "data/state_change_summary.txt"


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
        print("Not enough state history. Need at least 2 rows.")
        return None

    return df


def compare_rows(old_row: dict, new_row: dict) -> list[dict]:
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
            changes.append({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "PreviousStateTime": old_row.get("Timestamp", "UNKNOWN"),
                "CurrentStateTime": new_row.get("Timestamp", "UNKNOWN"),
                "Field": key,
                "OldValue": old_value,
                "NewValue": new_value,
                "Reason": f"{key} changed from {old_value} to {new_value}"
            })

    return changes


def save_changes(changes: list[dict]) -> None:
    if not changes:
        return

    out_df = pd.DataFrame(changes)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not OUTPUT_PATH.exists():
        out_df.to_csv(OUTPUT_PATH, index=False)
    else:
        out_df.to_csv(OUTPUT_PATH, mode="a", header=False, index=False)


def build_summary(changes: list[dict], old_row: dict, new_row: dict) -> str:
    lines = [
        "MINI CUBE STATE CHANGE SUMMARY",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Previous State Time: {old_row.get('Timestamp', 'UNKNOWN')}",
        f"Current State Time : {new_row.get('Timestamp', 'UNKNOWN')}",
        "",
    ]

    if not changes:
        lines.append("No state changes detected.")
        return "\n".join(lines)

    lines.append("Changes detected:")
    for change in changes:
        lines.append(f"- {change['Field']}: {change['OldValue']} -> {change['NewValue']}")

    return "\n".join(lines)


def main() -> None:
    df = load_state_log()
    if df is None:
        return

    old_row = df.iloc[-2].to_dict()
    new_row = df.iloc[-1].to_dict()

    changes = compare_rows(old_row, new_row)
    save_changes(changes)

    summary = build_summary(changes, old_row, new_row)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print(summary)

    if changes:
        print(f"\nSaved state changes to {OUTPUT_PATH}")
    print(f"Saved summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()