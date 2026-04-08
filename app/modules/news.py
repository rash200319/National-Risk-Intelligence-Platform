import feedparser
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import time
import logging
from urllib.parse import urlparse
from dateutil import parser as date_parser
import json
from utils.resilience import fetch_rss_with_retry
from utils.health import health_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- MASSIVE SOURCE LIST (The Volume Booster) ---
NEWS_SOURCES = [
    # Primary Sources
    {'name': 'Ada Derana', 'rss_url': 'http://www.adaderana.lk/rss.php', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Daily Mirror', 'rss_url': 'https://www.dailymirror.lk/RSS_Feeds/breaking-news', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Lanka Business Online', 'rss_url': 'https://www.lankabusinessonline.com/feed/', 'category': 'business', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'News First', 'rss_url': 'https://www.newsfirst.lk/latest-news/feed/', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Hiru News', 'rss_url': 'https://www.hirunews.lk/rss/hirunews-lk-news-sinhala-fb.xml', 'category': 'general', 'language': 'si', 'country': 'LK', 'active': False},
    
    # NEW SOURCES (Volume & Diversity)
    {'name': 'Gossip Lanka', 'rss_url': 'https://www.gossiplankanews.com/feeds/posts/default?alt=rss', 'category': 'local', 'language': 'si', 'country': 'LK', 'active': True},
    {'name': 'Ceylon Today', 'rss_url': 'https://ceylontoday.lk/feed/', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'The Morning', 'rss_url': 'https://www.themorning.lk/feed', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': False},
    {'name': 'Daily FT', 'rss_url': 'https://www.ft.lk/rss/front-page', 'category': 'business', 'language': 'en', 'country': 'LK', 'active': False},
    {'name': 'Sunday Times', 'rss_url': 'https://www.sundaytimes.lk/rss/news.xml', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': False},
    {'name': 'Groundviews', 'rss_url': 'https://groundviews.org/feed/', 'category': 'politics', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Sri Lanka Guardian', 'rss_url': 'https://slguardian.org/feed/', 'category': 'politics', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Economy Next', 'rss_url': 'https://economynext.com/feed/', 'category': 'business', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Colombo Telegraph', 'rss_url': 'https://www.colombotelegraph.com/index.php/feed/', 'category': 'politics', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Lanka News Web', 'rss_url': 'https://lankanewsweb.net/feed/', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True},
    {'name': 'Island.lk', 'rss_url': 'http://island.lk/feed/', 'category': 'general', 'language': 'en', 'country': 'LK', 'active': True}
]

# NewsAPI configuration 
NEWS_API_KEY = None  
NEWS_API_ENDPOINT = 'https://newsapi.org/v2/everything'

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object with timezone support."""
    if not date_str:
        return None
    
    try:
        # Try parsing with dateutil.parser which handles most formats
        dt = date_parser.parse(date_str)
        
        # If the date is naive (no timezone), assume it's in Sri Lanka time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))  # UTC+5:30
            
        return dt.isoformat()
    except (ValueError, OverflowError) as e:
        # logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None

def fetch_rss_feed(url: str, source_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch and parse an RSS feed with retry logic.
    Automatically retries failed requests up to 3 times with exponential backoff.
    """
    try:
        # Add cache-busting parameter
        joiner = '&' if '?' in url else '?'
        url_with_cache = f"{url}{joiner}_={int(time.time())}"

        parsed = urlparse(url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
        source_headers = {
            'Referer': base_origin or 'https://www.google.com/',
            'Origin': base_origin or 'https://www.google.com',
        }
        
        # Use resilient fetch with automatic retry
        response = fetch_rss_with_retry(url_with_cache, headers=source_headers)
        
        feed = feedparser.parse(response.content)
        
        items = []
        for entry in feed.entries[:limit]:
            try:
                published = parse_date(entry.get('published', '')) or datetime.now(timezone.utc).isoformat()
                
                # Extract content
                content = ''
                if 'content' in entry and entry.content:
                    content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                elif 'summary' in entry:
                    content = entry.summary
                
                items.append({
                    'source': source_name,
                    'title': entry.get('title', 'No title'),
                    'description': entry.get('description', ''),
                    'content': content,
                    'url': entry.get('link', ''),
                    'published': published,
                    'author': entry.get('author', ''),
                    'raw_data': json.dumps(entry, default=str)
                })
            except Exception as e:
                logger.debug(f"Skipped entry from {source_name}: {e}")
        
        return items
    except Exception as e:
        logger.error(f"Error fetching RSS feed {url}: {e}. Will retry automatically.")
        return []

def fetch_news(limit_per_source: int = 20) -> List[Dict[str, Any]]:
    """
    Fetches the latest news from configured RSS feeds.
    """
    logger.info("Fetching latest news from RSS feeds...")
    all_news = []
    
    for source in [s for s in NEWS_SOURCES if s['active']]:
        try:
            if not source.get('rss_url'):
                continue
            source_health_name = f"RSS - {source['name']}"
            items = fetch_rss_feed(source['rss_url'], source['name'], limit_per_source)
            
            # Add source metadata
            for item in items:
                item.update({
                    'source_name': source['name'],
                    'source_category': source['category'],
                    'source_language': source['language'],
                    'source_country': source['country']
                })
            
            all_news.extend(items)
            logger.info(f"Fetched {len(items)} items from {source['name']}")
            health_monitor.record_fetch(source_health_name, True, len(items))
            
        except Exception as e:
            logger.error(f"Error fetching from {source.get('name', 'unknown')}: {e}")
            health_monitor.record_fetch(f"RSS - {source.get('name', 'unknown')}", False, 0, str(e))
    
    # Sort by publication date (newest first)
    all_news.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    return all_news

def fetch_historical_news(start_date: datetime, end_date: datetime = None, limit: int = 100):
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    return _fetch_rss_with_date_filter(start_date, end_date, limit)

def _fetch_rss_with_date_filter(start_date: datetime, end_date: datetime, limit: int = 100):
    all_news = []
    for source in [s for s in NEWS_SOURCES if s['active'] and s.get('rss_url')]:
        try:
            items = fetch_rss_feed(source['rss_url'], source['name'], limit=20)
            all_news.extend(items)
        except:
            continue
    return all_news[:limit]