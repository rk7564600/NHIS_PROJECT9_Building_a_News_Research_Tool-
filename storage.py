"""
storage.py
----------
SQLite persistence for saved queries and historical sentiment analysis (Task 7.3).

The database file defaults to ./news_tool.db (override with DB_PATH in .env).
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from typing import Any, Dict, List, Optional

DEFAULT_DB = os.getenv("DB_PATH", "news_tool.db")


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    with closing(_connect(db_path)) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_queries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL,
                query         TEXT NOT NULL,
                summary       TEXT NOT NULL,
                sentiment     TEXT NOT NULL DEFAULT 'Unknown',
                n_articles    INTEGER NOT NULL DEFAULT 0,
                articles_json TEXT NOT NULL DEFAULT '[]',
                created_at    TEXT NOT NULL
            )
            """
        )


def save_query(
    username: str,
    query: str,
    summary: str,
    sentiment: str = "Unknown",
    articles: Optional[List[Dict[str, Any]]] = None,
    db_path: Optional[str] = None,
) -> int:
    articles = articles or []
    compact = [
        {
            "title": a.get("title"),
            "url": a.get("url"),
            "source": (a.get("source") or {}).get("name"),
            "publishedAt": a.get("publishedAt"),
            "description": a.get("description"),
        }
        for a in articles
    ]
    with closing(_connect(db_path)) as conn, conn:
        cur = conn.execute(
            "INSERT INTO saved_queries "
            "(username, query, summary, sentiment, n_articles, articles_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                username,
                query,
                summary,
                sentiment,
                len(compact),
                json.dumps(compact),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return int(cur.lastrowid)


def list_queries(username: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """All saved queries for a user, newest first."""
    with closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT * FROM saved_queries WHERE username = ? ORDER BY created_at DESC, id DESC",
            (username,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["articles"] = json.loads(d.pop("articles_json") or "[]")
        out.append(d)
    return out


def delete_query(username: str, query_id: int, db_path: Optional[str] = None) -> bool:
    with closing(_connect(db_path)) as conn, conn:
        cur = conn.execute(
            "DELETE FROM saved_queries WHERE id = ? AND username = ?", (query_id, username)
        )
        return cur.rowcount > 0


SENTIMENT_SCORE = {"Positive": 1, "Neutral": 0, "Mixed": 0, "Negative": -1}


def sentiment_score(label: str) -> Optional[int]:
    """+1 / 0 / -1 for charting; None for 'Unknown'."""
    return SENTIMENT_SCORE.get(label)
