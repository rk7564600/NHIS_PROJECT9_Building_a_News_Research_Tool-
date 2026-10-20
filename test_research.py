"""Tests for sentiment extraction and the research() pipeline (all mocked)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import langchain_config as cfg  # noqa: E402

ARTICLES = [
    {
        "title": "Tesla beats Q3 estimates",
        "description": "Profit above expectations.",
        "source": {"name": "Reuters"},
        "publishedAt": "2026-10-10T08:00:00Z",
        "url": "https://example.com/1",
    }
]


def test_extract_sentiment_variants():
    assert cfg.extract_sentiment("blah\nOverall sentiment: Positive") == "Positive"
    assert cfg.extract_sentiment("Overall sentiment: **mixed**") == "Mixed"
    assert cfg.extract_sentiment("overall sentiment - negative") == "Negative"
    assert cfg.extract_sentiment("no label here") == "Unknown"
    assert cfg.extract_sentiment("") == "Unknown"


def test_research_happy_path(monkeypatch):
    class FakeChain:
        def invoke(self, inputs):
            assert inputs["query"] == "tesla"
            assert "Tesla beats Q3 estimates" in inputs["summaries"]
            return "Tesla did well.\nOverall sentiment: Positive"

    monkeypatch.setattr(cfg, "get_news_articles", lambda *a, **k: ARTICLES)
    monkeypatch.setattr(cfg, "build_llm_chain", lambda **k: FakeChain())

    out = cfg.research("tesla")
    assert out["sentiment"] == "Positive"
    assert out["articles"] == ARTICLES
    assert "Tesla did well" in out["summary"]


def test_research_no_articles(monkeypatch):
    monkeypatch.setattr(cfg, "get_news_articles", lambda *a, **k: [])
    out = cfg.research("nothing")
    assert out["articles"] == []
    assert out["sentiment"] == "Unknown"
    assert "No relevant news" in out["summary"]
