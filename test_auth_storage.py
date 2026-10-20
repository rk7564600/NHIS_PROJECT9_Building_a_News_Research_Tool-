"""Tests for login (auth.py) and persistence (storage.py)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import auth  # noqa: E402
import storage  # noqa: E402


# ------------------------------------------------------------------ auth
def test_login_plain_password(monkeypatch):
    monkeypatch.setenv("AUTH_USERNAME", "analyst")
    monkeypatch.setenv("AUTH_PASSWORD", "s3cret")
    monkeypatch.delenv("AUTH_PASSWORD_SHA256", raising=False)
    assert auth.verify_login("analyst", "s3cret")
    assert not auth.verify_login("analyst", "wrong")
    assert not auth.verify_login("someone", "s3cret")


def test_login_hashed_password(monkeypatch):
    monkeypatch.setenv("AUTH_USERNAME", "analyst")
    monkeypatch.delenv("AUTH_PASSWORD", raising=False)
    monkeypatch.setenv("AUTH_PASSWORD_SHA256", auth.hash_password("pw123"))
    assert auth.verify_login("analyst", "pw123")
    assert not auth.verify_login("analyst", "pw124")


def test_login_rejected_when_not_configured(monkeypatch):
    monkeypatch.delenv("AUTH_PASSWORD", raising=False)
    monkeypatch.delenv("AUTH_PASSWORD_SHA256", raising=False)
    assert not auth.is_configured()
    assert not auth.verify_login("analyst", "")


def test_auth_disabled_flag(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert not auth.auth_enabled()
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert auth.auth_enabled()


# --------------------------------------------------------------- storage
ARTICLES = [
    {
        "title": "Tesla beats estimates",
        "url": "https://example.com/1",
        "source": {"name": "Reuters"},
        "publishedAt": "2026-10-10T08:00:00Z",
        "description": "Profit up.",
    }
]


def test_save_list_delete(tmp_path):
    db = str(tmp_path / "t.db")
    storage.init_db(db)
    qid = storage.save_query("amy", "tesla", "summary text", "Positive", ARTICLES, db_path=db)
    storage.save_query("bob", "hdfc", "other", "Negative", [], db_path=db)

    mine = storage.list_queries("amy", db_path=db)
    assert len(mine) == 1
    assert mine[0]["query"] == "tesla"
    assert mine[0]["n_articles"] == 1
    assert mine[0]["articles"][0]["source"] == "Reuters"

    # users cannot delete each other's rows
    assert not storage.delete_query("bob", qid, db_path=db)
    assert storage.delete_query("amy", qid, db_path=db)
    assert storage.list_queries("amy", db_path=db) == []


def test_sentiment_score():
    assert storage.sentiment_score("Positive") == 1
    assert storage.sentiment_score("Negative") == -1
    assert storage.sentiment_score("Mixed") == 0
    assert storage.sentiment_score("Unknown") is None
