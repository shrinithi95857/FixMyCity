"""
Heatmap Page - Advanced heatmap intelligence with clustering
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import DBSCAN
import numpy as np
from datetime import datetime

def get_complaints_with_location():
    """Fetch complaints that have location data."""
    try:
        api_base = st.session_state.get('api_base', 'http://127.0.0.1:5000')
        response = requests.get(f"{api_base}/api/complaints", timeout=10)
        response.raise_for_status()
        complaints = response.json()
        return [c for c in complaints if c.get('latitude') is not None and c.get('longitude') is not None]
    except Exception as e:
        st.error(f"Could not fetch complaints: {e}")
        return []

def cluster_complaints(df, eps=0.01, min_samples=2):
    """Cluster complaints using DBSCAN algorithm."""
    try:
        if len(df) < 2:
            # Return dataframe with all points labeled as noise
            df_result = df.copy()
            df_result['cluster'] = -1
            # Create empty stats for consistency
            empty_stats = pd.DataFrame(columns=['latitude', 'longitude', 'complaint_count', 'dominant_severity'])
            empty_stats.index.name = 'cluster'
            return df_result, empty_stats
        
        # Use DBSCAN for clustering
        coords = df[['latitude', 'longitude']].values
        clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='haversine').fit(
            np.radians(coords)
        )
        
        df_clustered = df.copy()
        df_clustered['cluster'] = clustering.labels_
        
        # Calculate cluster statistics
        def get_dominant_severity(severity_series):
            if len(severity_series) == 0:
                return 'low'
            severity_counts = severity_series.value_counts()
            if len(severity_counts) == 0:
                return 'low'
            return severity_counts.index[0]
        
        cluster_stats = df_clustered.groupby('cluster').agg({
            'latitude': 'mean',
            'longitude': 'mean',
            'id': 'count'
        }).rename(columns={'id': 'complaint_count'})
        
        # Add dominant severity separately to avoid lambda issues
        severity_by_cluster = df_clustered.groupby('cluster')['severity'].apply(get_dominant_severity)
        cluster_stats['dominant_severity'] = severity_by_cluster
        
        return df_clustered, cluster_stats
    
    except Exception as e:
        # Handle any clustering errors gracefully
        st.warning(f"Clustering failed: {str(e)}. Showing all points as individual complaints.")
        df_result = df.copy()
        df_result['cluster'] = -1
        empty_stats = pd.DataFrame(columns=['latitude', 'longitude', 'complaint_count', 'dominant_severity'])
        empty_stats.index.name = 'cluster'
        return df_result, empty_stats

def render():
    """Render the heatmap page."""
    st.title("🗺️ Heatmap Intelligence")
    st.markdown("""
    **Heatmap Intelligence** shows problem density at a glance. 
    Intense colored areas indicate high concentration of complaints - these are priority zones for authorities.
    """)
    
    # Fetch data
    complaints = get_complaints_with_location()
    
    if not complaints:
        st.info("No complaints with location data available. Submit complaints with coordinates to see the heatmap.")
        st.info("\ud83d\udca1 Tip: Enter area names like 'T Nagar', 'Anna Nagar', or 'Mylapore' and the system will automatically locate them!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(complaints)
    
    # Show location statistics
    st.subheader("Location Intelligence")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_locations = df[['latitude', 'longitude']].drop_duplicates().shape[0]
        st.metric("Unique Locations", total_locations)
    
    with col2:
        avg_complaints_per_location = len(df) / total_locations
        st.metric("Avg Complaints/Location", f"{avg_complaints_per_location:.1f}")
    
    with col3:
        location_coverage = len(df.dropna(subset=['area_name'])) / len(df) * 100
        st.metric("Area Names Provided", f"{location_coverage:.0f}%")
    
    # Clustering parameters
    st.sidebar.subheader("⚙️ Clustering Settings")
    clustering_enabled = st.sidebar.checkbox("Enable Clustering", value=True)
    eps = st.sidebar.slider("Clustering Distance (km)", 0.1, 2.0, 0.5, 0.1)
    min_samples = st.sidebar.slider("Minimum Complaints per Cluster", 1, 10, 2)
    
    # Severity mapping for colors
    severity_colors = {'low': 'blue', 'medium': 'yellow', 'high': 'orange', 'critical': 'red'}
    
    # Calculate map center
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["🔥 Density Heatmap", "📍 Clustered Points", "📈 Cluster Analysis"])
    
    with tab1:
        st.subheader("Density Heatmap - Problem Hotspots")
        
        # Enhanced heatmap with better visualization
        fig_heat = go.Figure(go.Densitymapbox(
            lat=df['latitude'],
            lon=df['longitude'],
            z=[1] * len(df),  # Uniform weight for basic density
            radius=20,
            colorscale=[
                [0, 'lightcyan'],    # Very low density
                [0.25, 'deepskyblue'],   # Low density
                [0.5, 'dodgerblue'], # Medium density
                [0.75, 'royalblue'],      # High density
                [1, 'navy']      # Very high density
            ],
            showscale=True,
            colorbar=dict(
                title="Complaint Density"
            )
        ))
        
        fig_heat.update_layout(
            mapbox=dict(
                style="open-street-map",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=11
            ),
            margin=dict(l=0, r=0, t=30, b=0),
            height=600,
            title="Complaint Density Heatmap - Intense Colors = High Problem Areas"
        )
        
        st.plotly_chart(fig_heat, width='stretch')
        
        # Density statistics
        st.subheader("📊 Density Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_points = len(df)
            st.metric("Total Complaints", total_points)
        
        with col2:
            unique_locations = df[['latitude', 'longitude']].drop_duplicates().shape[0]
            st.metric("Unique Locations", unique_locations)
        
        with col3:
            avg_density = total_points / max(unique_locations, 1)
            st.metric("Avg Complaints per Location", f"{avg_density:.1f}")
    
    with tab2:
        st.subheader("Clustered Complaint Points")
        
        if clustering_enabled and len(df) >= min_samples:
            # Apply clustering
            eps_radians = eps / 6371.0  # Convert km to radians
            df_clustered, cluster_stats = cluster_complaints(df, eps=eps_radians, min_samples=min_samples)
            
            # Create scatter plot with clusters
            # Use complaint count or severity for sizing instead of cluster ID
            df_clustered['complaint_size'] = df_clustered.groupby('cluster')['id'].transform('count')
            
            fig_cluster = px.scatter_mapbox(
                df_clustered,
                lat='latitude',
                lon='longitude',
                color='cluster',
                size='complaint_size',
                size_max=15,
                hover_data=['category', 'severity', 'description', 'timestamp', 'cluster'],
                zoom=11,
                center={'lat': center_lat, 'lon': center_lon},
                mapbox_style='open-street-map',
                title='Complaint Clusters - Same colors = Related Issues'
            )
            
            # Add cluster centers with enhanced information
            cluster_centers = cluster_stats[cluster_stats.index != -1]  # Exclude noise points
            if not cluster_centers.empty:
                # Add cluster center markers
                fig_cluster.add_trace(
                    go.Scattermapbox(
                        lat=cluster_centers['latitude'],
                        lon=cluster_centers['longitude'],
                        mode='markers',
                        marker=dict(
                            size=cluster_centers['complaint_count'] * 4,  # Larger markers
                            color='cyan',
                            symbol='circle'
                        ),
                        text=cluster_centers.apply(
                            lambda row: f"Hotspot #{row.name}<br>Complaints: {row['complaint_count']}<br>Severity: {row['dominant_severity'].title()}<br>Location: {row['latitude']:.4f}, {row['longitude']:.4f}",
                            axis=1
                        ),
                        name='Problem Hotspots'
                    )
                )
                
                # Add connection lines from complaints to cluster centers
                line_traces = []
                for cluster_id, center_data in cluster_centers.iterrows():
                    complaints_in_cluster = df_clustered[df_clustered['cluster'] == cluster_id]
                    if len(complaints_in_cluster) > 0:
                        # Create individual line segments for better visualization
                        for _, complaint in complaints_in_cluster.iterrows():
                            line_trace = go.Scattermapbox(
                                lat=[center_data['latitude'], complaint['latitude']],
                                lon=[center_data['longitude'], complaint['longitude']],
                                mode='lines',
                                line=dict(width=1, color='rgba(0,255,255,0.4)'),
                                showlegend=False,
                                hoverinfo='skip',
                                name=f'Cluster_{cluster_id}_connections'
                            )
                            line_traces.append(line_trace)
                
                # Add all line traces at once
                for trace in line_traces:
                    fig_cluster.add_trace(trace)
            
            fig_cluster.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                height=600
            )
            
            st.plotly_chart(fig_cluster, width='stretch')
            
            # Enhanced cluster information
            st.subheader("Cluster Analysis")
            
            # Show cluster summary
            total_clusters = len(cluster_stats[cluster_stats.index != -1])
            total_clustered_complaints = cluster_stats[cluster_stats.index != -1]['complaint_count'].sum()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Problem Clusters", total_clusters)
            with col2:
                st.metric("Clustered Issues", total_clustered_complaints)
            with col3:
                avg_per_cluster = total_clustered_complaints / total_clusters if total_clusters > 0 else 0
                st.metric("Avg Issues/Cluster", f"{avg_per_cluster:.1f}")
            
            # Show detailed cluster information
            if not cluster_stats.empty:
                valid_clusters = cluster_stats[cluster_stats.index != -1].copy()
                if not valid_clusters.empty:
                    # Add priority levels
                    def get_priority_level(count):
                        if count >= 5:
                            return "Critical"
                        elif count >= 3:
                            return "High"
                        else:
                            return "Medium"
                    
                    valid_clusters['priority_level'] = valid_clusters['complaint_count'].apply(get_priority_level)
                    valid_clusters['coordinates'] = valid_clusters.apply(
                        lambda row: f"{row['latitude']:.4f}, {row['longitude']:.4f}", axis=1
                    )
                    
                    st.dataframe(
                        valid_clusters[['priority_level', 'complaint_count', 'dominant_severity', 'coordinates']].style
                        .format({'complaint_count': '{}'}),
                        width='stretch',
                        hide_index=True
                    )
                else:
                    st.info("No valid clusters found with current settings.")
            
            # Add recommendations based on clustering
            st.subheader("Recommendations")
            high_priority_clusters = len(cluster_stats[(cluster_stats.index != -1) & (cluster_stats['complaint_count'] >= 3)])
            if high_priority_clusters > 0:
                st.warning(f"{high_priority_clusters} areas require immediate attention (3+ complaints in same location)")
            
            critical_severity_clusters = len(cluster_stats[(cluster_stats.index != -1) & (cluster_stats['dominant_severity'] == 'critical')])
            if critical_severity_clusters > 0:
                st.error(f"{critical_severity_clusters} clusters have critical severity issues")
            
            if high_priority_clusters == 0 and critical_severity_clusters == 0:
                st.success("All issues are well-distributed. No major hotspots detected!")
            
        else:
            # Simple scatter plot without clustering
            fig_simple = px.scatter_mapbox(
                df,
                lat='latitude',
                lon='longitude',
                color='severity',
                color_discrete_map=severity_colors,
                size_max=10,
                hover_data=['category', 'description', 'timestamp'],
                zoom=11,
                center={'lat': center_lat, 'lon': center_lon},
                mapbox_style='open-street-map',
                title='Complaint Locations by Severity'
            )
            
            fig_simple.update_layout(
                margin=dict(l=0, r=0, t=30, b=0),
                height=600
            )
            
            st.plotly_chart(fig_simple, width='stretch')
    
    with tab3:
        st.subheader("Advanced Cluster Analysis")
        
        if clustering_enabled and len(df) >= min_samples:
            eps_radians = eps / 6371.0  # Convert km to radians
            df_clustered, cluster_stats = cluster_complaints(df, eps=eps_radians, min_samples=min_samples)
            
            # Cluster statistics
            total_clusters = len(cluster_stats[cluster_stats.index != -1])
            noise_points = len(df_clustered[df_clustered['cluster'] == -1])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Clusters", total_clusters)
            with col2:
                st.metric("Clustered Complaints", len(df_clustered[df_clustered['cluster'] != -1]))
            with col3:
                st.metric("Isolated Complaints", noise_points)
            
            # Cluster size distribution
            valid_clusters = cluster_stats[cluster_stats.index != -1]
            if len(valid_clusters) > 0:
                cluster_sizes = valid_clusters['complaint_count']
                fig_dist = px.histogram(
                    x=cluster_sizes,
                    nbins=min(20, len(valid_clusters)),
                    title="Cluster Size Distribution"
                )
                fig_dist.update_layout(xaxis_title="Complaints per Cluster", yaxis_title="Number of Clusters")
                st.plotly_chart(fig_dist, width='stretch')
                
                # Dominant categories in clusters
                st.subheader("Dominant Categories by Cluster")
                def get_dominant_category(category_series):
                    if len(category_series) == 0:
                        return 'None'
                    category_counts = category_series.value_counts()
                    if len(category_counts) == 0:
                        return 'None'
                    return category_counts.index[0]
                
                cluster_categories = df_clustered.groupby('cluster')['category'].apply(get_dominant_category)
                # Filter out noise points (-1) and display only valid clusters
                valid_category_clusters = cluster_categories[cluster_categories.index != -1]
                if len(valid_category_clusters) > 0:
                    st.dataframe(valid_category_clusters.to_frame('Dominant Category'), width='stretch')
                else:
                    st.info("No dominant categories found in valid clusters.")
            else:
                st.info("No valid clusters to analyze with current settings.")
        else:
            st.info("Enable clustering and ensure sufficient data points for analysis.")
    
    # Information section
    with st.expander("ℹ️ How Heatmap Intelligence Works"):
        st.markdown("""
        **Heatmap Intelligence** uses advanced algorithms to:
        
        🔹 **Density Visualization**: Shows where complaints concentrate (blue = problems, light blue = fewer issues)
        
        🧩 **Clustering**: Groups nearby complaints to identify recurring problems in specific areas
        
        ⚡ **Hotspot Detection**: Automatically identifies areas needing urgent attention
        
        📊 **Pattern Recognition**: Reveals systematic issues rather than random complaints
        
        This helps authorities:
        - Focus resources on high-impact areas
        - Identify systemic problems
        - Allocate budgets more effectively
        - Track improvement over time
        """)