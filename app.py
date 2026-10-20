"""
app.py
------
Streamlit interface for the Equity Research News Tool.
Run with:  streamlit run app.py

Tabs:  Search | Saved queries | Trends (historical sentiment)
"""

import os

import pandas as pd
import streamlit as st

# Deployment: on Streamlit Community Cloud the keys are entered under "Secrets".
# Copy them into environment variables so the rest of the code (which reads
# os.getenv / .env) works unchanged. A real environment variable always wins.
def _export_secrets(mapping):
    for _name, _value in mapping.items():
        if isinstance(_value, (str, int, float, bool)):
            os.environ.setdefault(str(_name), str(_value))
        elif hasattr(_value, "items"):  # [section] tables in secrets.toml
            _export_secrets(_value)


try:
    _export_secrets(st.secrets)
except Exception:  # no secrets configured: local runs use the .env file
    pass

import storage  # noqa: E402
from auth import auth_enabled, is_configured, verify_login  # noqa: E402
from langchain_config import NEWSAPI_KEY, OPENAI_API_KEY, research  # noqa: E402

st.set_page_config(page_title="Equity Research News Tool", page_icon="📈", layout="wide")
storage.init_db()


# ---------------------------------------------------------------- Login (Task 7.1)
def login_gate() -> str:
    """Return the logged-in username, or show the login form and stop the script."""
    if not auth_enabled():
        return "guest"
    if st.session_state.get("user"):
        return st.session_state["user"]

    st.title("📈 Equity Research News Tool")
    if not is_configured():
        st.error(
            "Login is enabled but no password was found. Locally: add AUTH_USERNAME and "
            "AUTH_PASSWORD (or AUTH_PASSWORD_SHA256) to your .env file. On Streamlit "
            "Cloud: add them under App settings > Secrets, save, then reboot the app."
        )
        _names = ("OPENAI_API_KEY", "NEWSAPI_KEY", "AUTH_USERNAME", "AUTH_PASSWORD", "AUTH_PASSWORD_SHA256")
        st.caption(
            "Settings detected (names only): "
            + ", ".join(f"{n} {'✓' if os.getenv(n) else '✗'}" for n in _names)
        )
        st.stop()
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in", type="primary"):
            if verify_login(username, password):
                st.session_state["user"] = username.strip()
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.stop()


user = login_gate()

# ---------------------------------------------------------------- Sidebar
with st.sidebar:
    st.caption(f"Signed in as **{user}**")
    if auth_enabled() and st.button("Log out"):
        st.session_state.clear()
        st.rerun()

    st.header("⚙️ Settings")
    model = st.selectbox("OpenAI model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"])
    page_size = st.slider("Number of articles", 5, 30, 10)
    days_back = st.slider("Look back (days)", 1, 30, 7)
    sort_by = st.selectbox("Sort articles by", ["relevancy", "publishedAt", "popularity"])

    st.divider()
    st.subheader("🕘 Recent saved queries")
    recent = storage.list_queries(user)[:8]
    if recent:
        for item in recent:
            st.caption(f"• {item['query']}  ({item['created_at'][:16].replace('T', ' ')})")
    else:
        st.caption("Nothing saved yet.")

# ---------------------------------------------------------------- Main
st.title("📈 Equity Research News Tool")

missing = [
    name
    for name, val in (("OPENAI_API_KEY", OPENAI_API_KEY), ("NEWSAPI_KEY", NEWSAPI_KEY))
    if not val
]
if missing:
    st.error(
        f"Missing: {', '.join(missing)}. Copy `.env.example` to `.env`, add your keys, "
        "and restart the app."
    )
    st.stop()

tab_search, tab_saved, tab_trends = st.tabs(["🔎 Search", "💾 Saved queries", "📊 Trends"])


def show_articles(articles):
    if not articles:
        return
    st.markdown("### Source articles")
    for art in articles:
        title = art.get("title") or "Untitled"
        if title == "[Removed]":
            continue
        source = art.get("source")
        source = source.get("name", "Unknown") if isinstance(source, dict) else (source or "Unknown")
        published = (art.get("publishedAt") or "")[:10]
        with st.expander(f"{title} — {source} ({published})"):
            st.write(art.get("description") or "No description available.")
            if art.get("url"):
                st.markdown(f"[Read full article]({art['url']})")


