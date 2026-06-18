from pathlib import Path
from datetime import datetime
import pandas as pd

CURRENT_ALPHA_PATH = Path("data/alpha_ranking_results.csv")
CURRENT_MARKET_STATE_PATH = Path("data/market_state.csv")

PREV_ALPHA_SNAPSHOT_PATH = Path("data/prev_alpha_ranking_results.csv")
PREV_MARKET_STATE_SNAPSHOT_PATH = Path("data/prev_market_state.csv")

OUTPUT_PATH = Path("data/change_detection_results.csv")
SUMMARY_PATH = Path("data/change_detection_summary.txt")


def safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if path.stat().st_size == 0:
        return None
    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return None
    if df.empty:
        return None
    return df


def normalize_alpha(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "Pattern" not in out.columns:
        raise ValueError("alpha_ranking_results.csv must contain 'Pattern' column")

    for col in ["AlphaRank", "AlphaScore", "WinRate", "Trades"]:
        if col not in out.columns:
            out[col] = None

    out["Pattern"] = out["Pattern"].astype(str).str.strip()
    out["AlphaRank"] = pd.to_numeric(out["AlphaRank"], errors="coerce")
    out["AlphaScore"] = pd.to_numeric(out["AlphaScore"], errors="coerce")
    out["WinRate"] = pd.to_numeric(out["WinRate"], errors="coerce")
    out["Trades"] = pd.to_numeric(out["Trades"], errors="coerce")

    out = out[["Pattern", "AlphaRank", "AlphaScore", "WinRate", "Trades"]].copy()
    out = out.sort_values(by=["AlphaRank", "AlphaScore"], ascending=[True, False], na_position="last")
    out = out.reset_index(drop=True)

    return out


def normalize_market_state(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    required = ["Date", "SPY_Regime", "VIX_State", "FearScore", "PositiveScore", "HeadlineCount", "MarketState"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"market_state.csv missing required columns: {missing}")

    if "PrevMarketState" not in out.columns:
        out["PrevMarketState"] = None
    if "RegimeShiftFlag" not in out.columns:
        out["RegimeShiftFlag"] = False

    out["Date"] = out["Date"].astype(str).str.strip()
    out["SPY_Regime"] = out["SPY_Regime"].astype(str).str.strip().str.upper()
    out["VIX_State"] = out["VIX_State"].astype(str).str.strip().str.upper()
    out["MarketState"] = out["MarketState"].astype(str).str.strip().str.upper()
    out["PrevMarketState"] = out["PrevMarketState"].astype(str).str.strip().str.upper()

    out["FearScore"] = pd.to_numeric(out["FearScore"], errors="coerce").fillna(0.0)
    out["PositiveScore"] = pd.to_numeric(out["PositiveScore"], errors="coerce").fillna(0.0)
    out["HeadlineCount"] = pd.to_numeric(out["HeadlineCount"], errors="coerce").fillna(0.0)

    out["RegimeShiftFlag"] = out["RegimeShiftFlag"].astype(str).str.strip().str.lower()

    out = out[
        [
            "Date",
            "SPY_Regime",
            "VIX_State",
            "FearScore",
            "PositiveScore",
            "HeadlineCount",
            "MarketState",
            "PrevMarketState",
            "RegimeShiftFlag",
        ]
    ].copy()

    out = out.reset_index(drop=True)
    return out


def make_event(category: str, item: str, change_type: str, old_value: str, new_value: str, importance: str) -> dict:
    return {
        "Timestamp": datetime.now().isoformat(),
        "Category": category,
        "Item": item,
        "ChangeType": change_type,
        "OldValue": old_value,
        "NewValue": new_value,
        "Importance": importance,
    }


def compare_alpha(current_df: pd.DataFrame, prev_df: pd.DataFrame | None) -> list[dict]:
    events = []

    current_top = current_df.copy()
    prev_top = prev_df.copy() if prev_df is not None else None

    # Limit noise: only compare top ranked patterns
    current_top = current_top[current_top["AlphaRank"].fillna(999999) <= 20].copy()
    if prev_top is not None:
        prev_top = prev_top[prev_top["AlphaRank"].fillna(999999) <= 20].copy()

    current_map = {row["Pattern"]: row for _, row in current_top.iterrows()}
    prev_map = {} if prev_top is None else {row["Pattern"]: row for _, row in prev_top.iterrows()}

    current_patterns = set(current_map.keys())
    prev_patterns = set(prev_map.keys())

    new_patterns = current_patterns - prev_patterns
    dropped_patterns = prev_patterns - current_patterns
    shared_patterns = current_patterns & prev_patterns

    for pattern in sorted(new_patterns):
        row = current_map[pattern]
        events.append(make_event(
            "ALPHA",
            pattern,
            "NEW_PATTERN",
            "",
            f"Rank={row['AlphaRank']}, Score={row['AlphaScore']}",
            "IMPORTANT"
        ))

    for pattern in sorted(dropped_patterns):
        row = prev_map[pattern]
        events.append(make_event(
            "ALPHA",
            pattern,
            "DROPPED_PATTERN",
            f"Rank={row['AlphaRank']}, Score={row['AlphaScore']}",
            "",
            "IMPORTANT"
        ))

    for pattern in sorted(shared_patterns):
        old = prev_map[pattern]
        new = current_map[pattern]

        old_rank = old["AlphaRank"]
        new_rank = new["AlphaRank"]
        old_score = old["AlphaScore"]
        new_score = new["AlphaScore"]
        old_win = old["WinRate"]
        new_win = new["WinRate"]

        if pd.notna(old_rank) and pd.notna(new_rank):
            rank_diff = old_rank - new_rank
            if rank_diff >= 5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "RANK_IMPROVED",
                    f"Rank={int(old_rank)}",
                    f"Rank={int(new_rank)}",
                    "IMPORTANT"
                ))
            elif rank_diff <= -5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "RANK_WEAKENED",
                    f"Rank={int(old_rank)}",
                    f"Rank={int(new_rank)}",
                    "INFO"
                ))

        if pd.notna(old_score) and pd.notna(new_score):
            score_diff = new_score - old_score
            if score_diff >= 1.5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "SCORE_JUMP",
                    f"Score={old_score:.3f}",
                    f"Score={new_score:.3f}",
                    "IMPORTANT"
                ))
            elif score_diff <= -1.5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "SCORE_DROP",
                    f"Score={old_score:.3f}",
                    f"Score={new_score:.3f}",
                    "INFO"
                ))

        if pd.notna(old_win) and pd.notna(new_win):
            win_diff = new_win - old_win
            if win_diff >= 5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "WINRATE_IMPROVED",
                    f"WinRate={old_win:.2f}",
                    f"WinRate={new_win:.2f}",
                    "INFO"
                ))
            elif win_diff <= -5:
                events.append(make_event(
                    "ALPHA",
                    pattern,
                    "WINRATE_WEAKENED",
                    f"WinRate={old_win:.2f}",
                    f"WinRate={new_win:.2f}",
                    "INFO"
                ))

    return events


