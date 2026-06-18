import os
from pathlib import Path
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

SUMMARY_FILE = Path("data/research_summary.txt")


def send_message(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram env vars missing. Skipping alert.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }

    response = requests.post(url, data=payload, timeout=20)
    response.raise_for_status()
    print("Telegram alert sent.")


def build_message() -> str:
    if not SUMMARY_FILE.exists():
        return "Mini Cube: pipeline finished, but summary file was not found."

    text = SUMMARY_FILE.read_text(encoding="utf-8", errors="ignore").strip()

    if not text:
        return "Mini Cube: pipeline finished, but summary file was empty."

    lines = text.splitlines()

    # keep it short for Telegram
    short_text = "\n".join(lines[:12])

    return f"Mini Cube Update\n\n{short_text}"


if __name__ == "__main__":
    try:
        msg = build_message()
        send_message(msg)
    except Exception as e:
        print(f"Telegram alert failed: {e}")