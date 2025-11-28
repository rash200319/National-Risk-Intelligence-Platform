import feedparser
import pandas as pd
from datetime import datetime

# Sri Lankan RSS Feeds
RSS_FEEDS = {
    "Ada Derana": "http://www.adaderana.lk/rss.php",
    "Daily Mirror": "https://www.dailymirror.lk/RSS_Feeds/breaking-news",
    "Lanka Business Online": "https://www.lankabusinessonline.com/feed/"
}

def fetch_news():
    news_items = []
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Get top 5 latest from each
                news_items.append({
                    "source": source,
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", str(datetime.now())),
                    "summary": entry.get("summary", "")
                })
        except Exception as e:
            print(f"Error fetching {source}: {e}")
    
    return pd.DataFrame(news_items)

if __name__ == "__main__":
    df = fetch_news()
    print(df.head())
    # Save to CSV for now to build your dataset
    df.to_csv("sri_lanka_news.csv", index=False)