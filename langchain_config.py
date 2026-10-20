"""
langchain_config.py
-------------------
LangChain + NewsAPI configuration for the Equity Research News Tool.

Flow:
    query -> NewsAPI (fetch articles) -> format articles -> LLM chain -> summary

This file follows the project PDF (Tasks 2.1, 2.2 and 4.1) and keeps its names:
    openai_api_key, openai, newsapi, template, prompt, llm_chain,
    get_news_articles(), summarize_articles(), get_summary()
and `llm_chain.run({...})` works exactly as in the PDF.

Differences from the PDF (the PDF's `from langchain import OpenAI, LLMChain` imports
no longer exist in current LangChain):
    - uses langchain-openai's ChatOpenAI and `prompt | llm | parser` (LCEL)
    - API keys come from environment variables / .env, never hardcoded
"""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from newsapi import NewsApiClient

load_dotenv()

OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
NEWSAPI_KEY: Optional[str] = os.getenv("NEWSAPI_KEY")
DEFAULT_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Names used in the PDF (Task 2.2): the key and the LLM object.
openai_api_key: Optional[str] = OPENAI_API_KEY
openai = (
    ChatOpenAI(model=DEFAULT_MODEL, temperature=0.2, api_key=OPENAI_API_KEY)
    if OPENAI_API_KEY
    else None
)

# --------------------------------------------------------------------------
# Prompt (Task 2.2 + Task 4.1)
# --------------------------------------------------------------------------
template = """
You are an AI assistant helping an equity research analyst.
Given the following query and the provided news article summaries, provide an overall summary.

Instructions:
- Start with a 2-3 sentence executive summary.
- Then list the key developments as short bullet points (mention the source in brackets
  when the articles name one).
- Highlight anything that could affect the stock/company/sector (earnings, regulation,
  deals, management changes, macro factors).
- Use ONLY the information in the articles. If the articles do not cover the query,
  say so clearly instead of guessing.
- Finish with exactly one last line in this format:
  Overall sentiment: <Positive|Negative|Neutral|Mixed>

Query: {query}

Summaries:
{summaries}
"""

TEMPLATE = template  # backwards-compatible alias
prompt = PromptTemplate(template=template, input_variables=["query", "summaries"])


# --------------------------------------------------------------------------
# LLM chain
# --------------------------------------------------------------------------
class NewsChain:
    """
    Thin wrapper around `prompt | llm | parser` so the PDF's
    `llm_chain.run({'query': ..., 'summaries': ...})` still works.
    `invoke()` is the modern LangChain equivalent.
    """

    def __init__(self, runnable):
        self._chain = runnable

    def invoke(self, inputs: Dict[str, Any]) -> str:
        return self._chain.invoke(inputs)

    def run(self, inputs: Dict[str, Any]) -> str:
        inputs = dict(inputs)
        inputs.setdefault("summaries", "(no articles were provided)")
        return self._chain.invoke(inputs)


def build_llm_chain(model: str = DEFAULT_MODEL, temperature: float = 0.2) -> NewsChain:
    """Return the chain: prompt | ChatOpenAI | StrOutputParser."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Add it to your .env file (see .env.example)."
        )
    llm = ChatOpenAI(model=model, temperature=temperature, api_key=OPENAI_API_KEY)
    return NewsChain(prompt | llm | StrOutputParser())


# PDF name (`from langchain_config import llm_chain`).
llm_chain: Optional[NewsChain] = build_llm_chain() if OPENAI_API_KEY else None


# --------------------------------------------------------------------------
# NewsAPI helpers (Task 4.1)
# --------------------------------------------------------------------------
# PDF name: `newsapi = NewsApiClient(api_key=...)`.
newsapi: Optional[NewsApiClient] = NewsApiClient(api_key=NEWSAPI_KEY) if NEWSAPI_KEY else None


def _get_newsapi_client() -> NewsApiClient:
    if newsapi is None:
        raise RuntimeError(
            "NEWSAPI_KEY not found. Add it to your .env file (see .env.example)."
        )
    return newsapi


def get_news_articles(
    query: str,
    page_size: int = 10,
    days_back: int = 7,
    sort_by: str = "relevancy",
    client: Optional[NewsApiClient] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch English news articles for `query` from NewsAPI (PDF: `get_news_articles(query)`).

    The extra arguments are optional. The free Developer plan only returns articles
    from roughly the last 30 days, so `days_back` is capped at 30.
    """
    client = client or _get_newsapi_client()
    days_back = max(1, min(days_back, 30))
    from_date = (date.today() - timedelta(days=days_back)).isoformat()

    response = client.get_everything(
        q=query,
        language="en",
        sort_by=sort_by,
        from_param=from_date,
        page_size=page_size,
    )
    if response.get("status") != "ok":
        raise RuntimeError(f"NewsAPI error: {response.get('message', 'unknown error')}")
    return response.get("articles", [])


def summarize_articles(articles: List[Dict[str, Any]]) -> str:
    """
    PDF behaviour: join the article descriptions with a space.
    (Safe against missing/removed descriptions, which would crash the PDF version.)
    """
    summaries = [
        a["description"].strip()
        for a in articles
        if a.get("description") and a["description"] != "[Removed]"
    ]
    return " ".join(summaries)


def format_articles(articles: List[Dict[str, Any]]) -> str:
    """
    Richer version used by the app: numbered list with source, date, title and
    description, so the summary can cite sources. Skips removed/empty articles.
    """
    blocks = []
    for i, art in enumerate(articles, start=1):
        title = (art.get("title") or "").strip()
        desc = (art.get("description") or "").strip()
        if not title or title == "[Removed]" or not desc:
            continue
        source = (art.get("source") or {}).get("name", "Unknown")
        published = (art.get("publishedAt") or "")[:10]
        blocks.append(f"{i}. [{source} | {published}] {title}\n   {desc}")
    return "\n".join(blocks)


_SENTIMENT_RE = re.compile(
    r"overall\s+sentiment\s*[:\-]\s*[*_\s]*(positive|negative|neutral|mixed)", re.IGNORECASE
)


def extract_sentiment(summary: str) -> str:
    """Pull the 'Overall sentiment: X' label out of an LLM summary ('Unknown' if absent)."""
    matches = _SENTIMENT_RE.findall(summary or "")
    return matches[-1].capitalize() if matches else "Unknown"


def get_summary(query: str, **kwargs) -> str:
    """PDF behaviour: fetch articles for `query` and return their joined descriptions."""
    articles = get_news_articles(query, **kwargs)
    return summarize_articles(articles)


def research(
    query: str,
    model: str = DEFAULT_MODEL,
    page_size: int = 10,
    days_back: int = 7,
    sort_by: str = "relevancy",
) -> Dict[str, Any]:
    """
    End-to-end helper used by the Streamlit app.

    Returns {"summary": str, "articles": list, "sentiment": str}.
    """
    articles = get_news_articles(
        query, page_size=page_size, days_back=days_back, sort_by=sort_by
    )
    article_text = format_articles(articles)
    if not article_text:
        return {
            "summary": "No relevant news articles were found for this query. "
            "Try different keywords or a longer time range.",
            "articles": [],
            "sentiment": "Unknown",
        }
    chain = build_llm_chain(model=model)
    summary = chain.invoke({"query": query, "summaries": article_text})
    return {
        "summary": summary,
        "articles": articles,
        "sentiment": extract_sentiment(summary),
    }
