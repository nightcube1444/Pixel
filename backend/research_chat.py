from pathlib import Path
import pandas as pd
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "knowledge.db"


def read_csv(name):
    path = DATA_DIR / name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def knowledge_search(query):
    if not DB_PATH.exists():
        return "Knowledge database not found."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    pattern = f"%{query.lower()}%"

    cursor.execute(
        """
        SELECT c.title, t.name, c.wiki_summary
        FROM concepts c
        JOIN topics t ON c.topic_id = t.id
        WHERE lower(c.title) LIKE ?
           OR lower(c.wiki_summary) LIKE ?
           OR lower(t.name) LIKE ?
        LIMIT 5
        """,
        (pattern, pattern, pattern),
    )

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No knowledge match found."

    answer = []
    for title, topic, summary in rows:
        answer.append(f"- {title} ({topic}): {str(summary)[:250]}...")

    return "\n".join(answer)


def strongest_sector():
    df = read_csv("sector_strength.csv")

    if df is None or df.empty:
        return "sector_strength.csv not found. Run sector_strength_engine.py first."

    top = df.iloc[0]

    warning = ""
    if "StockCount" in df.columns and top["StockCount"] < 3:
        warning = "\nWarning: sector confidence is LOW because it has less than 3 tickers."

    return (
        f"Strongest sector: {top.get('Sector')}\n"
        f"AvgScore: {top.get('AvgScore')}\n"
        f"TopTicker: {top.get('TopTicker')}\n"
        f"StockCount: {top.get('StockCount')}"
        f"{warning}"
    )


def market_state():
    df = read_csv("market_state.csv")

    if df is None or df.empty:
        return "market_state.csv not found. Run market_state_engine.py first."

    latest = df.iloc[-1]

    return (
        f"Market State: {latest.get('MarketState', 'UNKNOWN')}\n"
        f"SPY Regime: {latest.get('SPY_Regime', 'UNKNOWN')}\n"
        f"VIX State: {latest.get('VIX_State', 'UNKNOWN')}\n"
        f"Regime Shift: {latest.get('RegimeShiftFlag', 'UNKNOWN')}"
    )


def top_patterns():
    df = read_csv("alpha_ranking_results.csv")

    if df is None or df.empty:
        return "alpha_ranking_results.csv not found."

    cols = [c for c in ["AlphaRank", "Pattern", "WinRate", "AvgReturn", "AlphaScore"] if c in df.columns]

    return df[cols].head(10).to_string(index=False)


def errors():
    df = read_csv("error_audit_report.csv")

    if df is None or df.empty:
        return "error_audit_report.csv not found. Run error_audit_engine.py first."

    high = df[df["Severity"] == "HIGH"] if "Severity" in df.columns else df

    if high.empty:
        return "No HIGH errors found."

    return high.to_string(index=False)


def research_questions():
    df = read_csv("research_questions.csv")

    if df is None or df.empty:
        return "research_questions.csv not found."

    cols = [c for c in ["Category", "Priority", "ResearchQuestion"] if c in df.columns]

    return df[cols].to_string(index=False)


def latest_signals():
    df = read_csv("latest_stock_signals.csv")

    if df is None or df.empty:
        return "latest_stock_signals.csv not found."

    if "FinalScore" in df.columns:
        df = df.sort_values("FinalScore", ascending=False)

    cols = [c for c in ["Ticker", "PrimarySignal", "MarketRegime", "FinalScore"] if c in df.columns]

    return df[cols].head(15).to_string(index=False)


def help_text():
    return """
Ask me things like:

- market state
- strongest sector
- latest signals
- top patterns
- errors
- research questions
- explain inflation
- explain volatility
- explain SpaceX
- explain sector rotation
- help
- exit
"""

def full_report_summary():
    path = DATA_DIR / "research_report.txt"

    if not path.exists():
        return "research_report.txt not found. Run research_report_engine.py first."

    text = path.read_text()

    sections = [
        "MARKET STATE",
        "DATA QUALITY",
        "RESEARCH QUESTIONS",
        "PATTERN DISCOVERY",
        "PATTERN STABILITY",
        "ALPHA RANKING",
        "BRUTAL TRUTH",
    ]

    output = ["Research Report Summary\n"]

    for section in sections:
        idx = text.upper().find(section)

        if idx == -1:
            continue

        snippet = text[idx:idx + 700]
        output.append(f"\n--- {section} ---")
        output.append(snippet[:700])

    return "\n".join(output)


