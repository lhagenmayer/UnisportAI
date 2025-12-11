"""Filtering utilities for offers and events.

This module provides functions to filter sports activities and events based on user criteria.

WHAT IS FILTERING?
------------------
Filtering means showing only items that match certain criteria. For example:
- "Show me only yoga classes" (sport filter)
- "Show me only Monday classes" (weekday filter)
- "Show me only morning classes" (time filter)
- "Show me only classes at Gym A" (location filter)

HOW FILTERING WORKS:
-------------------
1. User selects filter criteria (e.g., "Monday", "Morning", "Yoga")
2. Each event/offer is checked against these criteria
3. Only items that match ALL criteria are shown
4. Items that don't match are hidden

KEY CONCEPTS:
------------
- Hard Filters: Must match exactly (e.g., sport name, location)
- Date/Time Filters: Check if event is within a date or time range
- Boolean Filters: True/False checks (e.g., hide cancelled events)
- Multiple Filters: All filters must match (AND logic, not OR)

EXAMPLE:
--------
```python
# Filter events:
filtered = filter_events(
    events,
    sport_filter=['Yoga', 'Swimming'],
    weekday_filter=['Monday', 'Wednesday'],
    time_start=time(9, 0),  # 9 AM
    time_end=time(17, 0),    # 5 PM
    hide_cancelled=True
)
# Result: Only yoga/swimming events on Mon/Wed between 9 AM and 5 PM
```
"""

from datetime import datetime, time, date
import streamlit as st
from utils.formatting import parse_event_datetime

# =============================================================================
# INTERNAL HELPERS
# =============================================================================
# PURPOSE: Internal helper functions for filtering logic

def _check_event_matches_filters(event, sport_filter, weekday_filter, date_start, date_end,
                                 time_start, time_end, location_filter, hide_cancelled):
    """Check if event matches all filters. Internal helper function.
    
    Centralizes filter matching logic so it can be reused. All filters must match
    (AND logic). Returns False as soon as any filter doesn't match (short-circuit evaluation).
    
    Args:
        event (dict): Event dictionary to check.
        sport_filter (list, optional): List of sport names to match.
        weekday_filter (list, optional): List of weekday names to match.
        date_start (date, optional): Start date for date range filter.
        date_end (date, optional): End date for date range filter.
        time_start (time, optional): Start time for time range filter.
        time_end (time, optional): End time for time range filter.
        location_filter (list, optional): List of location names to match.
        hide_cancelled (bool): If True, exclude cancelled events.
    
    Returns:
        bool: True if event matches all filters, False otherwise.
    """
    if sport_filter and event.get('sport_name', '') not in sport_filter:
        return False
    if hide_cancelled and event.get('canceled'):
        return False
    
    start_dt = parse_event_datetime(event.get('start_time'))
    
    if weekday_filter and start_dt.strftime('%A') not in weekday_filter:
        return False
    
    event_date = start_dt.date()
    if (date_start and event_date < date_start) or (date_end and event_date > date_end):
        return False
    
    if time_start or time_end:
        event_time = start_dt.time()
        if (time_start and event_time < time_start) or (time_end and event_time > time_end):
            return False
    
    if location_filter and event.get('location_name', '') not in location_filter:
        return False
    
    return True

# =============================================================================
# OFFER FILTERING
# =============================================================================
# PURPOSE: Functions for filtering sport offers

def filter_offers(offers, show_upcoming_only=True, intensity=None, focus=None, setting=None,
                  max_results=20):
    """Filter offers by intensity/focus/setting. Returns offers with match_score=100.0.
    
    Filters offers based on user preferences. Only includes offers with meaningful
    tags (focus, setting, or intensity) for ML compatibility. Applies hard filters
    (intensity/focus/setting must match exactly), then sets match_score to 100.0 for
    all filtered offers.
    
    Args:
        offers (list): List of offer dictionaries to filter.
        show_upcoming_only (bool, optional): If True, only include offers with future events.
            Defaults to True.
        intensity (list, optional): List of intensity values to match.
        focus (list, optional): List of focus values to match.
        setting (list, optional): List of setting values to match.
        max_results (int, optional): Maximum number of results to return. Defaults to 20.
    
    Returns:
        list: List of filtered offer dictionaries with match_score=100.0.
    """
    # Filter offers with meaningful tags and apply hard filters
    filtered = [
        o for o in offers
        if (o.get('focus') or o.get('setting') or o.get('intensity'))
        and (not show_upcoming_only or o.get('future_events_count', 0) > 0)
    ]
    
    # Apply intensity/focus/setting filters if provided
    if intensity or focus or setting:
        filtered = [
            o for o in filtered
            if (not intensity or o.get('intensity') in intensity)
            and (not focus or any(f in (o.get('focus') or []) for f in focus))
            and (not setting or any(s in (o.get('setting') or []) for s in setting))
        ]
    
    # Set match_score for all filtered offers
    for o in filtered:
        o['match_score'] = 100.0
    
    return filtered[:max_results]

