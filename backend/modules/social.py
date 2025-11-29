import feedparser
import pandas as pd
import requests
import tweepy
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
from dateutil import parser as date_parser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Twitter API Configuration (set these in your environment variables)
TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
TWITTER_ACCESS_SECRET = os.getenv('TWITTER_ACCESS_SECRET')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# Sri Lanka related keywords and hashtags
SRI_LANKA_KEYWORDS = [
    '#SriLanka', '#LKA', '#SriLankaCrisis', '#SriLankaEconomicCrisis',
    'Colombo', 'Kandy', 'Galle', 'Jaffna', 'Sri Lanka', 'Colombo'
]

# Business risk related keywords
BUSINESS_RISK_KEYWORDS = [
    # Infrastructure
    'power', 'electricity', 'blackout', 'outage', 'water', 'fuel', 'gas', 'petrol', 'diesel',
    # Economic
    'economy', 'inflation', 'recession', 'debt', 'dollar', 'rupee', 'import', 'export', 'tax',
    # Social/Political
    'strike', 'protest', 'rally', 'demonstration', 'curfew', 'violence', 'unrest',
    # Transportation
    'traffic', 'road', 'blockade', 'strike', 'transport', 'bus', 'train',
    # Natural
    'flood', 'rain', 'weather', 'landslide', 'disaster', 'emergency', 'warning',
    # Utilities
    'shortage', 'price hike', 'increase', 'scarcity', 'ration'
]

