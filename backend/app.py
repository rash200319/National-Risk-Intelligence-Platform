'''
import streamlit as st
import pandas as pd
from news_fetcher import fetch_news
from social_listener import get_reddit_rss

# Page Config
st.set_page_config(page_title="MODE-LX: Sri Lanka Situational Awareness", layout="wide")

st.title("🇱🇰 MODE-LX: Real-Time Situational Awareness")
st.markdown("Monitoring national risks, logistics disruptions, and public sentiment.")

# Refresh Button
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

# Columns for Layout
col1, col2 = st.columns(2)

# --- COLUMN 1: NEWS ---
with col1:
    st.subheader("📰 National News (Ada Derana / Daily Mirror)")
    try:
        news_df = fetch_news()
        if not news_df.empty:
            for index, row in news_df.iterrows():
                with st.expander(f"{row['source']}: {row['title']}"):
                    st.write(f"**Published:** {row['published']}")
                    st.write(f"[Read full story]({row['link']})")
        else:
            st.info("No recent news found.")
    except Exception as e:
        st.error(f"Error loading news: {e}")

# --- COLUMN 2: SOCIAL SIGNALS ---
with col2:
    st.subheader("📢 Public Sentiment (Reddit Risk Signals)")
    try:
        social_df = get_reddit_rss()
        if not social_df.empty:
            # Simple "Risk Score" based on keywords
            high_risk_keywords = ["power", "flood", "strike", "shortage"]
            
            for index, row in social_df.iterrows():
                # Highlight High Risk
                title = row['signal']
                is_high_risk = any(k in title.lower() for k in high_risk_keywords)
                
                if is_high_risk:
                    st.error(f"🔴 **RISK:** {title}")
                else:
                    st.warning(f"🔸 {title}")
                
                st.caption(f"Source: {row['source']} | [View Post]({row['link']})")
        else:
            st.success("No active risk signals detected on Reddit.")
    except Exception as e:
        st.error(f"Error loading social signals: {e}")

# Footer
st.markdown("---")
st.caption("Powered by MODE-LX Engine | Built for the Final Hurdle")


import streamlit as st
import pandas as pd
from news_fetcher import fetch_news
from social_listener import get_reddit_rss

st.set_page_config(page_title="MODE-LX Dashboard", layout="wide")

# --- HEADER ---
st.title("🇱🇰 MODE-LX: National Situational Awareness")
st.markdown("Real-time monitoring of economic, infrastructure, and social risks in Sri Lanka.")
st.markdown("---")

# --- FETCH DATA FIRST ---
with st.spinner('Scanning digital signals...'):
    news_df = fetch_news()
    social_df = get_reddit_rss()

# --- CALCULATE RISK SCORE ---
# Simple logic: Start at 0. Add 10 points for every risk signal found.
risk_score = 0
risk_level = "LOW"
risk_color = "green"

if not social_df.empty:
    risk_count = len(social_df)
    risk_score = risk_count * 10 
    
    if risk_score > 50:
        risk_level = "CRITICAL"
        risk_color = "red"
    elif risk_score > 20:
        risk_level = "ELEVATED"
        risk_color = "orange"

# --- TOP METRICS ROW (The "Exec Summary") ---
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric(label="System Status", value="Online", delta="Live Feed")

with col_m2:
    st.metric(label="Risk Signals Detected", value=len(social_df) if not social_df.empty else 0)

with col_m3:
    # Custom HTML for colorful risk level
    st.markdown(f"""
        <div style="text-align: center;">
            <p style="margin:0; font-size: 14px;">National Risk Level</p>
            <h2 style="margin:0; color: {risk_color};">{risk_level} ({risk_score}%)</h2>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- MAIN CONTENT ---
col1, col2 = st.columns([1, 1.5]) # Make the Social column slightly wider

with col1:
    st.subheader("📰 National News")
    if not news_df.empty:
        for index, row in news_df.iterrows():
            st.markdown(f"**{row['source']}**: [{row['title']}]({row['link']})")
            st.caption(f"{row['published']}")
            st.markdown("---")
    else:
        st.info("No news fetched.")

with col2:
    st.subheader("📢 Social Risk Signals (Reddit)")
    if not social_df.empty:
        for index, row in social_df.iterrows():
            with st.container():
                # Make it look like a card
                st.error(f"⚠️ **{row['signal']}**")
                st.markdown(f"*Detected via {row['source']}* | [View Evidence]({row['link']})")
    else:
        st.success("No active community risks detected.")
'''

