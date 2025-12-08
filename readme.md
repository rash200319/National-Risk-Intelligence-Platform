
# MODEL-X: National Risk Intelligence Platform

MODEL-X is a real-time situational awareness and risk intelligence platform designed for the Sri Lankan business context. It aggregates unstructured data from multiple news sources and social media channels to detect, analyze, and visualize operational risks such as economic instability, natural disasters, and civil unrest.

The system is built as a multi-threaded ETL (Extract, Transform, Load) pipeline that processes data using Natural Language Processing (NLP) for sentiment analysis and industry tagging, presenting actionable insights via an interactive dashboard.

## Key Features

- **Real-Time Data Aggregation**: Automatically fetches breaking news and updates from over 16 Sri Lankan news RSS feeds and Reddit discussions every 5 minutes.
- **Deduplication Engine**: Implements a deterministic hashing algorithm to generate unique identifiers for every news item, preventing duplicate entries in the database.
- **AI-Powered Analysis**:
  - **Sentiment Scoring**: Uses NLP (TextBlob) to analyze the tone of each article (Positive/Negative) to assist in risk scoring.
  - **Industry Tagging**: Automatically categorizes risks into relevant sectors such as Energy, Finance, Logistics, and Agriculture based on keyword analysis.
  - **Geospatial Intelligence**: Maps risk events to specific locations across Sri Lanka to provide geographical context.
- **Business Intelligence Dashboard**:
  - Activity Trends: Automatically switches between hourly and daily views based on data volume.
  - Trending Topics: Visualizes high-frequency keywords to identify emerging narratives.
  - Critical Alerts: Highlights high-risk events that require immediate attention.
- **Crisis Simulation (Demo Mode)**: Includes a simulation tool to inject high-priority risk events for demonstration and testing purposes.

## Technical Architecture

The system follows a modular architecture comprising a backend collector, a persistent database, and a frontend visualization layer.

- **Collector Module**: A background thread that polls RSS feeds and APIs. It handles connection errors gracefully and parses unstructured text into structured records.
- **Processing Layer**: Cleans text, generates hash IDs for deduplication, calculates sentiment scores, and assigns risk levels (1-10) based on keyword severity.
- **Storage Layer**: Uses SQLite with Write-Ahead Logging (WAL) enabled to support concurrent reading and writing, ensuring the dashboard remains responsive while data is being collected.
- **Presentation Layer**: A Streamlit-based web interface that provides interactive charts (Plotly), maps, and searchable data tables.

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation Steps

1. Clone the repository to your local machine.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory (optional, if API keys are required for future extensions).

### Running the Application

To start the platform, run the following command in your terminal:

```bash
streamlit run app.py
```

The dashboard will launch in your default web browser at `http://localhost:8501`. The data collector will start automatically in the background.

## Usage Guide

- **Dashboard Overview**: The main page displays key metrics including total logs, critical alerts, and active sources.
- **Map View**: Select the "Geospatial View" tab to see risk events plotted on the map of Sri Lanka.
- **Analytics**: The "Business Analytics" tab provides trend lines, risk severity distributions, and industry impact charts.
- **Risk Feed**: The "Live Risk Feed" tab lists individual alerts with sentiment scores and source links.
- **Filters**: Use the sidebar to filter data by specific industries (e.g., Finance, Logistics) or search for keywords.
- **Simulation**: For demonstration purposes, use the "Simulate Crisis" button in the sidebar to inject a mock critical event.

## Dependencies

- Streamlit: Frontend framework.
- Pandas: Data manipulation and analysis.
- Plotly: Interactive charting.
- TextBlob: Sentiment analysis.
- WordCloud / Matplotlib: Keyword visualization.
- Feedparser: RSS feed aggregation.
- SQLite3: Database management.

## License

This project is developed for the MODEL-X Hackathon.
