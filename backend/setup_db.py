# backend/setup_db.py
# Creates your knowledge database
# Run this ONCE to set everything up

import sqlite3
import os

DB_PATH = "data/knowledge.db"

def setup():
    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Table 1 — Topics (Economics, Psychology etc)
    c.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT NOT NULL,
            color TEXT DEFAULT '#888888'
        )
    """)

    # Table 2 — Concepts (what you learn)
    c.execute("""
        CREATE TABLE IF NOT EXISTS concepts (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id       INTEGER,
            title          TEXT NOT NULL,
            wiki_summary   TEXT,
            explanation    TEXT,
            analogy        TEXT,
            key_takeaway   TEXT,
            date_added     TEXT DEFAULT (date('now')),
            times_reviewed INTEGER DEFAULT 0,
            last_reviewed  TEXT,
            next_review    TEXT DEFAULT (date('now')),
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)

    # Table 3 — Connections between concepts
    c.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_1  INTEGER,
            concept_2  INTEGER,
            note       TEXT,
            FOREIGN KEY (concept_1) REFERENCES concepts(id),
            FOREIGN KEY (concept_2) REFERENCES concepts(id)
        )
    """)

    # Table 4 — Your review history
    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            concept_id  INTEGER,
            date        TEXT DEFAULT (date('now')),
            result      TEXT,
            FOREIGN KEY (concept_id) REFERENCES concepts(id)
        )
    """)

    # Add your 7 topics
    topics = [
        ("Economics",    "#1d6fb8"),
        ("Psychology",   "#9b59b6"),
        ("History",      "#c0392b"),
        ("Science",      "#16a085"),
        ("Geopolitics",  "#d35400"),
        ("Philosophy",   "#2c3e50"),
        ("Markets",      "#27ae60"),
    ]

    c.executemany(
        "INSERT OR IGNORE INTO topics (name, color) VALUES (?,?)",
        topics
    )

    conn.commit()
    conn.close()

    print("=" * 40)
    print("Database created: data/knowledge.db")
    print("Topics created:")
    print("  Economics, Psychology, History")
    print("  Science, Geopolitics, Philosophy, Markets")
    print("=" * 40)
    print("Next step: run wikipedia_loader.py")

if __name__ == "__main__":
    setup()