# ---- Search tab
with tab_search:
    st.write("Enter your query to get the latest news articles summarized.")
    query = st.text_input(
        "Query", placeholder="e.g. Tesla Q3 earnings, HDFC Bank merger, RBI rate decision"
    )

    if st.button("Get News", type="primary"):
        if not query.strip():
            st.warning("Please enter a query.")
        else:
            try:
                with st.spinner("Fetching news and generating summary..."):
                    result = research(
                        query.strip(),
                        model=model,
                        page_size=page_size,
                        days_back=days_back,
                        sort_by=sort_by,
                    )
            except Exception as exc:  # network, quota, invalid key etc.
                st.error(f"Something went wrong: {exc}")
            else:
                st.session_state["last"] = {"query": query.strip(), "result": result, "saved": False}

    last = st.session_state.get("last")
    if last:
        res = last["result"]
        st.markdown("### Summary:")
        st.write(res["summary"])
        st.caption(f"Detected sentiment: **{res['sentiment']}**")

        col1, col2, _ = st.columns([1, 1, 4])
        with col1:
            if last["saved"]:
                st.button("✅ Saved", disabled=True)
            elif st.button("💾 Save result"):
                storage.save_query(
                    user, last["query"], res["summary"], res["sentiment"], res["articles"]
                )
                last["saved"] = True
                st.rerun()
        with col2:
            st.download_button(
                "⬇️ Export (.md)",
                data=f"# {last['query']}\n\n{res['summary']}\n",
                file_name="news_summary.md",
                mime="text/markdown",
            )
        show_articles(res["articles"])

# ---- Saved queries tab
with tab_saved:
    saved = storage.list_queries(user)
    if not saved:
        st.info("No saved queries yet. Run a search and click **Save result**.")
    else:
        labels = {
            s["id"]: f"{s['created_at'][:16].replace('T', ' ')} — {s['query']} [{s['sentiment']}]"
            for s in saved
        }
        chosen = st.selectbox("Select a saved query", list(labels), format_func=labels.get)
        item = next(s for s in saved if s["id"] == chosen)
        st.markdown(f"### {item['query']}")
        st.caption(f"Saved {item['created_at']} · {item['n_articles']} articles · {item['sentiment']}")
        st.write(item["summary"])
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            st.download_button(
                "⬇️ Export (.md)",
                data=f"# {item['query']}\n\n{item['summary']}\n",
                file_name=f"news_summary_{item['id']}.md",
                mime="text/markdown",
                key=f"dl_{item['id']}",
            )
        with c2:
            if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                storage.delete_query(user, item["id"])
                st.rerun()
        show_articles(item["articles"])

# ---- Trends tab (historical analysis)
with tab_trends:
    saved = storage.list_queries(user)
    if len(saved) < 1:
        st.info("Save a few results to see sentiment history here.")
    else:
        df = pd.DataFrame(saved)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["score"] = df["sentiment"].map(storage.sentiment_score)

        options = ["All queries"] + sorted(df["query"].unique().tolist())
        pick = st.selectbox("Filter by query", options)
        view = df if pick == "All queries" else df[df["query"] == pick]

        m1, m2, m3 = st.columns(3)
        m1.metric("Saved results", len(view))
        scored = view["score"].dropna()
        m2.metric("Average sentiment (-1 to +1)", f"{scored.mean():.2f}" if len(scored) else "n/a")
        m3.metric("Articles analysed", int(view["n_articles"].sum()))

        st.markdown("#### Sentiment over time (-1 = negative, +1 = positive)")
        series = view.dropna(subset=["score"]).sort_values("created_at").set_index("created_at")["score"]
        if len(series):
            st.line_chart(series)
        else:
            st.caption("No scored results yet.")

        st.markdown("#### Sentiment distribution")
        st.bar_chart(view["sentiment"].value_counts())

        st.markdown("#### History")
        st.dataframe(
            view[["created_at", "query", "sentiment", "n_articles"]].sort_values(
                "created_at", ascending=False
            ),
            width="stretch",
            hide_index=True,
        )
