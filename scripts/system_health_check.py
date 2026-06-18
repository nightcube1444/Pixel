from datetime import datetime
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MARKET_DATA_PATH = DATA_DIR / "market_data.csv"
NEWS_DATA_PATH = DATA_DIR / "news_data.csv"
NEWS_SIGNALS_PATH = DATA_DIR / "news_signals.csv"
LATEST_STOCK_SIGNALS_PATH = DATA_DIR / "latest_stock_signals.csv"
ALL_STOCK_SIGNALS_PATH = DATA_DIR / "all_stock_signals.csv"
LIVE_MONITOR_SUMMARY_PATH = DATA_DIR / "live_monitor_summary.txt"
LIVE_MONITOR_LOG_PATH = DATA_DIR / "live_monitor_log.txt"
ALERT_ENGINE_LOG_PATH = DATA_DIR / "alert_engine_log.txt"
MINI_CUBE_STATE_LOG_PATH = DATA_DIR / "mini_cube_state_log.csv"
STATE_CHANGE_HISTORY_PATH = DATA_DIR / "state_change_history.csv"
STATE_REASON_HISTORY_PATH = DATA_DIR / "state_reason_history.csv"
PERFORMANCE_LOG_PATH = DATA_DIR / "performance_log.csv"
OUTPUT_PATH = DATA_DIR / "system_health_report.txt"


FILE_RULES = [
    {
        "name": "market_data",
        "path": MARKET_DATA_PATH,
        "role": "heartbeat",
        "max_age_minutes": 180,
        "size_warn_mb": 25,
        "missing_status": "CRITICAL",
    },
    {
        "name": "news_data",
        "path": NEWS_DATA_PATH,
        "role": "heartbeat",
        "max_age_minutes": 180,
        "size_warn_mb": 10,
        "missing_status": "WARNING",
    },
    {
        "name": "news_signals",
        "path": NEWS_SIGNALS_PATH,
        "role": "heartbeat",
        "max_age_minutes": 180,
        "size_warn_mb": 5,
        "missing_status": "WARNING",
    },
    {
        "name": "latest_stock_signals",
        "path": LATEST_STOCK_SIGNALS_PATH,
        "role": "heartbeat",
        "max_age_minutes": 60,
        "size_warn_mb": 10,
        "missing_status": "CRITICAL",
    },
    {
        "name": "live_monitor_summary",
        "path": LIVE_MONITOR_SUMMARY_PATH,
        "role": "heartbeat",
        "max_age_minutes": 15,
        "size_warn_mb": 2,
        "missing_status": "WARNING",
    },
    {
        "name": "live_monitor_log",
        "path": LIVE_MONITOR_LOG_PATH,
        "role": "heartbeat",
        "max_age_minutes": 15,
        "size_warn_mb": 10,
        "missing_status": "WARNING",
    },
    {
        "name": "alert_engine_log",
        "path": ALERT_ENGINE_LOG_PATH,
        "role": "heartbeat",
        "max_age_minutes": 15,
        "size_warn_mb": 10,
        "missing_status": "WARNING",
    },
    {
        "name": "state_change_history",
        "path": STATE_CHANGE_HISTORY_PATH,
        "role": "event",
        "max_age_minutes": None,
        "size_warn_mb": 10,
        "missing_status": "INFO",
    },
    {
        "name": "state_reason_history",
        "path": STATE_REASON_HISTORY_PATH,
        "role": "event",
        "max_age_minutes": None,
        "size_warn_mb": 10,
        "missing_status": "INFO",
    },
    {
        "name": "mini_cube_state_log",
        "path": MINI_CUBE_STATE_LOG_PATH,
        "role": "event",
        "max_age_minutes": None,
        "size_warn_mb": 10,
        "missing_status": "INFO",
    },
    {
        "name": "all_stock_signals",
        "path": ALL_STOCK_SIGNALS_PATH,
        "role": "archive",
        "max_age_minutes": None,
        "size_warn_mb": 50,
        "missing_status": "WARNING",
    },
    {
        "name": "performance_log",
        "path": PERFORMANCE_LOG_PATH,
        "role": "archive",
        "max_age_minutes": None,
        "size_warn_mb": 10,
        "missing_status": "WARNING",
    },
]


def file_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    return round(path.stat().st_size / (1024 * 1024), 2)


def file_age_minutes(path: Path) -> float | None:
    if not path.exists():
        return None
    modified_time = datetime.fromtimestamp(path.stat().st_mtime)
    age = datetime.now() - modified_time
    return round(age.total_seconds() / 60, 2)


