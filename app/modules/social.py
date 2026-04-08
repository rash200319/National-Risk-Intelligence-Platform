import feedparser
import pandas as pd
import json
import logging
from datetime import datetime, timezone
from io import BytesIO
from dateutil import parser as date_parser
from utils.resilience import fetch_rss_with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Posts must carry business/risk signal to be ingested.
HIGH_PRIORITY_TERMS = {
    'protest', 'strike', 'curfew', 'riot', 'violence', 'attack', 'flood', 'disaster',
    'inflation', 'tax', 'interest rate', 'debt', 'imf', 'economy', 'recession',
    'fuel', 'power cut', 'electricity', 'blackout', 'port', 'shipping', 'airport',
    'supply chain', 'import', 'export', 'policy', 'regulation', 'ministry',
    'bank', 'rupee', 'dollar', 'forex', 'unemployment', 'layoff'
}

BUSINESS_CONTEXT_TERMS = {
    'market', 'business', 'industry', 'retail', 'manufacturing', 'tourism',
    'logistics', 'transport', 'agriculture', 'tea', 'garment', 'construction',
    'company', 'corporate', 'investment', 'cost', 'price', 'tariff', 'budget'
}

LOW_SIGNAL_PATTERNS = {
    'want to get', 'which vehicle', 'recommend me', 'my first car', 'for my family',
    'best phone', 'dating', 'relationship', 'movie suggestion', 'meme', 'joke'
}

HISTORICAL_PATTERNS = {
    'history', 'historical', 'archive', 'archival', 'committee report', 'report',
    'conference', 'thesis', 'research', 'study', 'paper', 'essay', 'old post',
    'remainder', 'remaindered', 'memoir', 'reprisal attacks', 'following the',
    'massacre', 'tragedy', '1974', '1980', '1981', '1983', '1990', '1996'
}


def is_reddit_post_relevant(title: str, summary: str) -> bool:
    """Return True only for posts with business or operational risk relevance."""
    text = f"{title} {summary}".lower()

    # Drop obvious low-signal personal chatter unless it also has strong risk terms.
    if any(pattern in text for pattern in LOW_SIGNAL_PATTERNS):
        if not any(term in text for term in HIGH_PRIORITY_TERMS):
            return False

    high_priority_hits = sum(1 for term in HIGH_PRIORITY_TERMS if term in text)
    business_hits = sum(1 for term in BUSINESS_CONTEXT_TERMS if term in text)
    historical_hits = sum(1 for term in HISTORICAL_PATTERNS if term in text)

    # Reject archive/history-oriented posts unless they contain a direct current risk signal.
    if historical_hits >= 1 and high_priority_hits == 0:
        return False

    # Keep posts with explicit risk signals, or at least two business-context signals.
    if high_priority_hits >= 1:
        return True
    if business_hits >= 2:
        return True

    return False

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
    Fetches posts from Sri Lankan subreddits with automatic retry logic.
    Automatically retries failed requests with exponential backoff.
    """
    logger.info("Fetching Reddit posts with resilient retry logic...")
    
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
            
            # Add cache-busting to force fresh data
            rss_url_with_cache = f"{rss_url}?t={int(datetime.now().timestamp())}"
            
            # Use resilient fetch with automatic retry (up to 3 attempts)
            response = fetch_rss_with_retry(rss_url_with_cache)
            
            # Skip if request failed
            if response.status_code != 200:
                logger.warning(f"Subreddit r/{subreddit} returned status {response.status_code}")
                continue

            feed = feedparser.parse(BytesIO(response.content))
            
            posts_count = 0
            skipped_irrelevant = 0
            for entry in feed.entries[:limit]:
                try:
                    title = entry.get('title', 'No title')
                    summary = entry.get('summary', '')

                    if not is_reddit_post_relevant(title, summary):
                        skipped_irrelevant += 1
                        continue

                    all_posts.append({
                        'source': f'reddit_r/{subreddit}',
                        'title': title,
                        'link': entry.get('link', ''),
                        'published': parse_date(entry.get('published', '')),
                        'raw_data': json.dumps({'summary': summary}, default=str)
                    })
                    posts_count += 1
                except Exception as e:
                    logger.debug(f"Skipped Reddit entry: {e}")
                    continue
            
            logger.info(
                f"Fetched {posts_count} relevant posts from r/{subreddit}; "
                f"skipped {skipped_irrelevant} irrelevant posts"
            )
                    
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit} (will retry): {e}")
            continue
    
    # Remove duplicates
    df = pd.DataFrame(all_posts)
    if not df.empty:
        df.drop_duplicates(subset=['link'], inplace=True)
        logger.info(f"Total Reddit posts after deduplication: {len(df)}")
    else:
        logger.warning("No Reddit posts fetched")
    
    return df

# Placeholder to prevent ImportErrors in collector.py
def fetch_twitter_data(*args, **kwargs):
    return []