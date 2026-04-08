# National Risk Intelligence Platform (MODEL-X)

A Streamlit-based risk intelligence system for Sri Lanka that continuously collects news from RSS feeds, Reddit, and GDELT, applies deterministic risk scoring, and presents data through interactive dashboards with geospatial visualization and health monitoring.

## Overview

**Core Functionality:**
- Continuous background data collection from 9+ sources (RSS feeds, Reddit, GDELT, World Bank indicators)
- Deterministic risk scoring (1-10 scale) based on sentiment, crisis keywords, source reliability, and industry classification
- SQLite database with automatic deduplication
- Multi-tab Streamlit dashboards with geospatial maps, analytics, live feeds, and source health monitoring
- CSV export of filtered data

## Implemented Features

**Data Collection:**
- Sri Lankan news RSS feeds
- Sri Lanka-related subreddits with relevance filtering
- GDELT global events database (no API key required)
- World Bank macroeconomic indicators (inflation, GDP, unemployment)
- NewsAPI integration (optional, requires `NEWS_API_KEY` environment variable)

**Risk Scoring Algorithm (Deterministic):**
- Base score: 4.0, adjusted by:
  - VADER sentiment analysis (negative sentiment increases risk)
  - Crisis keyword detection (26+ weighted terms: crisis, emergency, attack, violence, etc.)
  - Source reliability weighting (NewsAPI: 0.95, GDELT: 0.85, RSS: 0.80, Reddit: 0.55)
  - Industry classification boost (Energy, Logistics, Finance, Tourism, Agriculture, Public Safety)
  - Confidence scoring based on text length, keyword strength, and sentiment magnitude
- Final score clamped to 1-10 range

**Dashboard Visualization:**
1. **Geospatial View** - Interactive Pydeck map of Sri Lanka with risk points color-coded by severity
2. **Business Analytics** - Activity trends, trending keywords, risk distribution histogram, industry impact pie chart
3. **Live Risk Feed** - Top 20 risks displayed as cards with source, score, sentiment, category, and links
4. **Health Monitor** - Source status table, performance graphs, collection logs, detailed statistics

**Core Operations:**
- Auto-start background collector thread (configurable interval, default 120 seconds)
- Multi-source fallback strategy with retry logic (exponential backoff with jitter)
- SQLite persistence with MD5-based deduplication
- 30-day historical data retrieval from GDELT
- Sidebar controls: collector start/stop, filtering, settings, demo crisis injection, CSV export

## Project Structure

```text
National-Risk-Intelligence-Platform/
  readme.md
  requirements.txt
  runtime.txt
  .env (configuration)
  app/
    app.py               (Main Streamlit app with dashboards)
    collector.py         (Background data collector & risk scoring)
    config.py            (Configuration management)
    database_manager.py  (SQLite operations)
    populate_data.py     (Data seeding utility)
    data/                (SQLite database)
    logs/                (Collection logs)
    modules/
      news.py            (RSS & NewsAPI collection)
      social.py          (Reddit collection with filtering)
    pages/
      health_monitor.py  (Source health dashboard)
    utils/
      sources.py         (Multi-source fallback strategy)
      health.py          (Source health tracking)
      resilience.py      (Retry logic & resilience)
  tests/
    conftest.py
    test_database.py
    test_ingestion_parsing.py
    test_scoring.py
```

## Runtime Flow

1. Start Streamlit from the repository root: `streamlit run app/app.py`
2. App initializes database and auto-starts background collector thread
3. Collector runs every `MODELX_REFRESH_INTERVAL` seconds (default: 120 seconds)
4. Collector pipeline per cycle:
   - Fetch news from RSS feeds with retry logic
   - Fetch Reddit posts from 8 subreddits with relevance filtering
   - Fetch GDELT global events (no API key required)
   - Fetch World Bank macroeconomic indicators
   - Apply deterministic risk scoring to each item
   - Deduplicate against existing database (MD5-based)
   - Insert new records into SQLite
5. Dashboard reads from database and renders live visualizations in 3 main tabs + health monitor

## Requirements

- Python 3.10+
- pip
- Internet connection (for RSS feeds, GDELT, World Bank APIs, and Reddit)

### Dependencies

Core packages include:
- Streamlit (dashboards)
- pandas (data manipulation)
- requests (HTTP requests)
- feedparser (RSS parsing)
- newspaper3k (article extraction)
- praw (Reddit API)
- nltk (VADER sentiment)
- pydeck (geospatial maps)
- plotly (interactive charts)
- tenacity (retry logic)

Install all dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Clone and Setup

```bash
cd National-Risk-Intelligence-Platform
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env` template and set API keys (optional):

```bash
# Edit .env with your configuration
# NEWS_API_KEY is optional - system will fallback to RSS + GDELT if not set
# WORLD_BANK_COUNTRY and indicators are pre-configured for Sri Lanka
```

### 3. Run the Application

