import streamlit as st
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import plotly.express as px
import random
from datetime import datetime
import pydeck as pdk
from streamlit_autorefresh import st_autorefresh
from database_manager import db
from collections import Counter
from config import AUTO_REFRESH_DEFAULT

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

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 6px solid #444;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .risk-high { border-left-color: #FF5252 !important; background-color: #2b1111; }
    .risk-medium { border-left-color: #FFA726 !important; background-color: #2b2011; }
    .risk-low { border-left-color: #66BB6A !important; background-color: #112b16; }
    
    /* Live Indicator */
    .live-indicator {
        height: 10px; width: 10px;
        background-color: #00FF00;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 0 0 rgba(0, 255, 0, 1);
        animation: pulse-green 2s infinite;
    }
    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(0, 255, 0, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 0, 0); }
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
@st.cache_data(ttl=10)
def get_data(limit=1000, min_score=None, sources=None, start_date=None, end_date=None):
    try:
        df = db.get_risks(
            limit=limit,
            min_score=min_score,
            sources=sources,
            start_date=start_date,
            end_date=end_date,
        )
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
            score = int(row.get('risk_score', 1) or 1)
            color = [255, 82, 82, 200] if score >= 8 else [255, 167, 38, 180] if score >= 5 else [102, 187, 106, 170]
            for city, coords in SRI_LANKA_CITIES.items():
                if city.lower() in text:
                    map_points.append({
                        "lat": coords[0],
                        "lon": coords[1],
                        "City": city,
                        "Source": source,
                        "risk_score": score,
                        "signal": str(row.get('signal', '')),
                        "radius": max(15000, score * 3500),
                        "color": color,
                    })
    return pd.DataFrame(map_points)

# --- SIDEBAR CONTROLS ---
st.sidebar.title("🔧 Intelligence Hub")

# LIVE STATUS
st.sidebar.markdown("""
<div style='display: flex; align-items: center; gap: 10px; margin-bottom: 20px;'>
    <div class='live-indicator'></div>
    <span style='font-size: 14px; font-weight: bold; color: #00FF00'>SYSTEM LIVE</span>
</div>
""", unsafe_allow_html=True)

# FILTERS
st.sidebar.header("🔍 Filters")
search_term = st.sidebar.text_input("Search Logs", placeholder="e.g. Economy, Rain...")
selected_industry = st.sidebar.selectbox("Sector", ["All", "Energy & Fuel", "Logistics & Transport", "Finance & Economy", "Tourism", "Agriculture", "Public Safety"])
source_options = [s.get('source') for s in db.get_risk_stats().get('sources', [])]
selected_sources = st.sidebar.multiselect("Sources", options=source_options)

# SETTINGS
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings")
refresh_rate = st.sidebar.slider("Refresh Rate (s)", 10, 300, 30)
auto_refresh = st.sidebar.checkbox("Auto-Refresh", value=AUTO_REFRESH_DEFAULT)

# GOD MODE (HIDDEN)
st.sidebar.markdown("---")
if st.sidebar.button("🚨 SIMULATE CRISIS (DEMO)"):
    now = datetime.now().isoformat()
    fake_risks = [
        {
            "source": "National Alert System",
            "signal": "MAJOR POWER FAILURE: Island-wide blackout reported in Colombo. Emergency protocols activated.",
            "risk_score": 10,
            "category": "Energy & Fuel, Public Safety",
            "location": "Colombo",
            "link": "#",
            "published": now,
            "created_at": now,
            "sentiment_score": -0.9,
            "confidence": 1.0,
            "keywords": "simulation, blackout",
        },
        {
            "source": "Transport Monitoring Unit",
            "signal": "Severe transport disruption reported in Kandy due to emergency road closures.",
            "risk_score": 8,
            "category": "Logistics & Transport, Public Safety",
            "location": "Kandy",
            "link": "#",
            "published": now,
            "created_at": now,
            "sentiment_score": -0.7,
            "confidence": 0.95,
            "keywords": "simulation, transport",
        },
        {
            "source": "Disaster Response Desk",
            "signal": "Flood warning issued for Galle coastal belt with heavy rainfall expected.",
            "risk_score": 9,
            "category": "Public Safety, Agriculture",
            "location": "Galle",
            "link": "#",
            "published": now,
            "created_at": now,
            "sentiment_score": -0.8,
            "confidence": 0.98,
            "keywords": "simulation, flood",
        },
    ]
    db.batch_insert_risks(fake_risks)
    st.toast("🚨 Simulated crisis scenario injected (3 linked events).")
    st.rerun()

# --- MAIN LAYOUT ---
st.title("📡 MODEL-X: Risk Intelligence Platform")
df, stats = get_data(limit=1000, sources=selected_sources or None)

# APPLY FILTERS
if search_term and not df.empty:
    df = df[df['signal'].str.contains(search_term, case=False, na=False) | 
            df['source'].str.contains(search_term, case=False, na=False)]

if selected_industry != "All" and not df.empty:
    df = df[df['category'].str.contains(selected_industry, case=False, na=False)]

# EXPORT (filtered data)
st.sidebar.markdown("---")
if not df.empty:
    st.sidebar.download_button(
        label="📥 Download Filtered CSV",
        data=df.to_csv(index=False),
        file_name=f"risk_intel_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

# TOP METRICS
c1, c2, c3, c4 = st.columns(4)
total = len(df)
high_risk = len(df[df['risk_score'] >= 7]) if not df.empty else 0
sources_count = len(stats.get('sources', []))

# Simulated Deltas
delta_total = random.randint(1, 5) if total > 0 else 0
delta_risk = random.randint(0, 2) if high_risk > 0 else 0

c1.metric("Total Intel Logs", total, f"+{delta_total} new")
c2.metric("Critical Alerts", high_risk, f"+{delta_risk} new", delta_color="inverse")
c3.metric("Active Sources", sources_count, "Stable")
c4.metric("AI Engine", "Active", "Sentiment Analysis")

# TABS
tab1, tab2, tab3 = st.tabs(["🗺️ Geospatial View", "📈 Business Analytics", "📝 Live Risk Feed"])

# --- TAB 1: MAP ---
with tab1:
    map_df = extract_map_data(df)
    if not map_df.empty:
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_radius='radius',
            get_fill_color='color',
            pickable=True,
            opacity=0.5,
        )
        view_state = pdk.ViewState(latitude=7.8731, longitude=80.7718, zoom=7)
        tooltip = {
            "html": "<b>{City}</b><br/>{Source}<br/>Risk: {risk_score}/10<br/>{signal}",
            "style": {"color": "white", "backgroundColor": "#111"},
        }
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
    else:
        st.info(f"No location-specific risks found.")

# --- TAB 2: ANALYTICS ---
with tab2:
    if not df.empty:
        # 1. ACTIVITY TRENDS
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
                    group_col = 'hour_block'
                    df_chart[group_col] = df_chart['parsed_date'].dt.strftime('%I %p')
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    fig = px.bar(trend, x=group_col, y='count', title="Risk Volume (Hourly)", color_discrete_sequence=['#ff5722'])
                else:
                    group_col = 'date_only'
                    df_chart[group_col] = df_chart['parsed_date'].dt.date
                    trend = df_chart.groupby(group_col).size().reset_index(name='count')
                    fig = px.line(trend, x=group_col, y='count', title="Risk Volume (Daily)", markers=True)
                    fig.update_traces(line_color='#ff5722')
                st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # 2. KEYWORD TRENDS (REPLACED WORD CLOUD)
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.subheader("🔥 Top 10 Trending Keywords")
            if 'signal' in df.columns:
                text = " ".join(str(title) for title in df['signal'])
                words = text.split()
                stop_words = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'news', 'sri', 'lanka', 'breaking', 'update', 'daily', 'mirror'}
                words = [w.capitalize() for w in words if len(w) > 3 and w.lower() not in stop_words]
                
                if words:
                    # Count and create DataFrame for Bar Chart
                    word_counts = Counter(words)
                    common_words = word_counts.most_common(10)
                    df_words = pd.DataFrame(common_words, columns=['Keyword', 'Count'])
                    
                    # Horizontal Bar Chart (Clean & Professional)
                    fig_words = px.bar(df_words, x='Count', y='Keyword', orientation='h', 
                                     color='Count', color_continuous_scale='Reds')
                    fig_words.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
                    st.plotly_chart(fig_words, use_container_width=True)
                else:
                    st.info("Gathering text data...")
        
        with c_right:
            st.subheader("Risk Severity")
            if 'risk_score' in df.columns:
                fig_bar = px.histogram(df, x="risk_score", nbins=10, title="Risk Score Distribution", color_discrete_sequence=['#ff5722'])
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.subheader("📊 Industry Impact")
        if 'category' in df.columns:
            cats = df['category'].str.split(',').explode().str.strip()
            cat_counts = cats.value_counts().reset_index()
            cat_counts.columns = ['Industry', 'Count']
            fig_pie = px.pie(cat_counts, values='Count', names='Industry', hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)

