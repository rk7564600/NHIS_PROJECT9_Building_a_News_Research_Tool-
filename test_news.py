"""Unit tests (Phase 5) — no real API calls are made; everything is mocked."""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import langchain_config as cfg  # noqa: E402

SAMPLE = [
    {
        "title": "Tesla beats Q3 estimates",
        "description": "Tesla reported higher than expected profit.",
        "source": {"name": "Reuters"},
        "publishedAt": "2026-10-10T08:00:00Z",
        "url": "https://example.com/1",
    },
    {"title": "[Removed]", "description": "[Removed]", "source": {"name": "x"}},
    {"title": "No description", "description": None, "source": {"name": "y"}},
]


def test_format_articles_filters_bad_items():
    text = cfg.format_articles(SAMPLE)
    assert "Tesla beats Q3 estimates" in text
    assert "Reuters" in text
    assert "[Removed]" not in text
    assert "No description" not in text


def test_format_articles_empty():
    assert cfg.format_articles([]) == ""


def test_get_news_articles_calls_newsapi_and_caps_days():
    client = MagicMock()
    client.get_everything.return_value = {"status": "ok", "articles": SAMPLE}
    out = cfg.get_news_articles("tesla", page_size=5, days_back=999, client=client)
    assert out == SAMPLE
    kwargs = client.get_everything.call_args.kwargs
    assert kwargs["q"] == "tesla"
    assert kwargs["page_size"] == 5
    assert kwargs["language"] == "en"


def test_get_news_articles_raises_on_api_error():
    client = MagicMock()
    client.get_everything.return_value = {"status": "error", "message": "rate limited"}
    try:
        cfg.get_news_articles("tesla", client=client)
    except RuntimeError as exc:
        assert "rate limited" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_prompt_contains_variables():
    rendered = cfg.prompt.format(query="HDFC", summaries="1. test")
    assert "HDFC" in rendered and "1. test" in rendered
    assert "equity research analyst" in rendered
