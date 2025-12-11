"""
================================================================================
MACHINE LEARNING UTILITIES
================================================================================

Purpose: ML model loading and recommendation functions using K-Nearest Neighbors.

Each sport has 13 features (balance, strength, intensity, etc.). User preferences
are converted to a feature vector. KNN finds sports with similar vectors.
================================================================================
"""

import streamlit as st
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime

# Import filter and db functions at module level to avoid repeated imports
try:
    from .filters import filter_events, apply_soft_filters_to_score
    from .db import get_events
except ImportError:
    # Fallback for when running as script or if relative imports fail
    from utils.filters import filter_events, apply_soft_filters_to_score
    from utils.db import get_events

# Feature order (13 features)
ML_FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation',
    'strength', 'endurance', 'longevity',
    'intensity',
    'setting_team', 'setting_fun', 'setting_duo',
    'setting_solo', 'setting_competitive'
]

# Intensity mapping values
INTENSITY_VALUES = {'low': 0.33, 'moderate': 0.67, 'high': 1.0}
DEFAULT_INTENSITY = 0.67  # Used when intensity value is not recognized

# Feature lists
FOCUS_FEATURES = ['balance', 'flexibility', 'coordination', 'relaxation', 
                  'strength', 'endurance', 'longevity']
SETTING_FEATURES = ['team', 'fun', 'duo', 'solo', 'competitive']

ML_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "models" / "knn_recommender.joblib"


@st.cache_resource
def load_knn_model():
    """Load pre-trained KNN model from disk.
    
    Returns:
        dict or None: Dict with 'knn_model', 'scaler', and 'sports_df'.
        Returns None if model file not found.
        
    Note:
        Cached with @st.cache_resource for fast reuse. First load is slow (~2-3s),
        subsequent calls are instant. Train model first with ml/train.py.
    """
    # The model is stored alongside the scaler and source dataframe to
    # reproduce recommendation explanations (important for "why this sport?"
    # questions during evaluations).
    if not ML_MODEL_PATH.exists():
        model_path_str = str(ML_MODEL_PATH)
        st.warning(f"⚠️ KNN model not found at {model_path_str}. Run train.py first.")
        return None
    
    try:
        data = joblib.load(ML_MODEL_PATH)
        knn_model = data['knn_model']
        scaler = data['scaler']
        sports_df = data['sports_df']
        return {
            'knn_model': knn_model,
            'scaler': scaler,
            'sports_df': sports_df
        }
    except Exception as e:
        error_message = str(e)
        st.error(f"Error loading KNN model: {error_message}")
        return None


def build_user_preferences_from_filters(selected_focus, selected_intensity, selected_setting):
    """Convert user filter selections into a 13-dimensional feature vector.
    
    Converts user selections (e.g., "strength training, high intensity, solo") 
    into a numerical vector for the ML model.
    
    Args:
        selected_focus (list): List of focus areas (e.g., ['strength', 'endurance']).
        selected_intensity (list): List of intensity levels (e.g., ['high']).
        selected_setting (list): List of settings (e.g., ['solo', 'team']).
    
    Returns:
        dict: 13 feature values (mostly 0.0/1.0, intensity is 0.0-1.0).
    """
    # Strings are manually mapped to floats instead of relying on pandas
    # so every component of the 13-D vector can be explained during demo sessions.
    preferences = {}
    
    # Normalize inputs to lowercase for matching
    focus_lower = [f.lower() for f in (selected_focus or [])]
    setting_lower = [s.lower() for s in (selected_setting or [])]
    
    # Focus features (7 binary)
    for feature in FOCUS_FEATURES:
        preferences[feature] = 1.0 if feature in focus_lower else 0.0
    
    # Intensity (1 continuous) - average if multiple selected
    if selected_intensity:
        intensity_values = [
            INTENSITY_VALUES.get(i.lower(), DEFAULT_INTENSITY)
            for i in selected_intensity
        ]
        preferences['intensity'] = sum(intensity_values) / len(intensity_values)
    else:
        preferences['intensity'] = 0.0
    
    # Setting features (5 binary)
    for feature in SETTING_FEATURES:
        preferences[f'setting_{feature}'] = 1.0 if feature in setting_lower else 0.0
    
    return preferences


def get_ml_recommendations(selected_focus, selected_intensity, selected_setting, 
                          min_match_score=50, max_results=10, exclude_sports=None):
    """Get sport recommendations using KNN.
    
    Args:
        selected_focus (list): Focus areas selected.
        selected_intensity (list): Intensity levels selected.
        selected_setting (list): Settings selected.
        min_match_score (int, optional): Minimum score (0-100). Defaults to 50.
        max_results (int, optional): Max recommendations. Defaults to 10.
        exclude_sports (list, optional): Sports to exclude. Defaults to None.
    
    Returns:
        list: Dicts with 'sport', 'match_score', and 'item'.
        Empty list if model not found or no matches.
        
    Note:
        Requires pre-trained model. Train first with ml/train.py.
    """
    # Load model
    model_data = load_knn_model()
    if model_data is None:
        return []
    
    knn_model = model_data['knn_model']
    scaler = model_data['scaler']
    sports_df = model_data['sports_df']
    
    # Build user preferences from filters
    user_prefs = build_user_preferences_from_filters(
        selected_focus, selected_intensity, selected_setting
    )
    
    # Build feature vector
    feature_values = [user_prefs.get(col, 0.0) for col in ML_FEATURE_COLUMNS]
    user_vector = np.array(feature_values).reshape(1, -1)
    
    # Scale
    user_vector_scaled = scaler.transform(user_vector)
    
    # Get all sports as neighbors (filtering by threshold happens later)
    n_sports = len(sports_df)
    distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
    
    # Build recommendations
    exclude_sports = set(exclude_sports or [])
    recommendations = []
    
    distances_list = distances[0]
    indices_list = indices[0]
    
    for distance, idx in zip(distances_list, indices_list):
        sport_name = sports_df.iloc[idx]['Angebot']
        
        # Skip if in exclude list
        if sport_name in exclude_sports:
            continue
        
        # Convert distance to similarity score (0-100%)
        match_score = (1 - distance) * 100
        
        # Only include if above threshold
        if match_score >= min_match_score:
            recommendations.append({
                'sport': sport_name,
                'match_score': round(match_score, 1),
                'item': sports_df.iloc[idx].to_dict()
            })
        
        # Stop if enough recommendations found
        if len(recommendations) >= max_results:
            break
    
    return recommendations


# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.