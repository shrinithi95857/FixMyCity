"""
Analytics Dashboard Page - Comprehensive analytics and insights
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

def get_analytics():
    """Fetch analytics data from API."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/analytics", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Could not fetch analytics: {e}")
        return None

def get_complaints():
    """Fetch all complaints."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []

def render():
    """Render the analytics dashboard page."""
    st.title("📊 Analytics Dashboard")
    st.markdown("""
    **Data-Driven Insights** for smarter city management
    Transform complaints into actionable intelligence
    """)
    
    # Fetch data
    analytics = get_analytics()
    complaints = get_complaints()
    
    if not analytics or not complaints:
        st.info("No data available for analytics yet.")
        return
    
    # Convert complaints to DataFrame for analysis
    df = pd.DataFrame(complaints)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    
    # Time range selector
    st.sidebar.subheader("📅 Time Range")
    time_ranges = {
        'Last 7 Days': 7,
        'Last 30 Days': 30,
        'Last 90 Days': 90,
        'Last Year': 365,
        'All Time': None
    }
    selected_range = st.sidebar.selectbox("Analysis Period", list(time_ranges.keys()))
    
    # Filter data by time range
    if time_ranges[selected_range] is not None:
        cutoff_date = datetime.now() - timedelta(days=time_ranges[selected_range])
        # Handle timezone issues by converting both to naive datetime
        df['timestamp_naive'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
        cutoff_date_naive = cutoff_date.replace(tzinfo=None)
        df_filtered = df[df['timestamp_naive'] >= cutoff_date_naive]
        # Remove the temporary column
        df_filtered = df_filtered.drop('timestamp_naive', axis=1)
    else:
        df_filtered = df.copy()
    
    # Key Metrics
    st.subheader("📈 Key Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_complaints = len(df_filtered)
        st.metric("Total Complaints", total_complaints)
    
    with col2:
        resolved_count = len(df_filtered[df_filtered['status'] == 'resolved'])
        resolution_rate = (resolved_count / total_complaints * 100) if total_complaints > 0 else 0
        st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
    
    with col3:
        avg_resolution_time = calculate_avg_resolution_time(df_filtered)
        st.metric("Avg Resolution Time", f"{avg_resolution_time:.1f} days")
    
    with col4:
        critical_count = len(df_filtered[df_filtered['severity'] == 'critical'])
        st.metric("Critical Issues", critical_count, 
                 delta_color="inverse" if critical_count > 0 else "off")
    
    # Main dashboard tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "📈 Trends", 
        "🎯 Performance", 
        "🗺️ Geographic"
    ])
    
    with tab1:
        overview_tab(df_filtered, analytics)
    
    with tab2:
        trends_tab(df_filtered)
    
    with tab3:
        performance_tab(df_filtered)
    
    with tab4:
        geographic_tab(df_filtered)
    
    # Export options
    st.subheader("💾 Export Analytics")
    export_analytics(df_filtered, analytics)

def overview_tab(df, analytics):
    """Overview analytics tab."""
    st.subheader("Comprehensive Overview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Complaints by category
        if 'by_category' in analytics and analytics['by_category']:
            cat_df = pd.DataFrame(analytics['by_category'])
            fig_cat = px.bar(cat_df, x='category', y='count', 
                           title="Complaints by Category",
                           color='category')
        st.plotly_chart(fig_cat, width='stretch', key='analytics_cat')
        
        # Complaints by severity
        if 'by_severity' in analytics and analytics['by_severity']:
            sev_df = pd.DataFrame(analytics['by_severity'])
            fig_sev = px.pie(sev_df, values='count', names='severity',
                           title="Severity Distribution")
        st.plotly_chart(fig_sev, width='stretch', key='analytics_sev')
    
    with col2:
        # Complaints by status
        if 'by_status' in analytics and analytics['by_status']:
            status_df = pd.DataFrame(analytics['by_status'])
            fig_status = px.bar(status_df, x='status', y='count',
                              title="Status Distribution",
                              color='status')
        st.plotly_chart(fig_status, width='stretch', key='analytics_status')
        
        # Recent trends
        if 'recent_trends' in analytics and analytics['recent_trends']:
            trends_df = pd.DataFrame(analytics['recent_trends'])
            if not trends_df.empty:
                trends_df['date'] = pd.to_datetime(trends_df['date'])
                fig_trends = px.line(trends_df, x='date', y='count',
                                   title="Daily Complaint Volume")
                st.plotly_chart(fig_trends, width='stretch', key='analytics_trends')

def trends_tab(df):
    """Trends analysis tab."""
    st.subheader("Trend Analysis")
    
    # Time-based analysis
    daily_counts = df.groupby('date').size().reset_index(name='count')
    daily_counts['date'] = pd.to_datetime(daily_counts['date'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Daily trend
        fig_daily = px.line(daily_counts, x='date', y='count',
                          title="Daily Complaint Volume")
        st.plotly_chart(fig_daily, width='stretch', key='analytics_daily')
    
    with col2:
        # Moving average
        daily_counts['7_day_avg'] = daily_counts['count'].rolling(window=7).mean()
        fig_ma = px.line(daily_counts, x='date', 
                        y=['count', '7_day_avg'],
                        title="Complaints with 7-Day Moving Average")
        st.plotly_chart(fig_ma, width='stretch', key='analytics_ma')
    
    # Category trends over time
    st.subheader("Category Trends")
    category_trends = df.groupby([df['date'], 'category']).size().reset_index(name='count')
    category_trends['date'] = pd.to_datetime(category_trends['date'])
    
    fig_category_trends = px.line(category_trends, x='date', y='count', color='category',
                                title="Complaint Categories Over Time")
    st.plotly_chart(fig_category_trends, width='stretch', key='analytics_category')
    
    # Correlation analysis
    st.subheader("Pattern Analysis")
    if len(df) > 10:
        correlation_data = df.groupby(['category', 'severity']).size().unstack(fill_value=0)
        fig_corr = px.imshow(correlation_data, 
                           title="Category vs Severity Heatmap",
                           labels=dict(x="Severity", y="Category", color="Count"))
        st.plotly_chart(fig_corr, width='stretch', key='analytics_corr')

def performance_tab(df):
    """Performance metrics tab."""
    st.subheader("Performance Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Resolution time analysis
        resolved_complaints = df[df['status'] == 'resolved']
        if not resolved_complaints.empty:
            resolution_times = []
            for _, complaint in resolved_complaints.iterrows():
                submit_time = pd.to_datetime(complaint['timestamp'])
                # For demo purposes, we'll calculate artificial resolution times
                # In real implementation, you'd have actual resolution timestamps
                # Handle timezone issues
                if submit_time.tz is not None:
                    submit_time = submit_time.tz_localize(None)
                resolution_time = (datetime.now().replace(tzinfo=None) - submit_time).days
                resolution_times.append(min(resolution_time, 365))  # Cap at 1 year
            
            fig_res_time = px.histogram(x=resolution_times, nbins=30,
                                      title="Resolution Time Distribution",
                                      labels={'x': 'Days', 'y': 'Number of Complaints'})
            st.plotly_chart(fig_res_time, width='stretch', key='analytics_res_time')
    
    with col2:
        # Efficiency metrics by category
        category_efficiency = df.groupby('category').agg({
            'id': 'count',
            'status': lambda x: sum(x == 'resolved')
        }).rename(columns={'id': 'total', 'status': 'resolved'})
        category_efficiency['resolution_rate'] = (
            category_efficiency['resolved'] / category_efficiency['total'] * 100
        )
        
        fig_efficiency = px.bar(category_efficiency, 
                              y='resolution_rate',
                              title="Resolution Rate by Category")
        fig_efficiency.update_layout(yaxis_title="Resolution Rate (%)")
        st.plotly_chart(fig_efficiency, width='stretch', key='analytics_efficiency')
    
    # Performance benchmarks
    st.subheader("Performance Benchmarks")
    
    benchmarks = {
        'Excellent': {'time': 3, 'rate': 90},
        'Good': {'time': 7, 'rate': 75},
        'Average': {'time': 14, 'rate': 60},
        'Needs Improvement': {'time': 30, 'rate': 40}
    }
    
    avg_time = calculate_avg_resolution_time(df)
    resolution_rate = (len(df[df['status'] == 'resolved']) / len(df) * 100) if len(df) > 0 else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Your Average Resolution Time", f"{avg_time:.1f} days")
        for level, criteria in benchmarks.items():
            if avg_time <= criteria['time']:
                st.success(f"Performance: {level} (≤{criteria['time']} days)")
                break
    
    with col2:
        st.metric("Your Resolution Rate", f"{resolution_rate:.1f}%")
        for level, criteria in benchmarks.items():
            if resolution_rate >= criteria['rate']:
                st.success(f"Rate: {level} (≥{criteria['rate']}%)")
                break

def geographic_tab(df):
    """Geographic analytics tab."""
    st.subheader("Geographic Analysis")
    
    # Filter complaints with location data
    geo_complaints = df.dropna(subset=['latitude', 'longitude'])
    
    if not geo_complaints.empty:
        # Density analysis
        col1, col2 = st.columns(2)
        
        with col1:
            density_data = geo_complaints.groupby(['latitude', 'longitude']).size().reset_index(name='count')
            fig_density = px.scatter(density_data, x='longitude', y='latitude', 
                                   size='count', color='count',
                                   title="Complaint Density by Location",
                                   size_max=30)
            st.plotly_chart(fig_density, width='stretch', key='analytics_density')
        
        with col2:
            # Regional distribution
            region_counts = geo_complaints['area_name'].value_counts().head(10)
            if not region_counts.empty:
                fig_regions = px.bar(x=region_counts.index, y=region_counts.values,
                                   title="Top 10 Problem Areas")
                fig_regions.update_layout(xaxis_title="Area", yaxis_title="Complaint Count")
            st.plotly_chart(fig_regions, width='stretch', key='analytics_regions')
    else:
        st.info("No geographic data available for analysis.")

def calculate_avg_resolution_time(df):
    """Calculate average resolution time (simplified for demo)."""
    resolved_complaints = df[df['status'] == 'resolved']
    if not resolved_complaints.empty:
        times = []
        for _, complaint in resolved_complaints.iterrows():
            submit_time = pd.to_datetime(complaint['timestamp'])
            # Handle timezone issues
            if submit_time.tz is not None:
                submit_time = submit_time.tz_localize(None)
            resolution_time = (datetime.now().replace(tzinfo=None) - submit_time).days
            times.append(min(resolution_time, 365))  # Cap at 1 year
        return np.mean(times) if times else 0
    return 0

def export_analytics(df, analytics):
    """Export analytics data."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Summary Report"):
            report = create_summary_report(df, analytics)
            st.download_button(
                label="Download Summary",
                data=report,
                file_name="analytics_summary.txt",
                mime="text/plain"
            )
    
    with col2:
        if st.button("💾 Export Data CSV"):
            csv_data = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="analytics_data.csv",
                mime="text/csv"
            )
    
    with col3:
        if st.button("📈 Export Charts"):
            # This would generate chart images in a real implementation
            st.info("Chart export functionality would be implemented here")

