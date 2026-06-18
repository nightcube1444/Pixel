from datetime import datetime
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

LATEST_STOCK_SIGNALS_PATH = DATA_DIR / "latest_stock_signals.csv"
MARKET_DATA_PATH = DATA_DIR / "market_data.csv"
NEWS_DATA_PATH = DATA_DIR / "news_data.csv"
NEWS_SIGNALS_PATH = DATA_DIR / "news_signals.csv"
LIVE_MONITOR_SUMMARY_PATH = DATA_DIR / "live_monitor_summary.txt"
PERFORMANCE_LOG_PATH = DATA_DIR / "performance_log.csv"
OUTPUT_PATH = DATA_DIR / "failsafe_report.txt"

CRITICAL_FILES = [
    {"name": "latest_stock_signals", "path": LATEST_STOCK_SIGNALS_PATH, "max_age_minutes": 180},
    {"name": "market_data", "path": MARKET_DATA_PATH, "max_age_minutes": 360},
]

WARNING_FILES = [
    {"name": "news_data", "path": NEWS_DATA_PATH, "max_age_minutes": 180},
    {"name": "news_signals", "path": NEWS_SIGNALS_PATH, "max_age_minutes": 180},
    {"name": "live_monitor_summary", "path": LIVE_MONITOR_SUMMARY_PATH, "max_age_minutes": 15},
]


def file_age_minutes(path: Path) -> float | None:
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime)
    delta = datetime.now() - modified
    return round(delta.total_seconds() / 60, 2)


def is_csv_empty(path: Path) -> bool:
    if not path.exists():
        return True
    if path.stat().st_size == 0:
        return True

    try:
        df = pd.read_csv(path)
        return df.empty
    except Exception:
        return True


def is_text_empty(path: Path) -> bool:
    if not path.exists():
        return True
    if path.stat().st_size == 0:
        return True

    try:
        text = path.read_text(encoding="utf-8").strip()
        return text == ""
    except Exception:
        return True


def check_file(rule: dict, severity: str) -> list[str]:
    issues = []
    name = rule["name"]
    path = rule["path"]
    max_age = rule["max_age_minutes"]

    if not path.exists():
        issues.append(f"{severity}: {name} is missing.")
        return issues

    age = file_age_minutes(path)
    if age is not None and age > max_age:
        issues.append(f"{severity}: {name} is stale ({age} min old).")

    if path.suffix.lower() == ".csv":
        if is_csv_empty(path):
            issues.append(f"{severity}: {name} is empty or unreadable.")
    elif path.suffix.lower() == ".txt":
        if is_text_empty(path):
            issues.append(f"{severity}: {name} is empty or unreadable.")

    return issues


def load_recent_failures() -> list[str]:
    if not PERFORMANCE_LOG_PATH.exists():
        return ["WARNING: performance_log.csv is missing."]

    try:
        df = pd.read_csv(PERFORMANCE_LOG_PATH)
    except Exception:
        return ["WARNING: performance_log.csv could not be read."]

    if df.empty:
        return ["WARNING: performance_log.csv is empty."]

    needed = ["Timestamp", "Task", "Status"]
    for col in needed:
        if col not in df.columns:
            return [f"WARNING: performance_log.csv missing column {col}."]

    recent_failures = df[df["Status"].astype(str).str.upper().isin(["FAILED", "TIMEOUT"])]

    if recent_failures.empty:
        return []

    problems = []
    tail_rows = recent_failures.tail(5)
    for _, row in tail_rows.iterrows():
        problems.append(
            f"WARNING: Recent runtime issue in {row['Task']} at {row['Timestamp']} with status {row['Status']}."
        )
    return problems


def overall_status(issues: list[str]) -> str:
    if any(issue.startswith("CRITICAL:") for issue in issues):
        return "CRITICAL"
    if any(issue.startswith("WARNING:") for issue in issues):
        return "WARNING"
    return "HEALTHY"


def build_report(status: str, issues: list[str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "MINI CUBE FAILSAFE REPORT",
        f"Generated: {now}",
        f"Overall Status: {status}",
        "",
        "DETAILS",
    ]

    if not issues:
        lines.append("- No major failsafe issues detected.")
    else:
        for issue in issues:
            lines.append(f"- {issue}")

    lines.append("")
    lines.append("SAFE MODE DECISION")

    if status == "CRITICAL":
        lines.append("- Block non-essential alerts and treat system as unsafe.")
    elif status == "WARNING":
        lines.append("- Allow system to run, but review warnings carefully.")
    else:
        lines.append("- System looks safe to continue.")

    return "\n".join(lines)


def main() -> None:
    issues = []

    for rule in CRITICAL_FILES:
        issues.extend(check_file(rule, "CRITICAL"))

    for rule in WARNING_FILES:
        issues.extend(check_file(rule, "WARNING"))

    issues.extend(load_recent_failures())

    status = overall_status(issues)
    report = build_report(status, issues)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nSaved failsafe report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()