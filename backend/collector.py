import time
import random
import threading
import hashlib  # <--- NEW: For creating unique fingerprints
from datetime import datetime
import pandas as pd
from database_manager import db

# Import Feed Fetchers
from modules.news import fetch_news
from modules.social import get_reddit_rss

# --- CONFIGURATION ---
REFRESH_INTERVAL = 300  # 5 Minutes
FETCH_LIMIT = 20        # Items per source

class RiskCollector:
    def __init__(self):
        self.is_running = False
        self.thread = None

    def _generate_id(self, source, unique_text):
        """Creates a consistent ID based on content."""
        raw_string = f"{source}_{unique_text}"
        return hashlib.md5(raw_string.encode()).hexdigest()

    def fetch_realtime(self):
        print("📡 Running Real-time Collection Cycle...")
        
        # 1. NEWS COLLECTION
        try:
            news_items = fetch_news(limit_per_source=FETCH_LIMIT)
            if news_items:
                risks = []
                for item in news_items:
                    # Scoring Logic
                    text = (item.get('title', '') + " " + item.get('content', '')).lower()
                    score = 3
                    if any(x in text for x in ['crisis', 'warning', 'danger', 'flood']): score = 8
                    elif any(x in text for x in ['economy', 'debt', 'protest']): score = 6
                    
                    # Generate Deterministic ID
                    link = item.get('url', item.get('link', ''))
                    title = item.get('title', '')
                    risk_id = self._generate_id(item.get('source', 'News'), link or title)

                    risks.append({
                        "id": risk_id,  # <--- NO MORE RANDOM UUID
                        "source": item.get('source', 'News'),
                        "signal": title,
                        "link": link,
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": item.get('source_category', 'General'),
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 1.0,
                        "sentiment_score": 0.0,
                        "created_at": datetime.now().isoformat()
                    })
                
                # Batch insert (Duplicates will be ignored by DB)
                count = db.batch_insert_risks(risks)
                if count > 0:
                    print(f"   -> Saved {count} NEW News items.")
                else:
                    print("   -> No new News (duplicates skipped).")

        except Exception as e:
            print(f"❌ News Error: {e}")

        # 2. REDDIT COLLECTION
        try:
            social_df = get_reddit_rss(limit=FETCH_LIMIT)
            if not social_df.empty:
                s_risks = []
                for _, row in social_df.iterrows():
                    link = row.get('link', '')
                    title = row.get('title', '')
                    risk_id = self._generate_id(row.get('source', 'Reddit'), link or title)

                    s_risks.append({
                        "id": risk_id,
                        "source": row.get('source', 'Reddit'),
                        "signal": title,
                        "link": link,
                        "published": datetime.now().isoformat(),
                        "risk_score": random.randint(4, 7),
                        "category": "Social Media",
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 0.8,
                        "sentiment_score": 0.0,
                        "created_at": datetime.now().isoformat()
                    })
                
                count = db.batch_insert_risks(s_risks)
                if count > 0:
                    print(f"   -> Saved {count} NEW Reddit items.")
                else:
                    print("   -> No new Reddit posts (duplicates skipped).")

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
        print(f"🚀 Collector Started. Polling every {REFRESH_INTERVAL} seconds.")

collector = RiskCollector()