def compare_market_state(current_df: pd.DataFrame, prev_snapshot_df: pd.DataFrame | None) -> list[dict]:
    events = []

    if len(current_df) < 2 and (prev_snapshot_df is None or prev_snapshot_df.empty):
        return events

    # Prefer comparing current latest row vs previous snapshot latest row
    if prev_snapshot_df is not None and not prev_snapshot_df.empty:
        prev_row = prev_snapshot_df.iloc[-1]
        curr_row = current_df.iloc[-1]
    else:
        prev_row = current_df.iloc[-2]
        curr_row = current_df.iloc[-1]

    # Regime changes
    if str(prev_row["SPY_Regime"]) != str(curr_row["SPY_Regime"]):
        importance = "CRITICAL" if (
            ("BULL" in str(prev_row["SPY_Regime"]) and "BEAR" in str(curr_row["SPY_Regime"])) or
            ("BEAR" in str(prev_row["SPY_Regime"]) and "BULL" in str(curr_row["SPY_Regime"]))
        ) else "IMPORTANT"

        events.append(make_event(
            "MARKET_STATE",
            "SPY_Regime",
            "REGIME_FLIP",
            str(prev_row["SPY_Regime"]),
            str(curr_row["SPY_Regime"]),
            importance
        ))

    # VIX state changes
    if str(prev_row["VIX_State"]) != str(curr_row["VIX_State"]):
        importance = "CRITICAL" if (
            "EXTREME" in str(curr_row["VIX_State"]) or "HIGH" in str(curr_row["VIX_State"])
        ) else "IMPORTANT"

        events.append(make_event(
            "MARKET_STATE",
            "VIX_State",
            "VOL_SHIFT",
            str(prev_row["VIX_State"]),
            str(curr_row["VIX_State"]),
            importance
        ))

    # Market state changes
    if str(prev_row["MarketState"]) != str(curr_row["MarketState"]):
        events.append(make_event(
            "MARKET_STATE",
            "MarketState",
            "MARKET_STATE_CHANGE",
            str(prev_row["MarketState"]),
            str(curr_row["MarketState"]),
            "IMPORTANT"
        ))

    # Fear score change
    fear_diff = float(curr_row["FearScore"]) - float(prev_row["FearScore"])
    if abs(fear_diff) >= 0.25:
        events.append(make_event(
            "MARKET_STATE",
            "FearScore",
            "FEAR_CHANGE",
            f"{float(prev_row['FearScore']):.2f}",
            f"{float(curr_row['FearScore']):.2f}",
            "IMPORTANT" if fear_diff > 0 else "INFO"
        ))

    # Positive score change
    pos_diff = float(curr_row["PositiveScore"]) - float(prev_row["PositiveScore"])
    if abs(pos_diff) >= 0.25:
        events.append(make_event(
            "MARKET_STATE",
            "PositiveScore",
            "POSITIVE_CHANGE",
            f"{float(prev_row['PositiveScore']):.2f}",
            f"{float(curr_row['PositiveScore']):.2f}",
            "INFO" if pos_diff > 0 else "IMPORTANT"
        ))

    # Headline count change
    headline_diff = float(curr_row["HeadlineCount"]) - float(prev_row["HeadlineCount"])
    if abs(headline_diff) >= 3:
        events.append(make_event(
            "MARKET_STATE",
            "HeadlineCount",
            "HEADLINE_COUNT_CHANGE",
            f"{float(prev_row['HeadlineCount']):.0f}",
            f"{float(curr_row['HeadlineCount']):.0f}",
            "IMPORTANT"
        ))

    # Regime shift flag
    curr_flag = str(curr_row["RegimeShiftFlag"]).strip().lower()
    prev_flag = str(prev_row["RegimeShiftFlag"]).strip().lower()

    if curr_flag in ["true", "1", "yes"] and prev_flag not in ["true", "1", "yes"]:
        events.append(make_event(
            "MARKET_STATE",
            "RegimeShiftFlag",
            "REGIME_SHIFT_FLAGGED",
            str(prev_row["RegimeShiftFlag"]),
            str(curr_row["RegimeShiftFlag"]),
            "CRITICAL"
        ))

    return events