# =============================================================================
# EVENT FILTERING
# =============================================================================
# PURPOSE: Functions for filtering course events

def filter_events(events, sport_filter=None, weekday_filter=None, date_start=None, date_end=None,
                  time_start=None, time_end=None, location_filter=None, hide_cancelled=True, filters=None):
    """Filter events. Accepts either filters dict or individual parameters.
    
    Provides flexible API - can pass individual parameters or a filters dictionary.
    All filters must match (AND logic). Extracts values from filters dict if provided,
    otherwise uses individual parameters.
    
    Args:
        events (list): List of event dictionaries to filter.
        sport_filter (list, optional): List of sport names to match.
        weekday_filter (list, optional): List of weekday names to match.
        date_start (date, optional): Start date for date range filter.
        date_end (date, optional): End date for date range filter.
        time_start (time, optional): Start time for time range filter.
        time_end (time, optional): End time for time range filter.
        location_filter (list, optional): List of location names to match.
        hide_cancelled (bool, optional): If True, exclude cancelled events. Defaults to True.
        filters (dict, optional): Dictionary containing all filter values. If provided,
            individual parameters are ignored.
    
    Returns:
        list: List of filtered event dictionaries.
    """
    # Extract values from filters dict if provided, otherwise use individual parameters
    if filters:
        sport_filter = filters.get('selected_sports')
        weekday_filter = filters.get('selected_weekdays')
        date_start = filters.get('date_start')
        date_end = filters.get('date_end')
        time_start = filters.get('time_start')
        time_end = filters.get('time_end')
        location_filter = filters.get('selected_locations')
        hide_cancelled = filters.get('hide_cancelled', True) if hide_cancelled is None else hide_cancelled
    
    return [e for e in events if _check_event_matches_filters(
        e, sport_filter, weekday_filter, date_start, date_end,
        time_start, time_end, location_filter, hide_cancelled
    )]

# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================
# PURPOSE: Functions for managing filter values in session state

def get_filter_values_from_session():
    """Extract all filter values from session state.
    
    Centralizes reading filter values from session_state. Ensures consistent
    filter structure across the app. Reads all filter-related keys from session_state
    and returns a dictionary with standardized key names.
    
    Returns:
        dict: Dictionary containing all filter values with keys:
            - intensity, focus, setting, show_upcoming_only (offer filters)
            - selected_sports, selected_weekdays, date_start, date_end, time_start,
              time_end, selected_locations, hide_cancelled (event filters)
            - min_match_score, ml_min_match (ML filters)
    """
    return {
        # Offer filters
        'intensity': st.session_state.get('intensity', []),
        'focus': st.session_state.get('focus', []),
        'setting': st.session_state.get('setting', []),
        'show_upcoming_only': st.session_state.get('show_upcoming_only', True),
        
        # Event filters
        'selected_sports': st.session_state.get('offers', []),
        'selected_weekdays': st.session_state.get('weekday', []),
        'date_start': st.session_state.get('date_start', None),
        'date_end': st.session_state.get('date_end', None),
        'time_start': st.session_state.get('start_time', None),
        'time_end': st.session_state.get('end_time', None),
        'selected_locations': st.session_state.get('location', []),
        'hide_cancelled': st.session_state.get('hide_cancelled', True),
        
        # ML filters
        'min_match_score': st.session_state.get('min_match_score', 0),
        'ml_min_match': st.session_state.get('ml_min_match', 50),
    }

def has_event_filters(filters=None, selected_sports=None, selected_weekdays=None,
                      date_start=None, date_end=None, time_start=None, time_end=None,
                      selected_locations=None, hide_cancelled=None):
    """Check if any event filters are set. Accepts either filters dict or individual parameters.
    
    Used to determine if event filtering should be applied. Helps optimize
    queries by skipping filtering when no filters are set.
    
    Args:
        filters (dict, optional): Dictionary containing filter values. If provided,
            individual parameters are ignored.
        selected_sports (list, optional): List of selected sports.
        selected_weekdays (list, optional): List of selected weekdays.
        date_start (date, optional): Start date filter.
        date_end (date, optional): End date filter.
        time_start (time, optional): Start time filter.
        time_end (time, optional): End time filter.
        selected_locations (list, optional): List of selected locations.
        hide_cancelled (bool, optional): Hide cancelled events flag.
    
    Returns:
        bool: True if any event filter is set, False otherwise.
    """
    if filters:
        return bool(
            filters.get('selected_weekdays') or filters.get('date_start') or filters.get('date_end') or
            filters.get('time_start') or filters.get('time_end') or filters.get('selected_locations')
        )
    return bool(
        (selected_sports and len(selected_sports)) or
        (selected_weekdays and len(selected_weekdays)) or
        date_start or date_end or time_start or time_end or
        (selected_locations and len(selected_locations)) or
        hide_cancelled is not None
    )

