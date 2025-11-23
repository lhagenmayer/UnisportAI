"""
Visualization components for UnisportAI
Includes radar charts for ML feature visualization
"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).resolve().parents[1]
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from data.ml_integration import FEATURE_COLUMNS, load_knn_model


# Feature display names for better readability
FEATURE_DISPLAY_NAMES = {
    'balance': 'Balance',
    'flexibility': 'Flexibility',
    'coordination': 'Coordination',
    'relaxation': 'Relaxation',
    'strength': 'Strength',
    'endurance': 'Endurance',
    'longevity': 'Longevity',
    'intensity': 'Intensity',
    'setting_team': 'Team',
    'setting_fun': 'Fun',
    'setting_duo': 'Duo',
    'setting_solo': 'Solo',
    'setting_competitive': 'Competitive'
}


def get_sport_features(sport_name: str) -> dict:
    """
    Get the 13 ML features for a specific sport
    
    Args:
        sport_name: Name of the sport
        
    Returns:
        Dict with feature names and values, or None if sport not found
    """
    model_data = load_knn_model()
    if model_data is None:
        return None
    
    sports_df = model_data['sports_df']
    
    # Find the sport
    sport_row = sports_df[sports_df['Angebot'] == sport_name]
    
    if sport_row.empty:
        return None
    
    # Extract features
    features = {}
    for col in FEATURE_COLUMNS:
        features[col] = sport_row.iloc[0][col]
    
    return features


def create_radar_chart(sport_features: dict, sport_name: str = "Sport", 
                       comparison_features: dict = None, comparison_name: str = "Comparison"):
    """
    Create an interactive radar chart for sport features
    
    Args:
        sport_features: Dict with 13 feature values for primary sport
        sport_name: Name of the primary sport
        comparison_features: Optional dict with 13 feature values for comparison
        comparison_name: Name of the comparison sport
        
    Returns:
        Plotly figure object
    """
    # Prepare data
    categories = [FEATURE_DISPLAY_NAMES.get(col, col) for col in FEATURE_COLUMNS]
    values = [sport_features.get(col, 0.0) for col in FEATURE_COLUMNS]
    
    # Close the radar chart by repeating the first value
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]
    
    # Create figure
    fig = go.Figure()
    
    # Add primary sport trace
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        name=sport_name,
        line_color='#667eea',
        fillcolor='rgba(102, 126, 234, 0.3)',
        hovertemplate='<b>%{theta}</b><br>Value: %{r:.2f}<extra></extra>'
    ))
    
    # Add comparison sport if provided
    if comparison_features:
        comparison_values = [comparison_features.get(col, 0.0) for col in FEATURE_COLUMNS]
        comparison_values_closed = comparison_values + [comparison_values[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=comparison_values_closed,
            theta=categories_closed,
            fill='toself',
            name=comparison_name,
            line_color='#f093fb',
            fillcolor='rgba(240, 147, 251, 0.3)',
            hovertemplate='<b>%{theta}</b><br>Value: %{r:.2f}<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickmode='linear',
                tick0=0,
                dtick=0.25,
                showticklabels=True,
                ticks='outside'
            ),
            angularaxis=dict(
                direction='clockwise',
                period=13
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=500,
        margin=dict(l=80, r=80, t=40, b=80)
    )
    
    return fig


def render_sport_radar_chart(sport_name: str, allow_comparison: bool = True):
    """
    Render an interactive radar chart widget for a sport
    
    Args:
        sport_name: Name of the sport to visualize
        allow_comparison: Whether to show comparison dropdown
    """
    # Get features for the sport
    features = get_sport_features(sport_name)
    
    if features is None:
        st.warning(f"⚠️ Could not load features for '{sport_name}'")
        return
    
    # Optional: Add comparison sport selector
    comparison_features = None
    comparison_name = None
    
    if allow_comparison:
        model_data = load_knn_model()
        if model_data:
            sports_df = model_data['sports_df']
            all_sports = sorted(sports_df['Angebot'].unique().tolist())
            
            # Remove current sport from comparison options
            comparison_options = ['None'] + [s for s in all_sports if s != sport_name]
            
            selected_comparison = st.selectbox(
                "Compare with:",
                options=comparison_options,
                index=0,
                key=f"radar_compare_{sport_name}"
            )
            
            if selected_comparison != 'None':
                comparison_features = get_sport_features(selected_comparison)
                comparison_name = selected_comparison
    
    # Create and display radar chart
    fig = create_radar_chart(
        sport_features=features,
        sport_name=sport_name,
        comparison_features=comparison_features,
        comparison_name=comparison_name
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show feature breakdown
    with st.expander("📊 Feature Details", expanded=False):
        st.markdown("**ML Feature Values (0 = None, 1 = Maximum)**")
        
        # Create two columns for better layout
        col1, col2 = st.columns(2)
        
        # Group features
        focus_features = ['balance', 'flexibility', 'coordination', 'relaxation', 
                         'strength', 'endurance', 'longevity']
        setting_features = ['setting_team', 'setting_fun', 'setting_duo', 
                           'setting_solo', 'setting_competitive']
        
        with col1:
            st.markdown("**🎯 Focus Areas:**")
            for feat in focus_features:
                value = features.get(feat, 0.0)
                display_name = FEATURE_DISPLAY_NAMES.get(feat, feat)
                bar = '█' * int(value * 10)
                st.text(f"{display_name}: {bar} {value:.2f}")
        
        with col2:
            st.markdown("**💪 Intensity:**")
            intensity_val = features.get('intensity', 0.0)
            intensity_bar = '█' * int(intensity_val * 10)
            st.text(f"Intensity: {intensity_bar} {intensity_val:.2f}")
            
            st.markdown("**🏠 Settings:**")
            for feat in setting_features:
                value = features.get(feat, 0.0)
                display_name = FEATURE_DISPLAY_NAMES.get(feat, feat)
                bar = '█' * int(value * 10)
                st.text(f"{display_name}: {bar} {value:.2f}")


def render_user_preferences_radar(selected_focus: list, selected_intensity: list, 
                                  selected_setting: list, sport_name: str = None):
    """
    Render a radar chart comparing user preferences with a sport
    
    Args:
        selected_focus: List of selected focus filters
        selected_intensity: List of selected intensity filters
        selected_setting: List of selected setting filters
        sport_name: Optional sport to compare with
    """
    from data.ml_integration import build_user_preferences_from_filters
    
    # Build user preferences
    user_prefs = build_user_preferences_from_filters(
        selected_focus, selected_intensity, selected_setting
    )
    
    # Get sport features if provided
    sport_features = None
    sport_display_name = None
    if sport_name:
        sport_features = get_sport_features(sport_name)
        sport_display_name = sport_name
    
    # Create radar chart
    fig = create_radar_chart(
        sport_features=user_prefs,
        sport_name="Your Preferences",
        comparison_features=sport_features,
        comparison_name=sport_display_name
    )
    
    st.plotly_chart(fig, use_container_width=True)
