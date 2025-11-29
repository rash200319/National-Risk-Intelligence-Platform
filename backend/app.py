import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.express as px
import time
from datetime import datetime
from database_manager import db
import matplotlib.pyplot as plt
from wordcloud import WordCloud

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="MODEL-X Risk Intelligence",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. AUTO-START COLLECTOR ---
@st.cache_resource
def start_background_collector():
    from collector import collector
    collector.start()
    return collector

_ = start_background_collector()

# --- MAP COORDINATES ---
SRI_LANKA_CITIES = {
    "Colombo": [6.9271, 79.8612], "Kandy": [7.2906, 80.6337],
    "Galle": [6.0535, 80.2210], "Jaffna": [9.6615, 80.0255],
    "Trincomalee": [8.5874, 81.2152], "Negombo": [7.2088, 79.8358],
    "Matara": [5.9549, 80.5550], "Anuradhapura": [8.3114, 80.4037]
}

# --- HELPER FUNCTIONS ---
def get_data(limit=1000):
    try:
        df = db.get_risks(limit=limit)
        stats = db.get_risk_stats()
        return df, stats
    except Exception:
        return pd.DataFrame(), {}

def extract_map_data(df):
    map_points = []
    if not df.empty and 'signal' in df.columns:
        for _, row in df.iterrows():
            text = str(row.get('signal', '')).lower()
            source = row.get('source', 'Unknown')
            for city, coords in SRI_LANKA_CITIES.items():
                if city.lower() in text:
                    map_points.append({"lat": coords[0], "lon": coords[1], "City": city, "Source": source})
    return pd.DataFrame(map_points)

# --- SIDEBAR ---
st.sidebar.title("🔧 Controls")
refresh_rate = st.sidebar.slider("Refresh (seconds)", 10, 300, 30)
auto_refresh = st.sidebar.checkbox("Auto-Refresh", value=True)

# NEW: Industry Filter
st.sidebar.markdown("---")
st.sidebar.header("🏢 Industry Impact")
selected_industry = st.sidebar.selectbox("Filter by Sector", ["All", "Energy & Fuel", "Logistics & Transport", "Finance & Economy", "Tourism", "Agriculture", "Public Safety"])

# --- MAIN LAYOUT ---
st.title("📡 MODEL-X: Risk Intelligence Platform")
df, stats = get_data(limit=1000)

# APPLY FILTER: Filter Data by Industry
if selected_industry != "All" and not df.empty:
    # Filter columns that contain the selected industry string
    df = df[df['category'].str.contains(selected_industry, case=False, na=False)]

# Top Metrics
c1, c2, c3, c4 = st.columns(4)
total = len(df)
high_risk = len(df[df['risk_score'] >= 7]) if not df.empty else 0
c1.metric("Total Intel Logs", total)
c2.metric("Critical Alerts", high_risk, delta_color="inverse")
c3.metric("Active Sources", len(stats.get('sources', [])))
c4.metric("AI Engine", "Active", "Sentiment Analysis")

# Tabs
tab1, tab2, tab3 = st.tabs(["🗺️ Geospatial View", "📈 Business Analytics", "📝 Live Risk Feed"])

# --- TAB 1: MAP ---
with tab1:
    map_df = extract_map_data(df)
    if not map_df.empty:
        st.map(map_df, zoom=7, color="#FF0000", size=200)
    else:
        st.info(f"No location-specific risks found for {selected_industry}.")

# --- TAB 2: ANALYTICS (NOW WITH WORD CLOUD) ---
with tab2:
    if not df.empty:
        # Row 1: Activity Trend (Smart Bar/Line)
        st.subheader("Activity Trends")
        if 'published' in df.columns:
            df_chart = df.copy()
            df_chart['parsed_date'] = pd.to_datetime(df_chart['published'], errors='coerce', utc=True)
            df_chart = df_chart.dropna(subset=['parsed_date'])
            
            if not df_chart.empty:
                min_date = df_chart['parsed_date'].min()
                max_date = df_chart['parsed_date'].max()
                time_diff = max_date - min_date
                
                if time_diff.days < 1:
                    # Hourly Bar Chart
                    group_col = 'hour_block'
                    df_chart[group_col] = df_chart['parsed_date'].dt.strftime('%I %p')
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    fig = px.bar(trend, x=group_col, y='count', title="Risk Volume (Hourly)", color_discrete_sequence=['#ff5722'])
                else:
                    # Daily Line Chart
                    group_col = 'date_only'
                    df_chart[group_col] = df_chart['parsed_date'].dt.date
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    fig = px.line(trend, x=group_col, y='count', title="Risk Volume (Daily)", markers=True)
                    
                st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Row 2: Word Cloud & Risk Levels
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.subheader("🔥 Trending Topics")
            if 'signal' in df.columns:
                # Combine all text
                text = " ".join(str(title) for title in df['signal'])
                
                if text.strip():
                    try:
                        # Generate Cloud
                        wordcloud = WordCloud(
                            width=600, 
                            height=400, 
                            background_color='#1E1E1E', # Dark background to match theme
                            colormap='Reds',
                            min_font_size=10
                        ).generate(text)
                        
                        # Display using explicit figure
                        fig = plt.figure(figsize=(6, 4), facecolor='#1E1E1E')
                        plt.imshow(wordcloud, interpolation='bilinear')
                        plt.axis("off")
                        plt.tight_layout(pad=0)
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig) # Clean up memory
                    except Exception as e:
                        st.error(f"Could not generate word cloud: {e}")
                else:
                    st.info("Not enough text data for Word Cloud.")
        
        with c_right:
            st.subheader("Risk Severity")
            if 'risk_score' in df.columns:
                fig_bar = px.histogram(df, x="risk_score", nbins=10, 
                                      title="Risk Score Distribution", 
                                      color_discrete_sequence=['#ff5722'])
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        
        # Row 3: Industry Pie Chart
        st.subheader("📊 Industry Impact")
        if 'category' in df.columns:
            # Handle comma-separated tags (e.g., "Economy, Politics")
            cats = df['category'].str.split(',').explode().str.strip()
            cat_counts = cats.value_counts().reset_index()
            cat_counts.columns = ['Industry', 'Count']
            fig_pie = px.pie(cat_counts, values='Count', names='Industry', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 3: FEED (WITH SENTIMENT TAGS) ---
with tab3:
    if not df.empty:
        for _, row in df.head(20).iterrows():
            score = row.get('risk_score', 0)
            sentiment = row.get('sentiment_score', 0)
            
            if score >= 8: border = "#FF5252"
            elif score >= 5: border = "#FFA726"
            else: border = "#66BB6A"
            
            st.markdown(f"""
            <div style="background-color: #1E1E1E; border-left: 5px solid {border}; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; color: white; font-weight: bold;">
                    <span>{row.get('source')}</span>
                    <span>Risk: {score}/10</span>
                </div>
                <div style="color: #E0E0E0; margin-top: 5px; font-size: 1.1em;">{row.get('signal')}</div>
                <div style="font-size: 12px; color: #888; margin-top: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span>📂 {row.get('category')}</span>
                    <span style="background-color: #333; padding: 2px 6px; border-radius: 4px;">🤖 Sentiment: {round(sentiment, 2)}</span>
                    <a href="{row.get('link')}" target="_blank" style="color: #64B5F6; text-decoration: none;">Read More ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No data available.")

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()