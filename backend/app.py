# backend/app.py

from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import requests
import feedparser
from pathlib import Path
import pandas as pd

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DB_PATH = DATA_DIR / "knowledge.db"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


# ============================================================
# HELPERS
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        return {
            "error": f"{filename} not found",
            "path": str(path),
            "data": []
        }

    try:
        df = pd.read_csv(path)
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        return {
            "error": str(e),
            "data": []
        }


def read_text_file(filename):
    path = DATA_DIR / filename

    if not path.exists():
        return {
            "error": f"{filename} not found",
            "path": str(path),
            "content": ""
        }

    try:
        return {
            "content": path.read_text(encoding="utf-8")
        }
    except Exception as e:
        return {
            "error": str(e),
            "content": ""
        }


def explain_pattern_text(pattern):
    meanings = {
        "PANIC": "Fear selling is detected. Traders may be dumping positions quickly.",
        "MOMENTUM": "Price is moving strongly in one direction with trend strength.",
        "OVERBOUGHT": "Price may be stretched upward and could be due for cooling.",
        "OVERSOLD": "Price may be stretched downward and could be due for rebound.",
        "NONE": "No strong primary signal was detected.",

        "BULL": "Bullish market regime. Price is generally trending upward.",
        "BEAR": "Bearish market regime. Price is generally trending downward.",
        "SIDEWAYS": "Range-bound market. Price is moving without a strong trend.",
        "HIGH_VOLATILITY": "Large price swings are happening. Risk is elevated.",
        "INSUFFICIENT_HISTORY": "Not enough historical data to classify this part confidently.",

        "NORMAL": "Normal volatility condition.",
        "VOLATILE": "Volatility is above normal. Price movement is unstable.",
        "HIGH_VOL": "High trading volume or high activity condition.",

        "VIX_LOW": "Market fear is low.",
        "VIX_ELEVATED": "Market fear is elevated but not extreme.",
        "VIX_HIGH": "Market fear is high.",
        "VIX_EXTREME": "Market fear is extreme. This often appears during panic conditions.",
        "VIX_UNAVAILABLE": "VIX data was not available for this pattern."
    }

    parts = str(pattern).split("|")

    breakdown = []
    for part in parts:
        clean = part.strip().upper()
        breakdown.append({
            "component": clean,
            "meaning": meanings.get(clean, "No explanation available for this component yet.")
        })

    summary = (
        "This pattern combines signal, market regime, volatility, benchmark context, "
        "and VIX fear state. Use the historical appearance count, survival score, "
        "win rate, and average return before trusting it."
    )

    return {
        "pattern": pattern,
        "breakdown": breakdown,
        "summary": summary
    }


# ============================================================
# BASIC HEALTH
# ============================================================

@app.route("/api/ping")
def ping():
    return jsonify({"status": "running"})


# ============================================================
# KNOWLEDGE DATABASE ENDPOINTS
# ============================================================

@app.route("/api/topics")
def get_topics():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM topics ORDER BY name")
    topics = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(topics)


@app.route("/api/concepts/<int:topic_id>")
def get_concepts(topic_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT id, title, date_added, times_reviewed
        FROM concepts
        WHERE topic_id = ?
        ORDER BY title
    """, (topic_id,))
    concepts = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(concepts)


@app.route("/api/concept/<int:concept_id>")
def get_concept(concept_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify(dict(row))

    return jsonify({"error": "Not found"}), 404


@app.route("/api/search")
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify([])

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.id, c.title, t.name as topic
        FROM concepts c
        JOIN topics t ON c.topic_id = t.id
        WHERE c.title LIKE ?
        OR c.wiki_summary LIKE ?
        LIMIT 20
    """, (f"%{query}%", f"%{query}%"))

    results = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(results)


@app.route("/api/stats")
def stats():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM concepts")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM concepts WHERE times_reviewed > 0")
    reviewed = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM concepts WHERE next_review <= date('now')")
    due_today = c.fetchone()[0]

    c.execute("""
        SELECT t.name, COUNT(c.id) as count
        FROM topics t
        LEFT JOIN concepts c ON c.topic_id = t.id
        GROUP BY t.name
        ORDER BY count DESC
    """)

    by_topic = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify({
        "total_concepts": total,
        "reviewed": reviewed,
        "not_reviewed": total - reviewed,
        "due_today": due_today,
        "by_topic": by_topic
    })