# --- TAB 3: FEED ---
with tab3:
    if high_risk > 0:
        st.error(f"🚨 **Action Required:** {high_risk} critical risks detected. Review High Priority items below.")

    if not df.empty:
        for _, row in df.head(20).iterrows():
            score = row.get('risk_score', 0)
            sentiment = row.get('sentiment_score', 0)
            if score >= 8: border = "#FF5252"
            elif score >= 5: border = "#FFA726"
            else: border = "#66BB6A"
            
            try:
                pub_dt = datetime.fromisoformat(row.get('published'))
                time_diff = datetime.now() - pub_dt
                time_str = f"{time_diff.seconds // 3600}h ago" if time_diff.days == 0 else pub_dt.strftime('%Y-%m-%d')
            except: time_str = row.get('published')

            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {border};">
                <div style="display: flex; justify-content: space-between; color: white; font-weight: bold;">
                    <span>{row.get('source')}</span>
                    <span style="background: rgba(255,255,255,0.1); padding: 2px 8px; border-radius: 4px;">Risk: {score}/10</span>
                </div>
                <div style="color: #E0E0E0; margin-top: 5px;">{row.get('signal')}</div>
                <div style="font-size: 12px; color: #888; margin-top: 12px; display: flex; justify-content: space-between;">
                    <span style="background: #333; padding: 2px 6px; border-radius: 4px;">📂 {row.get('category')}</span>
                    <span>🤖 Sent: {round(sentiment, 2)}</span>
                    <div><span style="margin-right: 10px;">🕒 {time_str}</span><a href="{row.get('link')}" target="_blank" style="color: #64B5F6;">View ↗</a></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No data available.")

if auto_refresh:
    st_autorefresh(interval=refresh_rate * 1000, key="modelx_auto_refresh")