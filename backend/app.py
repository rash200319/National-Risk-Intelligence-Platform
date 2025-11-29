'''
import streamlit as st
import pandas as pd
from modules.database import fetch_all_data, fetch_stats


# --- MAP CONFIGURATION ---
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
    """Scans text for city names and returns coordinates."""
    locations = []
    if not text_df.empty:
        # Check every row in the 'signal' column
        for text in text_df['signal']:
            for city, coords in SRI_LANKA_CITIES.items():
                if city.lower() in str(text).lower():
                    locations.append({"lat": coords[0], "lon": coords[1], "City": city})
    return pd.DataFrame(locations)

st.set_page_config(page_title="MODE-LX Pro", layout="wide", page_icon="🇱🇰")

# --- CUSTOM CSS FOR PROFESSIONAL UI ---
st.markdown("""
    <style>
    .metric-card {background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #1f77b4;}
    .stMetric {background-color: #1E1E1E; padding: 10px; border-radius: 5px;}
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🔧 System Controls")
st.sidebar.markdown("**MODE-LX Enterprise v1.0**")
data_limit = st.sidebar.slider("Historical Data Depth", 50, 2000, 100)
auto_refresh = st.sidebar.checkbox("Auto-Refresh Dashboard", value=False)

if auto_refresh:
    import time
    time.sleep(30) # Refresh every 30s
    st.rerun()

# --- LOAD DATA ---
df = fetch_all_data(limit=data_limit)
total_records = fetch_stats()

# --- HEADER SECTION ---
st.title("🇱🇰 MODE-LX: National Situational Awareness")
c1, c2, c3, c4 = st.columns(4)
c1.metric("System Status", "ONLINE", "Monitoring")
c2.metric("Total Intelligence Records", total_records)
c3.metric("Critical Alerts (24h)", len(df[df['risk_score'] >= 10]), delta_color="inverse")
c4.metric("Sources Active", df['source'].nunique() if not df.empty else 0)

st.markdown("---")

# --- TABS FOR ORGANIZED VIEW ---
tab1, tab2, tab3 = st.tabs(["📊 Executive Dashboard", "📍 Live Geo-Map", "🗃️ Data Explorer"])

# TAB 1: EXECUTIVE VIEW
with tab1:
    col_news, col_social = st.columns(2)
    
    with col_news:
        st.subheader("📰 Latest News Signals")
        news_data = df[~df['source'].str.contains("Reddit", na=False)]
        if not news_data.empty:
            for _, row in news_data.head(5).iterrows():
                st.markdown(f"**{row['source']}**: [{row['signal']}]({row['link']})")
                st.caption(f"Published: {row['published']}")
                st.markdown("---")
    
    with col_social:
        st.subheader("📢 High Risk Social Indicators")
        social_data = df[df['source'].str.contains("Reddit", na=False)]
        critical = social_data[social_data['risk_score'] >= 5]
        if not critical.empty:
            for _, row in critical.head(5).iterrows():
                st.error(f"⚠️ **{row['signal']}**")
                st.markdown(f"[View Source]({row['link']}) | Score: {row['risk_score']}")
        else:
            st.success("No critical social risks detected in recent stream.")

# TAB 2: MAP (Use your existing map logic here)
# TAB 2: LIVE MAP
with tab2:
    st.subheader("📍 Geospatial Risk Visualization")
    
    # 1. Run the extractor on ALL data
    map_data = extract_locations(df)

    if not map_data.empty:
        # 2. Show the map
        st.map(map_data, zoom=7, size=200, color="#FF0000") 
        
        # 3. Show a list of affected cities
        unique_cities = map_data['City'].unique()
        st.caption(f"🔴 **Active Risk Zones:** {', '.join(unique_cities)}")
    else:
        st.info("No location-specific risks detected yet. (Map appears when cities like 'Colombo' or 'Kandy' are mentioned).")

# TAB 3: DATA EXPLORER (The 'Big Data' Proof)
with tab3:
    st.subheader("🗃️ Full Data Lake Access")
    st.markdown("Raw intelligence log for auditing and analysis.")
    
    # Search Bar
    search = st.text_input("Search Database", placeholder="e.g., 'Floods', 'Colombo', 'Economy'")
    
    view_df = df
    if search:
        view_df = df[df['signal'].str.contains(search, case=False, na=False)]
    
    st.dataframe(view_df[['created_at', 'source', 'risk_score', 'signal']], use_container_width=True, height=500)

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
from database_manager import db

# --- CONFIGURATION ---
st.set_page_config(
    page_title="MODEL-X Risk Intelligence",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- MAP COORDINATES ---
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
}

# --- DARK THEME CSS ---
st.markdown("""
    <style>
    /* Main Card Container */
    .metric-card {
        background-color: #1E1E1E; /* Dark Grey Background */
        border: 1px solid #333;
        color: #E0E0E0; /* Light Text */
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 6px solid #444;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
    }

    /* RISK LEVEL: HIGH (Red Neon) */
    .risk-high {
        border-left-color: #FF5252;
        background-color: #2C0B0E; /* Very Dark Red Tint */
    }

    /* RISK LEVEL: MEDIUM (Orange Neon) */
    .risk-medium {
        border-left-color: #FFA726;
        background-color: #2C1E0B; /* Very Dark Orange Tint */
    }

    /* RISK LEVEL: LOW (Green Neon) */
    .risk-low {
        border-left-color: #66BB6A;
        background-color: #0B2C14; /* Very Dark Green Tint */
    }

    /* Text Typography inside Cards */
    .card-header {
        font-size: 16px;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
        color: #FFFFFF;
    }
    
    .card-body {
        font-size: 14px;
        line-height: 1.5;
        margin-bottom: 12px;
        color: #D1D1D1;
    }

    .card-footer {
        font-size: 12px;
        color: #888;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid #333;
        padding-top: 8px;
    }

    /* Link Styling */
    .card-footer a {
        color: #64B5F6;
        text-decoration: none;
        font-weight: bold;
    }
    .card-footer a:hover {
        text-decoration: underline;
        color: #9BE7FF;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_data(limit=500, days_back=30):
    try:
        df = db.get_risks(limit=limit)
        stats = db.get_risk_stats()
        return df, stats
    except Exception as e:
        st.error(f"DB Error: {e}")
        return pd.DataFrame(), {}

def extract_map_data(df):
    map_points = []
    if not df.empty and 'signal' in df.columns:
        for _, row in df.iterrows():
            text = str(row.get('signal', '')).lower()
            source = row.get('source', 'Unknown')
            for city, coords in SRI_LANKA_CITIES.items():
                if city.lower() in text:
                    map_points.append({
                        "lat": coords[0],
                        "lon": coords[1],
                        "City": city,
                        "Source": source
                    })
    return pd.DataFrame(map_points)

# --- SIDEBAR ---
st.sidebar.title("🔧 Controls")
refresh_rate = st.sidebar.slider("Refresh (seconds)", 10, 300, 30)
auto_refresh = st.sidebar.checkbox("Auto-Refresh", value=True)
st.sidebar.markdown("---")
days_back = st.sidebar.slider("History (Days)", 1, 90, 30)

# --- MAIN DASHBOARD ---
st.title("📡 MODEL-X: National Risk Dashboard")

# 1. Fetch Data
df, stats = get_data(limit=500, days_back=days_back)

# 2. Key Metrics
col1, col2, col3, col4 = st.columns(4)
total = stats.get('total_risks', 0)
high_risk = len(df[df['risk_score'] >= 7]) if not df.empty and 'risk_score' in df.columns else 0
sources = len(stats.get('sources', []))

col1.metric("Total Intel Logs", total)
col2.metric("Critical Alerts", high_risk, delta_color="inverse")
col3.metric("Active Sources", sources)
col4.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))

# 3. Visuals & Map
tab1, tab2, tab3 = st.tabs(["🗺️ Live Map", "📈 Analytics", "📝 Risk Feed"])

with tab1:
    st.subheader("📍 Geospatial Risk Visualization")
    map_df = extract_map_data(df)
    if not map_df.empty:
        st.map(map_df, zoom=7, color="#FF0000", size=200)
        st.caption(f"Detected activity in: {', '.join(map_df['City'].unique())}")
    else:
        st.info("No location-specific risks detected yet.")

with tab2:
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("⚠️ Risk Severity")
            if 'risk_score' in df.columns:
                fig_hist = px.histogram(df, x="risk_score", nbins=10, 
                                      title="Risk Score Distribution", color_discrete_sequence=['#ff5722'])
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with c2:
            st.subheader("📅 Activity Over Time")
            if 'published' in df.columns:
                try:
                    df['parsed_date'] = pd.to_datetime(df['published'], errors='coerce', utc=True)
                    clean_df = df.dropna(subset=['parsed_date']).copy()
                    
                    if not clean_df.empty:
                        clean_df['date_only'] = clean_df['parsed_date'].dt.date
                        trend = clean_df.groupby('date_only').size().reset_index(name='count')
                        fig_line = px.line(trend, x='date_only', y='count', title="Daily Risk Volume")
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.warning("No valid dates found for trend analysis.")
                except Exception as e:
                    st.error(f"Error generating trend chart: {e}")

with tab3:
    st.subheader("🔴 Live Intelligence Stream")
    if not df.empty:
        for _, row in df.head(15).iterrows():
            score = row.get('risk_score', 0)
            
            # Assign CSS class based on risk score
            if score >= 7:
                css = "risk-high"
                score_label = "HIGH RISK"
            elif score >= 4:
                css = "risk-medium"
                score_label = "MEDIUM RISK"
            else:
                css = "risk-low"
                score_label = "LOW RISK"
            
            source = row.get('source', 'Unknown')
            date = row.get('published', 'N/A')
            text = row.get('signal', 'No content available')
            link = row.get('link', '#')

            # Render HTML Card
            st.markdown(f"""
            <div class="metric-card {css}">
                <div class="card-header">
                    <span>{source}</span>
                    <span>{score_label} ({score}/10)</span>
                </div>
                <div class="card-body">
                    {text}
                </div>
                <div class="card-footer">
                    <span>🕒 {date}</span>
                    <a href="{link}" target="_blank">View Source ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# --- AUTO-REFRESH ---
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
'''
import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime
from database_manager import db