# ============================================================
# MARKET INTELLIGENCE ENDPOINTS
# ============================================================

@app.route("/api/market/recommendations")
def market_recommendations():
    return jsonify(load_csv("institutional_recommendations.csv"))


@app.route("/api/market/live-patterns")
def market_live_patterns():
    return jsonify(load_csv("live_pattern_matches.csv"))


@app.route("/api/market/institutional-patterns")
def market_institutional_patterns():
    return jsonify(load_csv("institutional_patterns.csv"))


@app.route("/api/market/pattern-tickers")
def market_pattern_tickers():
    return jsonify(load_csv("institutional_pattern_tickers.csv"))


@app.route("/api/market/sectors")
def market_sectors():
    return jsonify(load_csv("sector_alpha_rankings.csv"))


@app.route("/api/market/sector-matrix")
def market_sector_matrix():
    return jsonify(load_csv("pattern_sector_matrix.csv"))


@app.route("/api/market/ticker-history")
def market_ticker_history():
    return jsonify(load_csv("ticker_pattern_history.csv"))


@app.route("/api/market/market-state")
def market_state():
    data = load_csv("market_state.csv")

    if isinstance(data, list) and len(data) > 0:
        return jsonify(data[-1])

    return jsonify(data)


@app.route("/api/market/research-questions")
def market_research_questions():
    return jsonify(load_csv("research_questions.csv"))


@app.route("/api/market/data-quality")
def market_data_quality():
    return jsonify(load_csv("data_quality_report.csv"))


@app.route("/api/market/change-detection")
def market_change_detection():
    return jsonify(load_csv("change_detection_results.csv"))


@app.route("/api/market/research-report")
def market_research_report():
    return jsonify(read_text_file("research_report.txt"))


@app.route("/api/market/dashboard")
def market_dashboard():
    market_state_data = load_csv("market_state.csv")
    recommendations = load_csv("institutional_recommendations.csv")
    patterns = load_csv("institutional_patterns.csv")
    live_patterns = load_csv("live_pattern_matches.csv")
    sectors = load_csv("sector_alpha_rankings.csv")
    quality = load_csv("data_quality_report.csv")
    questions = load_csv("research_questions.csv")

    latest_state = {}
    if isinstance(market_state_data, list) and len(market_state_data) > 0:
        latest_state = market_state_data[-1]

    return jsonify({
        "market_state": latest_state,
        "top_recommendations": recommendations[:10] if isinstance(recommendations, list) else [],
        "top_patterns": patterns[:10] if isinstance(patterns, list) else [],
        "live_patterns": live_patterns[:15] if isinstance(live_patterns, list) else [],
        "top_sectors": sectors[:10] if isinstance(sectors, list) else [],
        "data_quality": quality[:10] if isinstance(quality, list) else [],
        "research_questions": questions[:10] if isinstance(questions, list) else []
    })


@app.route("/api/market/explain-pattern", methods=["POST"])
def market_explain_pattern():
    data = request.json or {}
    pattern = data.get("pattern", "")

    if not pattern:
        return jsonify({"error": "pattern is required"}), 400

    explanation = explain_pattern_text(pattern)
    return jsonify(explanation)


@app.route("/api/market/explain-ticker/<ticker>")
def market_explain_ticker(ticker):
    ticker = ticker.upper().strip()

    recommendations = load_csv("institutional_recommendations.csv")
    live_patterns = load_csv("live_pattern_matches.csv")

    rec = None
    if isinstance(recommendations, list):
        for row in recommendations:
            if str(row.get("Ticker", "")).upper() == ticker:
                rec = row
                break

    live = None
    if isinstance(live_patterns, list):
        for row in live_patterns:
            if str(row.get("Ticker", "")).upper() == ticker:
                live = row
                break

    return jsonify({
        "ticker": ticker,
        "recommendation": rec,
        "live_pattern": live,
        "explanation": (
            f"{ticker} is explained using institutional recommendation data, "
            f"live pattern match data, alpha score, survival score, and sector context."
        )
    })


# ============================================================
# MARKET CHAT — RULE BASED FIRST
# ============================================================

