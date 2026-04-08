import time
import threading
import uuid
import logging
import re
from datetime import datetime
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import pandas as pd
from database_manager import db
from config import FETCH_LIMIT, REFRESH_INTERVAL
from utils.sources import multi_source_collector
from utils.health import health_monitor

# Configure logging
logger = logging.getLogger(__name__)

# Initialize VADER sentiment analyzer
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)
sia = SentimentIntensityAnalyzer()

# Import Feed Fetchers
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

HIGH_RISK_INDUSTRIES = {"Public Safety", "Energy & Fuel"}

STRONG_INDUSTRY_KEYWORDS = {
    "Energy & Fuel": {"blackout", "power cut", "fuel", "petrol"},
    "Logistics & Transport": {"port", "airport", "shipping", "train", "bus"},
    "Finance & Economy": {"bank", "fraud", "cbsl", "depositor", "depositor", "deposits", "imf"},
    "Tourism": {"airport", "visa", "hotel"},
    "Agriculture": {"fertilizer", "crop", "rice"},
    "Public Safety": {"protest", "strike", "curfew", "attack", "violence", "disaster", "flood"},
}

SOURCE_RELIABILITY = {
    "newsapi": 0.95,
    "gdelt": 0.85,
    "worldbank": 0.90,
    "rss": 0.80,
    "reddit": 0.55,
    "default": 0.70,
}

CRISIS_WEIGHTS = {
    "crisis": 1.8,
    "emergency": 2.4,
    "alert": 1.2,
    "warning": 1.0,
    "attack": 2.4,
    "dead": 2.0,
    "kill": 2.2,
    "violence": 2.0,
    "protest": 1.6,
    "strike": 1.6,
    "curfew": 1.8,
    "flood": 1.6,
    "disaster": 2.0,
    "riot": 2.2,
    "shortage": 1.4,
    "blackout": 1.6,
    "power cut": 1.6,
    "bankrupt": 2.0,
    "debt": 1.2,
    "inflation": 1.2,
    "layoff": 1.3,
}

LOW_SIGNAL_PATTERNS = [
    "anyone", "recommend", "suggestions", "looking for",
    "can someone", "help me", "advice", "where can i"
]

