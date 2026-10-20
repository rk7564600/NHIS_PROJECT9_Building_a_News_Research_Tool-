"""Checks that langchain_config keeps the names and behaviour used in the project PDF."""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import langchain_config as cfg  # noqa: E402


def test_pdf_names_exist():
    for name in (
        "openai_api_key", "openai", "newsapi", "template", "prompt", "llm_chain",
        "get_news_articles", "summarize_articles", "get_summary",
    ):
        assert hasattr(cfg, name), name


def test_summarize_articles_joins_descriptions_with_space():
    arts = [
        {"description": "First."},
        {"description": None},            # would crash the PDF version
        {"description": "[Removed]"},
        {"description": "Second."},
    ]
    assert cfg.summarize_articles(arts) == "First. Second."


def test_get_summary_uses_newsapi_and_joins(monkeypatch):
    client = MagicMock()
    client.get_everything.return_value = {
        "status": "ok",
        "articles": [{"description": "A."}, {"description": "B."}],
    }
    monkeypatch.setattr(cfg, "newsapi", client)
    assert cfg.get_summary("tesla") == "A. B."
    assert client.get_everything.call_args.kwargs["language"] == "en"
    assert client.get_everything.call_args.kwargs["sort_by"] == "relevancy"


def test_llm_chain_run_matches_pdf_call_style():
    class Fake:
        def invoke(self, inputs):
            return f"{inputs['query']}|{inputs['summaries']}"

    chain = cfg.NewsChain(Fake())
    assert chain.run({"query": "q", "summaries": "s"}) == "q|s"        # Task 4.2 style
    assert chain.run({"query": "q"}).startswith("q|")                   # Task 3.2 style


def test_prompt_has_both_variables_from_pdf():
    assert set(cfg.prompt.input_variables) == {"query", "summaries"}
