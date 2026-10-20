"""
smoke_test.py  (Phase 5: real end-to-end check with YOUR keys)
-------------------------------------------------------------
Usage:
    python smoke_test.py                       # default query
    python smoke_test.py "HDFC Bank merger"    # your own query

What it does
  5.1  Verifies keys are set, NewsAPI returns articles, and the LLM returns a summary.
  5.2  Prints the summary next to the numbered source articles so you can manually
       check accuracy: every claim in the summary should be traceable to a listed
       article, and the sentiment label should match the headlines.

Exit code 0 = all checks passed, 1 = a check failed.
"""

import sys

import langchain_config as cfg


def check(ok: bool, label: str) -> bool:
    print(("PASS  " if ok else "FAIL  ") + label)
    return ok


def main() -> int:
    query = " ".join(sys.argv[1:]).strip() or "Reliance Industries"
    print(f"Query: {query}\n")

    ok = check(bool(cfg.OPENAI_API_KEY), "OPENAI_API_KEY is set")
    ok &= check(bool(cfg.NEWSAPI_KEY), "NEWSAPI_KEY is set")
    if not ok:
        return 1

    try:
        result = cfg.research(query, page_size=8, days_back=14)
    except Exception as exc:
        check(False, f"research() ran without error ({exc})")
        return 1

    articles = [a for a in result["articles"] if a.get("title") != "[Removed]"]
    ok &= check(len(articles) > 0, f"NewsAPI returned articles ({len(articles)})")
    ok &= check(len(result["summary"].strip()) > 50, "LLM returned a non-trivial summary")
    ok &= check(
        result["sentiment"] != "Unknown", f"Sentiment label detected ({result['sentiment']})"
    )

    print("\n" + "=" * 70 + "\nSUMMARY\n" + "=" * 70)
    print(result["summary"])
    print("\n" + "=" * 70 + "\nSOURCE ARTICLES (compare against the summary)\n" + "=" * 70)
    for i, a in enumerate(articles, 1):
        src = (a.get("source") or {}).get("name", "Unknown")
        print(f"{i}. [{src} | {(a.get('publishedAt') or '')[:10]}] {a.get('title')}")
        print(f"   {a.get('url')}")

    print("\nManual check (5.2): are all key points above supported by these articles?")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
