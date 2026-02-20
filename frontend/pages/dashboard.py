"""
Dashboard Page - Overview of all complaints and quick actions
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def get_complaints():
    """Fetch complaints from API."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Could not fetch complaints: {e}")
        return []

def get_analytics():
    """Fetch analytics data."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/analytics", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def render():
    """Render the dashboard page."""
    st.title("🏠 FixMyCity Dashboard")
    
    # Fetch data
    complaints = get_complaints()
    analytics = get_analytics()
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_complaints = len(complaints)
        st.metric("Total Complaints", total_complaints, 
                 delta_color="inverse" if total_complaints > 0 else "off")
    
    with col2:
        unresolved = len([c for c in complaints if c['status'] == 'unresolved'])
        st.metric("Unresolved", unresolved, 
                 delta_color="inverse" if unresolved > 0 else "off")
    
    with col3:
        resolved = len([c for c in complaints if c['status'] == 'resolved'])
        st.metric("Resolved", resolved)
    
    with col4:
        critical = len([c for c in complaints if c['severity'] == 'critical'])
        st.metric("Critical Issues", critical, 
                 delta_color="inverse" if critical > 0 else "off")
    
    # Analytics section
    if analytics:
        st.subheader("📊 Quick Analytics")
        
        # Complaints by category
        if 'by_category' in analytics and analytics['by_category']:
            cat_df = pd.DataFrame(analytics['by_category'])
            fig_cat = px.bar(cat_df, x='category', y='count', 
                           title="Complaints by Category",
                           color='category')
            fig_cat.update_layout(showlegend=False)
            st.plotly_chart(fig_cat, width='stretch')
        
        # Complaints by severity
        if 'by_severity' in analytics and analytics['by_severity']:
            sev_df = pd.DataFrame(analytics['by_severity'])
            fig_sev = px.pie(sev_df, values='count', names='severity',
                           title="Complaints by Severity Level")
            st.plotly_chart(fig_sev, width='stretch')
    
    # Recent complaints
    st.subheader("🕐 Recent Complaints")
    
    if not complaints:
        st.info("No complaints yet. Be the first to report an issue!")
        if st.button("📝 File Your First Complaint"):
            st.session_state.current_page = 'complaint'
            st.rerun()
    else:
        # Show recent complaints (last 10)
        recent_complaints = sorted(complaints, key=lambda x: x['timestamp'], reverse=True)[:10]
        
        for complaint in recent_complaints:
            with st.expander(f"#{complaint['id']} - {complaint['category']} ({complaint['severity']})", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Description:** {complaint['description'][:100]}...")
                    if complaint.get('area_name'):
                        st.write(f"**Location:** {complaint['area_name']}")
                    else:
                        lat = complaint.get('latitude', 0)
                        lon = complaint.get('longitude', 0)
                        st.write(f"**Location:** Coordinates: {lat:.4f}, {lon:.4f}")
                    st.write(f"**Status:** {complaint['status'].title()}")
                    st.write(f"**Submitted:** {complaint['timestamp'][:19].replace('T', ' ')}")
                
                with col2:
                    if complaint.get('image_path'):
                        try:
                            api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                            filename = complaint['image_path'].split("/")[-1]
                            img_url = f"{api_base}/api/uploads/{filename}"
                            st.image(img_url, caption="Issue Photo", width=150)
                        except:
                            st.info("📷 Image")
                    else:
                        st.info("📷 No Image")
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button('📝 File New Complaint', width='stretch'):
            st.session_state.current_page = 'complaint'
            st.rerun()
    
    with col2:
        if st.button('🗺️ View Heatmap', width='stretch'):
            st.session_state.current_page = 'heatmap'
            st.rerun()
    
    with col3:
        if st.button('⚠️ Priority Zones', width='stretch'):
            st.session_state.current_page = 'priority'
            st.rerun()
    
    # User-specific actions
    if st.session_state.user:
        st.subheader(f"👤 Your Activity")
        
        if st.session_state.user['role'] == 'citizen':
            try:
                api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                response = requests.get(f"{api_base}/api/user/{st.session_state.user['id']}/complaints", timeout=10)
                if response.status_code == 200:
                    user_complaints = response.json()
                    st.write(f"You've filed {len(user_complaints)} complaints")
                    if user_complaints:
                        st.dataframe(pd.DataFrame(user_complaints)[['id', 'category', 'severity', 'status', 'timestamp']].head(), 
                                   use_container_width=True)
            except Exception as e:
                st.info("Could not load your complaint history")
        
        elif st.session_state.user['role'] == 'officer':
            try:
                api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                response = requests.get(f"{api_base}/api/officer/{st.session_state.user['id']}/actions", timeout=10)
                if response.status_code == 200:
                    actions = response.json()
                    st.write(f"You've taken {len(actions)} actions on complaints")
                    if actions:
                        action_df = pd.DataFrame(actions)
                        st.dataframe(action_df[['complaint_id', 'action', 'timestamp', 'category']].head(),
                                   use_container_width=True)
            except Exception as e:
                st.info("Could not load your action history")