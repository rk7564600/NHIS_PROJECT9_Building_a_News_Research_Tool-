# 📈 Equity Research News Tool

An LLM-powered news research assistant for equity research analysts. Enter a query
(a company, sector or event) and the tool fetches the latest news from **NewsAPI**,
then uses **LangChain + OpenAI** to produce an executive summary, key developments
and an overall sentiment, all inside a **Streamlit** web app.

## Features
- Live news search via NewsAPI (configurable number of articles, time range, sort order)
- LangChain pipeline (`prompt | ChatOpenAI | StrOutputParser`) tuned for equity research
- Summary with executive overview, bullet-point developments and a sentiment label
- Source article list with links
- **Login** (username + password from `.env`) to restrict access
- **Saved queries** stored in SQLite: save, reopen, export and delete results
- **Trends tab** (dashboard): sentiment over time, sentiment distribution and history table
- Export of any summary as Markdown
- Graceful error handling (missing keys, API limits, no results)
- API keys and passwords kept in `.env`, never in source code

## Project structure
```
news_research_tool/
├── app.py                # Streamlit UI (Search / Saved queries / Trends tabs)
├── langchain_config.py   # NewsAPI + LangChain logic, sentiment extraction
├── auth.py               # login check
├── storage.py            # SQLite: saved queries + history
├── smoke_test.py         # real end-to-end check with your keys (Phase 5)
├── requirements.txt
├── .env.example          # copy to .env and fill in
├── .gitignore
└── tests/                # mocked unit tests (no keys needed)
```

## Setup

### 1. Install dependencies (Task 1.1)
Python 3.9+ recommended, ideally inside a virtualenv:
```bash
pip install -r requirements.txt
```
(This covers the PDF's `pip install langchain openai streamlit newsapi-python`, plus
`langchain-openai`, `pandas`, `python-dotenv` and `pytest`.)

### 2. Get the API keys (Task 1.2)
**OpenAI key**
1. Sign up at https://platform.openai.com and open the API section of the dashboard.
2. Add billing details. OpenAI bills per token, so check current pricing and set a
   usage limit or alert in the dashboard to avoid surprises.
3. Create a new API key and copy it (it is shown only once).

**NewsAPI key**
1. Sign up at https://newsapi.org (Get API Key) with name, email and password.
2. Verify your email with the link they send.
3. Log in to your account page and copy the API key.
4. The free **Developer** plan is for development only (limited daily requests, ~30
   days of history); upgrade to a paid plan for production use.

### 3. Configure
```bash
cp .env.example .env     # Windows: copy .env.example .env
```
Edit `.env`: paste both keys and set `AUTH_USERNAME` / `AUTH_PASSWORD`.
To avoid keeping the password in clear text, set `AUTH_PASSWORD_SHA256` instead:
```bash
python -c "import hashlib;print(hashlib.sha256(b'your-password').hexdigest())"
```
Never commit `.env` (it is already in `.gitignore`).

### 4. Run the app (Task 3.3)
```bash
streamlit run app.py
```

## Usage
1. Log in.
2. **Search** tab: type a query such as `Tesla Q3 earnings`, `HDFC Bank merger`, `RBI repo rate`, adjust the sidebar settings if needed, click **Get News**.
3. Click **Save result** to keep it. Export it as `.md` if you want a copy.
4. **Saved queries** tab: reopen or delete earlier results.
5. **Trends** tab: see how sentiment for a query has moved across your saved runs.

## Testing and validation (Phase 5)
- **Unit tests** (mocked, no keys or internet needed):
  ```bash
  pytest -q
  ```
- **Real end-to-end check** with your keys:
  ```bash
  python smoke_test.py "Reliance Industries"
  ```
  It confirms both APIs work and prints the summary next to the numbered source
  articles. For accuracy validation (Task 5.2), check that each point in the summary
  is supported by one of the listed articles and that the sentiment label matches the
  headlines.

## Where each PDF task lives
| PDF task | Where |
|---|---|
| 1.1 Install libraries | `requirements.txt` |
| 1.2 API keys | this README, `.env.example` |
| 2.1 / 2.2 `langchain_config.py`, OpenAI, prompt | `langchain_config.py` (`openai`, `template`, `prompt`, `llm_chain`) |
| 3.1 - 3.3 `app.py`, UI, run | `app.py` (Search tab) |
| 4.1 NewsAPI | `langchain_config.py` (`newsapi`, `get_news_articles`, `summarize_articles`, `get_summary`, 2-variable prompt) |
| 4.2 App uses enhanced config | `app.py` calls `research()` (fetch + format + `llm_chain`) |
| 5.1 / 5.2 Testing | `tests/`, `smoke_test.py` |
| 6.1 / 6.2 Docs, deployment prep | docstrings, this README, `requirements.txt` |
| 7.1 Authentication | `auth.py` + login screen in `app.py` |
| 7.2 UI/UX | tabs, sidebar settings, spinner, expanders, charts |
| 7.3 Extra features | `storage.py` (saved queries), Trends tab, Markdown export |

The PDF's code uses `from langchain import OpenAI, LLMChain`, which no longer exists in
current LangChain. The tool keeps the PDF's names and call style (`llm_chain.run({...})`)
but builds them with `langchain-openai` and `prompt | llm | parser`.

## Notes
- Summaries are generated from article titles/descriptions, not full article text.
- The login is a single shared account, suitable for a small private deployment. For a
  public production app, put the tool behind a proper identity provider.
- GitHub only stores the code. To get a live link, deploy the repo (for example on
  Streamlit Community Cloud) and put the keys and login password in its Secrets/env settings.
- This tool is for research support and is **not financial advice**.