import streamlit as st
import pandas as pd
from news_fetcher import fetch_news
from social_listener import get_reddit_rss

st.set_page_config(page_title="MODE-LX Dashboard", layout="wide")

# --- 🗺️ THE GEO-LOCATION ENGINE ---
# We map city names to their Latitude/Longitude
SRI_LANKA_CITIES = {
    "Colombo": [6.9271, 79.8612],
    "Kandy": [7.2906, 80.6337],
    "Galle": [6.0535, 80.2210],
    "Jaffna": [9.6615, 80.0255],
    "Trincomalee": [8.5874, 81.2152],
    "Negombo": [7.2088, 79.8358],
    "Matara": [5.9549, 80.5550],
    "Anuradhapura": [8.3114, 80.4037],
    "Kurunegala": [7.4863, 80.3647],
    "Ratnapura": [6.6828, 80.3992],
    "Nuwara Eliya": [6.9497, 80.7891],
    "Batticaloa": [7.7310, 81.6747],
    "Hambantota": [6.1429, 81.1212],
    "Dambulla": [7.8742, 80.6511]
}

def extract_locations(text_df):
    """Scans text for city names and returns a DataFrame of coordinates."""
    locations = []
    if not text_df.empty:
        # Check both columns if they exist, otherwise just use what we have
        text_column = 'signal' if 'signal' in text_df.columns else 'title'
        
        for text in text_df[text_column]:
            for city, coords in SRI_LANKA_CITIES.items():
                if city.lower() in text.lower():
                    locations.append({"lat": coords[0], "lon": coords[1], "City": city})
    
    return pd.DataFrame(locations)

# --- HEADER ---
st.title("🇱🇰 MODE-LX: National Situational Awareness")
st.markdown("Real-time monitoring of economic, infrastructure, and social risks in Sri Lanka.")
st.markdown("---")

# --- FETCH DATA ---
with st.spinner('Scanning digital signals...'):
    news_df = fetch_news()
    social_df = get_reddit_rss()

# --- CALCULATE METRICS ---
risk_score = 0
risk_level = "LOW"
risk_color = "green"

if not social_df.empty:
    risk_score = len(social_df) * 10
    if risk_score > 50:
        risk_level = "CRITICAL"; risk_color = "red"
    elif risk_score > 20:
        risk_level = "ELEVATED"; risk_color = "orange"

# --- TOP METRICS ROW ---
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("System Status", "Online", "Live Feed")
col_m2.metric("Risk Signals Detected", len(social_df) + len(news_df))
col_m3.markdown(f"""
    <div style="text-align: center;">
        <p style="margin:0; font-size: 14px;">National Risk Level</p>
        <h2 style="margin:0; color: {risk_color};">{risk_level} ({risk_score}%)</h2>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- 🗺️ MAP SECTION (THE NEW WOW FACTOR) ---
st.subheader("📍 Live Risk Heatmap")

# 1. Combine all text to find locations
map_data = pd.concat([extract_locations(news_df), extract_locations(social_df)])

if not map_data.empty:
    # Display the map with red dots
    st.map(map_data, zoom=7, size=200, color="#FF0000") 
    st.caption(f"Active risk zones detected: {', '.join(map_data['City'].unique())}")
else:
    st.info("No location-specific risks detected yet (Map will appear when cities are mentioned).")
    # DEFAULT VIEW: Show Colombo just to keep the map visible (Optional trick)
    # st.map(pd.DataFrame({'lat': [6.9271], 'lon': [79.8612]}), zoom=7)

st.markdown("---")

# --- MAIN CONTENT GRID ---
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📰 National News")
    if not news_df.empty:
        for index, row in news_df.iterrows():
            st.markdown(f"**{row['source']}**: [{row['title']}]({row['link']})")
    else:
        st.info("No news fetched.")

with col2:
    st.subheader("📢 Social Risk Signals")
    if not social_df.empty:
        for index, row in social_df.iterrows():
            st.error(f"⚠️ **{row['signal']}**")
            st.markdown(f"*Detected via {row['source']}* | [View Evidence]({row['link']})")
    else:
        st.success("No active community risks detected.")