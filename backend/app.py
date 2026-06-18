# backend/app.py
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import requests
import feedparser
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_PATH = "data/knowledge.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/api/ping")
def ping():
    return jsonify({ "status": "running" })


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
    return jsonify({ "error": "Not found" }), 404


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


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
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

How to respond:
- Start directly with the answer, no filler phrases like "Great question!"
- Write in clear paragraphs
- Give real depth — causes, mechanisms, history, examples
- Use one good analogy if it helps
- Include specific numbers, dates, or names where relevant
- End with a bold key insight starting with "Key Idea:"

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={ "model": OLLAMA_MODEL, "prompt": prompt, "stream": False },
            timeout=60
        )
        result = response.json()
        answer = result.get("response", "No response from Ollama")
        return jsonify({ "answer": answer, "context_used": bool(context) })

    except Exception as e:
        return jsonify({
            "answer": f"Ollama error: {str(e)}\n\nMake sure Ollama is running:\nollama serve",
            "error": True
        })


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
    return jsonify({ "message": "Nothing to review today" })


@app.route("/api/review/save", methods=["POST"])
def save_review():
    data = request.json
    concept_id = data.get("concept_id")
    result = data.get("result")
    next_days = { "knew": 7, "partial": 2, "forgot": 1 }
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
    c.execute("INSERT INTO reviews (concept_id, result) VALUES (?, ?)", (concept_id, result))
    conn.commit()
    conn.close()
    return jsonify({ "saved": True, "next_review_in_days": days })


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


FEEDS = {
    "bbc":        "http://feeds.bbci.co.uk/news/rss.xml",
    "reuters":    "https://feeds.reuters.com/reuters/topNews",
    "et":         "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
    "guardian":   "https://www.theguardian.com/world/rss",
    "cnbc":       "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "business":   "https://feeds.bbci.co.uk/news/business/rss.xml",
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
                "title":   entry.get("title", ""),
                "summary": entry.get("summary", "")[:200],
                "link":    entry.get("link", ""),
                "source":  feed.feed.get("title", source.upper()),
                "date":    entry.get("published", "")
            })
        return jsonify({ "articles": articles, "source": source, "count": len(articles) })
    except Exception as e:
        return jsonify({ "error": str(e), "articles": [] })


@app.route("/api/ask_with_news", methods=["POST"])
def ask_with_news():
    data     = request.json
    question = data.get("question", "")
    source   = data.get("source", "bbc")

    url  = FEEDS.get(source, FEEDS["bbc"])
    feed = feedparser.parse(url)
    keywords = question.lower().split()
    relevant = []

    for entry in feed.entries[:20]:
        title   = entry.get("title", "").lower()
        summary = entry.get("summary", "").lower()
        for word in keywords:
            if len(word) > 4 and (word in title or word in summary):
                relevant.append({
                    "title":   entry.get("title", ""),
                    "summary": entry.get("summary", "")[:300]
                })
                break

    news_context = ""
    if relevant:
        news_context = "\n\nRELEVANT NEWS TODAY:\n"
        for a in relevant[:3]:
            news_context += f"- {a['title']}: {a['summary']}\n"

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

How to respond:
- Start directly with the answer
- Write in clear paragraphs
- Mention relevant news naturally if available
- Use one good analogy if it helps
- End with "Key Idea:" — one sharp sentence summary

Answer:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={ "model": OLLAMA_MODEL, "prompt": prompt, "stream": False },
            timeout=60
        )
        result = response.json()
        answer = result.get("response", "No response")
        return jsonify({ "answer": answer, "news_found": len(relevant), "db_found": bool(db_context) })

    except Exception as e:
        return jsonify({ "answer": f"Ollama error: {str(e)}", "error": True })


if __name__ == "__main__":
    print("\n" + "=" * 40)
    print("Knowledge Engine Backend")
    print("Running at http://localhost:5000")
    print("=" * 40 + "\n")
    app.run(debug=True, port=5000)
