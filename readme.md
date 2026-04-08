# National Risk Intelligence Platform (MODEL-X)

Streamlit-based risk intelligence platform focused on Sri Lanka. The system collects news and social signals, scores risk severity with a deterministic AI pipeline, stores records in SQLite, and presents live operational dashboards.

## Overview

This project provides:

- Continuous background ingestion from multiple data sources.
- Risk scoring using sentiment + crisis language + source reliability.
- Industry classification (Energy, Logistics, Finance, Tourism, Agriculture, Public Safety).
- Real-time Streamlit dashboards for geospatial, analytics, and feed monitoring.
- Data-source health monitoring dashboard.

## Current Capabilities

- Auto-start background collector from the main Streamlit app.
- Multi-source news ingestion with fallback strategy:
  - RSS feeds
  - NewsAPI (if `NEWS_API_KEY` is configured)
  - GDELT fallback
  - World Bank macro indicator enrichment
- Reddit ingestion from multiple Sri Lanka-related subreddits with relevance filtering.
- Deterministic risk scoring (`1-10`) using:
  - VADER sentiment
  - Crisis keyword weights
  - Source reliability weighting
  - Industry risk weighting
- SQLite persistence with deduplication (`INSERT OR IGNORE` with deterministic hash ID).
- Dashboard features:
  - Live metrics
  - Geospatial risk points
  - Activity trends
  - Trending keywords
  - Risk score distribution
  - Industry impact view
  - Live risk feed
  - CSV export
  - Demo crisis simulation injection

## Project Structure

```text
National-Risk-Intelligence-Platform/
  process.readme
  readme.md
  requirements.txt
  requirements-combined.txt
  app/
    app.py
    collector.py
    config.py
    database_manager.py
    populate_data.py
    data/
    logs/
    modules/
      news.py
      social.py
    pages/
      health_monitor.py
    utils/
      health.py
      resilience.py
      sources.py
  tests/
    conftest.py
    test_database.py
    test_ingestion_parsing.py
    test_scoring.py
```

## Runtime Flow

1. Start Streamlit with `app/app.py`.
2. App initializes and auto-starts background collector thread.
3. Collector runs every `MODELX_REFRESH_INTERVAL` seconds.
4. Collector pipeline:
   - Collect news via multi-source fallback.
   - Collect Reddit posts via RSS.
   - Score each item with deterministic risk analysis.
   - Insert deduplicated results into SQLite.
5. Dashboard reads data from DB and renders live visualizations.

## Requirements

- Python 3.10+
- pip
- Internet access for external feeds/APIs

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/app.py
```

Open:

- Main dashboard: `http://localhost:8501`

For the health dashboard page, use Streamlit multipage navigation and open the "Health Monitor" page.

## Configuration

Environment variables used by the app:

- `MODELX_DB_PATH`
  - SQLite database path.
  - Default: `app/data/modelx.db`
- `MODELX_REFRESH_INTERVAL`
  - Collector polling interval in seconds.
  - Default: `120`
- `MODELX_FETCH_LIMIT`
  - Max records fetched per collection cycle.
  - Default: `20`
- `MODELX_AUTO_REFRESH_DEFAULT`
  - Default state of UI auto-refresh toggle.
  - Default: `true`

Optional source configuration:

- `NEWS_API_KEY`
  - Enables NewsAPI collection path in multi-source strategy.
- `WORLD_BANK_COUNTRY`
  - World Bank country code (default `LKA`).
- `WORLD_BANK_INDICATORS`
  - Comma-separated indicator codes.
- `HISTORICAL_LOOKBACK_DAYS`
  - Historical enrichment window.
- `GDELT_REQUEST_DELAY_SECONDS`
  - Delay between GDELT query calls.

## Data Sources

### News

- RSS sources from `app/modules/news.py` (active/inactive list in `NEWS_SOURCES`).
- NewsAPI when configured.
- GDELT as global fallback and historical enrichment.
- World Bank indicators for macroeconomic context.

### Social

- Reddit RSS from configured subreddits.
- Relevance filtering removes low-signal chatter and historical-only posts.

## Database

- Engine: SQLite (`app/database_manager.py`)
- Core table: `risks`
- Additional tracking tables:
  - `historical_collection`
  - `locations`
  - `risk_trends`
  - `data_collection_logs`
- Deduplication:
  - Transient IDs are converted to deterministic MD5 IDs from `source + signal`.
  - Uses `INSERT OR IGNORE` to avoid duplicate rows.

## Testing

Run tests from repository root:

```bash
pytest -q
```

Current test files:

- `tests/test_database.py`
- `tests/test_ingestion_parsing.py`
- `tests/test_scoring.py`

## Utility Scripts

- `app/populate_data.py`
  - Injects sample simulation records into DB for dashboard demos.

## Notes

- If you run from different working directories, ensure `MODELX_DB_PATH` points to one canonical DB file.
- Streamlit app starts the collector automatically; avoid running multiple app instances against the same DB during demos.

## License

No license file is currently included.