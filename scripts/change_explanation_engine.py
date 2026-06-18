from pathlib import Path
from datetime import datetime
import pandas as pd

CHANGE_PATH = Path("data/change_detection_results.csv")
LATEST_SIGNALS_PATH = Path("data/latest_stock_signals.csv")
LIVE_MATCHES_PATH = Path("data/live_pattern_matches.csv")

OUTPUT_PATH = Path("data/change_explanations.csv")
SUMMARY_PATH = Path("data/change_explanations_summary.txt")


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return pd.DataFrame()


def find_signal_context(item: str, latest: pd.DataFrame) -> dict:
    if latest.empty or "Ticker" not in latest.columns:
        return {}

    rows = latest[latest["Ticker"].astype(str) == str(item)]

    if rows.empty:
        return {}

    row = rows.iloc[-1]

    return {
        "Ticker": row.get("Ticker", ""),
        "PrimarySignal": row.get("PrimarySignal", ""),
        "MarketRegime": row.get("MarketRegime", ""),
        "FinalScore": row.get("FinalScore", ""),
        "PatternBase": row.get("PatternBase", ""),
    }


def find_alpha_context(item: str, live: pd.DataFrame) -> dict:
    if live.empty:
        return {}

    # Item may be a ticker or pattern
    possible_cols = [c for c in ["Ticker", "Pattern", "CrossAssetPattern"] if c in live.columns]

    if not possible_cols:
        return {}

    mask = False

    for col in possible_cols:
        current_mask = live[col].astype(str) == str(item)
        mask = current_mask if isinstance(mask, bool) else (mask | current_mask)

    rows = live[mask]

    if rows.empty:
        return {}

    row = rows.iloc[-1]

    return {
        "AlphaScore": row.get("AlphaScore", ""),
        "WinRate": row.get("WinRate", ""),
        "PrimarySignal": row.get("PrimarySignal", ""),
        "MarketRegime": row.get("MarketRegime", ""),
    }


def explain_change(row: pd.Series, signal_ctx: dict, alpha_ctx: dict) -> tuple[str, str, str]:
    category = str(row.get("Category", ""))
    item = str(row.get("Item", ""))
    change_type = str(row.get("ChangeType", ""))
    old_value = str(row.get("OldValue", ""))
    new_value = str(row.get("NewValue", ""))
    importance = str(row.get("Importance", ""))

    reason = "Change detected from system snapshot comparison."
    confidence = "MEDIUM"
    action = "Record this change and monitor next pipeline run."

    if category == "MARKET_STATE":
        if item == "SPY_Regime":
            reason = f"SPY regime changed from {old_value} to {new_value}. This usually means the benchmark trend condition changed."
            action = "Review patterns under the new SPY regime before trusting old pattern rankings."
            confidence = "HIGH" if importance in ["CRITICAL", "IMPORTANT"] else "MEDIUM"

        elif item == "VIX_State":
            reason = f"VIX state changed from {old_value} to {new_value}. This suggests market volatility/risk conditions changed."
            action = "Separate research results by VIX condition because patterns may behave differently in high volatility."
            confidence = "HIGH"

        elif item == "MarketState":
            reason = f"Overall market state changed from {old_value} to {new_value}."
            action = "Check if top alpha patterns still perform well under the new market state."
            confidence = "HIGH"

        elif item == "FearScore":
            reason = f"Fear score changed from {old_value} to {new_value} based on news signal processing."
            action = "Compare fear change with price-based signals before drawing conclusions."
            confidence = "MEDIUM"

        elif item == "PositiveScore":
            reason = f"Positive news score changed from {old_value} to {new_value}."
            action = "Check whether positive news is confirmed by market price action."
            confidence = "MEDIUM"

    elif category == "ALPHA":
        if change_type == "NEW_PATTERN":
            reason = "A new pattern entered the top alpha ranking list."
            action = "Do not trust immediately. Check trades, win rate, average return, and sample size."
            confidence = "LOW"

        elif change_type == "DROPPED_PATTERN":
            reason = "A previously top-ranked pattern dropped out of the top alpha list."
            action = "Check whether the pattern is decaying or only temporarily weaker."
            confidence = "MEDIUM"

        elif change_type in ["RANK_IMPROVED", "SCORE_JUMP"]:
            reason = "A pattern improved in rank or alpha score."
            action = "Check whether the improvement is supported by enough trades and stable memory."
            confidence = "MEDIUM"

        elif change_type in ["RANK_WEAKENED", "SCORE_DROP", "WINRATE_WEAKENED"]:
            reason = "A pattern weakened compared with the previous snapshot."
            action = "Mark it for review. Avoid giving high confidence until it stabilizes again."
            confidence = "MEDIUM"

    if signal_ctx:
        reason += (
            f" Latest signal context: PrimarySignal={signal_ctx.get('PrimarySignal')}, "
            f"MarketRegime={signal_ctx.get('MarketRegime')}, "
            f"FinalScore={signal_ctx.get('FinalScore')}."
        )

    if alpha_ctx:
        reason += (
            f" Alpha context: AlphaScore={alpha_ctx.get('AlphaScore')}, "
            f"WinRate={alpha_ctx.get('WinRate')}."
        )

    return reason, confidence, action


def build_summary(df: pd.DataFrame) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "MINI CUBE CHANGE EXPLANATION SUMMARY",
        f"Time: {now}",
        "",
        f"Total explained changes: {len(df)}",
        "",
    ]

    if df.empty:
        lines.append("No explained changes available.")
        return "\n".join(lines)

    for importance in ["CRITICAL", "IMPORTANT", "INFO"]:
        sub = df[df["Importance"] == importance]
        if sub.empty:
            continue

        lines.append(f"{importance}:")
        for _, row in sub.head(10).iterrows():
            lines.append(f"- {row['Category']} | {row['Item']} | {row['ChangeType']}")
            lines.append(f"  Reason: {row['Reason']}")
            lines.append(f"  Action: {row['SuggestedAction']}")
        lines.append("")

    return "\n".join(lines).strip()


def main():
    changes = read_csv(CHANGE_PATH)
    latest = read_csv(LATEST_SIGNALS_PATH)
    live = read_csv(LIVE_MATCHES_PATH)

    if changes.empty:
        print("No change_detection_results.csv found or file is empty.")
        return

    rows = []

    for _, row in changes.iterrows():
        item = str(row.get("Item", ""))

        signal_ctx = find_signal_context(item, latest)
        alpha_ctx = find_alpha_context(item, live)

        reason, confidence, action = explain_change(row, signal_ctx, alpha_ctx)

        rows.append({
            "Timestamp": row.get("Timestamp", ""),
            "Category": row.get("Category", ""),
            "Item": row.get("Item", ""),
            "ChangeType": row.get("ChangeType", ""),
            "OldValue": row.get("OldValue", ""),
            "NewValue": row.get("NewValue", ""),
            "Importance": row.get("Importance", ""),
            "Reason": reason,
            "Confidence": confidence,
            "SuggestedAction": action,
        })

    out = pd.DataFrame(rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    summary = build_summary(out)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    print("\n===================================")
    print(" MINI CUBE CHANGE EXPLANATION ENGINE")
    print("===================================\n")
    print(summary)
    print(f"\nSaved to {OUTPUT_PATH}")
    print(f"Saved to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()