from pathlib import Path
from datetime import datetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_LOG_PATH = BASE_DIR / "data/mini_cube_state_log.csv"
OUTPUT_PATH = BASE_DIR / "data/state_reason_history.csv"
SUMMARY_PATH = BASE_DIR / "data/state_reason_summary.txt"


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


def to_int(value, default=0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def describe_change(field: str, old_value: str, new_value: str) -> str:
    old_num = None
    new_num = None

    try:
        old_num = float(old_value)
        new_num = float(new_value)
    except Exception:
        pass

    if field == "MarketState":
        return f"Overall market regime changed from {old_value} to {new_value}."

    if field == "TopTicker":
        return f"The strongest current setup shifted from {old_value} to {new_value}."

    if field == "TopPrimarySignal":
        return f"The top signal type changed from {old_value} to {new_value}."

    if field == "TopMarketRegime":
        return f"The top signal's regime changed from {old_value} to {new_value}."

    if field == "TopVolatility":
        return f"The top signal's volatility state changed from {old_value} to {new_value}."

    if field == "TopScore" and old_num is not None and new_num is not None:
        if new_num > old_num:
            return f"Top score improved from {old_num:.3f} to {new_num:.3f}, meaning the leading setup got stronger."
        return f"Top score dropped from {old_num:.3f} to {new_num:.3f}, meaning the leading setup got weaker."

    if field == "TopPriorityScore" and old_num is not None and new_num is not None:
        if new_num > old_num:
            return f"Top priority score increased from {int(old_num)} to {int(new_num)}, so urgency increased."
        return f"Top priority score fell from {int(old_num)} to {int(new_num)}, so urgency decreased."

    if field.endswith("Count") and old_num is not None and new_num is not None:
        if new_num > old_num:
            return f"{field} increased from {int(old_num)} to {int(new_num)}, so more stocks entered that category."
        return f"{field} decreased from {int(old_num)} to {int(new_num)}, so fewer stocks remained in that category."

    return f"{field} changed from {old_value} to {new_value}."


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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for key in keys_to_compare:
        old_value = str(old_row.get(key, "")).strip()
        new_value = str(new_row.get(key, "")).strip()

        if old_value != new_value:
            changes.append({
                "Timestamp": now,
                "PreviousStateTime": old_row.get("Timestamp", "UNKNOWN"),
                "CurrentStateTime": new_row.get("Timestamp", "UNKNOWN"),
                "Field": key,
                "OldValue": old_value,
                "NewValue": new_value,
                "ReasonText": describe_change(key, old_value, new_value),
            })

    return changes


def build_interpretation(old_row: dict, new_row: dict) -> list[str]:
    lines = []

    old_bear = to_int(old_row.get("BearCount", 0))
    new_bear = to_int(new_row.get("BearCount", 0))

    old_sideways = to_int(old_row.get("SidewaysCount", 0))
    new_sideways = to_int(new_row.get("SidewaysCount", 0))

    old_momentum = to_int(old_row.get("MomentumCount", 0))
    new_momentum = to_int(new_row.get("MomentumCount", 0))

    old_oversold = to_int(old_row.get("OversoldCount", 0))
    new_oversold = to_int(new_row.get("OversoldCount", 0))

    old_panic = to_int(old_row.get("PanicCount", 0))
    new_panic = to_int(new_row.get("PanicCount", 0))

    old_market = str(old_row.get("MarketState", "UNKNOWN")).strip()
    new_market = str(new_row.get("MarketState", "UNKNOWN")).strip()

    if new_market != old_market:
        lines.append(f"Market regime changed from {old_market} to {new_market}.")

    if new_momentum > old_momentum:
        lines.append("Momentum is increasing, which suggests more stocks are showing short-term strength.")

    if new_panic > old_panic:
        lines.append("Panic count increased, which suggests fear or sharp downside pressure is spreading.")

    if new_oversold < old_oversold:
        lines.append("Oversold count dropped, which may mean some weak stocks are rebounding out of extreme weakness.")

    if new_bear < old_bear and new_sideways > old_sideways:
        lines.append("Some stocks may be moving out of bearish conditions into neutral sideways behavior.")

    if not lines:
        lines.append("State changed, but the meaning is still limited without more history.")

    return lines


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
        "MINI CUBE STATE REASON SUMMARY",
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

    lines.append("")
    lines.append("Reasons:")
    for change in changes:
        lines.append(f"- {change['ReasonText']}")

    lines.append("")
    lines.append("Interpretation:")
    for line in build_interpretation(old_row, new_row):
        lines.append(f"- {line}")

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
        print(f"\nSaved state reasons to {OUTPUT_PATH}")
    print(f"Saved summary to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()