"""
Streamlit dashboard for health monitoring and data source status.
Shows real-time health status of all data collection sources.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from utils.health import health_monitor
import json


def render_health_dashboard():
    """Render the health monitoring dashboard."""
    
    st.set_page_config(page_title="Health Monitor", layout="wide")
    st.markdown("# 📊 Data Collection Health Monitor")
    
    # Get health data
    dashboard_data = health_monitor.get_dashboard_data()
    overall = dashboard_data['overall_health']
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        health_pct = float(overall.get('health_percentage', '0').rstrip('%'))
        if overall.get('overall_status') == 'no_data':
            color = "⚪"
        else:
            color = "🟢" if health_pct >= 80 else "🟡" if health_pct >= 60 else "🔴"
        st.metric(
            "System Health",
            f"{color} {overall.get('health_percentage', 'N/A')}",
            delta=f"{overall.get('healthy_sources', 0)}/{overall.get('active_sources', 0)} active ({overall.get('total_sources', 0)} total)"
        )
    
    with col2:
        success_rate = float(overall.get('overall_success_rate', '0').rstrip('%'))
        st.metric(
            "Success Rate",
            f"{overall.get('overall_success_rate', 'N/A')}",
            delta=f"{overall['uptime']['successful_collections']} successful"
        )
    
    with col3:
        best_source = overall.get('best_performing', 'N/A')
        st.metric(
            "Best Source",
            best_source,
            delta="Most reliable"
        )
    
    with col4:
        worst_source = overall.get('worst_performing', 'N/A')
        st.metric(
            "Needs Attention",
            worst_source if worst_source != 'N/A' else "All Good!",
            delta="Issues detected" if worst_source != 'N/A' else "No issues"
        )
    
    st.divider()
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Source Status", "📊 Graphs", "📋 Logs", "⚙️ Details"])
    
    with tab1:
        render_source_status(dashboard_data)
    
    with tab2:
        render_graphs(dashboard_data)
    
    with tab3:
        render_logs(dashboard_data)
    
    with tab4:
        render_details(dashboard_data)


def render_source_status(dashboard_data):
    """Render individual source health status."""
    st.subheader("Source Health Status")
    
    sources_health = dashboard_data['sources_health']
    
    if not sources_health:
        st.info("No sources registered yet")
        return
    
    # Create health status table
    health_data = []
    for source_name, stats in sources_health.items():
        health_data.append({
            'Source': source_name,
            'Status': stats['status'].upper(),
            'Type': stats['source_type'],
            'Last Fetch': stats['time_since_last_fetch'] or 'Never',
            'Success': f"{stats['success_count']}",
            'Failures': f"{stats['failure_count']}",
            'Success Rate': stats['success_rate'],
            'Latest Items': f"{stats['last_items_count']}",
            'Total Items': f"{stats.get('total_items_collected', 0)}",
            'Last Error': stats['last_error'][:50] if stats['last_error'] != 'None' else '✓'
        })
    
    df_health = pd.DataFrame(health_data)
    badge_map = {
        'HEALTHY': '🟢 Healthy',
        'UNHEALTHY': '🔴 Unhealthy',
        'NO_DATA': '⚪ No Data'
    }
    df_health['Status Badge'] = df_health['Status'].map(lambda value: badge_map.get(value, value))
    display_columns = [
        'Source',
        'Status Badge',
        'Type',
        'Last Fetch',
        'Success',
        'Failures',
        'Success Rate',
        'Latest Items',
        'Total Items',
        'Last Error',
    ]

    st.dataframe(df_health[display_columns], use_container_width=True, hide_index=True)
    
    # Source details in expanders
    st.subheader("Detailed Source Information")
    
    for source_name, stats in sources_health.items():
        with st.expander(f"📌 {source_name} - {stats['status'].upper()}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Type", stats['source_type'])
                st.metric("Last Fetch", stats['time_since_last_fetch'] or 'Never')
                st.metric("Uptime", f"{stats['uptime_days']} days")
            
            with col2:
                st.metric("Total Attempts", stats['total_attempts'])
                st.metric("Successful", stats['success_count'])
                st.metric("Failed", stats['failure_count'])
            
            with col3:
                st.metric("Success Rate", stats['success_rate'])
                st.metric("Latest Items", stats['last_items_count'])
                st.metric("Total Items", stats.get('total_items_collected', 0))
                if stats['last_error'] != 'None':
                    st.warning(f"Last Error: {stats['last_error']}")


def render_graphs(dashboard_data):
    """Render health graphs and visualizations."""
    st.subheader("Health Visualizations")
    
    sources_health = dashboard_data['sources_health']
    logs = dashboard_data['recent_logs']
    
    col1, col2 = st.columns(2)
    
    # Success Rate by Source
    with col1:
        health_data = []
        for source_name, stats in sources_health.items():
            success_rate = float(stats['success_rate'].rstrip('%'))
            health_data.append({'Source': source_name, 'Success Rate (%)': success_rate})
        
        if health_data:
            df_rates = pd.DataFrame(health_data).sort_values('Success Rate (%)', ascending=True)
            fig = px.bar(
                df_rates,
                x='Success Rate (%)',
                y='Source',
                title='Success Rate by Source',
                color='Success Rate (%)',
                color_continuous_scale=['red', 'yellow', 'green'],
                range_color=[0, 100],
                orientation='h'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Attempts by Source
    with col2:
        attempt_data = []
        for source_name, stats in sources_health.items():
            attempt_data.append({
                'Source': source_name,
                'Successful': stats['success_count'],
                'Failed': stats['failure_count']
            })
        
        if attempt_data:
            df_attempts = pd.DataFrame(attempt_data)
            fig = px.bar(
                df_attempts,
                x='Source',
                y=['Successful', 'Failed'],
                title='Collection Attempts by Source',
                barmode='stack',
                color_discrete_map={'Successful': '#90EE90', 'Failed': '#FFB6C6'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Timeline of Recent Logs
    if logs:
        st.subheader("Collection Timeline")
        
        # Convert logs to DataFrame
        log_data = []
        for log in logs[-50:]:  # Last 50 logs
            log_data.append({
                'Time': log['timestamp'],
                'Source': log['source'],
                'Status': 'Success' if log['success'] else 'Failed',
                'Items': log['items']
            })
        
        df_logs = pd.DataFrame(log_data)
        if not df_logs.empty:
            df_logs['Time'] = pd.to_datetime(df_logs['Time'])
            
            fig = px.scatter(
                df_logs,
                x='Time',
                y='Source',
                color='Status',
                size='Items',
                title='Collection Activity Timeline',
                color_discrete_map={'Success': '#90EE90', 'Failed': '#FFB6C6'},
                hover_data=['Items']
            )
            st.plotly_chart(fig, use_container_width=True)


def render_logs(dashboard_data):
    """Render recent collection logs."""
    st.subheader("Recent Collection Logs")
    
    logs = dashboard_data['recent_logs']
    
    if not logs:
        st.info("No logs yet")
        return
    
    # Display logs in reverse order (newest first)
    for log in reversed(logs[-100:]):
        status_icon = "✅" if log['success'] else "❌"
        timestamp = log['timestamp']
        source = log['source']
        items = log['items']
        error = log.get('error', '')
        
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
            
            with col1:
                st.write(status_icon)
            
            with col2:
                st.write(f"**{source}**")
            
            with col3:
                st.write(f"Items: {items}")
            
            with col4:
                st.caption(timestamp)
            
            if error:
                st.caption(f"⚠️ {error}")
        
        st.divider()


def render_details(dashboard_data):
    """Render detailed debug information."""
    st.subheader("System Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Overall Health Summary**")
        overall = dashboard_data['overall_health']
        st.json(overall)
    
    with col2:
        st.write("**Export Options**")
        
        # Export as JSON
        report_json = health_monitor.export_health_report()
        st.download_button(
            label="📥 Download Health Report (JSON)",
            data=report_json,
            file_name=f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        # Export as CSV
        sources_health = dashboard_data['sources_health']
        if sources_health:
            df_export = pd.DataFrame([
                {
                    'Source': name,
                    'Status': stats['status'],
                    'Type': stats['source_type'],
                    'Success Rate': stats['success_rate'],
                    'Total Attempts': stats['total_attempts'],
                    'Last Fetch': stats['last_fetch']
                }
                for name, stats in sources_health.items()
            ])
            
            csv_data = df_export.to_csv(index=False)
            st.download_button(
                label="📥 Download Sources Status (CSV)",
                data=csv_data,
                file_name=f"sources_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    st.divider()
    
    st.write("**All Sources Data**")
    if dashboard_data['sources_health']:
        st.json(dashboard_data['sources_health'])
    else:
        st.info("No sources data available")


if __name__ == "__main__":
    render_health_dashboard()
