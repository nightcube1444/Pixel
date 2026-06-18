from pathlib import Path
import pandas as pd
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PATH = DATA_DIR / "research_report.txt"


def read_csv(name):
    path = DATA_DIR / name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def line(title=""):
    if title:
        return f"\n{title}\n" + "-" * len(title) + "\n"
    return "\n"


def top_rows(df, columns, n=5):
    if df is None or df.empty:
        return "No data available.\n"

    available = [c for c in columns if c in df.columns]
    if not available:
        return "Required columns missing.\n"

    return df[available].head(n).to_string(index=False) + "\n"


def main():
    market_state = read_csv("market_state.csv")
    data_quality = read_csv("data_quality_report.csv")
    nan_report = read_csv("nan_inspection_report.csv")
    questions = read_csv("research_questions.csv")
    knowledge = read_csv("research_knowledge_report.csv")
    discovery = read_csv("signal_discovery_results.csv")
    stability = read_csv("pattern_stability_results.csv")
    confidence = read_csv("confidence_score_results.csv")
    alpha = read_csv("alpha_ranking_results.csv")
    sector = read_csv("sector_strength.csv")
    signals = read_csv("latest_stock_signals.csv")

    report = []

    report.append("=" * 60)
    report.append("MINI CUBE RESEARCH REPORT")
    report.append("=" * 60)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append(line("1. MARKET STATE"))

    if market_state is not None and not market_state.empty:
        latest = market_state.iloc[-1]
        report.append(f"Market State: {latest.get('MarketState', 'UNKNOWN')}")
        report.append(f"SPY Regime: {latest.get('SPY_Regime', 'UNKNOWN')}")
        report.append(f"VIX State: {latest.get('VIX_State', 'UNKNOWN')}")
        report.append(f"Regime Shift: {latest.get('RegimeShiftFlag', 'UNKNOWN')}\n")
    else:
        report.append("No market state data available.\n")

    report.append(line("2. DATA QUALITY"))

    if data_quality is not None and not data_quality.empty:
        warnings = data_quality[data_quality["Status"] != "OK"] if "Status" in data_quality.columns else pd.DataFrame()
        report.append(f"Files checked: {len(data_quality)}")
        report.append(f"Warnings/errors: {len(warnings)}\n")
        report.append(top_rows(data_quality, ["File", "Rows", "SizeMB", "Status", "Issue"], 10))
    else:
        report.append("No data quality report available.\n")

    report.append(line("3. NAN / MISSING VALUE HOTSPOTS"))

    if nan_report is not None and not nan_report.empty:
        report.append(top_rows(nan_report, ["File", "Column", "NaNCount", "NaNPct", "Status"], 10))
    else:
        report.append("No NaN inspection report available.\n")

    report.append(line("4. RESEARCH QUESTIONS"))

    if questions is not None and not questions.empty:
        report.append(top_rows(questions, ["Category", "Priority", "ResearchQuestion", "Reason"], 10))
    else:
        report.append("No research questions available.\n")

    report.append(line("5. KNOWLEDGE CONTEXT"))

    if knowledge is not None and not knowledge.empty:
        report.append(top_rows(
            knowledge,
            ["Category", "Priority", "ConceptTitle", "Topic", "ResearchHint"],
            10
        ))
    else:
        report.append("No knowledge context available.\n")

    report.append(line("6. LATEST SIGNAL SNAPSHOT"))

    if signals is not None and not signals.empty:
        report.append(top_rows(
            signals.sort_values("FinalScore", ascending=False) if "FinalScore" in signals.columns else signals,
            ["Ticker", "PrimarySignal", "MarketRegime", "FinalScore"],
            10
        ))
    else:
        report.append("No latest signal data available.\n")

    report.append(line("7. SECTOR STRENGTH"))

    if sector is not None and not sector.empty:
        report.append(top_rows(
            sector,
            ["Sector", "AvgScore", "MaxScore", "MinScore", "StockCount", "TopTicker"],
            10
        ))

        if "StockCount" in sector.columns:
            weak_sector = sector[sector["StockCount"] < 3]
            if not weak_sector.empty:
                report.append("Warning: Some sectors have less than 3 tickers. Sector results may be noisy.\n")
    else:
        report.append("No sector strength data available.\n")

    report.append(line("8. PATTERN DISCOVERY"))

    if discovery is not None and not discovery.empty:
        report.append(top_rows(
            discovery,
            ["Rank", "Pattern", "Count", "WinRate10D", "AvgReturn10D"],
            10
        ))
    else:
        report.append("No pattern discovery results available.\n")

    report.append(line("9. PATTERN STABILITY"))

    if stability is not None and not stability.empty:
        report.append(top_rows(
            stability,
            ["StabilityRank", "Pattern", "Occurrences", "WinRate", "AvgReturn", "StabilityScore"],
            10
        ))
    else:
        report.append("No pattern stability results available.\n")

    report.append(line("10. CONFIDENCE SCORES"))

    if confidence is not None and not confidence.empty:
        report.append(top_rows(
            confidence,
            ["ConfidenceRank", "Pattern", "Occurrences", "WinRate", "AvgReturn", "ConfidenceScore"],
            10
        ))
    else:
        report.append("No confidence score results available.\n")

    report.append(line("11. ALPHA RANKING"))

    if alpha is not None and not alpha.empty:
        report.append(top_rows(
            alpha,
            ["AlphaRank", "Pattern", "Occurrences", "WinRate", "AvgReturn", "AlphaScore"],
            10
        ))
    else:
        report.append("No alpha ranking results available.\n")

    report.append(line("12. NEW RESEARCH IDEAS"))

    ideas = [
        "Test whether FinalScore above 55 beats FinalScore below 55 over 5D and 10D forward returns.",
        "Study momentum signals separately during VIX_ELEVATED and VIX_HIGH conditions.",
        "Check if sector strength persists for 3, 5, and 10 days.",
        "Compare BULL, BEAR, TENSE_BULL, and RISK_OFF_WARNING market states.",
        "Filter patterns with low occurrence count before trusting win rate.",
        "Investigate whether high AlphaScore patterns are overfitted or stable across time.",
        "Build a new signal for volatility contraction before breakout.",
        "Build a new signal for panic reversal after VIX spikes.",
        "Build a new signal for sector rotation leadership.",
        "Build a new signal for crypto-stock divergence.",
    ]

    for i, idea in enumerate(ideas, start=1):
        report.append(f"{i}. {idea}")

    report.append(line("13. BRUTAL TRUTH / WARNINGS"))

    warnings = [
        "This system is a research platform, not a reliable prediction machine yet.",
        "High win rate is meaningless without enough historical samples.",
        "Patterns can disappear after discovery because markets change.",
        "Missing pattern fields or malformed CrossAssetPattern values can poison research conclusions."
        "Sector results are weak when based on only one or two tickers.",
        "Do not use live outputs as trade instructions without deeper validation.",
        "Research quality matters more than number of engines.",
    ]

    for warning in warnings:
        report.append(f"- {warning}")

    text = "\n".join(report)

    OUTPUT_PATH.write_text(text)

    print("\n===================================")
    print(" MINI CUBE RESEARCH REPORT ENGINE")
    print("===================================\n")
    print(text[:3000])
    print("\n... report truncated in terminal ...")
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()