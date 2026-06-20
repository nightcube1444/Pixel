import subprocess
import time
import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

PYTHON = sys.executable
PERFORMANCE_LOG_PATH = BASE_DIR / "data/performance_log.csv"

 
mode = sys.argv[1] if len(sys.argv) > 1 else "research"

research_scripts = [

    # ==========================================
    # DATA COLLECTION
    # ==========================================
    "scripts/fetch_news.py",
    "scripts/news_engine.py",
    "scripts/download_data.py",

    # ==========================================
    # MARKET CONTEXT
    # ==========================================
    "scripts/benchmark_context_engine.py",
    "scripts/market_state_engine.py",

    # ==========================================
    # SIGNAL GENERATION
    # ==========================================
    "scripts/signal_engine.py",
    "scripts/signal_cleaner_engine.py",
    "scripts/sector_strength_engine.py",

    # ==========================================
    # DATA MERGE
    # ==========================================
    "scripts/merge_engine.py",
    "scripts/cross_asset_merge_engine.py",
    "scripts/cross_asset_pattern_recognition_engine.py",

    # ==========================================
    # FORWARD RETURNS
    # ==========================================
    "scripts/historical_forward_return_engine.py",
    "scripts/forward_validation.py",

    # ==========================================
    # PATTERN DISCOVERY
    # ==========================================
    "scripts/signal_discovery_engine.py",
    "scripts/update_market_memory.py",
    "scripts/pattern_stability_tracker.py",
    "scripts/confidence_score_engine.py",
    "scripts/alpha_ranking_engine.py",

    # ==========================================
    # REGIME INTELLIGENCE
    # ==========================================
    "scripts/regime_pattern_survival_engine_v2.py",
    "scripts/pattern_regime_generalization_engine.py",
    "scripts/institutional_pattern_registry.py",

    "scripts/sector_alpha_engine.py",
    "scripts/pattern_sector_matrix.py",
    "scripts/ticker_pattern_history_engine.py",
    "scripts/institutional_pattern_ticker_registry.py",

    # ==========================================
    # LIVE INSTITUTIONAL SCANNER
    # ==========================================
    "scripts/live_pattern_match_engine.py",
    "scripts/institutional_opportunity_engine.py",
    "scripts/institutional_recommendation_engine.py",

    # ==========================================
    # SNAPSHOTS / MEMORY
    # ==========================================
    "scripts/pattern_snapshot_engine.py",

    # ==========================================
    # CHANGE TRACKING
    # ==========================================
    "scripts/change_detection_engine.py",
    "scripts/change_explanation_engine.py",

    # ==========================================
    # QUALITY CONTROL
    # ==========================================
    "scripts/data_quality_engine.py",
    "scripts/nan_inspector_engine.py",
    "scripts/error_audit_engine.py",

    # ==========================================
    # RESEARCH LAYER
    # ==========================================
    "scripts/research_question_engine.py",
    "scripts/research_knowledge_engine.py",

    # ==========================================
    # WATCHLISTS
    # ==========================================
    "scripts/speculative_watchlist_engine.py",

    # ==========================================
    # REPORTING
    # ==========================================
    "scripts/research_report_engine.py",
]

trading_scripts = [

    "scripts/context_aware_recommendation_engine.py",
    "scripts/live_alpha_dashboard.py",
    "scripts/live_monitor.py",

    "scripts/portfolio_construction_engine.py",
    "scripts/portfolio_performance_tracker.py",

    "scripts/paper_trade_executor.py",
    "scripts/trade_performance_engine.py",

    "scripts/equity_curve_engine.py",
    "scripts/risk_analytics_engine.py",

    "scripts/daily_report_engine.py",

    "scripts/speculative_trade_journal_engine.py",
    "scripts/speculative_exit_tracker.py",
    "scripts/trade_signal_engine.py",
]

if mode == "research":
    scripts = research_scripts
elif mode == "trading":
    scripts = research_scripts + trading_scripts
else:
    print("Use: python3 scripts/run_pipeline.py research")
    print("Or:  python3 scripts/run_pipeline.py trading")
    sys.exit(1)