# =============================================================================
# FILTER SESSION STATE DEFAULTS
# =============================================================================
# PURPOSE: Central definition of all filter-related session state keys and their defaults
# WHY: This is the single source of truth for filter session state management

FILTER_SESSION_DEFAULTS = {
    # Offer filters
    'intensity': [],
    'focus': [],
    'setting': [],
    'show_upcoming_only': True,
    
    # Event filters
    'offers': [],  # Selected sports (mapped to 'selected_sports' in get_filter_values_from_session)
    'weekday': [],
    'location': [],
    'date_start': None,
    'date_end': None,
    'start_time': None,
    'end_time': None,
    'hide_cancelled': True,
    
    # ML filters
    'min_match_score': 0,
    'ml_min_match': 50,
}

def get_filter_session_keys():
    """Return list of all filter-related session state keys.
    
    Returns:
        list: List of all filter-related session state key names.
        
    Note:
        Used by auth module to clear all filter-related session state on logout.
        Ensures all filter keys are cleared, preventing data leakage between users.
    """
    return list(FILTER_SESSION_DEFAULTS.keys())

def has_offer_filters(filters=None):
    """Check if any offer filters (focus/intensity/setting) are set.
    
    Args:
        filters (dict, optional): Dictionary containing filter values. If None,
            checks session state directly.
    
    Returns:
        bool: True if any offer filter is set, False otherwise.
        
    Note:
        Used to determine if ML recommendations should be applied. ML is only
        applied when offer filters are set.
    """
    if filters:
        return bool(filters.get('focus') or filters.get('intensity') or filters.get('setting'))
    # Fallback: check session state directly
    return bool(
        st.session_state.get('focus') or 
        st.session_state.get('intensity') or 
        st.session_state.get('setting')
    )

def initialize_session_state():
    """Initialize filter-related session state variables with defaults.
    
    All session state keys are explicitly enumerated to ensure consistent
    state management. Missing keys can cause KeyError and inconsistent UI state.
    Only sets defaults if key doesn't exist (preserves user selections).
    Centralizing defaults provides a single checklist when debugging.
    
    Note:
        Uses FILTER_SESSION_DEFAULTS as the source of truth for all default values.
    """
    # All session state keys are explicitly enumerated to ensure consistent
    # state management. Missing keys can cause KeyError and inconsistent UI state.
    # Centralizing defaults provides a single checklist when debugging.
    # Only set defaults if key doesn't exist (preserve user selections)
    for key, value in FILTER_SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value

# =============================================================================
# ML RECOMMENDATIONS
# =============================================================================
# PURPOSE: Functions for applying ML recommendations and scoring

def apply_soft_filters_to_score(match_score, offer, show_upcoming_only=False, filters=None, events_by_sport=None):
    """Apply soft filters: reduce score by 20% if no future events, 15% if no matching events.
    
    Soft filters reduce match scores instead of completely excluding offers.
    This allows offers with low scores to still appear if they're close matches.
    
    Args:
        match_score (float): Initial match score (0-100).
        offer (dict): Offer dictionary.
        show_upcoming_only (bool, optional): If True, reduce score if no future events.
            Defaults to False.
        filters (dict, optional): Event filters dictionary.
        events_by_sport (dict, optional): Dictionary of events grouped by sport name.
    
    Returns:
        float: Adjusted match score (0-100).
        
    Note:
        Reduces score by 20% if show_upcoming_only is True and offer has no future events.
        Reduces by 15% if event filters are set and offer has no matching events.
    """
    score = match_score
    if show_upcoming_only and offer.get('future_events_count', 0) == 0:
        score = max(0, score - 20)
    if filters and events_by_sport:
        # Use pre-grouped events for efficient lookup
        sport_name = offer.get('name', '')
        sport_events = events_by_sport.get(sport_name, [])
        if not sport_events or not filter_events(sport_events, filters=filters, hide_cancelled=True):
            score = max(0, score - 15)
    return score

def apply_ml_recommendations_to_offers(offers, offers_data, filters):
    """Apply ML recommendations with fallback thresholds.
    
    If no recommendations are found at the user's minimum match threshold,
    try lower thresholds to ensure some results are shown. Tries thresholds
    in descending order (ml_min_match, 40, 30, 20, 0) until recommendations
    are found.
    
    Args:
        offers (list): List of offer dictionaries (currently unused, kept for API compatibility).
        offers_data (list): List of all available offers from database.
        filters (dict): Filter dictionary containing ml_min_match and other filter values.
    
    Returns:
        list: List of offer dictionaries with match_score, or empty list if no matches found.
    """
    ml_min_match = filters.get('ml_min_match', 50)
    for threshold in [ml_min_match, 40, 30, 20, 0]:
        recs = get_merged_recommendations(offers_data, filters, threshold)
        if recs:
            return [{**r['offer'], 'match_score': r['match_score']} for r in recs]
    return []

