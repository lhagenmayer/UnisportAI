"""Machine Learning utilities for recommendations.

This module provides ML model loading and recommendation functions using
K-Nearest Neighbors (KNN) algorithm.

WHAT IS MACHINE LEARNING?
-------------------------
Machine Learning (ML) is a way for computers to learn patterns from data
and make predictions. In this app, ML is used to recommend sports that
match a user's preferences.

WHAT IS KNN?
------------
K-Nearest Neighbors (KNN) is a simple ML algorithm that finds items similar
to what you're looking for. Think of it like:
- "Find me sports similar to what I like"
- The algorithm looks at features (intensity, focus, setting) and finds
  sports with similar features
- It returns the "nearest neighbors" (most similar sports)

HOW IT WORKS IN THIS APP:
------------------------
1. Each sport has 13 features (balance, strength, intensity, etc.)
2. User selects preferences (e.g., "I like high-intensity strength training")
3. Preferences are converted to a 13-dimensional feature vector
4. KNN finds sports with similar feature vectors
5. The most similar sports are returned as recommendations

KEY CONCEPTS:
------------
- Feature Vector: A list of numbers representing a sport's characteristics
- Distance: How similar two feature vectors are (lower = more similar)
- Match Score: Converted distance to percentage (100% = perfect match)
- Model: Pre-trained ML model saved to disk (knn_recommender.joblib)

EXAMPLE:
--------
```python
# Get ML recommendations:
recommendations = get_ml_recommendations(
    selected_focus=['strength'],
    selected_intensity=['high'],
    selected_setting=['solo'],
    min_match_score=75,  # Only show 75%+ matches
    max_results=10
)
# Result: List of sports similar to user's preferences
```
"""

import streamlit as st
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime

# Feature order (13 features)
ML_FEATURE_COLUMNS = [
    'balance', 'flexibility', 'coordination', 'relaxation',
    'strength', 'endurance', 'longevity',
    'intensity',
    'setting_team', 'setting_fun', 'setting_duo',
    'setting_solo', 'setting_competitive'
]

ML_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "models" / "knn_recommender.joblib"


