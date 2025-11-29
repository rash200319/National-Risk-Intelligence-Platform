import feedparser
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any
import time
import logging
from dateutil import parser as date_parser
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# List of Sri Lankan news sources with additional metadata
NEWS_SOURCES = [
    {
        'name': 'Ada Derana',
        'rss_url': 'http://www.adaderana.lk/rss.php',
        'api_url': None,
        'category': 'general',
        'language': 'en',
        'country': 'LK',
        'active': True
    },
    {
        'name': 'Daily Mirror',
        'rss_url': 'https://www.dailymirror.lk/RSS_Feeds/breaking-news',
        'api_url': None,
        'category': 'general',
        'language': 'en',
        'country': 'LK',
        'active': True
    },
    {
        'name': 'Lanka Business Online',
        'rss_url': 'https://www.lankabusinessonline.com/feed/',
        'api_url': None,
        'category': 'business',
        'language': 'en',
        'country': 'LK',
        'active': True
    },
    {
        'name': 'News First',
        'rss_url': 'https://www.newsfirst.lk/latest-news/feed/',
        'api_url': None,
        'category': 'general',
        'language': 'en',
        'country': 'LK',
        'active': True
    },
    {
        'name': 'Hiru News',
        'rss_url': 'https://www.hirunews.lk/rss/hirunews-lk-news-sinhala-fb.xml',
        'api_url': None,
        'category': 'general',
        'language': 'si',  # Sinhala
        'country': 'LK',
        'active': True
    }
]

# NewsAPI configuration (if available)
NEWS_API_KEY = None  # Set your NewsAPI key here if available
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
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None

def fetch_rss_feed(url: str, source_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch and parse an RSS feed."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Add cache-busting parameter
        if '?' in url:
            url += f"&_={int(time.time())}"
        else:
            url += f"?_={int(time.time())}"
        
        feed = feedparser.parse(url, request_headers=headers)
        
        if feed.bozo and feed.bozo_exception:
            logger.warning(f"RSS feed parse error for {source_name}: {feed.bozo_exception}")
        
        items = []
        for entry in feed.entries[:limit]:
            try:
                published = parse_date(entry.get('published', '')) or datetime.now(timezone.utc).isoformat()
                
                # Extract content if available
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
                    'category': entry.get('category', ''),
                    'raw_data': json.dumps(entry, default=str)
                })
            except Exception as e:
                logger.error(f"Error processing entry from {source_name}: {e}", exc_info=True)
        
        return items
    except Exception as e:
        logger.error(f"Error fetching RSS feed {url}: {e}", exc_info=True)
        return []

def fetch_news(limit_per_source: int = 10) -> List[Dict[str, Any]]:
    """
    Fetches the latest news from configured RSS feeds.
    
    Args:
        limit_per_source: Maximum number of articles to fetch per source
        
    Returns:
        List of news items with metadata
    """
    logger.info("Fetching latest news from RSS feeds...")
    all_news = []
    
    for source in [s for s in NEWS_SOURCES if s['active']]:
        try:
            if not source.get('rss_url'):
                continue
                
            logger.debug(f"Fetching from {source['name']}...")
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
            
        except Exception as e:
            logger.error(f"Error fetching from {source.get('name', 'unknown')}: {e}", exc_info=True)
    
    # Sort by publication date (newest first)
    all_news.sort(key=lambda x: x.get('published', ''), reverse=True)
    
    return all_news

