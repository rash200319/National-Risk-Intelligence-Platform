import feedparser
import pandas as pd
import requests
from io import BytesIO

def get_reddit_rss():
    print("Scanning r/srilanka via RSS...")
    rss_url = "https://www.reddit.com/r/srilanka/new/.rss"
    
    # User-Agent prevents Reddit from blocking the script
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(rss_url, headers=headers)
        feed = feedparser.parse(BytesIO(response.content))
        
        posts = []
        
        # --- FINAL CLEAN KEYWORDS LIST ---
        # These are specific to Sri Lankan business risks
        keywords = [
            "power", "water", "fuel", "gas", "electricity",
            "strike", "protest", "curfew", "violence",
            "shortage", "price", "tax", "economy", "dollar",
            "delay", "blocked", "traffic", "road",
            "flood", "rain", "weather", "landslide"
        ]
        
        for entry in feed.entries:
            # Check if any keyword is in the title (case insensitive)
            if any(word in entry.title.lower() for word in keywords):
                posts.append({
                    "source": "Reddit (RSS)",
                    "signal": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", "N/A")
                })
        
        # Sort by newest first (just in case)
        df = pd.DataFrame(posts)
        print(f"DEBUG: Found {len(df)} relevant risk signals.")
        return df

    except Exception as e:
        print(f"Error fetching Reddit: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test run
    df = get_reddit_rss()
    print(df)
    if not df.empty:
        df.to_csv("srilanka_reddit_signals.csv", index=False)
        print("✅ Clean data saved.")
    else:
        print("ℹ️ No high-risk signals found right now (this is good news for the country, but empty for the CSV).")