def create_summary_report(df, analytics):
    """Create comprehensive summary report."""
    total_complaints = len(df)
    resolved = len(df[df['status'] == 'resolved'])
    resolution_rate = (resolved / total_complaints * 100) if total_complaints > 0 else 0
    avg_time = calculate_avg_resolution_time(df)
    
    report = f"""
FixMyCity Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Executive Summary:
- Total Complaints: {total_complaints}
- Resolution Rate: {resolution_rate:.1f}%
- Average Resolution Time: {avg_time:.1f} days
- Critical Issues: {len(df[df['severity'] == 'critical'])}

Complaints by Category:
{pd.DataFrame(analytics['by_category']).to_string(index=False) if 'by_category' in analytics else 'No data'}

Complaints by Severity:
{pd.DataFrame(analytics['by_severity']).to_string(index=False) if 'by_severity' in analytics else 'No data'}

Complaints by Status:
{pd.DataFrame(analytics['by_status']).to_string(index=False) if 'by_status' in analytics else 'No data'}

Key Insights:
1. {get_top_category(df)} is the most reported issue category
2. {get_most_severe_area(df)} has the highest concentration of severe issues
3. Average response time indicates {'excellent' if avg_time < 7 else 'good' if avg_time < 14 else 'average' if avg_time < 30 else 'needs improvement'} performance

Recommendations:
- Focus resources on {get_top_category(df)} issues
- Monitor {get_most_problematic_area(df)} area for systemic improvements
- Review processes for issues taking longer than average resolution time
    """
    return report

def get_top_category(df):
    """Get the most reported category."""
    return df['category'].value_counts().index[0] if not df.empty else "None"

def get_most_severe_area(df):
    """Get area with most severe issues."""
    severe_complaints = df[df['severity'].isin(['high', 'critical'])]
    if not severe_complaints.empty and 'area_name' in severe_complaints.columns:
        area_counts = severe_complaints['area_name'].value_counts()
        return area_counts.index[0] if not area_counts.empty else "Unknown"
    return "Unknown"

def get_most_problematic_area(df):
    """Get area with most complaints."""
    if 'area_name' in df.columns and not df['area_name'].isna().all():
        area_counts = df['area_name'].value_counts()
        return area_counts.index[0] if not area_counts.empty else "Unknown"
    return "Unknown"