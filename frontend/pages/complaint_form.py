"""
Complaint Form Page - Single form with category dropdown
"""
import streamlit as st
import requests
import base64
from PIL import Image
import io
from datetime import datetime

# Categories with icons
CATEGORIES = {
    "Road damage": "🛣️",
    "Water supply": "💧",
    "Waste management": "🗑️",
    "Street light": "💡",
    "Drainage": "🌊",
    "Other": "📋",
}

# Area importance levels
AREA_IMPORTANCE = {
    "low": "Low Priority Area",
    "normal": "Normal Priority Area", 
    "high": "High Priority Area (School/Hospital/Market)",
    "critical": "Critical Infrastructure"
}

def image_to_base64(image):
    """Convert PIL Image or bytes to base64 string."""
    if isinstance(image, Image.Image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
    elif isinstance(image, bytes):
        img_bytes = image
    else:
        return None
    return base64.b64encode(img_bytes).decode("utf-8")

def render(user):
    """Render the complaint form page."""
    st.title("📝 File a New Complaint")
    
    if not user:
        st.warning("Please login to file complaints")
        return
    
    with st.form("complaint_form", clear_on_submit=True):
        # Category selection dropdown
        category_options = [f"{icon} {name}" for name, icon in CATEGORIES.items()]
        selected_category_display = st.selectbox(
            "Issue Category",
            category_options,
            help="Select the category that best describes your complaint"
        )
        
        # Extract actual category name (remove icon)
        category = selected_category_display.split(" ", 1)[1] if " " in selected_category_display else selected_category_display
        
        col1, col2 = st.columns(2)
        
        with col1:
            severity = st.selectbox(
                "Severity Level",
                ["low", "medium", "high", "critical"],
                format_func=lambda x: x.title(),
                help="How urgent is this issue?"
            )
            
            area_importance = st.selectbox(
                "Area Importance",
                list(AREA_IMPORTANCE.keys()),
                format_func=lambda x: AREA_IMPORTANCE[x],
                help="Is this in a critical area like school/hospital?",
                index=1  # Default to normal
            )
            
            # Location input options
            location_option = st.radio(
                "Location Input Method",
                ["Auto-detect my location", "Enter coordinates manually", "Enter area name"],
                index=2
            )
            
            lat = None
            lon = None
            area_name = ""
            
            if location_option == "Auto-detect my location":
                st.info("📍 Location will be detected automatically when you submit the complaint")
                # We'll handle this in the backend or use browser geolocation
                area_name = st.text_input("Approximate Area Name (optional)", placeholder="e.g. T Nagar, Chennai")
                
            elif location_option == "Enter coordinates manually":
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    lat = st.number_input("Latitude", value=13.0827, format="%.6f", step=0.0001, 
                                        help="Enter latitude coordinate")
                with col_lon:
                    lon = st.number_input("Longitude", value=80.2707, format="%.6f", step=0.0001,
                                        help="Enter longitude coordinate")
                area_name = ""
                
            else:  # Enter area name
                area_name = st.text_input("Area/Location Name", placeholder="e.g. T Nagar, Chennai",
                                        help="Enter the area or landmark name")
                
                # Show geocoded coordinates if area name is provided
                if area_name:
                    try:
                        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                        response = requests.post(f"{api_base}/api/geocode", 
                                               json={"area_name": area_name}, timeout=5)
                        if response.status_code == 200:
                            geo_data = response.json()
                            if geo_data['status'] == 'success':
                                st.success(f"📍 Located: {geo_data['latitude']:.6f}, {geo_data['longitude']:.6f}")
                                lat, lon = geo_data['latitude'], geo_data['longitude']
                            else:
                                st.warning(f"⚠️ Using default location (Chennai): 13.0827, 80.2707")
                                lat, lon = 13.0827, 80.2707
                        else:
                            st.info("ℹ️ Location will be processed after submission")
                            lat, lon = None, None
                    except Exception as e:
                        st.info("ℹ️ Location will be processed after submission")
                        lat, lon = None, None
        
        with col2:
            st.markdown("**📸 Upload Image** (optional but helpful)")
            uploaded_file = st.file_uploader(
                "Choose an image...",
                type=["jpg", "jpeg", "png", "webp"],
                help="Upload a photo of the issue to help authorities understand better"
            )
            
            if uploaded_file is not None:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption="Image Preview", width=200)
                except Exception as e:
                    st.error(f"Error loading image: {e}")
            
            st.markdown("**ℹ️ Additional Info**")
            st.info("Multiple complaints about the same issue help prioritize it!")
        
        description = st.text_area(
            "Detailed Description",
            placeholder="Please describe the issue in detail. Include information like:\n- When did you first notice it?\n- How severe is the problem?\n- Any safety concerns?\n- Impact on daily life?",
            height=150,
            help="The more details you provide, the better authorities can address the issue"
        )
        
        submitted = st.form_submit_button('📤 Submit Complaint', type='primary', width='stretch')
    
    if submitted:
        # Validation
        if not description.strip():
            st.error("Please provide a detailed description of the issue")
        elif location_option == "Enter coordinates manually" and (lat is None or lon is None):
            st.error("Please provide both latitude and longitude coordinates")
        elif location_option == "Enter area name" and not area_name.strip():
            st.error("Please provide an area name")
        elif location_option == "Auto-detect my location" and not area_name.strip():
            st.warning("Area name is recommended for better location accuracy")
        else:
            # Prepare image data
            image_b64 = None
            if uploaded_file is not None:
                try:
                    image = Image.open(uploaded_file)
                    image_b64 = image_to_base64(image)
                    if image_b64:
                        image_b64 = f"data:image/jpeg;base64,{image_b64}"
                except Exception as e:
                    st.warning(f"Could not process image: {e}")
            
            # Prepare payload
            payload = {
                "category": category,
                "severity": severity,
                "description": description.strip(),
                "latitude": lat,
                "longitude": lon,
                "area_name": area_name.strip() if area_name else None,
                "image": image_b64,
                "user_id": user['id'],
                "area_importance": area_importance
            }
            
            # Submit complaint
            with st.spinner("Submitting your complaint..."):
                try:
                    api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
                    response = requests.post(f"{api_base}/api/complaints", json=payload, timeout=10)
                    response.raise_for_status()
                    result = response.json()
                    
                    st.success(f"✅ Complaint #{result['id']} submitted successfully!")
                    st.balloons()
                    
                    # Show submission details
                    st.info(f"""
                    **Submission Details:**
                    - Category: {result['category']}
                    - Severity: {result['severity'].title()}
                    - Area Importance: {AREA_IMPORTANCE[result['area_importance']]}
                    - Status: {result['status'].title()}
                    - Submitted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    """)
                    
                    if result.get('image_path'):
                        st.info(f"📸 Image uploaded successfully")
                        
                except requests.RequestException as e:
                    st.error(f"Failed to submit complaint: {str(e)}")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
    
    # Show tips and guidelines
    with st.expander("💡 Tips for Effective Complaints"):
        st.markdown("""
        **How to make your complaint more effective:**
        
        ✅ **Do:**
        - Provide specific location details
        - Include clear photos
        - Describe the impact on daily life
        - Mention if it's affecting multiple people
        - File multiple complaints for recurring issues
        
        ❌ **Avoid:**
        - Vague descriptions
        - Submitting without location info
        - Using offensive language
        - Duplicate submissions for the same issue
        
        **Remember:** Multiple citizens reporting the same issue helps authorities prioritize it!
        """)