def get_reddit_rss(limit: int = 20) -> pd.DataFrame:
    """
    Fetches the latest posts from Sri Lankan subreddits via RSS.
    
    Args:
        limit: Maximum number of posts to return per subreddit
        
    Returns:
        DataFrame with columns: source, signal, link, published, subreddit
    """
    logger.info("Fetching Reddit posts...")
    
    # List of Sri Lankan subreddits to monitor
    subreddits = [
        'srilanka', 'SriLanka', 'srilanka_memes', 'srilankans',
        'Colombo', 'kandy', 'Galle', 'Jaffna'
    ]
    
    all_posts = []
    
    for subreddit in subreddits:
        try:
            rss_url = f"https://www.reddit.com/r/{subreddit}/new/.rss"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Add cache-busting parameter
            rss_url_with_cache = f"{rss_url}?t={int(datetime.now().timestamp())}"
            
            response = requests.get(rss_url_with_cache, headers=headers, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(BytesIO(response.content))
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"RSS parse error for r/{subreddit}: {feed.bozo_exception}")
            
            for entry in feed.entries[:limit]:
                try:
                    # Check if post contains any of our keywords
                    title = entry.get('title', '').lower()
                    if not any(keyword in title for keyword in BUSINESS_RISK_KEYWORDS):
                        continue
                        
                    # Parse published date
                    published = entry.get('published', '')
                    if published:
                        try:
                            published = date_parser.parse(published).isoformat()
                        except (ValueError, OverflowError):
                            published = datetime.now(timezone.utc).isoformat()
                    
                    all_posts.append({
                        'source': 'reddit',
                        'signal': entry.get('title', 'No title'),
                        'description': entry.get('summary', ''),
                        'link': entry.get('link', ''),
                        'published': published,
                        'subreddit': subreddit,
                        'author': entry.get('author', ''),
                        'upvotes': entry.get('upvotes', 0),
                        'comments': entry.get('comments', 0),
                        'raw_data': json.dumps(entry, default=str)
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing Reddit entry: {e}", exc_info=True)
        
        except requests.RequestException as e:
            logger.error(f"Error fetching r/{subreddit}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error with r/{subreddit}: {e}", exc_info=True)
    
    return pd.DataFrame(all_posts)

def get_twitter_client() -> Optional[tweepy.API]:
    """Initialize and return a Twitter API client."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
        logger.warning("Twitter API credentials not fully configured")
        return None
    
    try:
        auth = tweepy.OAuthHandler(TWITTER_API_KEY, TWITTER_API_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        
        # Initialize API with wait_on_rate_limit to handle rate limits gracefully
        api = tweepy.API(
            auth,
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True,
            retry_count=3,
            retry_delay=5,
            timeout=60
        )
        
        # Verify credentials
        api.verify_credentials()
        return api
    except Exception as e:
        logger.error(f"Error initializing Twitter client: {e}")
        return None

def fetch_twitter_trends(woeid: int = 23424778) -> List[Dict[str, Any]]:
    """
    Fetch trending topics for Sri Lanka from Twitter.
    
    Args:
        woeid: Where On Earth ID for Sri Lanka (default is 23424778)
        
    Returns:
        List of trending topics with metadata
    """
    logger.info("Fetching Twitter trends...")
    
    try:
        api = get_twitter_client()
        if not api:
            return []
            
        trends = api.trends_place(woeid)
        
        if not trends or not trends[0].get('trends'):
            return []
            
        return [
            {
                'name': trend['name'],
                'url': trend['url'],
                'tweet_volume': trend.get('tweet_volume'),
                'promoted_content': trend.get('promoted_content')
            }
            for trend in trends[0]['trends']
            if trend['name'].lower().startswith('#')
        ]
        
    except Exception as e:
        logger.error(f"Error fetching Twitter trends: {e}", exc_info=True)
        return []

def search_twitter(
    query: str,
    count: int = 50,
    result_type: str = 'recent',
    since: Optional[datetime] = None,
    until: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Search for tweets matching a query.
    
    Args:
        query: Search query
        count: Number of results to return (max 100 per request)
        result_type: Type of results (mixed, recent, popular)
        since: Return tweets after this date
        until: Return tweets before this date
        
    Returns:
        List of tweets with metadata
    """
    logger.info(f"Searching Twitter for: {query}")
    
    try:
        api = get_twitter_client()
        if not api:
            return []
            
        # Build query with filters
        search_query = f"{query} -filter:retweets"
        
        # Add date filters if provided
        if since:
            search_query += f" since:{since.strftime('%Y-%m-%d')}"
        if until:
            search_query += f" until:{until.strftime('%Y-%m-%d')}"
        
        # Search for tweets
        tweets = []
        for tweet in tweepy.Cursor(
            api.search,
            q=search_query,
            lang='en',
            tweet_mode='extended',
            result_type=result_type,
            count=min(count, 100)  # Max 100 per request
        ).items(count):
            try:
                # Extract relevant data from tweet
                tweet_data = {
                    'id': tweet.id_str,
                    'text': tweet.full_text,
                    'created_at': tweet.created_at.isoformat(),
                    'user': tweet.user.screen_name,
                    'user_name': tweet.user.name,
                    'user_followers': tweet.user.followers_count,
                    'retweets': tweet.retweet_count,
                    'favorites': tweet.favorite_count,
                    'hashtags': [h['text'] for h in tweet.entities['hashtags']],
                    'mentions': [m['screen_name'] for m in tweet.entities['user_mentions']],
                    'urls': [u['expanded_url'] for u in tweet.entities['urls']],
                    'source': tweet.source,
                    'is_quote': hasattr(tweet, 'quoted_status'),
                    'is_reply': tweet.in_reply_to_status_id is not None,
                    'location': tweet.user.location,
                    'coordinates': tweet.coordinates,
                    'place': tweet.place.full_name if tweet.place else None
                }
                
                # Add media if available
                if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities:
                    tweet_data['media'] = [
                        {
                            'type': m['type'],
                            'url': m['media_url_https'],
                            'display_url': m['display_url']
                        }
                        for m in tweet.extended_entities['media']
                    ]
                
                tweets.append(tweet_data)
                
            except Exception as e:
                logger.error(f"Error processing tweet {getattr(tweet, 'id_str', 'unknown')}: {e}")
        
        return tweets
        
    except Exception as e:
        logger.error(f"Error searching Twitter: {e}", exc_info=True)
        return []

def fetch_twitter_data(
    keywords: List[str] = None,
    limit_per_query: int = 20,
    hours_back: int = 24
) -> List[Dict[str, Any]]:
    """
    Fetch relevant tweets based on business risk keywords.
    
    Args:
        keywords: List of keywords to search for (defaults to BUSINESS_RISK_KEYWORDS)
        limit_per_query: Max tweets to fetch per keyword
        hours_back: Only fetch tweets from the last N hours
        
    Returns:
        List of processed tweet data
    """
    if keywords is None:
        keywords = BUSINESS_RISK_KEYWORDS
    
    logger.info(f"Fetching Twitter data for {len(keywords)} keywords...")
    
    all_tweets = []
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    
    for keyword in keywords:
        try:
            # Search for tweets containing the keyword
            tweets = search_twitter(
                query=f"{keyword} Sri Lanka",
                count=limit_per_query,
                since=since,
                result_type='mixed'
            )
            
            # Add keyword and process each tweet
            for tweet in tweets:
                tweet['search_keyword'] = keyword
                
                # Add to results if not already present (by tweet ID)
                if not any(t['id'] == tweet['id'] for t in all_tweets):
                    all_tweets.append(tweet)
            
            logger.info(f"Found {len(tweets)} tweets for keyword: {keyword}")
            
            # Be nice to the Twitter API
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error processing keyword '{keyword}': {e}")
    
    return all_tweets

def fetch_social_media_data() -> Dict[str, Any]:
    """
    Fetch data from all configured social media platforms.
    
    Returns:
        Dictionary containing data from all platforms
    """
    logger.info("Starting social media data collection...")
    
    result = {
        'reddit': [],
        'twitter': {
            'trends': [],
            'tweets': []
        },
        'collected_at': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        # Fetch Reddit data
        logger.info("Fetching Reddit data...")
        reddit_df = get_reddit_rss(limit=30)
        result['reddit'] = reddit_df.to_dict('records')
        logger.info(f"Fetched {len(reddit_df)} Reddit posts")
        
        # Fetch Twitter data if configured
        if TWITTER_API_KEY:
            logger.info("Fetching Twitter data...")
            
            # Get trending topics
            trends = fetch_twitter_trends()
            result['twitter']['trends'] = trends
            logger.info(f"Found {len(trends)} trending topics")
            
            # Get tweets for business risk keywords
            tweets = fetch_twitter_data(limit_per_query=15, hours_back=12)
            result['twitter']['tweets'] = tweets
            logger.info(f"Fetched {len(tweets)} relevant tweets")
        
    except Exception as e:
        logger.error(f"Error in social media data collection: {e}", exc_info=True)
    
    return result

# For backward compatibility
def get_reddit_rss_df() -> pd.DataFrame:
    """Legacy function to return Reddit data as a DataFrame."""
    return get_reddit_rss()

# Alias for backward compatibility
get_reddit_rss = get_reddit_rss_df

if __name__ == "__main__":
    # Test the module
    print("=== Testing Social Media Module ===\n")
    
    # Test Reddit
    print("Testing Reddit integration...")
    reddit_data = get_reddit_rss(limit=5)
    print(f"Fetched {len(reddit_data)} Reddit posts")
    
    # Test Twitter if configured
    if TWITTER_API_KEY:
        print("\nTesting Twitter integration...")
        
        # Test trends
        print("Fetching trending topics...")
        trends = fetch_twitter_trends()
        print(f"Found {len(trends)} trending topics")
        
        # Test search
        print("\nSearching for recent tweets about Sri Lanka...")
        tweets = search_twitter("Sri Lanka", count=3)
        print(f"Found {len(tweets)} tweets")
        
        # Test business risk tweets
        print("\nFetching business risk tweets...")
        risk_tweets = fetch_twitter_data(limit_per_query=2, hours_back=24)
        print(f"Found {len(risk_tweets)} relevant tweets")
    else:
        print("\nTwitter API not configured. Set environment variables to enable Twitter features.")
    
    print("\n=== Social Media Module Tests Complete ===")