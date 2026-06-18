from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_PATH = DATA_DIR / "research_questions.csv"


def safe_read(path: Path):
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def add_question(rows, category, question, reason, priority):
    rows.append({
        "Category": category,
        "ResearchQuestion": question,
        "Reason": reason,
        "Priority": priority,
    })


def main():
    rows = []

    signals = safe_read(DATA_DIR / "latest_stock_signals.csv")
    sector = safe_read(DATA_DIR / "sector_strength.csv")
    confidence = safe_read(DATA_DIR / "confidence_score_results.csv")
    market_state = safe_read(DATA_DIR / "market_state.csv")
    quality = safe_read(DATA_DIR / "data_quality_report.csv")

    if signals is not None and "FinalScore" in signals.columns:
        weak_count = len(signals[signals["FinalScore"] < 55])
        strong_count = len(signals[signals["FinalScore"] >= 55])

        add_question(
            rows,
            "Signal Quality",
            "Are high FinalScore signals actually producing better forward returns?",
            f"Strong signals: {strong_count}, weak signals: {weak_count}",
            "HIGH"
        )

    if sector is not None and not sector.empty:
        top_sector = sector.iloc[0]["Sector"]

        add_question(
            rows,
            "Sector Research",
            f"Is {top_sector} strength persistent or only a one-day spike?",
            "Sector strength can be noisy if based on few tickers.",
            "HIGH"
        )

    if confidence is not None and "ConfidenceScore" in confidence.columns:
        high_conf = len(confidence[confidence["ConfidenceScore"] > 50])

        add_question(
            rows,
            "Pattern Reliability",
            "Which high-confidence patterns survive across different market regimes?",
            f"High confidence patterns found: {high_conf}",
            "HIGH"
        )

    if market_state is not None and "MarketState" in market_state.columns:
        latest_state = market_state.iloc[-1]["MarketState"]

        add_question(
            rows,
            "Market Regime",
            f"Do signals work differently during {latest_state} market state?",
            "Same pattern may behave differently in BULL, BEAR, or TRANSITION markets.",
            "MEDIUM"
        )

    if quality is not None and "Status" in quality.columns:
        warnings = len(quality[quality["Status"] != "OK"])

        add_question(
            rows,
            "Data Quality",
            "Which files are causing unreliable research results?",
            f"Data quality warnings/errors found: {warnings}",
            "HIGH" if warnings > 0 else "LOW"
        )

    if not rows:
        add_question(
            rows,
            "System",
            "Is there enough clean data to begin research?",
            "No source files were available.",
            "HIGH"
        )

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE RESEARCH QUESTIONS")
    print("===================================\n")
    print(df.to_string(index=False))
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()