def fetch_historical_news(
    start_date: datetime,
    end_date: datetime = None,
    query: str = 'Sri Lanka',
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch historical news using NewsAPI or fallback to RSS with date filtering.
    
    Args:
        start_date: Start date for historical data
        end_date: End date for historical data (defaults to now)
        query: Search query (for NewsAPI)
        limit: Maximum number of results to return
        
    Returns:
        List of historical news items
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    
    logger.info(f"Fetching historical news from {start_date} to {end_date}")
    
    # Try to use NewsAPI if available
    if NEWS_API_KEY:
        try:
            return _fetch_newsapi_historical(
                query=query,
                from_date=start_date,
                to_date=end_date,
                limit=limit
            )
        except Exception as e:
            logger.error(f"NewsAPI error: {e}. Falling back to RSS.")
    
    # Fallback to RSS with date filtering
    return _fetch_rss_with_date_filter(start_date, end_date, limit)

def _fetch_newsapi_historical(
    query: str,
    from_date: datetime,
    to_date: datetime,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Fetch historical news using NewsAPI."""
    if not NEWS_API_KEY:
        raise ValueError("NewsAPI key not configured")
    
    params = {
        'q': query,
        'from': from_date.strftime('%Y-%m-%d'),
        'to': to_date.strftime('%Y-%m-%d'),
        'sortBy': 'publishedAt',
        'pageSize': min(limit, 100),  # Max 100 per request
        'apiKey': NEWS_API_KEY,
        'language': 'en',
        'page': 1
    }
    
    all_articles = []
    
    try:
        while len(all_articles) < limit:
            response = requests.get(NEWS_API_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            if not articles:
                break
            
            for article in articles:
                try:
                    published = parse_date(article.get('publishedAt'))
                    if not published:
                        continue
                        
                    all_articles.append({
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'title': article.get('title', 'No title'),
                        'description': article.get('description', ''),
                        'content': article.get('content', ''),
                        'url': article.get('url', ''),
                        'published': published,
                        'author': article.get('author', ''),
                        'urlToImage': article.get('urlToImage', ''),
                        'source_name': article.get('source', {}).get('name', '')
                    })
                    
                    if len(all_articles) >= limit:
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing article: {e}", exc_info=True)
            
            # Check if we have more pages
            if len(articles) < params['pageSize'] or len(all_articles) >= limit:
                break
                
            params['page'] += 1
            
    except requests.RequestException as e:
        logger.error(f"NewsAPI request failed: {e}")
    
    return all_articles

def _fetch_rss_with_date_filter(
    start_date: datetime,
    end_date: datetime,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fallback method to fetch news from RSS with date filtering.
    This is less reliable as not all RSS feeds support date filtering.
    """
    logger.warning("Using fallback RSS method which may not return complete historical data")
    
    all_news = []
    collected = 0
    
    for source in [s for s in NEWS_SOURCES if s['active'] and s.get('rss_url')]:
        try:
            items = fetch_rss_feed(source['rss_url'], source['name'], limit=50)
            
            # Filter by date
            filtered_items = []
            for item in items:
                try:
                    pub_date = date_parser.parse(item['published'])
                    if start_date <= pub_date <= end_date:
                        filtered_items.append(item)
                except (ValueError, KeyError):
                    continue
            
            all_news.extend(filtered_items)
            collected += len(filtered_items)
            
            if collected >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error in RSS fallback for {source.get('name')}: {e}")
    
    # Sort by date and limit results
    all_news.sort(key=lambda x: x.get('published', ''), reverse=True)
    return all_news[:limit]

# For backward compatibility
def fetch_news_df() -> pd.DataFrame:
    """Legacy function to return news as a DataFrame."""
    news_items = fetch_news()
    return pd.DataFrame([{
        'source': item['source'],
        'title': item['title'],
        'link': item.get('url', ''),
        'published': item.get('published', '')
    } for item in news_items])

# Removed alias to prevent overriding fetch_news function
# fetch_news = fetch_news_df

if __name__ == "__main__":
    # Test the module
    print("=== Testing News Module ===")
    
    # Test current news
    print("\nFetching current news...")
    current_news = fetch_news(limit_per_source=3)
    print(f"Fetched {len(current_news)} current news items")
    
    # Test historical news (last 7 days)
    print("\nFetching historical news (last 7 days)...")
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)
    historical_news = fetch_historical_news(start_date, end_date, limit=5)
    print(f"Fetched {len(historical_news)} historical news items")