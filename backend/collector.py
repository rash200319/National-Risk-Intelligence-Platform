import time
import random
import threading
from datetime import datetime, timedelta
import pandas as pd
from database_manager import db
from modules.news import fetch_news  # Ensure these files exist in 'modules' or root
from modules.social import get_reddit_rss

# --- CONFIGURATION ---
HISTORY_DAYS = 90  # 3 Months
REFRESH_INTERVAL = 600  # 10 Minutes

# Fake locations and signals for "History Simulation"
SRI_LANKA_LOCATIONS = ["Colombo", "Kandy", "Galle", "Jaffna", "Trincomalee", "Negombo"]
SIMULATED_EVENTS = [
    ("Heavy rain causing minor floods.", 5),
    ("Economic protest gathering in city center.", 7),
    ("Power outage reported in industrial zone.", 6),
    ("Traffic collision causing delays.", 3),
    ("New tourism initiative launched.", 1),
    ("Dengue warning issued for the district.", 6),
    ("Fishermen strike continues.", 5)
]

class RiskCollector:
    def __init__(self):
        self.is_running = False
        self.thread = None

    def generate_history(self):
        """Generates 3 months of synthetic data if DB is empty."""
        print("⏳ Checking historical data...")
        
        # Check if we already have data
        existing_data = db.get_risks(limit=1)
        if not existing_data.empty:
            print("✅ Historical data already exists. Skipping backfill.")
            return

        print(f"⚠️ No history found. Generating {HISTORY_DAYS} days of backfill data...")
        
        historical_risks = []
        start_date = datetime.now() - timedelta(days=HISTORY_DAYS)
        
        # Generate ~3-5 events per day for the last 90 days
        for day in range(HISTORY_DAYS):
            current_date = start_date + timedelta(days=day)
            daily_events = random.randint(3, 8)
            
            for _ in range(daily_events):
                event, base_score = random.choice(SIMULATED_EVENTS)
                loc = random.choice(SRI_LANKA_LOCATIONS)
                
                # Add some randomness to the signal
                signal = f"{event} Reported in {loc}."
                score = min(10, max(1, base_score + random.randint(-1, 2)))
                
                risk = {
                    "source": "Historical Archive",
                    "signal": signal,
                    "risk_score": score,
                    "published": current_date.isoformat(),
                    "link": "http://archive.modelx.internal",
                    "location": loc,
                    "created_at": current_date.isoformat()
                }
                historical_risks.append(risk)

        # Batch save
        if historical_risks:
            db.batch_insert_risks(historical_risks)
            print(f"✅ Successfully injected {len(historical_risks)} historical records.")

    def fetch_realtime(self):
        """Fetches REAL data from News and Reddit."""
        print("📡 Running Real-time Collection Cycle...")
        try:
            # 1. Fetch News
            news_items = fetch_news(limit=5)
            if news_items:
                # Transform to risk format
                risks = []
                for item in news_items:
                    risks.append({
                        "source": item.get('source', 'News'),
                        "signal": item.get('title', ''),
                        "risk_score": random.randint(3, 8), # Placeholder AI score
                        "published": datetime.now().isoformat(),
                        "link": item.get('link', '#'),
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(risks)
                print(f"   -> Saved {len(risks)} News items.")

            # 2. Fetch Social
            social_items = get_reddit_rss(limit=5)
            if not social_items.empty:
                # Convert DataFrame to list of dicts
                s_risks = []
                for _, row in social_items.iterrows():
                    s_risks.append({
                        "source": "Reddit",
                        "signal": row.get('title', ''),
                        "risk_score": random.randint(4, 9), # Placeholder AI score
                        "published": datetime.now().isoformat(),
                        "link": row.get('link', '#'),
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(s_risks)
                print(f"   -> Saved {len(s_risks)} Social items.")
                
        except Exception as e:
            print(f"❌ Collection Error: {e}")

    def run_loop(self):
        """The main infinite loop for the background thread."""
        while self.is_running:
            self.fetch_realtime()
            time.sleep(REFRESH_INTERVAL)

    def start(self):
        """Starts the collector in a background thread."""
        if self.is_running:
            return
            
        # 1. First, ensure history exists
        self.generate_history()
        
        # 2. Start the real-time looper
        self.is_running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        print("🚀 Collector System Started (Background Thread)")

# Singleton Instance
collector = RiskCollector()