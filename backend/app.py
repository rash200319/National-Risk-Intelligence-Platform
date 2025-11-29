import streamlit as st
from dotenv import load_dotenv
load_dotenv()  # Load keys first

import pandas as pd
import plotly.express as px
import time
from datetime import datetime
from database_manager import db

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
        # Fetch raw risks
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

# --- TAB 1: MAP ---
with tab1:
    map_df = extract_map_data(df)
    if not map_df.empty:
        st.map(map_df, zoom=7, color="#FF0000", size=200)
    else:
        st.info("No location data found in current window.")

# --- TAB 2: ANALYTICS (GRAPHS RESTORED) ---
with tab2:
    if not df.empty:
        # Create columns for the charts
        col1, col2 = st.columns(2)
        
        # 1. Pie Chart
        with col1:
            st.subheader("Source Distribution")
            if 'source' in df.columns:
                source_counts = df['source'].value_counts().reset_index()
                source_counts.columns = ['Source', 'Count']
                fig_pie = px.pie(source_counts, values='Count', names='Source', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
                
        # 2. Bar Chart
        with col2:
            st.subheader("Risk Levels")
            if 'risk_score' in df.columns:
                fig_bar = px.histogram(df, x="risk_score", nbins=10, 
                                      title="Risk Score Distribution", 
                                      color_discrete_sequence=['#ff5722'])
                st.plotly_chart(fig_bar, use_container_width=True)

        # 3. Line Chart
        # 3. ACTIVITY TRENDS (Smart Switching)
        st.subheader("Activity Trends")
        if 'published' in df.columns:
            # Safe Copy
            df_chart = df.copy()
            df_chart['parsed_date'] = pd.to_datetime(df_chart['published'], errors='coerce', utc=True)
            df_chart = df_chart.dropna(subset=['parsed_date'])
            
            if not df_chart.empty:
                # Calculate time span
                min_date = df_chart['parsed_date'].min()
                max_date = df_chart['parsed_date'].max()
                time_diff = max_date - min_date
                
                # LOGIC: 
                # If < 24 hours of data -> Use BAR CHART (Hourly) - easier to see single points
                # If > 24 hours of data -> Use LINE CHART (Daily) - better for trends
                
                if time_diff.days < 1:
                    # HOURLY BAR CHART
                    group_col = 'hour_block'
                    df_chart[group_col] = df_chart['parsed_date'].dt.strftime('%I %p') # e.g. "01 PM"
                    
                    # Group by hour
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    
                    # Sort primarily by time, not just string (optional but good)
                    
                    fig = px.bar(trend, x=group_col, y='count', 
                                 title="Risk Volume (Hourly)",
                                 labels={group_col: "Time", 'count': 'Events'},
                                 color_discrete_sequence=['#ff5722'])
                    
                    # Force bars to be visible width
                    fig.update_layout(bargap=0.5) 
                    
                else:
                    # DAILY LINE CHART
                    group_col = 'date_only'
                    df_chart[group_col] = df_chart['parsed_date'].dt.date
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    
                    fig = px.line(trend, x=group_col, y='count', 
                                  title="Risk Volume (Daily Trend)",
                                  labels={group_col: "Date", 'count': 'Events'},
                                  markers=True) # Always show markers
                    fig.update_traces(line_color='#ff5722', line_width=3)

                st.plotly_chart(fig, use_container_width=True)
# --- TAB 3: FEED ---
with tab3:
    if not df.empty:
        for _, row in df.head(15).iterrows():
            score = row.get('risk_score', 0)
            
            if score >= 8: css = "risk-high"
            elif score >= 5: css = "risk-medium"
            else: css = "risk-low"
            
            st.markdown(f"""
            <div class="metric-card {css}">
                <div class="card-header"><span>{row.get('source')}</span><span>{score}/10</span></div>
                <div>{row.get('signal')}</div>
                <div class="card-footer">{row.get('published')} | <a href="{row.get('link')}" target="_blank">Source</a></div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No data available in Risk Feed.")

# --- AUTO REFRESH ---
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()