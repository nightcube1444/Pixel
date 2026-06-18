from pathlib import Path
import pandas as pd

HISTORY_DIR = Path("data/pattern_history")
OUTPUT_PATH = Path("data/pattern_change_report.csv")


def main():

    files = sorted(
        HISTORY_DIR.glob("*_alpha.csv")
    )

    if len(files) < 2:
        print("Need at least 2 snapshots.")
        return

    previous_file = files[-2]
    current_file = files[-1]

    print(f"Previous: {previous_file.name}")
    print(f"Current : {current_file.name}")

    prev_df = pd.read_csv(previous_file)
    curr_df = pd.read_csv(current_file)

    prev_map = {
        row["Pattern"]: row
        for _, row in prev_df.iterrows()
    }

    curr_map = {
        row["Pattern"]: row
        for _, row in curr_df.iterrows()
    }

    rows = []

    shared_patterns = (
        set(prev_map.keys())
        &
        set(curr_map.keys())
    )

    for pattern in shared_patterns:

        old = prev_map[pattern]
        new = curr_map[pattern]

        old_alpha = float(old.get("AlphaScore", 0))
        new_alpha = float(new.get("AlphaScore", 0))

        old_win = float(old.get("WinRate5D", 0))
        new_win = float(new.get("WinRate5D", 0))

        old_trades = float(old.get("Trades", 0))
        new_trades = float(new.get("Trades", 0))

        alpha_change = round(
            new_alpha - old_alpha,
            4
        )

        trade_change = round(
            new_trades - old_trades,
            0
        )

        win_change = round(
            new_win - old_win,
            2
        )

        reasons = []

        if alpha_change > 5:
            reasons.append(
                "Alpha expanded"
            )

        if win_change > 1:
            reasons.append(
                "Win rate improved"
            )

        if trade_change > 20:
            reasons.append(
                "More evidence collected"
            )

        if not reasons:
            reasons.append(
                "Minor statistical movement"
            )

        rows.append({
            "Pattern": pattern,
            "OldAlpha": old_alpha,
            "NewAlpha": new_alpha,
            "AlphaChange": alpha_change,
            "WinRateChange": win_change,
            "TradeChange": trade_change,
            "Reason": "; ".join(reasons)
        })

    result = pd.DataFrame(rows)

    result = result.sort_values(
        "AlphaChange",
        ascending=False
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print()
    print("PATTERN CHANGE REPORT")
    print()
    print(result.head(20))

    print()
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()