@st.cache_resource
def load_knn_model():
    """
    Load the pre-trained KNN machine learning model from disk.
    
    WHAT DOES THIS DO?
    ------------------
    Loads a saved ML model that was previously trained. The model contains:
    - knn_model: The KNN algorithm trained on sport features
    - scaler: A StandardScaler that normalizes feature values
    - sports_df: A DataFrame with all sports and their features
    
    WHY CACHE IT?
    -------------
    Loading ML models from disk is slow (can take seconds). By caching:
    - First call: Loads from disk (slow, ~2-3 seconds)
    - Subsequent calls: Returns cached model (fast, ~1ms)
    - Model stays in memory for the entire Streamlit session
    
    STREAMLIT CONCEPT - @st.cache_resource:
    --------------------------------------
    Use @st.cache_resource for objects that:
    - Are expensive to create/load
    - Can't be serialized (converted to bytes)
    - Should be reused across page reruns
    
    ML models fit this description perfectly!
    
    HOW IT WORKS:
    ------------
    1. Check if model file exists at ML_MODEL_PATH
    2. If not found: Show warning and return None
    3. If found: Load using joblib.load()
    4. Return dictionary with model components
    5. Streamlit caches the result
    
    EXAMPLE:
    --------
    ```python
    model_data = load_knn_model()
    if model_data:
        knn = model_data['knn_model']
        scaler = model_data['scaler']
        sports = model_data['sports_df']
        # Now you can use the model!
    ```
    
    Returns:
        Dictionary with keys:
            - 'knn_model': Trained KNN model
            - 'scaler': StandardScaler for feature normalization
            - 'sports_df': DataFrame with sports and features
        Returns None if model file not found or error occurred
    
    Note:
        The model must be trained first using ml/train.py before this
        function can load it. The model file is saved as a .joblib file.
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
    """
    Convert user filter selections into a 13-dimensional feature vector.
    
    WHAT DOES THIS DO?
    ------------------
    Takes user selections from the sidebar (e.g., "I want strength training,
    high intensity, solo") and converts them into a numerical vector that
    the ML model can understand.
    
    WHY IS THIS NEEDED?
    -------------------
    ML models work with numbers, not words. Strings must be converted to numbers:
    - "strength" → 1.0 (user wants this) or 0.0 (user doesn't want this)
    - "high intensity" → 1.0 (on a scale where low=0.33, moderate=0.67, high=1.0)
    - "solo" → 1.0 (user wants solo activities)
    
    THE 13 FEATURES:
    ---------------
    1-7. Focus features (binary: 0.0 or 1.0):
        - balance, flexibility, coordination, relaxation
        - strength, endurance, longevity
    8. Intensity (continuous: 0.0 to 1.0):
        - low = 0.33, moderate = 0.67, high = 1.0
        - If multiple selected, average them
    9-13. Setting features (binary: 0.0 or 1.0):
        - setting_team, setting_fun, setting_duo
        - setting_solo, setting_competitive
    
    EXAMPLE:
    --------
    ```python
    # User selects:
    focus = ['strength', 'endurance']
    intensity = ['high']
    setting = ['solo']
    
    # Convert to feature vector:
    prefs = build_user_preferences_from_filters(focus, intensity, setting)
    # Result:
    # {
    #   'strength': 1.0,
    #   'endurance': 1.0,
    #   'flexibility': 0.0,
    #   ...
    #   'intensity': 1.0,
    #   'setting_solo': 1.0,
    #   'setting_team': 0.0,
    #   ...
    # }
    ```
    
    Args:
        selected_focus: List of focus areas (e.g., ['strength', 'endurance'])
        selected_intensity: List of intensity levels (e.g., ['high'])
        selected_setting: List of settings (e.g., ['solo', 'team'])
    
    Returns:
        Dictionary with 13 feature values. Most are 0.0 or 1.0 (binary),
            except intensity which is 0.0 to 1.0 (continuous)
    
    Note:
        This vector is then used by the KNN model to find similar sports.
        The model compares this vector to feature vectors of all sports.
    """
    # Strings are manually mapped to floats instead of relying on pandas
    # so every component of the 13-D vector can be explained during demo sessions.
    preferences = {}
    
    # Normalize inputs to lowercase for matching
    focus_lower = []
    if selected_focus:
        for f in selected_focus:
            focus_lower.append(f.lower())
    
    setting_lower = []
    if selected_setting:
        for s in selected_setting:
            setting_lower.append(s.lower())
    
    # Focus features (7 binary)
    focus_features = ['balance', 'flexibility', 'coordination', 'relaxation', 
                     'strength', 'endurance', 'longevity']
    for feature in focus_features:
        if feature in focus_lower:
            preferences[feature] = 1.0
        else:
            preferences[feature] = 0.0
    
    # Intensity (1 continuous) average if multiple selected
    if selected_intensity:
        intensity_map = {'low': 0.33, 'moderate': 0.67, 'high': 1.0}
        intensity_values = []
        for i in selected_intensity:
            intensity_lower = i.lower()
            intensity_value = intensity_map.get(intensity_lower, 0.67)
            intensity_values.append(intensity_value)
        total_intensity = sum(intensity_values)
        count_intensity = len(intensity_values)
        preferences['intensity'] = total_intensity / count_intensity
    else:
        preferences['intensity'] = 0.0
    
    # Setting features (5 binary)
    setting_features = ['team', 'fun', 'duo', 'solo', 'competitive']
    for feature in setting_features:
        setting_key = f'setting_{feature}'
        if feature in setting_lower:
            preferences[setting_key] = 1.0
        else:
            preferences[setting_key] = 0.0
    
    return preferences


def get_ml_recommendations(selected_focus, selected_intensity, selected_setting, 
                          min_match_score=50, max_results=10, exclude_sports=None):
    """
    Get sport recommendations using machine learning (KNN algorithm).
    
    WHAT DOES THIS DO?
    ------------------
    Uses the KNN (K-Nearest Neighbors) ML algorithm to find sports that are
    most similar to the user's preferences. Returns a ranked list of recommendations
    with match scores (how similar each sport is to user preferences).
    
    HOW IT WORKS (STEP BY STEP):
    ----------------------------
    1. Load the pre-trained KNN model
    2. Convert user filters to a 13-dimensional feature vector
    3. Normalize the vector using StandardScaler (so all features are on same scale)
    4. Use KNN to find sports with similar feature vectors
    5. Convert distances to similarity scores (0-100%)
    6. Filter by minimum match score
    7. Return top N recommendations
    
    MATCH SCORE EXPLANATION:
    -----------------------
    - 100% = Perfect match (sport features exactly match user preferences)
    - 75% = Very similar (sport is quite similar to what user wants)
    - 50% = Somewhat similar (sport has some matching features)
    - 0% = No match (sport is completely different)
    
    EXAMPLE:
    --------
    ```python
    recommendations = get_ml_recommendations(
        selected_focus=['strength', 'endurance'],
        selected_intensity=['high'],
        selected_setting=['solo'],
        min_match_score=75,  # Only show 75%+ matches
        max_results=5        # Return top 5
    )
    
    # Result:
    # [
    #   {'sport': 'Weight Training', 'match_score': 95.2, 'item': {...}},
    #   {'sport': 'CrossFit', 'match_score': 88.7, 'item': {...}},
    #   ...
    # ]
    ```
    
    Args:
        selected_focus: List of focus areas user selected
        selected_intensity: List of intensity levels user selected
        selected_setting: List of settings user selected
        min_match_score: Minimum similarity score (0-100). Only sports
            with this score or higher are returned. Default: 75
        max_results: Maximum number of recommendations to return. Default: 10
        exclude_sports: List of sport names to exclude from
            results (e.g., sports already shown in main results)
    
    Returns:
        List of recommendation dictionaries, each containing:
            - 'sport': Sport name
            - 'match_score': Similarity percentage (0-100)
            - 'item': Complete sport data dictionary
        Returns empty list if model not found or no matches above threshold
    
    Note:
        This function requires a pre-trained model. If the model file doesn't
        exist, it will return an empty list. Train the model first using ml/train.py.
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
    feature_values = []
    for col in ML_FEATURE_COLUMNS:
        value = user_prefs.get(col, 0.0)
        feature_values.append(value)
    user_vector = np.array(feature_values)
    user_vector = user_vector.reshape(1, -1)
    
    # Scale
    user_vector_scaled = scaler.transform(user_vector)
    
    # Get all sports as neighbors (filtering by threshold happens later)
    n_sports = len(sports_df)
    distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
    
    # Build recommendations
    recommendations = []
    if exclude_sports is None:
        exclude_sports = []
    
    distances_list = distances[0]
    indices_list = indices[0]
    # Use enumerate() instead of range(len()) for better Pythonic code
    for i, distance in enumerate(distances_list):
        idx = indices_list[i]
        sport_name = sports_df.iloc[idx]['Angebot']
        
        # Skip if in exclude list
        if sport_name in exclude_sports:
            continue
        
        # Convert distance to similarity score (0 100%)
        one_minus_distance = 1 - distance
        match_score = one_minus_distance * 100
        
        # Only include if above threshold
        if match_score >= min_match_score:
            rounded_score = round(match_score, 1)
            sport_dict = sports_df.iloc[idx].to_dict()
            recommendations.append({
                'sport': sport_name,
                'match_score': rounded_score,
                'item': sport_dict
            })
        
        # Stop if enough recommendations found
        if len(recommendations) >= max_results:
            break
    
    return recommendations


def get_merged_recommendations(
    sports_data,
    selected_focus=None,
    selected_intensity=None,
    selected_setting=None,
    search_text="",
    show_upcoming_only=True,
    event_filters=None,
    min_match_score=0
):
    """
    Get merged recommendations combining KNN ML recommendations and filtered results.
    
    This function creates a unified list of sports recommendations by:
    1. Getting KNN recommendations for all sports (based on intensity/focus/setting)
    2. Getting filtered results (based on all filters including intensity/focus/setting)
    3. Merging both lists (keeping higher score when sport appears in both)
    4. Applying additional filters (search_text, show_upcoming_only, event filters) with score reduction
    5. Returning sorted list ready for use in Top Recommendations, Graph, and Sports Overview
    
    WHAT DOES THIS DO?
    ------------------
    Creates a single source of truth for sports recommendations that combines:
    - ML-based similarity scores (from KNN model)
    - Filter-based matching (exact matches for intensity/focus/setting)
    - Additional filter adjustments (soft filters that reduce score instead of excluding)
    
    FILTER LOGIC:
    -------------
    - Hard filters (intensity/focus/setting): Applied via filter_offers() - exact matches only
    - Soft filters (applied with score reduction):
      - show_upcoming_only: -20% if no future events
      - search_text: -30% if not in sport name
      - event_filters: -15% if no matching events
    
    EXAMPLE:
    --------
    ```python
    recommendations = get_merged_recommendations(
        sports_data=all_sports,
        selected_focus=['strength'],
        selected_intensity=['high'],
        selected_setting=['solo'],
        search_text="yoga",
        show_upcoming_only=True,
        event_filters={
            'weekday': ['Monday', 'Wednesday'],
            'date_start': date(2025, 1, 1),
            'date_end': date(2025, 12, 31)
        }
    )
    ```
    
    Args:
        sports_data: List of all sport offer dictionaries
        selected_focus: List of focus areas (e.g., ['strength', 'endurance'])
        selected_intensity: List of intensity levels (e.g., ['high'])
        selected_setting: List of settings (e.g., ['solo', 'team'])
        search_text: Text to search in sport names (soft filter)
        show_upcoming_only: If True, reduce score for sports without future events
        event_filters: Dictionary with optional keys:
            - weekday: List of weekdays
            - date_start: Start date
            - date_end: End date
            - time_start: Start time
            - time_end: End time
            - location: List of location names
        min_match_score: Minimum match score threshold (0-100)
    
    Returns:
        List of dictionaries, each containing:
            - 'name': Sport name
            - 'match_score': Match percentage (0-100)
            - 'offer': Complete sport offer dictionary
        Sorted by match_score descending
    """
    from .filters import filter_offers, filter_events
    from .db import get_events
    
    # STEP 1: Get filtered results (hard filters: intensity/focus/setting)
    filtered_results = filter_offers(
        sports_data,
        show_upcoming_only=False,  # We'll handle this separately with score reduction
        search_text="",  # We'll handle this separately with score reduction
        intensity=selected_intensity if selected_intensity else None,
        focus=selected_focus if selected_focus else None,
        setting=selected_setting if selected_setting else None,
        min_match_score=0,
        max_results=100000  # Get all filtered results
    )
    
    # STEP 2: Get KNN recommendations for ALL sports (not just top N)
    model_data = load_knn_model()
    merged_dict = {}
    
    if model_data:
        knn_model = model_data['knn_model']
        scaler = model_data['scaler']
        sports_df = model_data['sports_df']
        
        # Build user preferences from filters
        user_prefs = build_user_preferences_from_filters(
            selected_focus, selected_intensity, selected_setting
        )
        
        # Build feature vector
        feature_values = []
        for col in ML_FEATURE_COLUMNS:
            value = user_prefs.get(col, 0.0)
            feature_values.append(value)
        user_vector = np.array(feature_values)
        user_vector = user_vector.reshape(1, -1)
        
        # Scale
        user_vector_scaled = scaler.transform(user_vector)
        
        # Get all sports as neighbors
        n_sports = len(sports_df)
        distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
        
        # Add all KNN recommendations to merged dict
        for distance, idx in zip(distances[0], indices[0]):
            sport_name = sports_df.iloc[idx]['Angebot']
            match_score = (1 - distance) * 100
            
            # Find full offer data
            matching_offer = None
            for offer in sports_data:
                if offer.get('name') == sport_name:
                    matching_offer = offer.copy()
                    break
            
            if matching_offer:
                merged_dict[sport_name] = {
                    'name': sport_name,
                    'match_score': round(match_score, 1),
                    'offer': matching_offer
                }
    
    # STEP 3: Merge filtered results (keep higher score when sport appears in both)
    for offer in filtered_results:
        sport_name = offer.get('name')
        if sport_name:
            filtered_score = offer.get('match_score', 100.0)
            
            if sport_name in merged_dict:
                # Sport appears in both - keep higher score
                existing_score = merged_dict[sport_name]['match_score']
                if filtered_score > existing_score:
                    merged_dict[sport_name]['match_score'] = filtered_score
            else:
                # Sport only in filtered results - add it
                merged_dict[sport_name] = {
                    'name': sport_name,
                    'match_score': filtered_score,
                    'offer': offer.copy()
                }
    
    # STEP 4: Apply soft filters with score reduction
    # Load events if event filters are provided
    all_events = None
    if event_filters:
        try:
            all_events = get_events()
        except Exception:
            # If events can't be loaded, continue without event filtering
            all_events = []
    
    final_recommendations = []
    for sport_name, sport_data in merged_dict.items():
        offer = sport_data['offer']
        match_score = sport_data['match_score']
        
        # Apply show_upcoming_only filter (soft: reduce score by 20%)
        if show_upcoming_only:
            future_events_count = offer.get('future_events_count', 0)
            if future_events_count == 0:
                match_score = max(0, match_score - 20)
        
        # Apply search_text filter (soft: reduce score by 30%)
        if search_text:
            offer_name = offer.get('name', '').lower()
            search_text_lower = search_text.lower()
            if search_text_lower not in offer_name:
                match_score = max(0, match_score - 30)
        
        # Apply event filters (soft: reduce score by 15% if no matching events)
        if event_filters and all_events:
            # Get events for this sport
            sport_events = [e for e in all_events if e.get('sport_name') == sport_name]
            
            if sport_events:
                # Filter events based on event_filters
                filtered_sport_events = filter_events(
                    sport_events,
                    weekday_filter=event_filters.get('weekday'),
                    date_start=event_filters.get('date_start'),
                    date_end=event_filters.get('date_end'),
                    time_start=event_filters.get('time_start'),
                    time_end=event_filters.get('time_end'),
                    location_filter=event_filters.get('location'),
                    hide_cancelled=True
                )
                
                # If no matching events, reduce score
                if not filtered_sport_events:
                    match_score = max(0, match_score - 15)
            else:
                # No events at all for this sport, reduce score
                match_score = max(0, match_score - 15)
        
        # Only include if above minimum threshold
        if match_score >= min_match_score:
            final_recommendations.append({
                'name': sport_name,
                'match_score': round(match_score, 1),
                'offer': offer
            })
    
    # STEP 5: Sort by match score (highest first)
    final_recommendations = sorted(final_recommendations, key=lambda x: x['match_score'], reverse=True)
    
    return final_recommendations

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
