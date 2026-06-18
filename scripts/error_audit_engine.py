from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

OUTPUT_PATH = DATA_DIR / "error_audit_report.csv"


def read_csv(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return None

    try:
        return pd.read_csv(path)
    except Exception:
        return None


def add_issue(rows, category, severity, issue, evidence, fix):
    rows.append({
        "Category": category,
        "Severity": severity,
        "Issue": issue,
        "Evidence": evidence,
        "SuggestedFix": fix,
    })


def check_pattern_key(rows):
    df = read_csv("all_stock_signals_with_context.csv")

    if df is None:
        df = read_csv("all_stock_signals.csv")

    if df is None:
        add_issue(
            rows,
            "Signals",
            "HIGH",
            "Signal pattern file missing or unreadable",
            "Missing all_stock_signals_with_context.csv and all_stock_signals.csv",
            "Run signal_engine.py and cross_asset_merge_engine.py first."
        )
        return

    if "CrossAssetPattern" in df.columns:
        return

    if "SignalSetup" in df.columns:
        return

    add_issue(
        rows,
        "Signals",
        "HIGH",
        "No Pattern System Found",
        "Missing CrossAssetPattern and SignalSetup",
        "Generate pattern fields before research."
    )
    return

    nan_pct = round(df["PatternKey"].isna().mean() * 100, 2)

    if nan_pct >= 90:
        add_issue(
            rows,
            "Signals",
            "HIGH",
            "PatternKey mostly empty",
            f"PatternKey NaN = {nan_pct}%",
            "Generate PatternKey properly or remove it from research logic."
        )


def check_latest_signal_nan(rows):
    df = read_csv("latest_stock_signals.csv")

    if df is None:
        add_issue(
            rows,
            "Signals",
            "HIGH",
            "latest_stock_signals.csv missing",
            "File not available",
            "Run signal_engine.py first."
        )
        return

    important_cols = [
        "Ticker",
        "PrimarySignal",
        "MarketRegime",
        "FinalScore",
    ]

    for col in important_cols:
        if col not in df.columns:
            add_issue(
                rows,
                "Signals",
                "HIGH",
                f"Important column missing: {col}",
                f"{col} not found in latest_stock_signals.csv",
                "Fix signal_engine.py output columns."
            )
            continue

        nan_count = int(df[col].isna().sum())

        if nan_count > 0:
            add_issue(
                rows,
                "Signals",
                "MEDIUM",
                f"NaN values in latest signals column: {col}",
                f"{nan_count} missing values",
                f"Fill or fix {col} before using latest signal snapshots."
            )


def check_knowledge_matches(rows):
    df = read_csv("research_knowledge_report.csv")

    if df is None:
        add_issue(
            rows,
            "Knowledge",
            "MEDIUM",
            "research_knowledge_report.csv missing",
            "File not available",
            "Run research_knowledge_engine.py."
        )
        return

    if "ConceptTitle" not in df.columns:
        add_issue(
            rows,
            "Knowledge",
            "MEDIUM",
            "ConceptTitle column missing",
            "Knowledge report has no ConceptTitle column",
            "Fix research_knowledge_engine.py output."
        )
        return

    missing = int(df["ConceptTitle"].isna().sum())
    total = len(df)

    if total > 0:
        missing_pct = round((missing / total) * 100, 2)

        if missing_pct > 50:
            add_issue(
                rows,
                "Knowledge",
                "MEDIUM",
                "Weak knowledge matching",
                f"{missing_pct}% of research questions have no concept match",
                "Improve keyword extraction or add more Wikipedia concepts."
            )


def check_sector_sample_size(rows):
    df = read_csv("sector_strength.csv")

    if df is None:
        add_issue(
            rows,
            "Sector",
            "MEDIUM",
            "sector_strength.csv missing",
            "File not available",
            "Run sector_strength_engine.py."
        )
        return

    if "StockCount" not in df.columns:
        add_issue(
            rows,
            "Sector",
            "MEDIUM",
            "StockCount column missing",
            "Cannot validate sector sample size",
            "Add StockCount to sector_strength_engine.py."
        )
        return

    weak = df[df["StockCount"] < 3]

    if not weak.empty:
        sectors = ", ".join(weak["Sector"].astype(str).tolist())

        add_issue(
            rows,
            "Sector",
            "MEDIUM",
            "Weak sector sample size",
            f"Sectors with less than 3 tickers: {sectors}",
            "Add more tickers per sector or mark these sectors as low confidence."
        )


def check_unknown_patterns(rows):
    files = [
        "signal_discovery_results.csv",
        "pattern_stability_results.csv",
        "confidence_score_results.csv",
        "alpha_ranking_results.csv",
    ]

    for filename in files:
        df = read_csv(filename)

        if df is None or df.empty:
            continue

        pattern_col = None

        for col in [
            "Pattern",
            "CrossAssetPattern",
            "SignalSetup",
            "PatternKey",
        ]:
            if col in df.columns:
                pattern_col = col
                break

        if not pattern_col:
            continue

        unknown_count = df[pattern_col].astype(str).str.contains("UNKNOWN", na=False).sum()
        total = len(df)

        if total > 0:
            unknown_pct = round((unknown_count / total) * 100, 2)

            if unknown_pct > 25:
                add_issue(
                    rows,
                    "Patterns",
                    "MEDIUM",
                    f"Many UNKNOWN parts in {filename}",
                    f"{unknown_pct}% of patterns contain UNKNOWN",
                    "Fix missing regime/context values before trusting pattern research."
                )


def check_pattern_sample_size(rows):
    files = [
        "signal_discovery_results.csv",
        "pattern_stability_results.csv",
        "confidence_score_results.csv",
        "alpha_ranking_results.csv",
    ]

    for filename in files:
        df = read_csv(filename)

        if df is None or df.empty:
            continue

        count_col = None

        for col in [

            "Count",
            "Occurrences",
            "SampleSize",
            "Trades",
            "Appearances",
            "AvgTrades",
        ]:
            if col in df.columns:
                count_col = col
                break

        if not count_col:
            add_issue(
                rows,
                "Patterns",
                "HIGH",
                f"Sample size column missing in {filename}",
                "No Count / Occurrences / SampleSize / Trades / Appearances column found"
                "Add sample size to pattern reports. Win rate without sample size is dangerous."
            )
            continue

        weak = df[df[count_col] < 30]

        if not weak.empty:
            add_issue(
                rows,
                "Patterns",
                "MEDIUM",
                f"Low-sample patterns in {filename}",
                f"{len(weak)} rows have {count_col} < 30",
                "Mark low-sample patterns as weak evidence."
            )


def check_trading_files(rows):
    trading_files = [
        "model_portfolio.csv",
        "portfolio_positions.csv",
        "paper_trades.csv",
        "trade_performance_summary.csv",
        "equity_curve.csv",
        "risk_analytics.csv",
    ]

    existing = []

    for filename in trading_files:
        if (DATA_DIR / filename).exists():
            existing.append(filename)

    if existing:
        add_issue(
            rows,
            "ResearchMode",
            "LOW",
            "Trading output files still exist",
            ", ".join(existing),
            "Keep them archived or remove trading engines from run_pipeline.py."
        )


def check_trading_scripts_in_pipeline(rows):
    pipeline_path = SCRIPTS_DIR / "run_pipeline.py"

    if not pipeline_path.exists():
        return

    text = pipeline_path.read_text()

    trading_scripts = [
        "portfolio_construction_engine.py",
        "portfolio_performance_tracker.py",
        "paper_trade_executor.py",
        "trade_performance_engine.py",
        "equity_curve_engine.py",
        "risk_analytics_engine.py",
    ]

    active = []

    for script in trading_scripts:
        if script in text:
            active.append(script)

    if active:
        add_issue(
            rows,
            "ResearchMode",
            "HIGH",
            "Trading scripts still referenced in pipeline",
            ", ".join(active),
            "Comment out trading scripts if the system is now research-only."
        )


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    check_pattern_key(rows)
    check_latest_signal_nan(rows)
    check_knowledge_matches(rows)
    check_sector_sample_size(rows)
    check_unknown_patterns(rows)
    check_pattern_sample_size(rows)
    check_trading_files(rows)
    check_trading_scripts_in_pipeline(rows)

    if not rows:
        rows.append({
            "Category": "System",
            "Severity": "OK",
            "Issue": "No major errors found",
            "Evidence": "All audit checks passed",
            "SuggestedFix": "Continue research."
        })

    report = pd.DataFrame(rows)

    severity_order = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
        "OK": 3,
    }

    report["SeverityRank"] = report["Severity"].map(severity_order).fillna(9)
    report = report.sort_values(["SeverityRank", "Category"]).drop(columns=["SeverityRank"])

    report.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE ERROR AUDIT REPORT")
    print("===================================\n")
    print(report.to_string(index=False))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()