"""
ML-based sport recommendations using KNN
"""
import os
from pathlib import Path
import joblib
import numpy as np
import streamlit as st
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# Feature order (13 features)
FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation',
    'strength', 'endurance', 'longevity',
    'intensity',
    'setting_team', 'setting_fun', 'setting_duo',
    'setting_solo', 'setting_competitive'
]

MODEL_PATH = Path(__file__).resolve().parents[1] / "machine" / "knn_recommender.joblib"


@st.cache_resource
def load_knn_model():
    """Load the trained KNN model (cached for performance)"""
    if not MODEL_PATH.exists():
        st.warning(f"⚠️ KNN model not found at {MODEL_PATH}. Run ml_knn_recommender.py first.")
        return None
    
    try:
        data = joblib.load(MODEL_PATH)
        return {
            'knn_model': data['knn_model'],
            'scaler': data['scaler'],
            'sports_df': data['sports_df']
        }
    except Exception as e:
        st.error(f"Error loading KNN model: {e}")
        return None


def build_user_preferences_from_filters(selected_focus, selected_intensity, selected_setting):
    """
    Build user preference vector from sidebar filter selections
    
    Args:
        selected_focus: List of selected focus values (e.g., ['strength', 'endurance'])
        selected_intensity: List of selected intensity values (e.g., ['high'])
        selected_setting: List of selected setting values (e.g., ['solo'])
    
    Returns:
        Dict with 13 feature values (0.0 or 1.0)
    """
    preferences = {}
    
    # Focus features (7 binary)
    focus_features = ['balance', 'flexibility', 'coordination', 'relaxation', 
                     'strength', 'endurance', 'longevity']
    for feature in focus_features:
        preferences[feature] = 1.0 if feature in selected_focus else 0.0
    
    # Intensity (1 continuous) - average if multiple selected
    if selected_intensity:
        intensity_map = {'low': 0.33, 'moderate': 0.67, 'high': 1.0}
        intensity_values = [intensity_map.get(i.lower(), 0.67) for i in selected_intensity]
        preferences['intensity'] = sum(intensity_values) / len(intensity_values)
    else:
        preferences['intensity'] = 0.0
    
    # Setting features (5 binary)
    setting_features = ['team', 'fun', 'duo', 'solo', 'competitive']
    for feature in setting_features:
        preferences[f'setting_{feature}'] = 1.0 if feature in selected_setting else 0.0
    
    return preferences


def get_ml_recommendations(selected_focus, selected_intensity, selected_setting, 
                          min_match_score=75, max_results=10, exclude_sports=None):
    """
    Get ML-based sport recommendations using KNN
    
    Args:
        selected_focus: List of selected focus filters
        selected_intensity: List of selected intensity filters
        selected_setting: List of selected setting filters
        min_match_score: Minimum match percentage (0-100)
        max_results: Maximum number of recommendations
        exclude_sports: List of sport names to exclude (e.g., already shown in main results)
    
    Returns:
        List of dicts: [{'sport': name, 'match_score': percentage, 'item': offer_dict}, ...]
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
    user_vector = np.array([user_prefs.get(col, 0.0) for col in FEATURE_COLUMNS])
    user_vector = user_vector.reshape(1, -1)
    
    # Scale
    user_vector_scaled = scaler.transform(user_vector)
    
    # Get all sports as neighbors (we'll filter by threshold later)
    n_sports = len(sports_df)
    distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
    
    # Build recommendations
    recommendations = []
    exclude_sports = exclude_sports or []
    
    for distance, idx in zip(distances[0], indices[0]):
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
        
        # Stop if we have enough
        if len(recommendations) >= max_results:
            break
    
    return recommendations