# --- 1. CONFIGURATION (MUST BE FIRST) ---
st.set_page_config(
    page_title="MODEL-X Risk Intelligence",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. AUTO-START COLLECTOR ---
# We initialize this AFTER set_page_config
@st.cache_resource
def start_background_collector():
    from collector import collector
    collector.start()
    return collector

# Initialize the collector immediately
_ = start_background_collector()

# --- MAP COORDINATES ---
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
}

# --- DARK THEME CSS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        color: #E0E0E0;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 6px solid #444;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .risk-high { border-left-color: #FF5252; background-color: #2C0B0E; }
    .risk-medium { border-left-color: #FFA726; background-color: #2C1E0B; }
    .risk-low { border-left-color: #66BB6A; background-color: #0B2C14; }
    .card-header { font-weight: 600; display: flex; justify-content: space-between; color: #FFF; }
    .card-footer { font-size: 12px; color: #888; margin-top: 8px; }
    .card-footer a { color: #64B5F6; text-decoration: none; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def get_data(limit=500, days_back=30):
    try:
        df = db.get_risks(limit=limit)
        stats = db.get_risk_stats()
        return df, stats
    except Exception as e:
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
days_back = st.sidebar.slider("History (Days)", 1, 90, 30)

# --- MAIN LAYOUT ---
st.title("📡 MODEL-X: National Risk Dashboard")
df, stats = get_data(limit=1000, days_back=days_back)

# Top Metrics
c1, c2, c3, c4 = st.columns(4)
total = stats.get('total_risks', 0)
high_risk = len(df[df['risk_score'] >= 7]) if not df.empty and 'risk_score' in df.columns else 0
c1.metric("Total Intel Logs", total)
c2.metric("Critical Alerts", high_risk, delta_color="inverse")
c3.metric("Active Sources", len(stats.get('sources', [])))
c4.metric("System Status", "ONLINE", "Collector Running")

# Tabs
tab1, tab2, tab3 = st.tabs(["🗺️ Live Map", "📈 Analytics", "📝 Risk Feed"])

with tab1:
    map_df = extract_map_data(df)
    if not map_df.empty:
        st.map(map_df, zoom=7, color="#FF0000", size=200)
    else:
        st.info("No location data found in current window.")

with tab2:
    if not df.empty and 'published' in df.columns:
        df['parsed_date'] = pd.to_datetime(df['published'], errors='coerce', utc=True)
        clean_df = df.dropna(subset=['parsed_date'])
        if not clean_df.empty:
            clean_df['date_only'] = clean_df['parsed_date'].dt.date
            trend = clean_df.groupby('date_only').size().reset_index(name='count')
            st.plotly_chart(px.line(trend, x='date_only', y='count', title="Risk Volume Trend (Last 90 Days)"), use_container_width=True)

with tab3:
    if not df.empty:
        for _, row in df.head(15).iterrows():
            score = row.get('risk_score', 0)
            css = "risk-high" if score >= 7 else "risk-medium" if score >= 4 else "risk-low"
            st.markdown(f"""
            <div class="metric-card {css}">
                <div class="card-header"><span>{row.get('source')}</span><span>{score}/10</span></div>
                <div>{row.get('signal')}</div>
                <div class="card-footer">{row.get('published')} | <a href="{row.get('link')}" target="_blank">Source</a></div>
            </div>
            """, unsafe_allow_html=True)

if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()