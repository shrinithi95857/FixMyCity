"""
FixMyCity - Main Streamlit Application
Unified interface with user authentication and navigation
"""
import streamlit as st
import requests
import os
from datetime import datetime

# Import page modules
from pages import complaint_form, dashboard, heatmap, priority_zones, data_table, analytics

# Configuration
DEFAULT_API_BASE = "https://fixmycity-x0rl.onrender.com"
CATEGORIES = {
    "Road damage": "🛣️",
    "Water supply": "💧",
    "Waste management": "🗑️",
    "Street light": "💡",
    "Drainage": "🌊",
    "Other": "📋",
}

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

def api_request(method, endpoint, data=None, params=None):
    """Make API requests with error handling."""
    try:
        url = f"{st.session_state.get('api_base', DEFAULT_API_BASE)}{endpoint}"
        if method == 'GET':
            response = requests.get(url, params=params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, timeout=10)
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def login_page():
    """User login interface."""
    st.title("🔐 Login to FixMyCity")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username and password:
                result = api_request('POST', '/api/login', {
                    'username': username,
                    'password': password
                })
                
                if result and 'user' in result:
                    st.session_state.authenticated = True
                    st.session_state.user = result['user']
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Please enter both username and password")

def register_page():
    """User registration interface."""
    st.title("📝 Register for FixMyCity")
    
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username")
            email = st.text_input("Email")
        
        with col2:
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            role = st.selectbox("Role", ["citizen", "officer"])
        
        submitted = st.form_submit_button("Register")
        
        if submitted:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill all fields")
            elif password != confirm_password:
                st.error("Passwords don't match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                result = api_request('POST', '/api/register', {
                    'username': username,
                    'email': email,
                    'password': password,
                    'role': role
                })
                
                if result:
                    st.success("Registration successful! Please login.")
                    st.session_state.current_page = 'login'
                    st.rerun()
                else:
                    st.error("Registration failed")

def main_app():
    """Main application interface after authentication."""
    # Sidebar navigation
    with st.sidebar:
        st.title("🏙️ FixMyCity")
        
        if st.session_state.user:
            st.subheader(f"Welcome, {st.session_state.user['username']}!")
            st.caption(f"Role: {st.session_state.user['role'].title()}")
        
        # Navigation
        page = st.selectbox(
            "Navigate to",
            [
                "🏠 Dashboard",
                "📝 File Complaint", 
                "🗺️ Heatmap",
                "⚠️ Priority Zones",
                "📋 Data Table",
                "📊 Analytics"
            ],
            index=[
                "🏠 Dashboard",
                "📝 File Complaint", 
                "🗺️ Heatmap",
                "⚠️ Priority Zones",
                "📋 Data Table",
                "📊 Analytics"
            ].index({
                'dashboard': "🏠 Dashboard",
                'complaint': "📝 File Complaint",
                'heatmap': "🗺️ Heatmap",
                'priority': "⚠️ Priority Zones",
                'datatable': "📋 Data Table",
                'analytics': "📊 Analytics"
            }.get(st.session_state.current_page, "🏠 Dashboard"))
        )
        
        # API settings
        st.divider()
        st.subheader("🔧 Settings")
        api_url = st.text_input("Backend API URL", 
                              value=st.session_state.get('api_base', DEFAULT_API_BASE))
        if api_url != st.session_state.get('api_base', DEFAULT_API_BASE):
            st.session_state.api_base = api_url.rstrip("/")
        
        # Logout
        if st.button("🚪 Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.current_page = 'dashboard'
            st.rerun()
    
    # Update current page based on selection
    page_mapping = {
        "🏠 Dashboard": "dashboard",
        "📝 File Complaint": "complaint",
        "🗺️ Heatmap": "heatmap",
        "⚠️ Priority Zones": "priority",
        "📋 Data Table": "datatable",
        "📊 Analytics": "analytics"
    }
    st.session_state.current_page = page_mapping.get(page, "dashboard")
    
    # Render selected page
    if st.session_state.current_page == 'dashboard':
        dashboard.render()
    elif st.session_state.current_page == 'complaint':
        complaint_form.render(st.session_state.user)
    elif st.session_state.current_page == 'heatmap':
        heatmap.render()
    elif st.session_state.current_page == 'priority':
        priority_zones.render()
    elif st.session_state.current_page == 'datatable':
        data_table.render()
    elif st.session_state.current_page == 'analytics':
        analytics.render()

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="FixMyCity - Smart City Management",
        page_icon="🏙️",
        layout="wide"
    )
    
    # Check authentication status
    if not st.session_state.authenticated:
        # Show login/registration tabs
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            login_page()
            
        with tab2:
            register_page()
    else:
        # Show main application
        main_app()

if __name__ == "__main__":
    main()
