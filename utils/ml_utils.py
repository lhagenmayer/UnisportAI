"""
================================================================================
MACHINE LEARNING UTILITIES
================================================================================

Purpose: ML model loading and recommendation functions using K-Nearest Neighbors (KNN) algorithm.

HOW IT WORKS:
1. Each sport has 13 features (balance, strength, intensity, etc.)
2. User selects preferences (e.g., "I like high-intensity strength training")
3. Preferences are converted to a 13-dimensional feature vector
4. KNN finds sports with similar feature vectors
5. The most similar sports are returned as recommendations

KEY CONCEPTS:
- Feature Vector: A list of numbers representing a sport's characteristics
- Distance: How similar two feature vectors are (lower = more similar)
- Match Score: Converted distance to percentage (100% = perfect match)
- Model: Pre-trained ML model saved to disk (knn_recommender.joblib)
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
    """Load the pre-trained KNN machine learning model from disk.
    
    Loads a saved ML model that was previously trained. The model contains:
    - knn_model: The KNN algorithm trained on sport features
    - scaler: A StandardScaler that normalizes feature values
    - sports_df: A DataFrame with all sports and their features
    
    Returns:
        dict or None: Dictionary with keys:
            - 'knn_model': Trained KNN model
            - 'scaler': StandardScaler for feature normalization
            - 'sports_df': DataFrame with sports and features
        Returns None if model file not found or error occurred.
        
    Note:
        Loading ML models from disk is slow (can take seconds). By caching:
        - First call: Loads from disk (slow, ~2-3 seconds)
        - Subsequent calls: Returns cached model (fast, ~1ms)
        - Model stays in memory for the entire Streamlit session
        
        Uses @st.cache_resource for objects that are expensive to create/load,
        can't be serialized, and should be reused across page reruns.
        ML models fit this description perfectly.
        
        The model must be trained first using ml/train.py before this
        function can load it. The model file is saved as a .joblib file.
        
        Process:
        1. Check if model file exists at ML_MODEL_PATH
        2. If not found: Show warning and return None
        3. If found: Load using joblib.load()
        4. Return dictionary with model components
        5. Streamlit caches the result
        
    Example:
        >>> model_data = load_knn_model()
        >>> if model_data:
        ...     knn = model_data['knn_model']
        ...     scaler = model_data['scaler']
        ...     sports = model_data['sports_df']
        ...     # Now you can use the model!
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
    
    Takes user selections from the sidebar (e.g., "I want strength training,
    high intensity, solo") and converts them into a numerical vector that
    the ML model can understand. ML models work with numbers, not words.
    
    Args:
        selected_focus (list): List of focus areas (e.g., ['strength', 'endurance']).
        selected_intensity (list): List of intensity levels (e.g., ['high']).
        selected_setting (list): List of settings (e.g., ['solo', 'team']).
    
    Returns:
        dict: Dictionary with 13 feature values. Most are 0.0 or 1.0 (binary),
            except intensity which is 0.0 to 1.0 (continuous). Keys:
            - Focus features (binary): balance, flexibility, coordination, relaxation,
              strength, endurance, longevity
            - Intensity (continuous): 0.0 to 1.0 (low=0.33, moderate=0.67, high=1.0)
            - Setting features (binary): setting_team, setting_fun, setting_duo,
              setting_solo, setting_competitive
        
    Note:
        This vector is then used by the KNN model to find similar sports.
        The model compares this vector to feature vectors of all sports.
        If multiple intensity values are selected, they are averaged.
        Strings are manually mapped to floats instead of relying on pandas
        so every component of the 13-D vector can be explained during demo sessions.
        
    Example:
        >>> # User selects:
        >>> focus = ['strength', 'endurance']
        >>> intensity = ['high']
        >>> setting = ['solo']
        >>> 
        >>> # Convert to feature vector:
        >>> prefs = build_user_preferences_from_filters(focus, intensity, setting)
        >>> # Result:
        >>> # {
        >>> #   'strength': 1.0,
        >>> #   'endurance': 1.0,
        >>> #   'flexibility': 0.0,
        >>> #   ...
        >>> #   'intensity': 1.0,
        >>> #   'setting_solo': 1.0,
        >>> #   'setting_team': 0.0,
        >>> #   ...
        >>> # }
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
    """Get sport recommendations using machine learning (KNN algorithm).
    
    Uses the KNN (K-Nearest Neighbors) ML algorithm to find sports that are
    most similar to the user's preferences. Returns a ranked list of recommendations
    with match scores (how similar each sport is to user preferences).
    
    Args:
        selected_focus (list): List of focus areas user selected.
        selected_intensity (list): List of intensity levels user selected.
        selected_setting (list): List of settings user selected.
        min_match_score (int, optional): Minimum similarity score (0-100). Only sports
            with this score or higher are returned. Defaults to 50.
        max_results (int, optional): Maximum number of recommendations to return.
            Defaults to 10.
        exclude_sports (list, optional): List of sport names to exclude from
            results (e.g., sports already shown in main results). Defaults to None.
    
    Returns:
        list: List of recommendation dictionaries, each containing:
            - 'sport' (str): Sport name
            - 'match_score' (float): Similarity percentage (0-100)
            - 'item' (dict): Complete sport data dictionary
        Returns empty list if model not found or no matches above threshold.
        
    Note:
        This function requires a pre-trained model. If the model file doesn't
        exist, it will return an empty list. Train the model first using ml/train.py.
        
        Process:
        1. Load the pre-trained KNN model
        2. Convert user filters to a 13-dimensional feature vector
        3. Normalize the vector using StandardScaler (so all features are on same scale)
        4. Use KNN to find sports with similar feature vectors
        5. Convert distances to similarity scores (0-100%)
        6. Filter by minimum match score
        7. Return top N recommendations
        
        Match Score Explanation:
        - 100% = Perfect match (sport features exactly match user preferences)
        - 75% = Very similar (sport is quite similar to what user wants)
        - 50% = Somewhat similar (sport has some matching features)
        - 0% = No match (sport is completely different)
        
    Example:
        >>> recommendations = get_ml_recommendations(
        ...     selected_focus=['strength', 'endurance'],
        ...     selected_intensity=['high'],
        ...     selected_setting=['solo'],
        ...     min_match_score=75,  # Only show 75%+ matches
        ...     max_results=5        # Return top 5
        ... )
        >>> # Result:
        >>> # [
        >>> #   {'sport': 'Weight Training', 'match_score': 95.2, 'item': {...}},
        >>> #   {'sport': 'CrossFit', 'match_score': 88.7, 'item': {...}},
        >>> #   ...
        >>> # ]
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