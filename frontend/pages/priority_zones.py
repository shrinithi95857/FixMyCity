"""
Priority Zones Page - Enhanced priority scoring with area importance
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def get_priority_zones(top_n=10):
    """Fetch priority zones from API."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints/priority-zones", 
                              params={'top': top_n}, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Could not fetch priority zones: {e}")
        return []

def get_complaints_with_location():
    """Fetch all complaints with location data."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints", timeout=10)
        response.raise_for_status()
        complaints = response.json()
        return [c for c in complaints if c.get('latitude') is not None and c.get('longitude') is not None]
    except Exception as e:
        return []

def render():
    """Render the priority zones page."""
    st.title("⚠️ Priority Zones")
    st.markdown("""
    **Priority Scoring** intelligently ranks problem areas based on:
    - Complaint frequency
    - Severity levels
    - Time unresolved
    - Area importance (schools, hospitals, markets)
    """)
    
    # Priority calculation explanation
    with st.expander("📊 How Priority Scoring Works"):
        st.markdown("""
        **Priority Score Formula:**
        
        `Score = (Complaint Count × 2) + (Severity Weight × 3) + (Days Unresolved × 1.5) + (Area Importance × 2)`
        
        **Weights:**
        - **Severity**: Low=1, Medium=2, High=3, Critical=4
        - **Area Importance**: Low=0.5, Normal=1, High=2, Critical=3
        - **Time Factor**: More urgent if unresolved longer
        
        Higher scores = More urgent attention needed!
        """)
    
    # Fetch data
    zones = get_priority_zones(20)  # Get more zones for better analysis
    all_complaints = get_complaints_with_location()
    
    if not zones:
        st.info("No priority zones available yet. Submit more complaints with location data.")
        return
    
    # Convert to DataFrame
    df_zones = pd.DataFrame(zones)
    
    # Display priority zones table
    st.subheader("📋 Top Priority Zones")
    
    # Enhanced table with better formatting
    display_df = df_zones.copy()
    display_df['latitude'] = display_df['latitude'].round(4)
    display_df['longitude'] = display_df['longitude'].round(4)
    display_df['priority_score'] = display_df['priority_score'].round(1)
    
    # Add ranking
    display_df.insert(0, 'Rank', range(1, len(display_df) + 1))
    
    st.dataframe(
        display_df[['Rank', 'latitude', 'longitude', 'complaint_count', 'severity', 'area_importance', 'days_unresolved', 'priority_score']].style
        .format({
            'latitude': '{:.4f}',
            'longitude': '{:.4f}',
            'priority_score': '{:.1f}'
        })
        .background_gradient(subset=['priority_score'], cmap='RdYlGn_r'),
        width='stretch',
        hide_index=True
    )
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Priority score distribution
        st.subheader("📈 Priority Score Distribution")
        fig_hist = px.histogram(df_zones, x='priority_score', nbins=15,
                              title='Distribution of Priority Scores')
        fig_hist.update_layout(xaxis_title='Priority Score', yaxis_title='Number of Zones')
        st.plotly_chart(fig_hist, width='stretch')
    
    with col2:
        # Complaint count vs priority score
        st.subheader("⚖️ Complaint Count vs Priority")
        fig_scatter = px.scatter(df_zones, x='complaint_count', y='priority_score',
                               color='severity', size='priority_score',
                               title='Complaint Count vs Priority Score',
                               hover_data=['area_importance', 'days_unresolved'])
        st.plotly_chart(fig_scatter, width='stretch')
    
    # Map visualization
    st.subheader("🗺️ Priority Zones Map")
    
    if all_complaints:
        # Calculate map center
        df_all = pd.DataFrame(all_complaints)
        center_lat = df_all['latitude'].mean()
        center_lon = df_all['longitude'].mean()
    else:
        center_lat = zones[0]['latitude']
        center_lon = zones[0]['longitude']
    
    # Create map with priority zones
    fig_map = go.Figure()
    
    # Add all complaints as background points
    if all_complaints:
        df_all = pd.DataFrame(all_complaints)
        fig_map.add_trace(go.Scattermapbox(
            lat=df_all['latitude'],
            lon=df_all['longitude'],
            mode='markers',
            marker=dict(size=4, color='lightgray', opacity=0.6),
            name='All Complaints',
            hoverinfo='skip'
        ))
    
    # Add priority zones
    fig_map.add_trace(go.Scattermapbox(
        lat=df_zones['latitude'],
        lon=df_zones['longitude'],
        mode='markers',
        marker=dict(
            size=df_zones['priority_score'] * 2,  # Scale marker size by priority
            color=df_zones['priority_score'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Priority Score")
        ),
        text=df_zones.apply(
            lambda row: f"Rank: {df_zones[df_zones['latitude']==row['latitude']].index[0]+1}<br>"
                       f"Score: {row['priority_score']:.1f}<br>"
                       f"Complaints: {row['complaint_count']}<br>"
                       f"Severity: {row['severity']}<br>"
                       f"Area: {row['area_importance']}<br>"
                       f"Days Unresolved: {row['days_unresolved']}",
            axis=1
        ),
        name='Priority Zones'
    ))
    
    fig_map.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=11
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        height=600,
        title="Priority Zones - Larger Circles = Higher Priority"
    )
    
    st.plotly_chart(fig_map, width='stretch')
    
    # Detailed analysis
    st.subheader("🔍 Detailed Analysis")
    
    # Severity breakdown
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Severity Distribution**")
        severity_counts = df_zones['severity'].value_counts()
        fig_sev = px.pie(values=severity_counts.values, names=severity_counts.index,
                        title='Priority Zones by Severity')
        st.plotly_chart(fig_sev, width='stretch')
    
    with col2:
        st.markdown("**Area Importance Distribution**")
        area_counts = df_zones['area_importance'].value_counts()
        fig_area = px.bar(x=area_counts.index, y=area_counts.values,
                         title='Priority Zones by Area Importance')
        fig_area.update_layout(xaxis_title='Area Importance', yaxis_title='Count')
        st.plotly_chart(fig_area, width='stretch')
    
    # Time analysis
    st.subheader("⏱️ Time-Based Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        avg_days = df_zones['days_unresolved'].mean()
        st.metric("Average Days Unresolved", f"{avg_days:.1f} days")
    
    with col2:
        critical_zones = len(df_zones[df_zones['severity'] == 'critical'])
        st.metric("Critical Severity Zones", critical_zones)
    
    # Action recommendations
    st.subheader("⚡ Action Recommendations")
    
    highest_priority = df_zones.iloc[0]
    st.info(f"""
    **Top Priority Zone:**
    - Location: {highest_priority['latitude']:.4f}, {highest_priority['longitude']:.4f}
    - Score: {highest_priority['priority_score']:.1f}
    - Issues: {highest_priority['complaint_count']} complaints
    - Severity: {highest_priority['severity']}
    - Area: {highest_priority['area_importance']}
    - Unresolved: {highest_priority['days_unresolved']} days
    
    **Recommended Action:** Immediate investigation and resource allocation
    """)
    
    # Export options
    st.subheader("💾 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Priority Zones CSV"):
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="priority_zones.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Export Full Report"):
            # Create summary report
            report = f"""
FixMyCity Priority Zones Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary Statistics:
- Total Priority Zones: {len(df_zones)}
- Average Priority Score: {df_zones['priority_score'].mean():.2f}
- Highest Priority Score: {df_zones['priority_score'].max():.2f}
- Average Days Unresolved: {df_zones['days_unresolved'].mean():.1f}

Top 5 Priority Zones:
{display_df.head().to_string(index=False)}

Area Distribution:
{df_zones['area_importance'].value_counts().to_string()}

Severity Distribution:
{df_zones['severity'].value_counts().to_string()}
            """
            st.download_button(
                label="Download Report",
                data=report,
                file_name="priority_zones_report.txt",
                mime="text/plain"
            )