def find_problems():
    df = read_csv("error_audit_report.csv")

    if df is None or df.empty:
        return "error_audit_report.csv not found. Run error_audit_engine.py first."

    output = []

    high = df[df["Severity"] == "HIGH"] if "Severity" in df.columns else pd.DataFrame()
    medium = df[df["Severity"] == "MEDIUM"] if "Severity" in df.columns else pd.DataFrame()

    output.append("Mini Cube Problem Audit\n")
    output.append(f"HIGH issues: {len(high)}")
    output.append(f"MEDIUM issues: {len(medium)}\n")

    if not high.empty:
        output.append("HIGH PRIORITY")
        for _, row in high.iterrows():
            output.append(f"- {row.get('Issue')}")
            output.append(f"  Evidence: {row.get('Evidence')}")
            output.append(f"  Fix: {row.get('SuggestedFix')}")

    if not medium.empty:
        output.append("\nMEDIUM PRIORITY")
        for _, row in medium.head(5).iterrows():
            output.append(f"- {row.get('Issue')}")
            output.append(f"  Fix: {row.get('SuggestedFix')}")

    return "\n".join(output)


def next_research():
    q = read_csv("research_questions.csv")
    e = read_csv("error_audit_report.csv")

    output = ["Next Research Priorities\n"]

    if e is not None and not e.empty and "Severity" in e.columns:
        high = e[e["Severity"] == "HIGH"]
        if not high.empty:
            output.append("Fix these system problems first:")
            for _, row in high.head(5).iterrows():
                output.append(f"- {row.get('Issue')}")
                output.append(f"  Fix: {row.get('SuggestedFix')}")
            output.append("")

    if q is not None and not q.empty:
        output.append("Research questions to study:")
        for _, row in q.head(5).iterrows():
            output.append(f"- [{row.get('Priority')}] {row.get('ResearchQuestion')}")

    return "\n".join(output)


def why_sector(sector_name):
    df = read_csv("latest_stock_signals.csv")

    if df is None or df.empty:
        return "latest_stock_signals.csv not found."

    universe_path = BASE_DIR / "config" / "asset_universe.csv"

    if not universe_path.exists():
        return "config/asset_universe.csv not found."

    universe = pd.read_csv(universe_path)

    if "Ticker" not in universe.columns or "Sector" not in universe.columns:
        return "asset_universe.csv must have Ticker and Sector columns."

    df["TickerClean"] = df["Ticker"].astype(str).str.replace(".NS", "", regex=False)
    universe["TickerClean"] = universe["Ticker"].astype(str).str.replace(".NS", "", regex=False)

    merged = df.merge(
        universe[["TickerClean", "Sector"]],
        on="TickerClean",
        how="left"
    )

    sector_rows = merged[
        merged["Sector"].astype(str).str.lower() == sector_name.lower()
    ]

    if sector_rows.empty:
        return f"No latest signals found for sector: {sector_name}"

    if "FinalScore" in sector_rows.columns:
        sector_rows = sector_rows.sort_values("FinalScore", ascending=False)

    cols = [c for c in ["Ticker", "PrimarySignal", "MarketRegime", "FinalScore"] if c in sector_rows.columns]

    avg_score = round(sector_rows["FinalScore"].mean(), 2) if "FinalScore" in sector_rows.columns else "UNKNOWN"

    return (
        f"{sector_name.upper()} sector analysis\n"
        f"Average Score: {avg_score}\n"
        f"Stocks found: {len(sector_rows)}\n\n"
        + sector_rows[cols].to_string(index=False)
    )

def research_signal_quality():
    df = read_csv("all_stock_signals.csv")

    if df is None or df.empty:
        return "all_stock_signals.csv not found."

    needed = ["FinalScore"]
    for col in needed:
        if col not in df.columns:
            return f"Missing column: {col}"

    forward_cols = [c for c in ["Return5D", "Return10D", "ForwardReturn5D", "ForwardReturn10D"] if c in df.columns]

    if not forward_cols:
        return (
            "No forward return columns found.\n"
            "Run forward_validation.py or update it to attach 5D/10D returns to all_stock_signals.csv."
        )

    return_col = forward_cols[-1]

    strong = df[df["FinalScore"] >= 55]
    weak = df[df["FinalScore"] < 30]

    def summarize(part, label):
        clean = part.dropna(subset=[return_col])
        if clean.empty:
            return f"{label}: no valid forward return data."

        win_rate = round((clean[return_col] > 0).mean() * 100, 2)
        avg_return = round(clean[return_col].mean(), 3)

        return (
            f"{label}\n"
            f"Samples: {len(clean)}\n"
            f"WinRate: {win_rate}%\n"
            f"AvgReturn: {avg_return}%\n"
        )

    return (
        "Signal Quality Research\n\n"
        + summarize(strong, "Strong signals FinalScore >= 55")
        + "\n"
        + summarize(weak, "Weak signals FinalScore < 30")
    )


