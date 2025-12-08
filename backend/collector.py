import time
import random
import threading
import uuid
import logging
from datetime import datetime
from textblob import TextBlob  # <--- AI Sentiment
import pandas as pd
from database_manager import db

# Import Feed Fetchers
from modules.news import fetch_news
from modules.social import get_reddit_rss

# --- CONFIGURATION ---
REFRESH_INTERVAL = 300  # 5 Minutes
FETCH_LIMIT = 20        # Items per source

# --- INDUSTRY KEYWORDS (BUSINESS CONTEXT) ---
INDUSTRIES = {
    # 1. Separated Energy
    "Energy": ["power", "electricity", "energy", "grid", "ceb", "solar", "renewable"],
    # 2. Separated Fuel
    "Fuel": ["fuel", "gas", "petrol", "diesel", "cpc", "kerosene", "oil"],
    "Logistics & Transport": ["road", "traffic", "train", "bus", "port", "shipping", "airline", "flight", "transport"],
    "Finance & Economy": ["rupee", "dollar", "bank", "tax", "inflation", "stock", "market", "imf", "debt", "economy"],
    "Tourism": ["tourist", "hotel", "visa", "airport", "travel", "resort", "booking"],
    "Agriculture": ["farmer", "crop", "rice", "fertilizer", "food", "tea", "export"],
    "Public Safety": ["protest", "strike", "curfew", "police", "attack", "violence", "disaster", "flood"]
}

# --- BUSINESS IMPACT LOGIC (The "Why it matters" layer) ---
# Maps industry tags to actionable business consequences
IMPACT_RULES = {
    "Fuel": "⚠️ Direct impact on transport logistics and diesel generator costs.",
    "Energy": "⚡ Risk of production downtime due to power instability or tariff hikes.",
    "Finance & Economy": "💰 Currency fluctuation may affect import costs and pricing strategies.",
    "Logistics & Transport": "🚚 Supply chain delays expected; adjust delivery timelines.",
    "Public Safety": "🛑 Possible disruption to employee commute and physical store operations.",
    "Agriculture": "🌾 Impact on raw material availability and food supply chain prices.",
    "Tourism": "✈️ Potential drop in footfall; hospitality sector advisory.",
    "General": "ℹ️ General market awareness required."
}

class RiskCollector:
    def __init__(self):
        self.is_running = False
        self.thread = None

    def _analyze_context(self, text):
        """
        Professional Analysis: Multi-Factor Weighted Risk Engine
        Returns: (Risk Score [1-10], Sentiment [-1 to 1], Industry Tags)
        """
        txt = text.lower()
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity  # -1.0 to 1.0

        # --- 1. ADVANCED SENTIMENT CATEGORIES (Emotional Context) ---
        category_score = 0
        SENTIMENT_WEIGHTS = {
            "fear": (["bomb", "terror", "attack", "dead", "kill", "explosion", "panic"], 3),
            "anger": (["strike", "protest", "corruption", "fraud", "riot", "mob"], 2),
            "uncertainty": (["crisis", "warning", "alert", "shortage", "unstable", "debt"], 2),
            "relief": (["aid", "support", "rebuild", "donation", "help", "peace"], -2),
            "positive": (["growth", "improve", "success", "win", "recover"], -1)
        }

        for cat, (words, weight) in SENTIMENT_WEIGHTS.items():
            if any(w in txt for w in words):
                category_score += weight

        # Clamp category score between 0 and 10
        category_score = max(0, min(category_score, 10))

        # --- 2. TOPIC RISK MULTIPLIERS (Sector Relevance) ---
        topic_score = 0
        TOPIC_MULTIPLIERS = {
            "political": ["government", "president", "minister", "election", "parliament"],
            "security": ["attack", "terror", "bomb", "kill", "military", "police"],
            "economic": ["inflation", "debt", "rupee", "market", "loss", "bank"],
            "infrastructure": ["power", "grid", "fuel", "blackout", "water"],
            "climate": ["flood", "storm", "cyclone", "drought", "rain"],
            "health": ["disease", "virus", "infection", "hospital"]
        }
        
        for topic, words in TOPIC_MULTIPLIERS.items():
            if any(w in txt for w in words):
                topic_score += 2
        
        # --- 3. INTENSITY MODIFIER ---
        intensity = 0
        if any(w in txt for w in ["massive", "severe", "critical", "dangerous", "deadly"]):
            intensity += 2
        if any(w in txt for w in ["minor", "small", "controlled", "handled", "fake"]):
            intensity -= 2

        # --- 4. SENTIMENT RISK ---
        sentiment_risk = (1 - sentiment) * 5

        # --- 5. FINAL FUSION FORMULA ---
        final_score = (
            (0.40 * category_score) + 
            (0.30 * sentiment_risk) + 
            (0.20 * topic_score) + 
            (0.10 * max(intensity, 0))
        )

        final_score = round(max(1, min(final_score, 10)))

        # --- INDUSTRY DETECTION ---
        detected_industries = []
        for industry, keywords in INDUSTRIES.items():
            if any(k in txt for k in keywords):
                detected_industries.append(industry)
        
        if not detected_industries:
            detected_industries.append("General")

        return final_score, sentiment, ", ".join(detected_industries)
    
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
                    
                    # --- BUSINESS IMPACT GENERATION ---
                    impact_msg = "Monitor situation."
                    # Split tags (e.g. "Energy, Fuel") and find the first matching rule
                    for tag in industries.split(", "):
                        if tag in IMPACT_RULES:
                            impact_msg = IMPACT_RULES[tag]
                            break

                    risks.append({
                        "id": f"news_{uuid.uuid4().hex[:8]}",
                        "source": item.get('source', 'News'),
                        "signal": item.get('title', ''),
                        "link": item.get('url', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,
                        "business_impact": impact_msg,  # <--- NEW FIELD
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 1.0,
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(risks)
                print(f"   -> Processed {len(risks)} News items with Business Impact.")
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

                    # --- BUSINESS IMPACT GENERATION ---
                    impact_msg = "Monitor public sentiment."
                    for tag in industries.split(", "):
                        if tag in IMPACT_RULES:
                            impact_msg = IMPACT_RULES[tag]
                            break

                    s_risks.append({
                        "id": f"reddit_{uuid.uuid4().hex[:8]}",
                        "source": row.get('source', 'Reddit'),
                        "signal": row.get('title', ''),
                        "link": row.get('link', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,
                        "business_impact": impact_msg,  # <--- NEW FIELD
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": "",
                        "confidence": 0.8,
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                db.batch_insert_risks(s_risks)
                print(f"   -> Processed {len(s_risks)} Reddit items with Business Impact.")
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