def check_file(rule: dict) -> dict:
    name = rule["name"]
    path = rule["path"]
    role = rule["role"]
    max_age_minutes = rule["max_age_minutes"]
    size_warn_mb = rule["size_warn_mb"]
    missing_status = rule["missing_status"]

    if not path.exists():
        return {
            "name": name,
            "role": role,
            "status": missing_status,
            "freshness": "MISSING",
            "size_status": "UNKNOWN",
            "age_minutes": None,
            "size_mb": 0.0,
            "message": f"{name} is missing.",
        }

    size_mb = file_size_mb(path)
    age_minutes = file_age_minutes(path)

    if size_mb >= size_warn_mb:
        size_status = "OPTIMIZE"
    elif size_mb >= size_warn_mb * 0.7:
        size_status = "LARGE"
    else:
        size_status = "OK"

    # Heartbeat files: freshness matters a lot
    if role == "heartbeat":
        if age_minutes is None:
            freshness = "UNKNOWN"
            status = "WARNING"
            message = f"{name} age could not be determined."
        elif max_age_minutes is not None and age_minutes > max_age_minutes:
            freshness = "STALE"
            status = "CRITICAL" if missing_status == "CRITICAL" else "WARNING"
            message = f"{name} is stale ({age_minutes} min old)."
        else:
            freshness = "OK"
            status = "OK" if size_status == "OK" else "WARNING"
            if size_status == "OK":
                message = f"{name} is healthy."
            else:
                message = f"{name} is fresh, but file size should be reviewed."

    # Event files: do not punish them for not updating often
    elif role == "event":
        freshness = "EVENT_DRIVEN"
        if size_status == "OK":
            status = "OK"
            message = f"{name} is event-driven. No freshness check applied."
        else:
            status = "WARNING"
            message = f"{name} is event-driven, but file size should be reviewed."

    # Archive files: mostly size-watch files
    else:
        freshness = "N/A"
        if size_status == "OK":
            status = "OK"
            message = f"{name} archive file looks normal."
        else:
            status = "WARNING"
            message = f"{name} archive file is growing large."

    return {
        "name": name,
        "role": role,
        "status": status,
        "freshness": freshness,
        "size_status": size_status,
        "age_minutes": age_minutes,
        "size_mb": size_mb,
        "message": message,
    }


def load_performance_log() -> pd.DataFrame:
    if not PERFORMANCE_LOG_PATH.exists():
        return pd.DataFrame()

    try:
        df = pd.read_csv(PERFORMANCE_LOG_PATH)
    except Exception as e:
        print(f"Failed to read performance log: {e}")
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    required_cols = ["Timestamp", "Task", "DurationSeconds", "Status"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"performance_log.csv missing columns: {missing_cols}")
        return pd.DataFrame()

    return df.copy()


def get_latest_runtime_rows(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    working = df.copy()
    working["DurationSeconds"] = pd.to_numeric(working["DurationSeconds"], errors="coerce")
    working = working.dropna(subset=["Task", "DurationSeconds"])

    latest_rows = []
    for task in sorted(working["Task"].dropna().unique()):
        task_df = working[working["Task"] == task].copy()
        if task_df.empty:
            continue

        row = task_df.iloc[-1]
        duration = float(row["DurationSeconds"])
        latest_rows.append({
            "Task": task,
            "Timestamp": str(row["Timestamp"]),
            "DurationSeconds": round(duration, 2),
            "Status": str(row["Status"]),
        })

    return latest_rows


def build_report(file_results: list[dict], runtime_rows: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    heartbeat_results = [r for r in file_results if r["role"] == "heartbeat"]
    event_results = [r for r in file_results if r["role"] == "event"]
    archive_results = [r for r in file_results if r["role"] == "archive"]

    recommendations = []

    for r in file_results:
        if r["status"] in ["WARNING", "CRITICAL"]:
            recommendations.append(f"- {r['message']}")

    lines = [
        "MINI CUBE SYSTEM HEALTH REPORT",
        f"Generated: {now}",
        "",
        "HEARTBEAT FILES",
    ]

    for r in heartbeat_results:
        age_text = "N/A" if r["age_minutes"] is None else f"{r['age_minutes']} min"
        lines.append(
            f"- {r['name']}: Status={r['status']} | Freshness={r['freshness']} | "
            f"Age={age_text} | Size={r['size_mb']} MB | SizeStatus={r['size_status']}"
        )

    lines.append("")
    lines.append("EVENT FILES")

    for r in event_results:
        lines.append(
            f"- {r['name']}: Status={r['status']} | Freshness={r['freshness']} | "
            f"Size={r['size_mb']} MB | SizeStatus={r['size_status']}"
        )

    lines.append("")
    lines.append("ARCHIVE FILES")

    for r in archive_results:
        lines.append(
            f"- {r['name']}: Status={r['status']} | Freshness={r['freshness']} | "
            f"Size={r['size_mb']} MB | SizeStatus={r['size_status']}"
        )

    lines.append("")
    lines.append("LATEST RUNTIME STATUS")

    if not runtime_rows:
        lines.append("- No runtime data available.")
    else:
        for row in runtime_rows:
            lines.append(
                f"- {row['Task']}: Runtime={row['DurationSeconds']} sec | Status={row['Status']}"
            )

    lines.append("")
    lines.append("OPTIMIZATION RECOMMENDATIONS")

    if not recommendations:
        lines.append("- No major issues detected.")
    else:
        for item in recommendations:
            lines.append(item)

    return "\n".join(lines)


def main() -> None:
    file_results = [check_file(rule) for rule in FILE_RULES]

    perf_df = load_performance_log()
    runtime_rows = get_latest_runtime_rows(perf_df)

    report = build_report(file_results, runtime_rows)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    print(report)
    print(f"\nSaved system health report to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()