def research_patterns():
    df = read_csv("alpha_ranking_results.csv")

    if df is None or df.empty:
        return "alpha_ranking_results.csv not found."

    cols = [c for c in ["AlphaRank", "Pattern", "Trades", "WinRate", "AvgReturn", "AlphaScore"] if c in df.columns]

    if not cols:
        return "No useful pattern columns found."

    output = ["Pattern Research Evidence\n"]

    output.append(df[cols].head(10).to_string(index=False))

    if "Trades" in df.columns:
        weak = df[df["Trades"] < 30]
        output.append(f"\nLow-sample warning: {len(weak)} patterns have Trades < 30.")

    return "\n".join(output)


def research_market_states():
    df = read_csv("market_state.csv")

    if df is None or df.empty:
        return "market_state.csv not found."

    if "MarketState" not in df.columns:
        return "MarketState column missing."

    counts = df["MarketState"].value_counts().reset_index()
    counts.columns = ["MarketState", "Days"]

    output = ["Market State Research\n"]
    output.append(counts.to_string(index=False))

    latest = df.iloc[-1]
    output.append("\nCurrent:")
    output.append(f"MarketState: {latest.get('MarketState', 'UNKNOWN')}")
    output.append(f"SPY_Regime: {latest.get('SPY_Regime', 'UNKNOWN')}")
    output.append(f"VIX_State: {latest.get('VIX_State', 'UNKNOWN')}")

    return "\n".join(output)


def research_sectors():
    df = read_csv("sector_strength.csv")

    if df is None or df.empty:
        return "sector_strength.csv not found."

    cols = [c for c in ["Sector", "AvgScore", "MaxScore", "MinScore", "StockCount", "TopTicker"] if c in df.columns]

    output = ["Sector Research Evidence\n"]
    output.append(df[cols].to_string(index=False))

    if "StockCount" in df.columns:
        weak = df[df["StockCount"] < 3]
        if not weak.empty:
            output.append("\nWarning: weak sector sample size:")
            output.append(", ".join(weak["Sector"].astype(str).tolist()))

    return "\n".join(output)

def answer(question):
    q = question.lower().strip()

    if q in ["help", "?"]:
        return help_text()

    if "market state" in q or "market regime" in q:
        return market_state()

    if "strongest sector" in q or "sector strength" in q:
        return strongest_sector()

    if "latest signal" in q or "signals" in q:
        return latest_signals()

    if "top pattern" in q or "alpha pattern" in q or "best pattern" in q:
        return top_patterns()

    if "error" in q or "audit" in q or "problem" in q:
        return errors()

    if "research question" in q or "what should i research" in q:
        return research_questions()
    
    if "full report" in q or "research report" in q:
        return full_report_summary()

    if "find problems" in q or "problems" in q or "system errors" in q:
        return find_problems()

    if "next research" in q or "what should we research" in q:
        return next_research()

    if q.startswith("why is "):
        sector_name = q.replace("why is ", "").replace("weak", "").replace("strong", "").strip()
        return why_sector(sector_name)

    if q.startswith("explain "):
        topic = q.replace("explain ", "").strip()
        return knowledge_search(topic)
    
    if "research signal quality" in q:
        return research_signal_quality()

    if "research patterns" in q:
        return research_patterns()

    if "research market state" in q or "research market regime" in q:
        return research_market_states()

    if "research sectors" in q:
        return research_sectors()

    

    return (
        "I don't understand that yet.\n"
        "Type 'help' to see what I can answer."
    )


def main():
    print("\n===================================")
    print(" MINI CUBE RESEARCH CHAT")
    print("===================================")
    print("Type 'help' for commands. Type 'exit' to stop.")

    while True:
        question = input("\nYou: ").strip()

        if question.lower() in ["exit", "quit", "q"]:
            print("\nMiniCube: Goodbye.")
            break

        print("\nMiniCube:")
        print(answer(question))


if __name__ == "__main__":
    main()