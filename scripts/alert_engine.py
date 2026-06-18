import os
from pathlib import Path
from datetime import datetime
import hashlib
import pandas as pd
import requests

# =====================================================
# Paths
# =====================================================
CHANGE_RESULTS_PATH = Path("data/change_detection_results.csv")
ALERT_MEMORY_PATH = Path("data/alert_memory.csv")
ALERT_SUMMARY_PATH = Path("data/alert_summary.txt")

STOCK_SOURCE_CANDIDATES = [
    Path("data/all_stock_signals_with_context.csv"),
    Path("data/all_stock_signals.csv"),
    Path("data/behavior_events.csv"),
]

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

MAX_TELEGRAM_MESSAGE_LENGTH = 3500


# =====================================================
# Helpers
# =====================================================
def safe_read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print(f"Missing file: {path}")
        return None

    if path.stat().st_size == 0:
        print(f"Empty file: {path}")
        return None

    try:
        df = pd.read_csv(path)
    except Exception as e:
        print(f"Failed reading {path}: {e}")
        return None

    if df.empty:
        print(f"No rows in file: {path}")
        return None

    return df


def send_telegram_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram env vars missing. Skipping alert.")
        return False

    if len(text) > MAX_TELEGRAM_MESSAGE_LENGTH:
        text = text[:MAX_TELEGRAM_MESSAGE_LENGTH] + "\n\n[truncated]"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }

    try:
        response = requests.post(url, data=payload, timeout=20)
        response.raise_for_status()
        print("Telegram alert sent.")
        return True
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False


def choose_pattern_column(df: pd.DataFrame) -> str | None:
    for col in ["StateAwarePattern", "CrossAssetPattern", "PatternBase", "SignalSetup", "Pattern"]:
        if col in df.columns:
            return col
    return None


def choose_ticker_column(df: pd.DataFrame) -> str | None:
    for col in ["Ticker", "ticker", "Symbol", "symbol", "Asset", "asset"]:
        if col in df.columns:
            return col
    return None


def load_stock_source() -> pd.DataFrame | None:
    for path in STOCK_SOURCE_CANDIDATES:
        df = safe_read_csv(path)
        if df is not None:
            print(f"Using stock source: {path}")
            return df

    print("No usable stock source found for ticker mapping.")
    return None


def build_pattern_to_tickers_map(stock_df: pd.DataFrame) -> dict[str, list[str]]:
    pattern_col = choose_pattern_column(stock_df)
    ticker_col = choose_ticker_column(stock_df)

    if pattern_col is None or ticker_col is None:
        print("Pattern or ticker column missing in stock source.")
        return {}

    df = stock_df.copy()
    df[pattern_col] = df[pattern_col].astype(str).str.strip()
    df[ticker_col] = df[ticker_col].astype(str).str.strip().str.upper()

    mapping = {}
    grouped = df.groupby(pattern_col)[ticker_col].apply(list)

    for pattern, tickers in grouped.items():
        seen = set()
        unique = []
        for ticker in tickers:
            if ticker and ticker not in seen:
                unique.append(ticker)
                seen.add(ticker)

        mapping[str(pattern)] = unique[:8]

    return mapping


def score_event(row: pd.Series) -> int:
    base = 0
    importance = str(row.get("Importance", "INFO")).upper()
    category = str(row.get("Category", "")).upper()
    change_type = str(row.get("ChangeType", "")).upper()

    if importance == "CRITICAL":
        base += 80
    elif importance == "IMPORTANT":
        base += 60
    else:
        base += 35

    if category == "MARKET_STATE":
        base += 10

    if "REGIME" in change_type:
        base += 10
    if "VOL" in change_type:
        base += 8
    if "FEAR" in change_type:
        base += 8
    if "HEADLINE_SURGE" in change_type:
        base += 6
    if "NEW_PATTERN" in change_type:
        base += 5
    if "SCORE_JUMP" in change_type:
        base += 7

    if category == "ALPHA":
        base += 5

    return min(base, 100)


def classify_level(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 60:
        return "IMPORTANT"
    return "INFO"


def build_reason(row: pd.Series) -> str:
    category = str(row.get("Category", "")).upper()
    change_type = str(row.get("ChangeType", "")).upper()
    old_value = str(row.get("OldValue", "")).strip()
    new_value = str(row.get("NewValue", "")).strip()

    if category == "MARKET_STATE":
        if "REGIME_FLIP" in change_type:
            return "Market regime changed meaningfully."
        if "VOL_SHIFT" in change_type:
            return "Volatility regime changed."
        if "MARKET_STATE_CHANGE" in change_type:
            return "Overall market state changed."
        if "FEAR_JUMP" in change_type:
            return "Fear score rose sharply."
        if "HEADLINE_SURGE" in change_type:
            return "Headline activity surged."
        if "REGIME_SHIFT_FLAGGED" in change_type:
            return "Regime shift flag was triggered."
        return f"Market state changed: {old_value} -> {new_value}"

    if category == "ALPHA":
        if "NEW_PATTERN" in change_type:
            return "A new pattern entered the ranked set."
        if "DROPPED_PATTERN" in change_type:
            return "A previously ranked pattern disappeared."
        if "RANK_IMPROVED" in change_type:
            return "Pattern rank improved versus the prior snapshot."
        if "RANK_WEAKENED" in change_type:
            return "Pattern rank weakened versus the prior snapshot."
        if "SCORE_JUMP" in change_type:
            return "Pattern score jumped meaningfully."
        if "SCORE_DROP" in change_type:
            return "Pattern score dropped meaningfully."
        return f"Alpha pattern changed: {old_value} -> {new_value}"

    return f"Change detected: {old_value} -> {new_value}"


def event_key(row: pd.Series) -> str:
    raw = "||".join([
        str(row.get("Category", "")),
        str(row.get("Item", "")),
        str(row.get("ChangeType", "")),
        str(row.get("OldValue", "")),
        str(row.get("NewValue", "")),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_alert_memory() -> pd.DataFrame:
    df = safe_read_csv(ALERT_MEMORY_PATH)
    if df is None:
        return pd.DataFrame(columns=["EventKey", "LastSentAt"])
    return df


def save_alert_memory(df: pd.DataFrame) -> None:
    ALERT_MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ALERT_MEMORY_PATH, index=False)


def filter_new_events(events_df: pd.DataFrame, memory_df: pd.DataFrame) -> pd.DataFrame:
    existing = set(memory_df["EventKey"].astype(str).tolist()) if not memory_df.empty else set()
    return events_df[~events_df["EventKey"].isin(existing)].copy()


def update_memory_with_sent(events_df: pd.DataFrame, memory_df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now().isoformat()

    new_rows = pd.DataFrame({
        "EventKey": events_df["EventKey"].astype(str),
        "LastSentAt": now,
    })

    merged = pd.concat([memory_df, new_rows], ignore_index=True)
    merged = merged.drop_duplicates(subset=["EventKey"], keep="last").reset_index(drop=True)
    return merged


def format_tickers(tickers: list[str]) -> str:
    if not tickers:
        return "N/A"
    return ", ".join(tickers[:5])


def build_grouped_message(events_df: pd.DataFrame, pattern_to_tickers: dict[str, list[str]]) -> str:
    if events_df.empty:
        return ""

    lines = [
        "MINI CUBE ALERT ENGINE",
        "",
    ]

    for level in ["CRITICAL", "IMPORTANT", "INFO"]:
        sub = events_df[events_df["AlertLevel"] == level].copy()
        if sub.empty:
            continue

        lines.append(level)
        lines.append("-" * len(level))

        for _, row in sub.head(6).iterrows():
            category = str(row["Category"])
            item = str(row["Item"])
            change_type = str(row["ChangeType"])
            score = int(row["AlertScore"])
            reason = str(row["Why"])
            tickers = pattern_to_tickers.get(item, [])

            lines.append(f"[{category}] {item}")
            lines.append(f"Type: {change_type}")
            lines.append(f"Score: {score}")
            if tickers:
                lines.append(f"Stocks: {format_tickers(tickers)}")
            lines.append(f"Why: {reason}")
            lines.append("")

    message = "\n".join(lines).strip()

    if len(message) > MAX_TELEGRAM_MESSAGE_LENGTH:
        message = message[:MAX_TELEGRAM_MESSAGE_LENGTH] + "\n\n[truncated]"

    return message


def main() -> None:
    changes_df = safe_read_csv(CHANGE_RESULTS_PATH)
    if changes_df is None:
        msg = "No change detection results found."
        ALERT_SUMMARY_PATH.write_text(msg, encoding="utf-8")
        print(msg)
        return

    required_cols = ["Category", "Item", "ChangeType", "OldValue", "NewValue", "Importance"]
    missing = [c for c in required_cols if c not in changes_df.columns]
    if missing:
        raise ValueError(f"Missing required columns in change_detection_results.csv: {missing}")

    stock_df = load_stock_source()
    pattern_to_tickers = build_pattern_to_tickers_map(stock_df) if stock_df is not None else {}

    df = changes_df.copy()
    df["EventKey"] = df.apply(event_key, axis=1)
    df["AlertScore"] = df.apply(score_event, axis=1)
    df["AlertLevel"] = df["AlertScore"].apply(classify_level)
    df["Why"] = df.apply(build_reason, axis=1)

    df = df[df["AlertLevel"].isin(["CRITICAL", "IMPORTANT", "INFO"])].copy()
    df = df[~((df["AlertLevel"] == "INFO") & (df["AlertScore"] < 40))].copy()

    memory_df = load_alert_memory()
    new_df = filter_new_events(df, memory_df)

    if new_df.empty:
        msg = "No new alert-worthy events. No Telegram alert sent."
        ALERT_SUMMARY_PATH.write_text(msg, encoding="utf-8")
        print(msg)
        return

    new_df = new_df.sort_values(
        by=["AlertScore", "Category", "Item"],
        ascending=[False, True, True]
    ).reset_index(drop=True)

    message = build_grouped_message(new_df, pattern_to_tickers)

    if not message:
        msg = "No grouped message created."
        ALERT_SUMMARY_PATH.write_text(msg, encoding="utf-8")
        print(msg)
        return

    ALERT_SUMMARY_PATH.write_text(message, encoding="utf-8")

    sent_ok = send_telegram_message(message)

    if sent_ok:
        memory_df = update_memory_with_sent(new_df, memory_df)
        save_alert_memory(memory_df)
        print("Alert engine sent grouped message.")
    else:
        print("Alert engine built message, but Telegram send failed. Memory not updated.")


if __name__ == "__main__":
    main()