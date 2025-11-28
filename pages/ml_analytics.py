"""ML Analytics Dashboard

This page provides detailed visualizations and analytics about the ML recommendation system,
including model performance, feature importance, and recommendation patterns.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data.auth import is_logged_in
from data.ml_integration import load_knn_model, get_ml_recommendations, FEATURE_COLUMNS, build_user_preferences_from_filters
from data.shared_sidebar import render_sidebar_user_info

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Render user info in sidebar
render_sidebar_user_info()

st.title("🤖 ML Analytics Dashboard")
st.write("Detailed insights into the AI recommendation system")

# Load model data
model_data = load_knn_model()
if model_data is None:
    st.error("⚠️ ML model not available. Please ensure the model is trained.")
    st.stop()

sports_df = model_data['sports_df']
knn_model = model_data['knn_model']
scaler = model_data['scaler']

# Create tabs for different analytics views
tab1, tab2, tab3, tab4 = st.tabs(["📊 Model Overview", "🎯 Feature Analysis", "📈 Sports Distribution", "🔬 Recommendation Testing"])

with tab1:
    st.subheader("📊 Model Performance Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sports", len(sports_df))
    
    with col2:
        st.metric("Features Used", len(FEATURE_COLUMNS))
    
    with col3:
        st.metric("Model Type", "K-Nearest Neighbors")
    
    with col4:
        n_neighbors = knn_model.n_neighbors if hasattr(knn_model, 'n_neighbors') else 'N/A'
        st.metric("K Value", n_neighbors)
    
    # Feature importance based on variance
    st.subheader("🔍 Feature Importance Analysis")
    
    # Calculate feature statistics from the sports data
    feature_stats = {}
    for i, feature in enumerate(FEATURE_COLUMNS):
        if feature in sports_df.columns:
            if feature == 'intensity':
                # Convert intensity to numeric
                intensity_values = sports_df[feature].map({'low': 0.33, 'moderate': 0.67, 'high': 1.0}).fillna(0.5)
                feature_stats[feature] = {
                    'mean': intensity_values.mean(),
                    'std': intensity_values.std(),
                    'unique_values': len(intensity_values.unique())
                }
            else:
                values = pd.to_numeric(sports_df[feature], errors='coerce').fillna(0)
                feature_stats[feature] = {
                    'mean': values.mean(),
                    'std': values.std(),
                    'unique_values': len(values.unique())
                }
    
    # Create feature importance chart based on standard deviation (variability)
    if feature_stats:
        features = list(feature_stats.keys())
        std_values = [feature_stats[f]['std'] for f in features]
        
        fig_importance = px.bar(
            x=std_values,
            y=[f.replace('setting_', '').capitalize() for f in features],
            orientation='h',
            title="Feature Variability (Higher = More Discriminative)",
            labels={'x': 'Standard Deviation', 'y': 'Features'}
        )
        fig_importance.update_layout(height=500)
        st.plotly_chart(fig_importance, use_container_width=True)

with tab2:
    st.subheader("🎯 Sports Feature Analysis")
    
    # Feature correlation heatmap
    numeric_features = []
    for feature in FEATURE_COLUMNS:
        if feature in sports_df.columns:
            if feature == 'intensity':
                sports_df[f'{feature}_numeric'] = sports_df[feature].map({'low': 0.33, 'moderate': 0.67, 'high': 1.0}).fillna(0.5)
                numeric_features.append(f'{feature}_numeric')
            else:
                sports_df[f'{feature}_numeric'] = pd.to_numeric(sports_df[feature], errors='coerce').fillna(0)
                numeric_features.append(f'{feature}_numeric')
    
    if len(numeric_features) > 1:
        corr_matrix = sports_df[numeric_features].corr()
        
        fig_heatmap = px.imshow(
            corr_matrix,
            x=[f.replace('_numeric', '').replace('setting_', '').capitalize() for f in corr_matrix.columns],
            y=[f.replace('_numeric', '').replace('setting_', '').capitalize() for f in corr_matrix.columns],
            color_continuous_scale='RdBu',
            aspect='auto',
            title="Feature Correlation Matrix"
        )
        fig_heatmap.update_layout(height=600)
        st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # Feature distribution plots
    st.subheader("📈 Feature Distributions")
    
    # Select feature to analyze
    available_features = [f for f in FEATURE_COLUMNS if f in sports_df.columns]
    selected_feature = st.selectbox("Choose feature to analyze:", available_features)
    
    if selected_feature == 'intensity':
        # Special handling for intensity
        intensity_counts = sports_df[selected_feature].value_counts()
        fig_dist = px.pie(
            values=intensity_counts.values,
            names=intensity_counts.index,
            title=f"Distribution of {selected_feature.capitalize()}"
        )
    else:
        # Binary features
        feature_values = pd.to_numeric(sports_df[selected_feature], errors='coerce').fillna(0)
        counts = feature_values.value_counts().sort_index()
        fig_dist = px.bar(
            x=counts.index,
            y=counts.values,
            title=f"Distribution of {selected_feature.replace('setting_', '').capitalize()}",
            labels={'x': 'Value', 'y': 'Count'}
        )
    
    st.plotly_chart(fig_dist, use_container_width=True)

with tab3:
    st.subheader("📈 Sports Catalog Statistics")
    
    # Intensity distribution
    if 'intensity' in sports_df.columns:
        intensity_counts = sports_df['intensity'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_intensity = px.pie(
                values=intensity_counts.values,
                names=[name.capitalize() for name in intensity_counts.index],
                title="Sports by Intensity Level"
            )
            st.plotly_chart(fig_intensity, use_container_width=True)
        
        with col2:
            # Focus areas distribution
            focus_features = ['strength', 'endurance', 'flexibility', 'balance', 'coordination']
            focus_counts = {}
            
            for feature in focus_features:
                if feature in sports_df.columns:
                    count = pd.to_numeric(sports_df[feature], errors='coerce').fillna(0).sum()
                    focus_counts[feature.capitalize()] = count
            
            if focus_counts:
                fig_focus = px.bar(
                    x=list(focus_counts.keys()),
                    y=list(focus_counts.values()),
                    title="Sports by Focus Area"
                )
                fig_focus.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_focus, use_container_width=True)
    
    # Settings distribution
    setting_features = ['setting_team', 'setting_solo', 'setting_competitive', 'setting_fun']
    setting_counts = {}
    
    for feature in setting_features:
        if feature in sports_df.columns:
            count = pd.to_numeric(sports_df[feature], errors='coerce').fillna(0).sum()
            setting_counts[feature.replace('setting_', '').capitalize()] = count
    
    if setting_counts:
        fig_settings = px.bar(
            x=list(setting_counts.keys()),
            y=list(setting_counts.values()),
            title="Sports by Setting Type",
            color=list(setting_counts.values()),
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_settings, use_container_width=True)

with tab4:
    st.subheader("🔬 Interactive Recommendation Testing")
    st.write("Test the recommendation system with different filter combinations")
    
    # Interactive filter selection for testing
    col1, col2 = st.columns(2)
    
    with col1:
        test_focus = st.multiselect(
            "Focus Areas",
            ['balance', 'flexibility', 'coordination', 'relaxation', 'strength', 'endurance', 'longevity'],
            default=['strength', 'endurance'],
            key="test_focus"
        )
        
        test_intensity = st.multiselect(
            "Intensity Level",
            ['low', 'moderate', 'high'],
            default=['moderate'],
            key="test_intensity"
        )
    
    with col2:
        test_setting = st.multiselect(
            "Activity Settings",
            ['team', 'fun', 'duo', 'solo', 'competitive'],
            default=['solo'],
            key="test_setting"
        )
        
        test_min_score = st.slider(
            "Minimum Match Score",
            min_value=50,
            max_value=100,
            value=70,
            step=5,
            key="test_min_score"
        )
    
    if st.button("🚀 Test Recommendations", type="primary"):
        with st.spinner("Running recommendation test..."):
            test_recommendations = get_ml_recommendations(
                selected_focus=test_focus,
                selected_intensity=test_intensity,
                selected_setting=test_setting,
                min_match_score=test_min_score,
                max_results=15
            )
        
        if test_recommendations:
            st.success(f"Found {len(test_recommendations)} recommendations!")
            
            # Visualize test results
            sports_names = [rec['sport'] for rec in test_recommendations]
            match_scores = [rec['match_score'] for rec in test_recommendations]
            
            # Create interactive scatter plot
            fig_test = go.Figure()
            
            fig_test.add_trace(go.Scatter(
                x=range(1, len(match_scores) + 1),
                y=match_scores,
                mode='markers+lines',
                marker=dict(
                    size=12,
                    color=match_scores,
                    colorscale='viridis',
                    showscale=True,
                    colorbar=dict(title="Match Score %")
                ),
                text=sports_names,
                hovertemplate="<b>%{text}</b><br>Match Score: %{y}%<extra></extra>",
                line=dict(width=2)
            ))
            
            fig_test.update_layout(
                title="Test Results: Recommendation Scores",
                xaxis_title="Recommendation Rank",
                yaxis_title="Match Score (%)",
                height=400,
                hovermode='closest'
            )
            
            st.plotly_chart(fig_test, use_container_width=True)
            
            # Show detailed results
            results_df = pd.DataFrame({
                'Rank': range(1, len(test_recommendations) + 1),
                'Sport': sports_names,
                'Match Score (%)': match_scores
            })
            
            st.dataframe(results_df, use_container_width=True, hide_index=True)
        else:
            st.warning("No recommendations found with the selected criteria. Try lowering the minimum score.")

# Footer
st.markdown("---")
st.caption("🤖 ML Analytics Dashboard - UnisportAI Recommendation Engine")