# MODEL-X: National Risk Intelligence Platform

This repository is a Streamlit-based risk intelligence prototype for Sri Lanka. It ingests RSS news and Reddit posts, assigns each item a risk score and industry tags, stores records in SQLite, and renders a live operations dashboard.

This README is based on the current codebase state and is intended to explain exactly what is implemented today.

## 1) What this project does

- Runs a Streamlit app from `app/app.py`.
- Starts a background collector thread automatically when the app starts.
- Fetches data from:
  - Multiple Sri Lankan news RSS feeds (`app/modules/news.py`)
  - Multiple Sri Lankan subreddits via RSS (`app/modules/social.py`)
- Analyzes text using TextBlob sentiment + keyword matching (`app/collector.py`).
- Persists data in SQLite (`app/database_manager.py`) with deduplication.
- Displays map bubbles, trend charts, keyword bars, severity histogram, industry impact pie, and a live feed (`app/app.py`).

## 2) End-to-end runtime flow

1. `app/app.py` runs under Streamlit.
2. `load_dotenv()` is called, then `start_background_collector()` starts `collector` in a daemon thread.
3. Collector loop (`RiskCollector.run_loop`) executes every 300 seconds:
   - Pull news items from `fetch_news(...)`
   - Pull Reddit posts from `get_reddit_rss(...)`
   - Score each item with `_analyze_context(...)`
   - Insert into DB via `db.batch_insert_risks(...)`
4. Streamlit UI repeatedly queries DB via:
   - `db.get_risks(limit=...)`
   - `db.get_risk_stats()`
5. Optional auto-refresh uses `streamlit-autorefresh` timers (no blocking sleep loop).

## 3) Current project structure (everything in workspace)

```text
National-Risk-Intelligence-Platform/
  .env.example
  documentation (2).pdf
  process.readme
  readme.md
  requirements.txt
  .vscode/
    settings.json
  app/
    app.py
    collector.py
    database_manager.py
    populate_data.py
    data/
      modelx.db
      modelx.db-shm
      modelx.db-wal
    logs/
      system.log
    modules/
      news.py
      social.py
      __pycache__/*.pyc
    __pycache__/*.pyc
  data/
    modelx.db
```

Notes:
- `__pycache__` files are generated artifacts.
- `*.db`, `*.db-shm`, and `*.db-wal` are runtime database files.
- `documentation (2).pdf` exists but is not referenced by Python code.
- There are two DB locations in workspace (`app/data/modelx.db` and `data/modelx.db`). Current default config uses `app/data/modelx.db`.

## 4) File-by-file explanation

### Root files

- `.env.example`
  - Contains environment-style settings and placeholders.
  - Currently includes duplicate `DATABASE_URL` entries and Twitter credential keys.
  - The current Python code does not actively read most of these env vars yet.

- `process.readme`
  - Legacy setup notes from an earlier structure.
  - Not fully aligned with the current `app/` layout.

- `requirements.txt`
  - Active dependency file for this repo.
  - Includes Streamlit, streamlit-autorefresh, feedparser, plotly, pydeck, textblob, and pytest.

- `.vscode/settings.json`
  - Adds Python analysis extra path to `app` for editor import resolution.

### App pipeline

- `app/app.py`
  - Streamlit UI entrypoint.
  - Loads dotenv and autostarts collector thread.
  - Uses `db.get_risks()` and `db.get_risk_stats()` for data.
  - Includes:
    - Sidebar filters and controls
    - CSV download
    - "Simulate Crisis" button that inserts a 3-event scenario
    - 3 tabs: geospatial, analytics, live feed
  - Uses simple location extraction by checking city names in signal text.

- `app/collector.py`
  - Background data collection service.
  - Core runtime values are loaded from env via `app/config.py`.
  - `_analyze_context(text)`:
    - Uses `TextBlob(...).sentiment.polarity`
    - Converts sentiment to risk score buckets
    - Boosts risk if crisis keywords appear
    - Maps keywords to industries
  - `fetch_realtime()`:
    - Ingests news + reddit
    - Constructs normalized records
    - Writes to DB through `db.batch_insert_risks(...)`

- `app/database_manager.py`
  - SQLite manager with WAL mode enabled.
  - Ensures DB parent directory exists from configured DB path.
  - Creates tables:
    - `risks`
    - `historical_collection`
    - `locations`
    - `risk_trends`
    - `data_collection_logs`
  - Dedup behavior:
    - Rewrites transient IDs (`news_*`, `reddit_*`) into deterministic MD5 hash of `source + signal`
    - Uses `INSERT OR IGNORE`
  - `get_risks(...)` now supports source and date filtering.
  - Exposes:
    - `insert_risk`
    - `batch_insert_risks`
    - `get_risks`
    - `get_risk_stats`

- `app/populate_data.py`
  - Inserts 5 simulation records directly into DB for testing map/chart behavior.
  - Uses raw SQL insert via `db._get_connection()`.

### Data source modules

- `app/modules/news.py`
  - Defines large RSS source list in `NEWS_SOURCES`.
  - `fetch_rss_feed(...)` parses feed entries and normalizes fields.
  - `fetch_news(...)` loops all active sources and returns consolidated, date-sorted items.
  - Includes historical fetch helpers.
  - `NEWS_API_KEY` currently hard-coded as `None` and not actively used for API calls.

- `app/modules/social.py`
  - Fetches subreddit RSS feeds with custom User-Agent.
  - Returns DataFrame of deduplicated posts by `link`.
  - Contains placeholder `fetch_twitter_data(...)` to avoid import failures.

### Runtime artifacts

- `app/logs/system.log`
  - Historical run logs.
  - Shows prior schema mismatch errors (`no column named category`) from older DB state.

- `app/data/modelx.db` (+ shm/wal)
  - Canonical runtime DB path by default.

- `data/modelx.db`
  - Additional DB file at root level.
  - May be from running scripts from a different working directory.

- `__pycache__/*.pyc`
  - Python bytecode cache files.

## 5) How to run (current, tested command shape)

From repository root:

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

Alternative from `app/`:

```bash
pip install -r ..\requirements.txt
streamlit run app.py
```

App URL: `http://localhost:8501`

## 6) Environment variables and config status

Current code behavior:
- `load_dotenv()` is called in `app/app.py` and `app/config.py`.
- Runtime values are env-driven:
  - `MODELX_DB_PATH`
  - `MODELX_REFRESH_INTERVAL`
  - `MODELX_FETCH_LIMIT`
  - `MODELX_AUTO_REFRESH_DEFAULT`

## 7) Known gaps and quirks (important)

- There are still two DB files in the repository tree (`app/data/modelx.db` and `data/modelx.db`) and this can confuse manual inspection.
- Test imports rely on `tests/conftest.py` path injection; package-style imports were not introduced yet.
- Duplicate DB files in two locations can cause confusion about which dataset is shown.

## 8) Suggested cleanup roadmap

1. Move all secrets out of `.env.example`, keep placeholders only.
2. Remove or archive `data/modelx.db` so only one DB file is kept for demos.
3. Keep env placeholders only in `.env.example` and never commit real secrets.
4. Expand the test suite with one Streamlit smoke test and one collector integration test.
5. Add a simple Makefile or task runner command for one-step setup.

## 9) License

No explicit license file is present in the repository at this time.
