from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
TRADE_LOG_PATH = BASE_DIR / "data/paper_trade_log.csv"
OUTPUT_PATH = BASE_DIR / "data/pattern_learning_scores.csv"


def main() -> None:
    if not TRADE_LOG_PATH.exists():
        print(f"Missing file: {TRADE_LOG_PATH}")
        return

    df = pd.read_csv(TRADE_LOG_PATH)

    if df.empty:
        print("paper_trade_log.csv is empty.")
        return

    required_cols = ["PatternKey", "ReturnPct", "WinLoss"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"Missing required columns: {missing}")
        return

    df["PatternKey"] = df["PatternKey"].astype(str).str.strip()
    df["ReturnPct"] = pd.to_numeric(df["ReturnPct"], errors="coerce").fillna(0.0)
    df["WinFlag"] = df["WinLoss"].astype(str).str.upper().eq("WIN").astype(int)

    grouped = df.groupby("PatternKey").agg(
        Trades=("PatternKey", "count"),
        WinRate=("WinFlag", "mean"),
        AvgReturn=("ReturnPct", "mean")
    ).reset_index()

    def compute_adjustment(row) -> int:
        trades = row["Trades"]
        win_rate = row["WinRate"]
        avg_return = row["AvgReturn"]

        if trades < 5:
            return 0

        score = 0

        if win_rate >= 0.65:
            score += 15
        elif win_rate >= 0.55:
            score += 8
        elif win_rate >= 0.45:
            score += 2
        elif win_rate >= 0.35:
            score -= 5
        else:
            score -= 12

        if avg_return > 2.0:
            score += 5
        elif avg_return > 0.5:
            score += 2
        elif avg_return < -2.0:
            score -= 5
        elif avg_return < -0.5:
            score -= 2

        return score

    grouped["ScoreAdjustment"] = grouped.apply(compute_adjustment, axis=1)
    grouped["WinRate"] = grouped["WinRate"].round(3)
    grouped["AvgReturn"] = grouped["AvgReturn"].round(3)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    grouped.to_csv(OUTPUT_PATH, index=False)

    print("Saved learning scores to:", OUTPUT_PATH)
    print(grouped.sort_values("ScoreAdjustment", ascending=False))


if __name__ == "__main__":
    main()
