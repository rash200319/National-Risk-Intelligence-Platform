# MODEL-X: National Risk Intelligence Platform

**MODEL-X** is a real-time situational awareness and risk intelligence platform designed for the Sri Lankan business context. It aggregates unstructured data from multiple news sources and social media channels to detect, analyze, and visualize operational risks such as economic instability, natural disasters, and civil unrest.

The system is built as a multi-threaded **ETL (Extract, Transform, Load)** pipeline that processes data using NLP for sentiment analysis and industry tagging, presenting actionable insights via an interactive dashboard.

---

## 🚀 Key Features

### **Real-Time Data Aggregation**
- Automatically fetches breaking news and updates from over **16 Sri Lankan news RSS feeds** and **Reddit** every 5 minutes.

### **Deduplication Engine**
- Uses a **deterministic hashing algorithm** to generate unique IDs for every news item.
- Prevents duplicate entries in the database.

### **AI-Powered Analysis**
- **Sentiment Scoring:** NLP (TextBlob) determines tone (Positive/Negative) to support risk scoring.  
- **Industry Tagging:** Categorizes news into sectors like Energy, Finance, Logistics, and Agriculture based on keyword analysis.

### **Geospatial Intelligence**
- Maps risk events to specific Sri Lankan locations for added situational awareness.

### **Business Intelligence Dashboard**
- **Activity Trends:** Automatically switches between hourly and daily aggregation.  
- **Trending Topics:** Highlights frequently appearing keywords.  
- **Critical Alerts:** Flags high-risk events requiring immediate attention.  
- **Crisis Simulation (Demo Mode):** Injects mock high-priority events for showcasing and testing.

---

## 🏗️ Technical Architecture

MODEL-X follows a modular architecture with three major layers: **Collector**, **Processor**, and **Dashboard**.

### **Collector Module**
- Background thread polling RSS feeds and APIs.
- Handles connection failures gracefully.
- Converts unstructured text into structured objects.

### **Processing Layer**
- Cleans text and normalizes fields.
- Generates **hash IDs** for deduplication.
- Applies sentiment scoring.
- Assigns **risk levels (1–10)** based on keyword severity.

### **Storage Layer**
- SQLite database with **Write-Ahead Logging (WAL)** enabled.
- Supports concurrent reads/writes for high responsiveness.

### **Presentation Layer**
- Streamlit web interface.
- Interactive charts powered by Plotly.
- Keyword clouds, maps, and searchable data tables.

---

## 🛠️ Installation and Setup

### **Prerequisites**
- Python 3.8+
- pip (Python package manager)

### **Installation Steps**
1. Clone the repository.
2. Install dependencies:

```bash
pip install -r requirements.txt

## 🛠️ Optional Setup

### **Environment Variables (.env)**
You may create a `.env` file in the project root to store future API keys or configuration variables:



