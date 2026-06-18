from pathlib import Path
import sqlite3
import time
import wikipediaapi

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "knowledge.db"

wiki = wikipediaapi.Wikipedia(
    language="en",
    extract_format=wikipediaapi.ExtractFormat.WIKI,
    user_agent="KnowledgeEngine/1.0"
)

KNOWLEDGE = {
    "Economics": [
        "Inflation",
        "Recession",
        "Gross domestic product",
        "Interest rate",
        "Central bank",
        "Supply and demand",
        "Stock market",
        "Compound interest",
        "Quantitative easing",
        "Trade deficit",
        "Financial risk",
        "Systemic risk",
        "Liquidity risk",
        "Value at risk",
        "Sharpe ratio",
    ],

    "Psychology": [
        "Loss aversion",
        "Herd behavior",
        "Confirmation bias",
        "Cognitive bias",
        "Dunning-Kruger effect",
        "Cognitive dissonance",
        "Dopamine",
        "Fear",
        "Panic",
        "Decision-making",
        "Behavioral economics",
        "Overconfidence effect",
        "Investor sentiment",
        "Fear of missing out",
        "Risk aversion",
        "Prospect theory",
    ],

    "History": [
        "2008 financial crisis",
        "Great Depression",
        "Dot-com bubble",
        "Tulip mania",
        "Roman Empire",
        "Cold War",
        "Industrial Revolution",
        "British Empire",
        "Soviet Union",
        "World War I",
    ],

    "Science": [
        "Machine learning",
        "Internet",
        "DNA",
        "Evolution",
        "Quantum mechanics",
        "Entropy",
        "Electricity",
        "Computer",
        "Artificial intelligence",
        "Statistics",
        "Sample size determination",
        "Statistical significance",
        "P-value",
        "Confidence interval",
        "Regression analysis",
        "Correlation",
        "Overfitting",
    ],

    "Geopolitics": [
        "BRICS",
        "NATO",
        "Belt and Road Initiative",
        "Petrodollar",
        "Economic sanctions",
        "Soft power",
        "United States dollar",
        "Economy of China",
        "Economy of India",
        "Organization of the Petroleum Exporting Countries",
    ],

    "Philosophy": [
        "Stoicism",
        "First principle",
        "Occam's razor",
        "Scientific method",
        "Survivorship bias",
        "Second-order logic",
        "Mental model",
        "Correlation and dependence",
        "Critical thinking",
        "Logical fallacy",
    ],

    "Markets": [
        "Relative strength index",
        "MACD",
        "Technical analysis",
        "Fundamental analysis",
        "Market sentiment",
        "Stock market crash",
        "Bull market",
        "Bear market",
        "Volatility (finance)",
        "Risk management",
        "Momentum investing",
        "Trend following",
        "Mean reversion",
        "Market trend",
        "Business cycle",
        "Sector rotation",
        "Moving average",
        "Volatility index",
        "Beta (finance)",
        "Backtesting",
        "Look-ahead bias",
        "Data snooping",
        "Selection bias",
        "Publication bias",
    ],

    "Space Economy": [
        "SpaceX",
        "Starlink",
        "Rocket Lab",
        "Falcon 9",
        "Reusable launch system",
        "Satellite internet access",
        "Low Earth orbit",
        "Space industry",
        "Artemis program",
        "Commercial spaceflight",
    ],

    "Defense": [
        "Military budget",
        "Defense industry",
        "Geopolitical risk",
        "Missile defense",
        "Arms industry",
        "National security",
        "Military–industrial complex",
    ],
}


def get_topic_id(cursor, topic_name):
    cursor.execute(
        "SELECT id FROM topics WHERE name = ?",
        (topic_name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def ensure_topic(cursor, conn, topic_name):
    topic_id = get_topic_id(cursor, topic_name)

    if topic_id:
        return topic_id

    cursor.execute(
        "INSERT INTO topics (name) VALUES (?)",
        (topic_name,)
    )
    conn.commit()

    return cursor.lastrowid


def concept_exists(cursor, title):
    cursor.execute(
        "SELECT id FROM concepts WHERE title = ?",
        (title,)
    )
    return cursor.fetchone() is not None


def load_wikipedia(search_title):
    page = wiki.page(search_title)

    if not page.exists():
        return None

    return page.summary[:1000]


def run():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run this first:")
        print("python3 backend/setup_db.py")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total_added = 0
    total_skipped = 0
    total_failed = 0
    total_topics_created = 0

    for topic_name, titles in KNOWLEDGE.items():
        before = get_topic_id(cursor, topic_name)
        topic_id = ensure_topic(cursor, conn, topic_name)

        if before is None:
            print(f"Created topic: {topic_name}")
            total_topics_created += 1

        print(f"\n{topic_name}")
        print("-" * 30)

        for title in titles:
            if concept_exists(cursor, title):
                print(f"  SKIP  {title}")
                total_skipped += 1
                continue

            summary = load_wikipedia(title)

            if summary:
                cursor.execute(
                    """
                    INSERT INTO concepts
                    (topic_id, title, wiki_summary)
                    VALUES (?, ?, ?)
                    """,
                    (topic_id, title, summary)
                )
                conn.commit()

                print(f"  ADDED {title}")
                total_added += 1
            else:
                print(f"  FAIL  {title} not found on Wikipedia")
                total_failed += 1

            time.sleep(0.5)

    conn.close()

    print("\n" + "=" * 40)
    print(f"Topics created: {total_topics_created}")
    print(f"Added:          {total_added} concepts")
    print(f"Skipped:        {total_skipped} already existed")
    print(f"Failed:         {total_failed} not found")
    print("=" * 40)
    print("Database is ready.")
    print("Next step:")
    print("python3 scripts/research_knowledge_engine.py")


if __name__ == "__main__":
    run()