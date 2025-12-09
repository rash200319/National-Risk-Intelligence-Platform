import feedparser
import pandas as pd
import requests
import json
import logging
from datetime import datetime, timezone,timedelta
from io import BytesIO
from dateutil import parser as date_parser


BUSINESS_KEYWORDS = [
    'business', 'economy', 'finance', 'stock', 'market', 'investment',
    'trade', 'company', 'corporate', 'bank', 'industry', 'profit', 'loss',
    'ceylon', 'export', 'import', 'policy', 'government','power', 'disaster','flood','fuel','tourism','protest'
]

def filter_business_posts(posts: pd.DataFrame, keywords: list) -> pd.DataFrame:
    if posts.empty:
        return posts
    mask = (
        posts['title'].str.contains('|'.join(keywords), case=False, na=False) |
        posts['raw_data'].str.contains('|'.join(keywords), case=False, na=False)
    )
    return posts[mask]

def filter_recent(posts: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    if posts.empty:
        return posts
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    posts['published'] = pd.to_datetime(posts['published'])
    return posts[posts['published'] >= cutoff]
    
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> str:
    """Robust date parsing helper."""
    try:
        if not date_str:
            return datetime.now(timezone.utc).isoformat()
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except:
        return datetime.now(timezone.utc).isoformat()

# --- REDDIT MODULE ---
def get_reddit_rss(limit: int = 50) -> pd.DataFrame:
    """
    Fetches posts from an expanded list of Sri Lankan subreddits.
    """
    logger.info("Fetching Reddit posts...")
    
    # Expanded Subreddit List
    subreddits = [
        'srilanka', 'Colombo', 'kandy', 'Galle', 'Jaffna', 
        'srilankans', 'srilanka_memes', 'ceylon'
    ]
    
    all_posts = []
    
    for subreddit in subreddits:
        try:
            # Use 'new' to get the latest chatter
            rss_url = f"https://www.reddit.com/r/{subreddit}/new/.rss"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Add cache-busting to force fresh data
            rss_url_with_cache = f"{rss_url}?t={int(datetime.now().timestamp())}"
            
            response = requests.get(rss_url_with_cache, headers=headers, timeout=10)
            
            # Skip if subreddit doesn't exist or is private
            if response.status_code != 200:
                continue

            feed = feedparser.parse(BytesIO(response.content))
            
            for entry in feed.entries[:limit]:
                try:
                    all_posts.append({
                        'source': f'reddit_r/{subreddit}',
                        'title': entry.get('title', 'No title'),
                        'link': entry.get('link', ''),
                        'published': parse_date(entry.get('published', '')),
                        'raw_data': json.dumps({'summary': entry.get('summary', '')}, default=str)
                    })
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
            continue
    
    # Remove duplicates
    df = pd.DataFrame(all_posts)
    if not df.empty:
        df.drop_duplicates(subset=['link'], inplace=True)
        df = filter_business_posts(df, BUSINESS_KEYWORDS)
        df = filter_recent(df, days=7)
    return df

# Placeholder to prevent ImportErrors in collector.py
def fetch_twitter_data(*args, **kwargs):
    return []