@app.route("/api/market/chat", methods=["POST"])
def market_chat():
    data = request.json or {}
    question = data.get("question", "").strip()
    q = question.lower()

    recommendations = load_csv("institutional_recommendations.csv")
    patterns = load_csv("institutional_patterns.csv")
    tickers = load_csv("institutional_pattern_tickers.csv")
    sectors = load_csv("sector_alpha_rankings.csv")

    if "top" in q and "recommend" in q:
        top = recommendations[:5] if isinstance(recommendations, list) else []
        lines = ["Top institutional recommendations:"]
        for row in top:
            lines.append(
                f"{row.get('RecommendationRank')}. {row.get('Ticker')} "
                f"Score={row.get('OpportunityScore')} "
                f"Sector={row.get('Sector')}"
            )
        return jsonify({"answer": "\n".join(lines)})

    if "sector" in q:
        top = sectors[:5] if isinstance(sectors, list) else []
        lines = ["Top sectors by sector alpha:"]
        for row in top:
            lines.append(
                f"{row.get('SectorRank')}. {row.get('Sector')} "
                f"Score={row.get('SectorAlphaScore')} "
                f"WinRate={row.get('WinRate')}"
            )
        return jsonify({"answer": "\n".join(lines)})

    if "explain" in q:
        words = question.upper().replace("EXPLAIN", "").strip()

        if words:
            exp = explain_pattern_text(words)
            lines = [f"Explanation: {words}", ""]

            for item in exp["breakdown"]:
                lines.append(
                    f"{item['component']}: {item['meaning']}"

                )
            lines.append("")

            lines.append(exp["summary"])

            return jsonify({

                "answer": "\n".join(lines)

            })

    for row in recommendations if isinstance(recommendations, list) else []:
        ticker = str(row.get("Ticker", "")).lower()
        if ticker and ticker in q:
            answer = (
                f"{row.get('Ticker')} is ranked #{row.get('RecommendationRank')}.\n"
                f"Sector: {row.get('Sector')}\n"
                f"Market: {row.get('Market')}\n"
                f"Opportunity Score: {row.get('OpportunityScore')}\n"
                f"Alpha Score: {row.get('AlphaScore')}\n"
                f"Survival Score: {row.get('SurvivalScore')}\n\n"
                f"Meaning: this ticker is currently appearing in your institutional "
                f"recommendation layer because its live pattern matched historically "
                f"validated pattern evidence."
            )
            return jsonify({"answer": answer})

    top_patterns = patterns[:3] if isinstance(patterns, list) else []
    lines = [
        "I can answer questions like:",
        "- Why is JPM recommended?",
        "- Show top recommendations",
        "- Show top sectors",
        "- Explain PANIC|HIGH_VOLATILITY|VOLATILE|HIGH_VOL|VIX_EXTREME",
        "",
        "Top institutional patterns right now:"
    ]

    for row in top_patterns:
        lines.append(
            f"{row.get('InstitutionalRank')}. {row.get('Pattern')} "
            f"Survival={row.get('SurvivalScore')}"
        )

    return jsonify({"answer": "\n".join(lines)})


# ============================================================
# OLLAMA KNOWLEDGE CHAT
# ============================================================

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json or {}
    question = data.get("question", "")
    concept_id = data.get("concept_id", None)

    conn = get_db()
    c = conn.cursor()
    context = ""

    if concept_id:
        c.execute("SELECT title, wiki_summary FROM concepts WHERE id = ?", (concept_id,))
        row = c.fetchone()
        if row:
            context = f"Title: {row[0]}\n\nKnowledge: {row[1]}"
    else:
        words = question.lower().split()
        for word in words:
            if len(word) > 4:
                c.execute("""
                    SELECT title, wiki_summary
                    FROM concepts
                    WHERE title LIKE ?
                    OR wiki_summary LIKE ?
                    LIMIT 3
                """, (f"%{word}%", f"%{word}%"))
                rows = c.fetchall()
                for row in rows:
                    context += f"\nTitle: {row[0]}\nKnowledge: {row[1][:300]}\n"

    conn.close()

    if not context:
        context = "No specific knowledge found in database for this question."

    prompt = f"""You are a knowledgeable and friendly AI assistant. Explain concepts clearly and intelligently, like a great teacher.

KNOWLEDGE FROM DATABASE:
{context}

QUESTION: {question}

Answer clearly and end with a bold Key Idea.

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        result = response.json()
        answer = result.get("response", "No response from Ollama")

        return jsonify({
            "answer": answer,
            "context_used": bool(context)
        })

    except Exception as e:
        return jsonify({
            "answer": f"Ollama error: {str(e)}\n\nMake sure Ollama is running:\nollama serve",
            "error": True
        })


# ============================================================
# REVIEW SYSTEM
# ============================================================

@app.route("/api/review/next")
def next_review():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT c.*, t.name as topic_name
        FROM concepts c
        JOIN topics t ON c.topic_id = t.id
        WHERE c.next_review <= date('now')
        ORDER BY c.next_review ASC
        LIMIT 1
    """)

    row = c.fetchone()
    conn.close()

    if row:
        return jsonify(dict(row))

    return jsonify({"message": "Nothing to review today"})