```bash
streamlit run app/app.py
```

The app will:
- Open at `http://localhost:8501`
- Auto-start the background collector thread
- Display three main dashboards: Geospatial View, Business Analytics, Live Risk Feed
- Provide source health monitoring page

### 4. Using the Interface

**Sidebar Controls:**
- **Collector Status**: View collector health and thread status
- **Search & Filters**: Search by text, filter by sector, select specific sources
- **Settings**: Adjust collection interval and auto-refresh rate
- **Demo Crisis**: Inject test risk scenarios for demonstration
- **Export**: Download filtered data as CSV

### Running Tests

```bash
pytest tests/
```

## Environment Configuration

Configure the app via `.env` file in the repository root. Required and optional settings:

**Core Runtime:**
- `MODELX_DB_PATH` - SQLite database path (default: `app/data/modelx.db`)
- `MODELX_REFRESH_INTERVAL` - Collector polling interval in seconds (default: `120`)
- `MODELX_FETCH_LIMIT` - Max records fetched per cycle (default: `20`)
- `MODELX_AUTO_REFRESH_DEFAULT` - Dashboard auto-refresh toggle (default: `true`)

**Optional APIs:**
- `NEWS_API_KEY` - NewsAPI key for news aggregation (optional; system falls back to RSS + GDELT if not set)
- `MASSIVE_API_KEY` - (Reserved for future use)
- `TWITTER_API_*` - Twitter integration (not currently implemented)

**World Bank Indicators:**
- `WORLD_BANK_COUNTRY` - Country code (default: `LKA` for Sri Lanka)
- `WORLD_BANK_INDICATORS` - Comma-separated indicator codes (e.g., `FP.CPI.TOTL.ZG,NY.GDP.MKTP.KD.ZG,SL.UEM.TOTL.ZS`)

## Data Architecture

### Collection Pipeline

Sources are queried in priority order with automatic fallback:

1. **NewsAPI** (if `NEWS_API_KEY` configured)
2. **RSS Feeds** (10 active Sri Lankan news feeds)
3. **Reddit** (8 subreddits with relevance filtering)
4. **GDELT** (global events, no auth required)
5. **World Bank** (macroeconomic indicators)

Each item is scored using the deterministic risk algorithm, deduplicated via MD5 hash, and inserted into SQLite.

### Database Schema

**Main Table: `risks`**
- `id` - MD5 hash (source + signal) for deterministic deduplication
- `source` - Data origin (e.g., "Ada Derana RSS", "Reddit", "GDELT")
- `signal` - Headline or title
- `link` - URL to original source
- `published` - Publication timestamp
- `risk_score` - Computed risk (1-10 scale)
- `sentiment_score` - VADER sentiment (-1 to +1)
- `category` - Industry classification
- `location`, `district`, `province` - Geographic tags
- `confidence` - Score confidence (0-1)
- `keywords` - Detected crisis keywords
- `created_at`, `updated_at` - Record timestamps

**Supporting Tables:**
- `historical_collection` - Collection event tracking
- `locations` - Sri Lanka geographic reference data
- `risk_trends` - Time series aggregations
- `data_collection_logs` - Audit trail

### Risk Scoring Algorithm

Each collected item is scored deterministically (1-10):

```
Base Score: 4.0

Adjustments:
+ Sentiment: -sentiment_compound × 1.5 (negative ↑ risk)
+ Crisis Keywords: min(crisis_strength, 5.0) × 1.0
+ Source Reliability: (reliability - 0.7) × 2.0
+ Industry Risk: +0.6 (high-risk) or +0.3 (medium)
- Question Discount: -1.0 (if contains "?")
- Historical Discount: -1.0 (if references old dates)

Minimum Boost: 8.0 if ≥3.5 crisis strength + ≥2 keywords matched

Final Score: clamp(computed_score, 1, 10)
```

**Confidence Score** combines:
- Source reliability (45%)
- Text length normalization (20%)
- Keyword signal strength (25%)
- Sentiment magnitude (10%)

**Source Reliability Weights:**
- NewsAPI: 0.95
- GDELT: 0.85
- World Bank: 0.90
- RSS feeds: 0.80
- Reddit: 0.55

**Detected Industries:** Energy & Fuel, Logistics & Transport, Finance & Economy, Tourism, Agriculture, Public Safety

## Testing

Run test suite:

```bash
pytest tests/ -v
```

Test files:
- `tests/test_database.py` - SQLite operations and deduplication
- `tests/test_ingestion_parsing.py` - Data collection and parsing
- `tests/test_scoring.py` - Risk scoring algorithm

## Utility Scripts

- `app/populate_data.py`
  - Injects sample simulation records into DB for dashboard demos.

## Notes

- If you run from different working directories, ensure `MODELX_DB_PATH` points to one canonical DB file.
- Streamlit app starts the collector automatically; avoid running multiple app instances against the same DB during demos.

## License

No license file is currently included.