def add_baseline_if_empty(events_df: pd.DataFrame, current_market: pd.DataFrame) -> pd.DataFrame:
    if not events_df.empty:
        return events_df

    last_row = current_market.iloc[-1]

    baseline = pd.DataFrame([make_event(
        "MARKET_STATE",
        "MarketState",
        "BASELINE_MONITOR",
        str(last_row.get("PrevMarketState", "UNKNOWN")),
        str(last_row.get("MarketState", "UNKNOWN")),
        "INFO"
    )])

    return baseline


def build_summary(events_df: pd.DataFrame) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if events_df.empty:
        return f"CHANGE DETECTION SUMMARY\nTime: {now}\n\nNo changes detected."

    critical = events_df[events_df["Importance"] == "CRITICAL"]
    important = events_df[events_df["Importance"] == "IMPORTANT"]
    info = events_df[events_df["Importance"] == "INFO"]

    lines = [
        "CHANGE DETECTION SUMMARY",
        f"Time: {now}",
        "",
        f"Critical changes: {len(critical)}",
        f"Important changes: {len(important)}",
        f"Info changes: {len(info)}",
        "",
    ]

    for label in ["CRITICAL", "IMPORTANT", "INFO"]:
        sub = events_df[events_df["Importance"] == label]
        if sub.empty:
            continue
        lines.append(f"{label}:")
        for _, row in sub.head(10).iterrows():
            lines.append(
                f"[{label}] {row['Category']} | {row['Item']} | {row['ChangeType']} | "
                f"{row['OldValue']} -> {row['NewValue']}"
            )
        lines.append("")

    return "\n".join(lines).strip()


def save_snapshots(current_alpha: pd.DataFrame, current_market: pd.DataFrame) -> None:
    current_alpha.to_csv(PREV_ALPHA_SNAPSHOT_PATH, index=False)
    current_market.to_csv(PREV_MARKET_STATE_SNAPSHOT_PATH, index=False)


def main() -> None:
    current_alpha_raw = safe_read_csv(CURRENT_ALPHA_PATH)
    current_market_raw = safe_read_csv(CURRENT_MARKET_STATE_PATH)

    if current_alpha_raw is None:
        print(f"Missing or empty: {CURRENT_ALPHA_PATH}")
        return

    if current_market_raw is None:
        print(f"Missing or empty: {CURRENT_MARKET_STATE_PATH}")
        return

    current_alpha = normalize_alpha(current_alpha_raw)
    current_market = normalize_market_state(current_market_raw)

    prev_alpha_raw = safe_read_csv(PREV_ALPHA_SNAPSHOT_PATH)
    prev_market_raw = safe_read_csv(PREV_MARKET_STATE_SNAPSHOT_PATH)

    prev_alpha = normalize_alpha(prev_alpha_raw) if prev_alpha_raw is not None else None
    prev_market = normalize_market_state(prev_market_raw) if prev_market_raw is not None else None

    alpha_events = compare_alpha(current_alpha, prev_alpha)
    market_events = compare_market_state(current_market, prev_market)

    all_events = alpha_events + market_events
    events_df = pd.DataFrame(all_events)

    if events_df.empty:
        events_df = pd.DataFrame(columns=[
            "Timestamp", "Category", "Item", "ChangeType",
            "OldValue", "NewValue", "Importance"
        ])

    events_df = add_baseline_if_empty(events_df, current_market)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    events_df.to_csv(OUTPUT_PATH, index=False)

    summary = build_summary(events_df)
    SUMMARY_PATH.write_text(summary, encoding="utf-8")

    save_snapshots(current_alpha, current_market)

    print(f"Saved change detection results to {OUTPUT_PATH}")
    print(f"Saved change detection summary to {SUMMARY_PATH}")
    print(summary)


if __name__ == "__main__":
    main()