@app.route("/api/review/save", methods=["POST"])
def save_review():
    data = request.json or {}
    concept_id = data.get("concept_id")
    result = data.get("result")

    next_days = {
        "knew": 7,
        "partial": 2,
        "forgot": 1
    }

    days = next_days.get(result, 3)

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        UPDATE concepts
        SET times_reviewed = times_reviewed + 1,
            last_reviewed  = date('now'),
            next_review    = date('now', ? || ' days')
        WHERE id = ?
    """, (f"+{days}", concept_id))

    c.execute(
        "INSERT INTO reviews (concept_id, result) VALUES (?, ?)",
        (concept_id, result)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "saved": True,
        "next_review_in_days": days
    })


# ============================================================
# NEWS
# ============================================================

FEEDS = {
    "bbc": "http://feeds.bbci.co.uk/news/rss.xml",
    "reuters": "https://feeds.reuters.com/reuters/topNews",
    "et": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "guardian": "https://www.theguardian.com/world/rss",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
}


@app.route("/api/news")
def get_news():
    source = request.args.get("source", "bbc")
    url = FEEDS.get(source, FEEDS["bbc"])

    try:
        feed = feedparser.parse(url)

        articles = []
        for entry in feed.entries[:15]:
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:200],
                "link": entry.get("link", ""),
                "source": feed.feed.get("title", source.upper()),
                "date": entry.get("published", "")
            })

        return jsonify({
            "articles": articles,
            "source": source,
            "count": len(articles)
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "articles": []
        })


@app.route("/api/ask_with_news", methods=["POST"])
def ask_with_news():
    data = request.json or {}
    question = data.get("question", "")
    source = data.get("source", "bbc")

    url = FEEDS.get(source, FEEDS["bbc"])
    feed = feedparser.parse(url)
    keywords = question.lower().split()
    relevant = []

    for entry in feed.entries[:20]:
        title = entry.get("title", "").lower()
        summary = entry.get("summary", "").lower()

        for word in keywords:
            if len(word) > 4 and (word in title or word in summary):
                relevant.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300]
                })
                break

    news_context = ""
    if relevant:
        news_context = "\n\nRELEVANT NEWS TODAY:\n"
        for article in relevant[:3]:
            news_context += f"- {article['title']}: {article['summary']}\n"

    conn = get_db()
    c = conn.cursor()
    db_context = ""

    for word in keywords:
        if len(word) > 4:
            c.execute("""
                SELECT title, wiki_summary
                FROM concepts
                WHERE title LIKE ?
                OR wiki_summary LIKE ?
                LIMIT 2
            """, (f"%{word}%", f"%{word}%"))

            rows = c.fetchall()
            for row in rows:
                db_context += f"\nKNOWLEDGE: {row[0]}\n{row[1][:300]}\n"

    conn.close()

    full_context = db_context + news_context

    if not full_context:
        full_context = "No specific knowledge or news found. Answer from general knowledge."

    prompt = f"""You are a knowledgeable and friendly AI assistant. Explain clearly and intelligently.

CONTEXT:
{full_context}

QUESTION: {question}

Answer clearly and end with Key Idea.

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        result = response.json()
        answer = result.get("response", "No response")

        return jsonify({
            "answer": answer,
            "news_found": len(relevant),
            "db_found": bool(db_context)
        })

    except Exception as e:
        return jsonify({
            "answer": f"Ollama error: {str(e)}",
            "error": True
        })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Knowledge + Market Intelligence Backend")
    print("Running at http://localhost:5000")
    print("=" * 50 + "\n")

    app.run(
        debug=True,
        port=5000
    )