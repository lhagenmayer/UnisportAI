import streamlit as st
import pandas as pd
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@st.cache_resource
def load_ml_model():
    """Load the trained ML model (cached)"""
    try:
        model_path = Path(__file__).parent.parent / "machine" / "ml_model.joblib"
        model = joblib.load(model_path)
        logger.info("ML model loaded successfully")
        return model
    except Exception as e:
        logger.error(f"Error loading ML model: {e}")
        st.error(f"Failed to load ML model: {e}")
        return None

def get_sport_recommendations(user_preferences: dict, top_n: int = 5):
    """
    Get sport recommendations based on user preferences
    
    Args:
        user_preferences: Dictionary with 13 features:
            - balance, flexibility, coordination, relaxation, strength, endurance, longevity
            - intensity
            - setting_team, setting_fun, setting_duo, setting_solo, setting_competitive
        top_n: Number of recommendations to return
    
    Returns:
        List of tuples: [(sport_name, confidence_score), ...]
    """
    model = load_ml_model()
    if model is None:
        return []
    
    try:
        # Ensure correct feature order
        feature_order = [
            'balance', 'flexibility', 'coordination', 'relaxation', 
            'strength', 'endurance', 'longevity',
            'intensity',
            'setting_team', 'setting_fun', 'setting_duo', 
            'setting_solo', 'setting_competitive'
        ]
        
        # Create DataFrame with correct feature order
        X = pd.DataFrame([user_preferences])[feature_order]
        
        # Get predictions
        probabilities = model.predict_proba(X)[0]
        
        # Get top N predictions
        top_indices = probabilities.argsort()[-top_n:][::-1]
        
        recommendations = []
        for idx in top_indices:
            sport = model.classes_[idx]
            confidence = probabilities[idx] * 100
            recommendations.append((sport, confidence))
        
        return recommendations
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        st.error(f"Error getting recommendations: {e}")
        return []

def validate_user_preferences(preferences: dict) -> bool:
    """Validate that all required features are present"""
    required_features = [
        'balance', 'flexibility', 'coordination', 'relaxation', 
        'strength', 'endurance', 'longevity', 'intensity',
        'setting_team', 'setting_fun', 'setting_duo', 
        'setting_solo', 'setting_competitive'
    ]
    
    for feature in required_features:
        if feature not in preferences:
            return False
        if not isinstance(preferences[feature], (int, float)):
            return False
        if not (0 <= preferences[feature] <= 1):
            return False
    
    return True

def get_recommendations_from_sidebar():
    """
    Generate ML recommendations using existing sidebar filters.
    Maps the current sidebar filter state to ML model features.
    
    Returns:
        List of dicts with 'sport' and 'confidence' keys
    """
    from data.state_manager import get_filter_state
    
    # Get current sidebar filter values
    intensity = get_filter_state('intensity', [])
    focus = get_filter_state('focus', [])
    setting = get_filter_state('setting', [])
    
    # Map to ML features (13 required features)
    user_prefs = {
        # Fitness goals (0-1 scale based on focus filter)
        'balance': 1.0 if 'Balance' in focus else 0.3,
        'flexibility': 1.0 if 'Flexibility' in focus else 0.3,
        'coordination': 1.0 if 'Coordination' in focus else 0.3,
        'relaxation': 1.0 if 'Low' in intensity or 'Relaxation' in focus else 0.3,
        'strength': 1.0 if 'Strength' in focus else 0.3,
        'endurance': 1.0 if 'Endurance' in focus else 0.3,
        'longevity': 0.5,  # Default value (not in current filters)
        
        # Intensity (based on intensity filter)
        'intensity': 0.8 if 'High' in intensity else (0.5 if 'Medium' in intensity else 0.2),
        
        # Settings (0 or 1 based on setting filter)
        'setting_team': 1.0 if 'Team' in setting else 0.0,
        'setting_fun': 0.5,  # Default value (not in current filters)
        'setting_duo': 0.0,  # Not in current filters
        'setting_solo': 1.0 if 'Solo' in setting else 0.0,
        'setting_competitive': 0.5,  # Default value (not in current filters)
    }
    
    # Get recommendations
    recommendations = get_sport_recommendations(user_prefs, top_n=10)
    
    # Convert to dict format
    return [{'sport': sport, 'confidence': confidence} for sport, confidence in recommendations]
