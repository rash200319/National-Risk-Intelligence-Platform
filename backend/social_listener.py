import feedparser
import pandas as pd

def get_reddit_rss():
    print("Scanning r/srilanka via RSS...")
    # Just add .rss to any subreddit URL!
    rss_url = "https://www.reddit.com/r/srilanka/new/.rss"
    
    feed = feedparser.parse(rss_url)
    posts = []
    
    print(f"DEBUG: Found {len(feed.entries)} entries in RSS feed.") 

    # 2. UPDATE KEYWORDS to include common things just for testing
    keywords = ["power", "water", "bus", "rain", "flood", "school", "help", "travel", "the", "a"] 
    # Added "the" and "a" just to force it to capture posts so you see data.

    for entry in feed.entries:
        print(f"Checking: {entry.title}") # Print titles as they are scanned
        if any(word in entry.title.lower() for word in keywords):
            posts.append({
                "source": "Reddit (RSS)",
                "signal": entry.title,
                "link": entry.link,
                "published": entry.published
            })
            
    return pd.DataFrame(posts)

if __name__ == "__main__":
    df = get_reddit_rss()
    print(df)
    df.to_csv("srilanka_reddit_signals.csv", index=False)