def get_merged_recommendations(sports_data, filters, min_match_score=0):
    """Get merged recommendations combining KNN ML and filtered results.
    
    Combines rule-based filtering (100% matches) with ML recommendations
    (similarity-based matches). Filtered results get priority (higher scores).
    
    Args:
        sports_data (list): List of all available sports offers from database.
        filters (dict): Filter dictionary containing focus, intensity, setting, etc.
        min_match_score (int, optional): Minimum match score threshold. Defaults to 0.
    
    Returns:
        list: List of recommendation dictionaries sorted by match_score (descending),
            each containing:
            - name (str): Sport name
            - match_score (float): Match score (0-100)
            - offer (dict): Complete offer dictionary
    
    Note:
        Process:
        1. Get filtered results (hard filters: intensity/focus/setting)
        2. Get KNN recommendations for all sports
        3. Merge both, keeping higher score when sport appears in both
        4. Apply soft filters and filter by threshold
    """
    import numpy as np
    from utils.ml_utils import load_knn_model, build_user_preferences_from_filters, ML_FEATURE_COLUMNS
    from utils.db import get_events_grouped_by_sport
    
    # Extract filter values
    selected_focus = filters.get('focus')
    selected_intensity = filters.get('intensity')
    selected_setting = filters.get('setting')
    show_upcoming_only = filters.get('show_upcoming_only', True)
    
    # STEP 1: Get filtered results (hard filters: intensity/focus/setting)
    filtered_results = filter_offers(
        sports_data,
        show_upcoming_only=False,  # We'll handle this separately with score reduction
        intensity=selected_intensity if selected_intensity else None,
        focus=selected_focus if selected_focus else None,
        setting=selected_setting if selected_setting else None,
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
        user_vector = np.array([user_prefs.get(col, 0.0) for col in ML_FEATURE_COLUMNS]).reshape(1, -1)
        
        # Scale
        user_vector_scaled = scaler.transform(user_vector)
        
        # Get all sports as neighbors
        n_sports = len(sports_df)
        distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
        
        # Add all KNN recommendations to merged dict
        offers_by_name = {o.get('name'): o for o in sports_data}
        for distance, idx in zip(distances[0], indices[0]):
            sport_name = sports_df.iloc[idx]['Angebot']
            if sport_name in offers_by_name:
                merged_dict[sport_name] = {
                    'name': sport_name,
                    'match_score': round((1 - distance) * 100, 1),
                    'offer': offers_by_name[sport_name].copy()
                }
    
    # STEP 3: Merge filtered results (keep higher score when sport appears in both)
    for offer in filtered_results:
        sport_name = offer.get('name')
        if sport_name:
            score = offer.get('match_score', 100.0)
            if sport_name in merged_dict:
                merged_dict[sport_name]['match_score'] = max(merged_dict[sport_name]['match_score'], score)
            else:
                merged_dict[sport_name] = {'name': sport_name, 'match_score': score, 'offer': offer.copy()}
    
    # STEP 4: Apply soft filters and filter by threshold
    # Use grouped events for efficient lookup if event filters are set
    try:
        events_by_sport = get_events_grouped_by_sport() if has_event_filters(filters=filters) else {}
    except Exception:
        events_by_sport = {}
    
    final_recommendations = []
    for name, data in merged_dict.items():
        offer = data['offer']
        match_score = data['match_score']
        
        # Hard filter: If show_upcoming_only is True, completely exclude offers with 0 future events
        # This applies to ALL recommendations (both 100% matches and ML recommendations)
        # ML recommendations (non-100% matches) should only be shown if they have upcoming events
        # IMPORTANT: For non-100% matches (ML recommendations), only show if future_events_count > 0
        future_events_count = offer.get('future_events_count')
        if future_events_count is None:
            future_events_count = 0
        else:
            # Ensure it's an integer
            try:
                future_events_count = int(future_events_count)
            except (ValueError, TypeError):
                future_events_count = 0
        
        # Exclude offers with 0 future events if show_upcoming_only is True
        if show_upcoming_only and future_events_count <= 0:
            continue
        
        score = apply_soft_filters_to_score(
            match_score, offer, show_upcoming_only, filters, events_by_sport
        )
        if score >= min_match_score:
            final_recommendations.append({
                'name': name,
                'match_score': round(score, 1),
                'offer': offer
            })
    
    return sorted(final_recommendations, key=lambda x: x['match_score'], reverse=True)

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