post_scripts = [
    #["/bin/bash", "scripts/auto_push.sh"],
    [PYTHON, "scripts/send_telegram_alert.py"],
    [PYTHON, "scripts/send_change_alert.py"],
    [PYTHON, "scripts/alert_engine.py"],
    
]


def ensure_performance_log() -> None:
    PERFORMANCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PERFORMANCE_LOG_PATH.exists():
        df = pd.DataFrame(columns=["Timestamp", "Task", "DurationSeconds", "Status"])
        df.to_csv(PERFORMANCE_LOG_PATH, index=False)


def append_performance(task: str, duration: float, status: str) -> None:
    ensure_performance_log()
    row = pd.DataFrame([{
        "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "Task": task,
        "DurationSeconds": round(duration, 2),
        "Status": status,
    }])
    row.to_csv(PERFORMANCE_LOG_PATH, mode="a", header=False, index=False)


def runtime_status(task: str, duration: float) -> str:

    # Heavy jobs
    if "download_data.py" in task:
        return "SLOW" if duration > 120 else "OK"

    if "fetch_news.py" in task:
        return "SLOW" if duration > 120 else "OK"

    if "signal_discovery_engine.py" in task:
        return "SLOW" if duration > 180 else "OK"

    if "alpha_ranking_engine.py" in task:
        return "SLOW" if duration > 180 else "OK"

    if "cross_asset_merge_engine.py" in task:
        return "SLOW" if duration > 120 else "OK"

    # Medium jobs
    if "paper_trade_executor.py" in task:
        return "SLOW" if duration > 30 else "OK"

    if "live_pattern_match_engine.py" in task:
        return "SLOW" if duration > 30 else "OK"

    if "context_aware_recommendation_engine.py" in task:
        return "SLOW" if duration > 30 else "OK"

    if "portfolio_construction_engine.py" in task:
        return "SLOW" if duration > 30 else "OK"

    if "daily_report_engine.py" in task:
        return "SLOW" if duration > 30 else "OK"

    # Fast jobs
    if "live_monitor.py" in task:
        return "SLOW" if duration > 20 else "OK"

    if "alert_engine.py" in task:
        return "SLOW" if duration > 20 else "OK"

    # Entire pipeline
    if "run_pipeline.py" in task:
        return "SLOW" if duration > 600 else "OK"

    return "OK"

    if duration > 300:
        return "CRITICAL"

    if duration > 120:
        return "SLOW"

    return "OK"


def run_command(command: list[str], timeout: int = 120) -> bool:
    name = " ".join(command)
    task_name = Path(command[-1]).name if command else "unknown_task"

    print(f"\n{'=' * 60}")
    print(f"Running: {name}")
    print(f"{'=' * 60}")

    start = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"TIMEOUT after {elapsed:.2f}s: {name}")
        append_performance(task_name, elapsed, "TIMEOUT")
        return False
    except Exception as e:
        elapsed = time.time() - start
        print(f"FAILED after {elapsed:.2f}s: {name}")
        print(f"Reason: {e}")
        append_performance(task_name, elapsed, "FAILED")
        return False

    elapsed = time.time() - start

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    print(f"Finished in {elapsed:.2f}s with return code {result.returncode}")

    status = runtime_status(task_name, elapsed)
    if result.returncode != 0:
        status = "FAILED"

    append_performance(task_name, elapsed, status)

    return result.returncode == 0


def main() -> None:
    ensure_performance_log()
    failures = []

    pipeline_start = time.time()

    for script in scripts:
        ok = run_command([PYTHON, script], timeout=180)
        if not ok:
            failures.append(script)

    for command in post_scripts:
        ok = run_command(command, timeout=120)
        if not ok:
            failures.append(" ".join(command))

    total_elapsed = time.time() - pipeline_start
    append_performance("run_pipeline.py", total_elapsed, runtime_status("run_pipeline.py", total_elapsed))

    print("\n" + "=" * 60)
    print("Pipeline finished.")
    if failures:
        print("Failures:")
        for item in failures:
            print(f" - {item}")
    else:
        print("All steps completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()