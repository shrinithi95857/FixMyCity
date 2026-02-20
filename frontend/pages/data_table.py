"""
Data Table Page - Comprehensive complaint data view with filtering
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Categories with icons
CATEGORIES = {
    "Road damage": "🛣️",
    "Water supply": "💧",
    "Waste management": "🗑️",
    "Street light": "💡",
    "Drainage": "🌊",
    "Other": "📋",
}

def get_complaints():
    """Fetch all complaints from API."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Could not fetch complaints: {e}")
        return []

def delete_complaint(complaint_id):
    """Delete a user's complaint."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.delete(
            f"{api_base}/api/user/{st.session_state.user['id']}/complaints/{complaint_id}",
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Could not delete complaint: {e}")
        return False

def resolve_complaint(complaint_id, action, notes=""):
    """Resolve/unresolve a complaint (officer only)."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        endpoint = f"/api/complaints/{complaint_id}/{action}"
        response = requests.post(
            f"{api_base}{endpoint}",
            json={
                "officer_id": st.session_state.user['id'],
                "notes": notes
            },
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Could not update complaint: {e}")
        return False

def render():
    """Render the data table page."""
    st.title("📋 Complaint Data Table")
    
    # Fetch data
    complaints = get_complaints()
    
    if not complaints:
        st.info("No complaints available yet.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(complaints)
    
    # Data processing
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['time'] = df['timestamp'].dt.time
    
    # Add category icons
    df['category_icon'] = df['category'].map(CATEGORIES).fillna('📋')
    df['category_display'] = df['category_icon'] + ' ' + df['category']
    
    # Filters sidebar
    st.sidebar.subheader("🔍 Filters")
    
    # Category filter
    categories = ['All'] + sorted(df['category'].unique())
    selected_category = st.sidebar.selectbox("Category", categories)
    
    # Severity filter
    severities = ['All'] + sorted(df['severity'].unique())
    selected_severity = st.sidebar.selectbox("Severity", severities)
    
    # Status filter
    statuses = ['All'] + sorted(df['status'].unique())
    selected_status = st.sidebar.selectbox("Status", statuses)
    
    # Date range filter
    st.sidebar.subheader("📅 Date Range")
    date_options = {
        'All Time': None,
        'Last 7 Days': 7,
        'Last 30 Days': 30,
        'Last 90 Days': 90,
        'Last Year': 365
    }
    selected_date_range = st.sidebar.selectbox("Time Period", list(date_options.keys()))
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['category'] == selected_category]
    
    if selected_severity != 'All':
        filtered_df = filtered_df[filtered_df['severity'] == selected_severity]
    
    if selected_status != 'All':
        filtered_df = filtered_df[filtered_df['status'] == selected_status]
    
    if selected_date_range != 'All Time':
        days = date_options[selected_date_range]
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_df = filtered_df[filtered_df['timestamp'] >= cutoff_date]
    
    # Display filtered data
    st.subheader(f"📋 Complaints ({len(filtered_df)} of {len(df)} total)")
    
    # Action buttons based on user role
    if st.session_state.user:
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info(f"Viewing as {st.session_state.user['role'].title()}")
        
        with col2:
            if st.button("📊 Quick Stats"):
                show_stats(filtered_df)
        
        with col3:
            if st.button("📈 Visual Analysis"):
                show_charts(filtered_df)
    else:
        st.info("Login to access additional features")
    
    # Display data table
    if not filtered_df.empty:
        # Prepare columns for display
        display_columns = [
            'id', 'category_display', 'severity', 'status', 'area_name', 
            'latitude', 'longitude', 'date', 'time', 'description'
        ]
        
        # Truncate long descriptions
        display_df = filtered_df[display_columns].copy()
        display_df['description'] = display_df['description'].apply(
            lambda x: x[:100] + '...' if len(x) > 100 else x
        )
        
        # Display with styling
        # Create a numeric mapping for severity for coloring
        severity_map = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        display_df['severity_numeric'] = display_df['severity'].map(severity_map)
        
        st.dataframe(
            display_df.style.format({
                'latitude': '{:.4f}',
                'longitude': '{:.4f}',
                'description': lambda x: x[:50] + '...' if len(x) > 50 else x
            }).background_gradient(subset=['severity_numeric'], cmap='RdYlGn_r'),
            width='stretch',
            hide_index=True
        )
        
        # Drop the temporary column
        display_df = display_df.drop('severity_numeric', axis=1)
        
        # Detailed view for individual complaints
        st.subheader("🔍 Detailed View")
        
        # Search/complaint selection
        complaint_ids = filtered_df['id'].tolist()
        selected_id = st.selectbox("Select Complaint ID", ['None'] + complaint_ids)
        
        if selected_id != 'None':
            complaint = filtered_df[filtered_df['id'] == selected_id].iloc[0]
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**ID:** {complaint['id']}")
                st.markdown(f"**Category:** {complaint['category_display']}")
                st.markdown(f"**Severity:** {complaint['severity'].title()}")
                st.markdown(f"**Status:** {complaint['status'].title()}")
                st.markdown(f"**Description:** {complaint['description']}")
                
                if complaint.get('area_name'):
                    st.markdown(f"**Location:** {complaint['area_name']}")
                if complaint.get('latitude') and complaint.get('longitude'):
                    st.markdown(f"**Coordinates:** {complaint['latitude']:.4f}, {complaint['longitude']:.4f}")
                
                st.markdown(f"**Submitted:** {complaint['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                if complaint.get('area_importance'):
                    st.markdown(f"**Area Importance:** {complaint['area_importance'].title()}")
            
            with col2:
                # Action buttons based on user role
                if st.session_state.user:
                    if st.session_state.user['role'] == 'citizen':
                        # Check if this is the user's complaint
                        user_complaints = get_user_complaints_safe()
                        if complaint['id'] in [c['id'] for c in user_complaints]:
                            if st.button('🗑️ Delete Complaint', type='secondary', width='stretch'):
                                if delete_complaint(complaint['id']):
                                    st.success("Complaint deleted!")
                                    st.rerun()
                        else:
                            st.info("Not your complaint")
                    
                    elif st.session_state.user['role'] == 'officer':
                        current_status = complaint['status']
                        if current_status == 'unresolved':
                            notes = st.text_area("Resolution Notes", height=100)
                            if st.button('✅ Mark as Resolved', type='primary', width='stretch'):
                                if resolve_complaint(complaint['id'], 'resolve', notes):
                                    st.success("Complaint marked as resolved!")
                                    st.rerun()
                        else:
                            notes = st.text_area("Unresolve Reason", height=100)
                            if st.button('↩️ Mark as Unresolved', type='secondary', width='stretch'):
                                if resolve_complaint(complaint['id'], 'unresolve', notes):
                                    st.success("Complaint marked as unresolved!")
                                    st.rerun()
                
                # Image display
                if complaint.get('image_path'):
                    try:
                        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                        filename = complaint['image_path'].split("/")[-1]
                        img_url = f"{api_base}/api/uploads/{filename}"
                        st.image(img_url, caption='Issue Photo', width='stretch')
                    except:
                        st.info("📷 Image available")
    else:
        st.info("No complaints match the current filters.")

def get_user_complaints_safe():
    """Safely get user complaints."""
    try:
        if not st.session_state.user or st.session_state.user['role'] != 'citizen':
            return []
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/user/{st.session_state.user['id']}/complaints", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def show_stats(df):
    """Display quick statistics."""
    with st.expander("📊 Quick Statistics", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Complaints", len(df))
        
        with col2:
            st.metric("Categories", df['category'].nunique())
        
        with col3:
            st.metric("Unresolved", len(df[df['status'] == 'unresolved']))
        
        with col4:
            st.metric("Critical", len(df[df['severity'] == 'critical']))
        
        # Top categories
        st.subheader("Top Categories")
        category_counts = df['category'].value_counts()
        st.write(category_counts)

def show_charts(df):
    """Display visual charts."""
    with st.expander("📈 Visual Analysis", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Complaints by category
            fig1 = px.pie(df, names='category', title='Complaints by Category')
            st.plotly_chart(fig1, width='stretch')
        
        with col2:
            # Complaints by severity
            fig2 = px.histogram(df, x='severity', title='Complaints by Severity')
            st.plotly_chart(fig2, width='stretch')
        
        # Timeline
        fig3 = px.line(df.groupby('date').size().reset_index(name='count'),
                      x='date', y='count', title='Complaints Over Time')
        st.plotly_chart(fig3, width='stretch')

# Export functionality
def export_data(df, format_type):
    """Export data in specified format."""
    if format_type == 'csv':
        return df.to_csv(index=False)
    elif format_type == 'excel':
        return df.to_excel(index=False)
    elif format_type == 'json':
        return df.to_json(orient='records')