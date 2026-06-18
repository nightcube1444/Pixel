from pathlib import Path
import sqlite3
import pandas as pd
import re

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "knowledge.db"
QUESTIONS_PATH = DATA_DIR / "research_questions.csv"
OUTPUT_PATH = DATA_DIR / "research_knowledge_report.csv"


KEYWORD_MAP = {
    "volatility": ["volatility", "vix", "risk", "uncertainty", "panic"],
    "momentum": ["momentum", "trend", "breakout", "market trend"],
    "inflation": ["inflation", "interest rate", "quantitative easing", "recession"],
    "sentiment": ["sentiment", "fear", "greed", "herd behavior", "behavioral finance"],
    "regime": ["bull market", "bear market", "market cycle", "financial crisis"],
    "sector": ["sector", "industry", "technology", "energy", "financial"],
    "confidence": ["statistics", "probability", "sample size", "bias"],
    "data": ["data quality", "missing data", "statistics", "measurement"],
    "finalscore": ["technical analysis", "backtesting", "statistical significance"],
    "signal": ["technical analysis", "momentum investing", "backtesting"],
    "sector": ["sector rotation", "market trend", "stock market"],
    "confidence": ["confidence interval", "sample size determination", "statistical significance"],
    "data quality": ["statistics", "overfitting", "backtesting"],
    "market state": ["market trend", "volatility index", "bull market", "bear market"],
    "tense_bull": ["volatility index", "bull market", "risk management"],
}


def extract_keywords(text: str) -> list[str]:
    text = str(text).lower()
    found = []

    for main_key, words in KEYWORD_MAP.items():
        if main_key in text:
            found.extend(words)

        for word in words:
            if word in text:
                found.extend(words)

    clean = []
    for item in found:
        if item not in clean:
            clean.append(item)

    return clean[:8]


def search_knowledge(conn, keywords: list[str]) -> list[dict]:
    if not keywords:
        return []

    rows = []

    for kw in keywords:
        query = """
        SELECT c.id, c.title, t.name, c.wiki_summary
        FROM concepts c
        JOIN topics t ON c.topic_id = t.id
        WHERE lower(c.title) LIKE ?
           OR lower(t.name) LIKE ?
           OR lower(c.wiki_summary) LIKE ?
        LIMIT 3
        """

        pattern = f"%{kw.lower()}%"

        try:
            results = conn.execute(query, (pattern, pattern, pattern)).fetchall()
        except Exception as e:
            print(f"Knowledge search failed for {kw}: {e}")
            results = []

        for r in results:
            rows.append({
                "Keyword": kw,
                "ConceptID": r[0],
                "ConceptTitle": r[1],
                "Topic": r[2],
                "Summary": str(r[3])[:300] if r[3] else "",
            })

    unique = []
    seen = set()

    for row in rows:
        key = (row["ConceptID"], row["Keyword"])
        if key not in seen:
            unique.append(row)
            seen.add(key)

    return unique[:10]


def make_research_hint(question: str, concepts: list[dict]) -> str:
    q = str(question).lower()

    if "volatility" in q or "vix" in q or "tense" in q:
        return "Study this pattern separately during calm VIX, elevated VIX, and high VIX periods."

    if "sector" in q:
        return "Check whether sector strength persists for 3, 5, and 10 days instead of only one day."

    if "finalscore" in q or "signal" in q:
        return "Compare forward returns of high-score signals versus low-score signals using 5D and 10D windows."

    if "confidence" in q or "pattern" in q:
        return "Require minimum sample size before trusting confidence results."

    if "data" in q or "quality" in q:
        return "Fix missing values, stale rows, duplicate rows, and empty pattern labels before drawing conclusions."

    if concepts:
        titles = ", ".join([c["ConceptTitle"] for c in concepts[:3]])
        return f"Use related concepts ({titles}) to explain why this research question may matter."

    return "Not enough knowledge context found. Add more concepts to the knowledge database."


def main():
    if not DB_PATH.exists():
        print(f"Missing knowledge database: {DB_PATH}")
        return

    if not QUESTIONS_PATH.exists():
        print(f"Missing research questions file: {QUESTIONS_PATH}")
        return

    questions = pd.read_csv(QUESTIONS_PATH)

    if "ResearchQuestion" not in questions.columns:
        print("ResearchQuestion column missing")
        return

    conn = sqlite3.connect(DB_PATH)

    output_rows = []

    for _, row in questions.iterrows():
        category = row.get("Category", "UNKNOWN")
        question = row.get("ResearchQuestion", "")
        priority = row.get("Priority", "UNKNOWN")

        keywords = extract_keywords(question)
        concepts = search_knowledge(conn, keywords)
        hint = make_research_hint(question, concepts)

        if not concepts:
            output_rows.append({
                "Category": category,
                "Priority": priority,
                "ResearchQuestion": question,
                "Keyword": "",
                "ConceptTitle": "",
                "Topic": "",
                "KnowledgeSummary": "",
                "ResearchHint": hint,
            })
            continue

        for concept in concepts:
            output_rows.append({
                "Category": category,
                "Priority": priority,
                "ResearchQuestion": question,
                "Keyword": concept["Keyword"],
                "ConceptTitle": concept["ConceptTitle"],
                "Topic": concept["Topic"],
                "KnowledgeSummary": concept["Summary"],
                "ResearchHint": hint,
            })

    conn.close()

    report = pd.DataFrame(output_rows)
    report.to_csv(OUTPUT_PATH, index=False)

    print("\n===================================")
    print(" MINI CUBE RESEARCH KNOWLEDGE REPORT")
    print("===================================\n")

    if report.empty:
        print("No knowledge matches found.")
    else:
        print(report[[
            "Category",
            "Priority",
            "ResearchQuestion",
            "ConceptTitle",
            "Topic",
            "ResearchHint",
        ]].head(20).to_string(index=False))

    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()