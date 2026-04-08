import time
import random
import threading
import uuid
import logging
from datetime import datetime
from textblob import TextBlob  # <--- NEW: AI Sentiment
import pandas as pd
from database_manager import db
from config import FETCH_LIMIT, REFRESH_INTERVAL

# Import Feed Fetchers
from modules.news import fetch_news
from modules.social import get_reddit_rss

# --- INDUSTRY KEYWORDS (BUSINESS CONTEXT) ---
INDUSTRIES = {
    "Energy & Fuel": ["power", "electricity", "fuel", "gas", "petrol", "energy", "grid", "ceb", "cpc"],
    "Logistics & Transport": ["road", "traffic", "train", "bus", "port", "shipping", "airline", "flight", "transport"],
    "Finance & Economy": ["rupee", "dollar", "bank", "tax", "inflation", "stock", "market", "imf", "debt", "economy"],
    "Tourism": ["tourist", "hotel", "visa", "airport", "travel", "resort", "booking"],
    "Agriculture": ["farmer", "crop", "rice", "fertilizer", "food", "tea", "export"],
    "Public Safety": ["protest", "strike", "curfew", "police", "attack", "violence", "disaster", "flood"]
}

class RiskCollector:
    def __init__(self):
        self.is_running = False
        self.thread = None

    def _analyze_context(self, text):
        """
        AI Analysis: Returns (Risk Score, Sentiment Score, Industry List)
        """
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity  # -1.0 (Negative) to 1.0 (Positive)
        
        # 1. Base Risk on Sentiment
        # If sentiment is very negative (-0.5), Risk is High (8-9)
        # If sentiment is positive (+0.5), Risk is Low (1-2)
        if sentiment < -0.3:
            base_score = random.randint(7, 9)
        elif sentiment < 0:
            base_score = random.randint(5, 6)
        else:
            base_score = random.randint(1, 4)

        # 2. Boost Score for Crisis Keywords (The "Hard" Check)
        text_lower = text.lower()
        if any(x in text_lower for x in ['crisis', 'emergency', 'dead', 'kill', 'warning', 'alert']):
            base_score = max(base_score, 8)

        # 3. Detect Industries
        detected_industries = []
        for industry, keywords in INDUSTRIES.items():
            if any(k in text_lower for k in keywords):
                detected_industries.append(industry)
        
        if not detected_industries:
            detected_industries.append("General")

        return base_score, sentiment, ", ".join(detected_industries)

    def fetch_realtime(self):
        print("📡 Running Smart Collection Cycle...")
        
        # 1. NEWS COLLECTION
        try:
            news_items = fetch_news(limit_per_source=FETCH_LIMIT)
            if news_items:
                risks = []
                for item in news_items:
                    # Combine title and content for better AI context
                    full_text = f"{item.get('title', '')} {item.get('content', '')}"
                    
                    # --- AI PROCESSING ---
                    score, sentiment, industries = self._analyze_context(full_text)
                    
                    risks.append({
                        "id": f"news_{uuid.uuid4().hex[:8]}",
                        "source": item.get('source', 'News'),
                        "signal": item.get('title', ''),
                        "link": item.get('url', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,  # <--- Saving Industry instead of just "General"
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 1.0,
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(risks)
                print(f"   -> Processed {len(risks)} News items with AI.")
        except Exception as e:
            print(f"❌ News Error: {e}")

        # 2. REDDIT COLLECTION
        try:
            social_df = get_reddit_rss(limit=FETCH_LIMIT)
            if not social_df.empty:
                s_risks = []
                for _, row in social_df.iterrows():
                    full_text = f"{row.get('title', '')}"
                    score, sentiment, industries = self._analyze_context(full_text)

                    s_risks.append({
                        "id": f"reddit_{uuid.uuid4().hex[:8]}",
                        "source": row.get('source', 'Reddit'),
                        "signal": row.get('title', ''),
                        "link": row.get('link', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 0.8,
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(s_risks)
                print(f"   -> Processed {len(s_risks)} Reddit items with AI.")
        except Exception as e:
            print(f"❌ Reddit Error: {e}")

    def run_loop(self):
        while self.is_running:
            self.fetch_realtime()
            time.sleep(REFRESH_INTERVAL)

    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        print(f"🚀 AI Collector Started. Polling every {REFRESH_INTERVAL} seconds.")

collector = RiskCollector()