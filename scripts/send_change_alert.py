import os
from pathlib import Path
import pandas as pd
import requests

CHANGE_RESULTS_PATH = Path("data/change_detection_results.csv")
CHANGE_ALERT_STATE_PATH = Path("data/change_alert_state.txt")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def send_telegram_message(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram env vars missing. Skipping change alert.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }

    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()
    print("Change alert sent.")


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
        print(f"No rows in: {path}")
        return None

    return df


def build_alert_key(df: pd.DataFrame) -> str:
    important = df[df["Importance"] == "IMPORTANT"].copy()

    if important.empty:
        return "NO_IMPORTANT_CHANGES"

    parts = []
    for _, row in important.head(10).iterrows():
        parts.append(
            f"{row['Category']}|{row['Item']}|{row['ChangeType']}|{row['OldValue']}|{row['NewValue']}"
        )

    return "\n".join(parts)


def load_previous_key() -> str:
    if not CHANGE_ALERT_STATE_PATH.exists():
        return ""
    try:
        return CHANGE_ALERT_STATE_PATH.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return ""


def save_current_key(key: str) -> None:
    CHANGE_ALERT_STATE_PATH.write_text(key, encoding="utf-8")


def build_message(df: pd.DataFrame) -> str:
    important = df[df["Importance"] == "IMPORTANT"].copy()

    if important.empty:
        return ""

    lines = []
    lines.append("MINI CUBE CHANGE ALERT")
    lines.append("")

    for _, row in important.head(8).iterrows():
        lines.append(
            f"[{row['Category']}] {row['Item']} | {row['ChangeType']}"
        )
        lines.append(f"{row['OldValue']} -> {row['NewValue']}")
        lines.append("")

    return "\n".join(lines).strip()


def main() -> None:
    df = safe_read_csv(CHANGE_RESULTS_PATH)
    if df is None:
        print("No change detection file available.")
        return

    if "Importance" not in df.columns:
        print("Missing Importance column.")
        return

    current_key = build_alert_key(df)
    previous_key = load_previous_key()

    if current_key == "NO_IMPORTANT_CHANGES":
        print("No important changes. No alert sent.")
        save_current_key(current_key)
        return

    if current_key == previous_key:
        print("Important changes already alerted. No duplicate alert sent.")
        return

    message = build_message(df)
    if not message:
        print("No message built. No alert sent.")
        return

    send_telegram_message(message)
    save_current_key(current_key)


if __name__ == "__main__":
    main()