class RiskCollector:
    def __init__(self):
        self.is_running = False
        self.thread = None

    def _resolve_source_type(self, source_name: str) -> str:
        source = (source_name or "").strip().lower()
        if source.startswith("reddit"):
            return "reddit"
        if source == "newsapi":
            return "newsapi"
        if source == "gdelt":
            return "gdelt"
        if source == "worldbank":
            return "worldbank"
        return "rss"

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _extract_industries(self, text_lower: str):
        detected = []
        for industry, keywords in INDUSTRIES.items():
            keyword_hits = sum(1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", text_lower))
            strong_hits = sum(1 for keyword in STRONG_INDUSTRY_KEYWORDS.get(industry, set()) if re.search(rf"\b{re.escape(keyword)}\b", text_lower))
            if strong_hits >= 1 or keyword_hits >= 2:
                detected.append(industry)
        return detected or ["General"]

    def _analyze_context(self, text, source_name="default"):
        """
        Deterministic risk analysis.

        Returns:
            risk_score (1-10), sentiment_score (-1 to +1), industries (str), confidence (0-1)
        """
        text_lower = text.lower().strip()
        scores = sia.polarity_scores(text)
        sentiment = scores["compound"]

        crisis_strength = 0.0
        matched_keywords = []
        seen = set()
        for keyword, weight in CRISIS_WEIGHTS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                if keyword in seen:
                    continue
                crisis_strength += weight
                matched_keywords.append(keyword)
                seen.add(keyword)

        source_type = self._resolve_source_type(source_name)
        source_reliability = SOURCE_RELIABILITY.get(source_type, SOURCE_RELIABILITY["default"])

        industry_list = self._extract_industries(text_lower)

        # Deterministic, explainable risk formula.
        # Start from neutral 5, then adjust by sentiment, crisis language, and source reliability.
        sentiment_component = (-sentiment) * 1.5
        crisis_component = min(crisis_strength, 5.0) * 1.0
        source_component = (source_reliability - 0.7) * 2.0
        industry_component = 0.6 if any(industry in HIGH_RISK_INDUSTRIES for industry in industry_list) else 0.3 if industry_list != ["General"] else 0.0

        risk_score = 4.0 + sentiment_component + crisis_component + source_component + industry_component

        if any(pattern in text_lower for pattern in LOW_SIGNAL_PATTERNS):
            risk_score = min(risk_score, 4.0)

        if "?" in text:
            risk_score -= 1.0

        # Hard floor for very strong crisis language, but still deterministic.
        if crisis_strength >= 3.5 and len(matched_keywords) >= 2:
            risk_score = max(risk_score, 8.0)

        # Historical references should not look like current risk.
        if re.search(r"\b(?:197|198|199|200)\d\b", text_lower):
            risk_score -= 1.0

        # Serious institutional questions should keep their weight; casual questions should soften.
        if "?" in text and crisis_strength < 2.0:
            risk_score -= 1.0

        # Economic/institutional failures deserve a modest boost.
        if any(term in text_lower for term in ["bank", "fraud", "cbsl", "depositor", "depositor", "deposits"]):
            risk_score += 1.0

        risk_score = int(round(self._clamp(risk_score, 1.0, 10.0)))

        # Confidence reflects source reliability and signal strength, not just risk.
        text_length_score = self._clamp(len(text) / 280.0, 0.0, 1.0)
        keyword_signal_score = self._clamp(crisis_strength / 4.0, 0.0, 1.0)
        sentiment_strength = abs(sentiment)

        confidence = (
            (source_reliability * 0.45) +
            (text_length_score * 0.20) +
            (keyword_signal_score * 0.25) +
            (sentiment_strength * 0.10)
        )
        confidence = round(self._clamp(confidence, 0.1, 1.0), 2)

        risk_breakdown = {
            "sentiment": round(sentiment_component, 2),
            "crisis": round(crisis_component, 2),
            "source": round(source_component, 2),
            "industry": round(industry_component, 2),
        }

        return risk_score, sentiment, ", ".join(industry_list), confidence, ", ".join(matched_keywords), risk_breakdown

    def fetch_realtime(self):
        """Fetch news and social data with multi-source fallback and health tracking."""
        print("📡 Running Smart Collection Cycle with Multi-Source Fallback...")
        
        # 1. NEWS COLLECTION WITH MULTI-SOURCE FALLBACK
        try:
            # Use multi-source fallback strategy
            news_items = multi_source_collector.collect_news_with_fallback(limit=FETCH_LIMIT)
            
            if news_items:
                risks = []
                for item in news_items:
                    # Combine title and content for better AI context
                    full_text = f"{item.get('title', '')} {item.get('content', '')}"
                    source_name = item.get('source', 'News')
                    
                    # --- AI PROCESSING ---
                    score, sentiment, industries, confidence, matched_keywords, risk_breakdown = self._analyze_context(full_text, source_name)
                    
                    risks.append({
                        "id": f"news_{uuid.uuid4().hex[:8]}",
                        "source": source_name,
                        "signal": item.get('title', ''),
                        "link": item.get('url', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": matched_keywords,
                        "confidence": confidence,
                        "risk_breakdown": str(risk_breakdown),
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                
                db.batch_insert_risks(risks)
                print(f"   ✅ Processed {len(risks)} News items with AI.")
                
                # Record health metrics
                health_monitor.record_fetch('NewsAPI_Multi-Source', True, len(risks))
            else:
                print("   ⚠️ No news items collected from any source")
                health_monitor.record_fetch('NewsAPI_Multi-Source', False, 0, 'No items returned')
                
        except Exception as e:
            print(f"❌ News Collection Error: {e}")
            logger.error(f"News collection failed: {e}")
            health_monitor.record_fetch('NewsAPI_Multi-Source', False, 0, str(e))

        # 2. REDDIT COLLECTION WITH HEALTH TRACKING
        try:
            reddit_source = 'Reddit - Mixed Subreddits'
            social_df = get_reddit_rss(limit=FETCH_LIMIT)
            
            if not social_df.empty:
                s_risks = []
                for _, row in social_df.iterrows():
                    raw_summary = ''
                    try:
                        raw_summary = row.get('raw_data', '')
                    except Exception:
                        raw_summary = ''

                    full_text = f"{row.get('title', '')} {raw_summary}"
                    source_name = row.get('source', 'Reddit')
                    score, sentiment, industries, confidence, matched_keywords, risk_breakdown = self._analyze_context(full_text, source_name)

                    s_risks.append({
                        "id": f"reddit_{uuid.uuid4().hex[:8]}",
                        "source": source_name,
                        "signal": row.get('title', ''),
                        "link": row.get('link', '#'),
                        "published": datetime.now().isoformat(),
                        "risk_score": score,
                        "category": industries,
                        "location": "Sri Lanka",
                        "district": "",
                        "province": "",
                        "keywords": matched_keywords,
                        "confidence": confidence,
                        "risk_breakdown": str(risk_breakdown),
                        "sentiment_score": sentiment,
                        "created_at": datetime.now().isoformat()
                    })
                
                db.batch_insert_risks(s_risks)
                print(f"   ✅ Processed {len(s_risks)} Reddit items with AI.")
                
                # Record health metrics
                health_monitor.record_fetch(reddit_source, True, len(s_risks))
            else:
                print("   ⚠️ No Reddit posts fetched")
                health_monitor.record_fetch(reddit_source, False, 0, 'No posts returned')
                
        except Exception as e:
            print(f"❌ Reddit Collection Error: {e}")
            logger.error(f"Reddit collection failed: {e}")
            health_monitor.record_fetch('Reddit - Mixed Subreddits', False, 0, str(e))

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