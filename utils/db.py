"""
================================================================================
SUPABASE DATA ACCESS LAYER
================================================================================

Purpose: Centralize all database access operations for UnisportAI.
Architecture: Streamlit UI → utils.* service helpers → utils.db → Supabase REST API

WHY THIS MODULE EXISTS:
- Centralizing database queries in one place improves maintainability and consistency
- Other modules should not import Supabase directly, they should use functions from this module
- Provides a single point of change when database schema or queries need updates

KEY CONCEPTS:
- Caching: Database queries are cached to reduce load and improve response time
- Error Handling: All database operations use try/except for graceful degradation
- Connection Management: Single cached connection per user session (not per query)
================================================================================
"""

import streamlit as st
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict
from pathlib import Path
from st_supabase_connection import SupabaseConnection
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# CONNECTION MANAGEMENT
# =============================================================================
# PURPOSE: Get cached Supabase database connection
# WHY: Streamlit reruns the script on each interaction, so opening a new DB connection
#      every time would kill performance. The @st.cache_resource decorator turns this
#      function into a singleton per user session, ensuring we only create one connection.

@st.cache_resource
def supaconn():
    """Get cached Supabase database connection.
    
    Returns:
        SupabaseConnection: Cached Supabase connection instance.
        
    Note:
        Uses @st.cache_resource to ensure only one connection per user session.
        Streamlit reruns scripts on each interaction, so caching prevents
        creating multiple connections which would degrade performance.
    """
    return st.connection("supabase", type=SupabaseConnection)

# =============================================================================
# INTERNAL HELPERS
# =============================================================================
# PURPOSE: Internal utility functions used by public database functions

def _sort_dict_by_count_desc(counts_dict):
    """Sort dictionary by values in descending order.
    
    Args:
        counts_dict (dict): Dictionary with numeric values to sort.
    
    Returns:
        dict: New dictionary sorted by values in descending order (highest first).
        
    Note:
        Used for analytics functions that need to display counts sorted by frequency.
    """
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_items)

def _handle_db_error(e, context="database operation"):
    """Centralized error handling for database operations.
    
    Provides consistent error messages and helps identify configuration vs. runtime errors.
    Database queries can fail for various reasons (network, auth, config), so we need
    to handle them gracefully and provide helpful error messages to users.
    
    Args:
        e (Exception): The exception that occurred.
        context (str, optional): Description of the operation that failed. 
                                 Defaults to "database operation".
    """
    error_message = str(e)
    logger.error(f"Error in {context}: {error_message}")
    
    # Categorize error types for better user feedback
    has_url_error = "URL not provided" in error_message or "url" in error_message.lower()
    has_key_error = "key not provided" in error_message or "api key" in error_message.lower()
    has_auth_error = "authentication" in error_message.lower() or "unauthorized" in error_message.lower()
    
    if has_url_error or has_key_error:
        st.error("⚠️ **Database Configuration Error**\n\nPlease check your Supabase credentials in Streamlit Cloud secrets.")
    elif has_auth_error:
        st.error("⚠️ **Database Authentication Error**\n\nPlease verify your Supabase API key has the correct permissions.")
    else:
        st.error(f"⚠️ **Failed to {context}**\n\nError: {error_message[:200]}")

def _get_user_id(user_sub):
    """Resolve user_id from user_sub.
    
    Internal helper to convert OIDC sub (external ID) to internal database user_id.
    
    Args:
        user_sub (str): OIDC subject identifier (external user ID).
    
    Returns:
        int or None: Internal database user_id if found, None otherwise.
        
    Note:
        Database queries can fail, so error handling is important.
    """
    result = supaconn().table("users").select("id").eq("sub", user_sub).execute()
    return result.data[0]['id'] if result.data else None

def _has_sport_features(offer):
    """Check if offer has at least one sport feature (focus, setting, or intensity).
    
    Args:
        offer (dict): Offer dictionary from database.
    
    Returns:
        bool: True if offer has at least one feature (focus, setting, or intensity),
              False otherwise.
        
    Note:
        Some offers don't have focus, setting, or intensity, so we filter those out
        to only show offers that can be used for ML recommendations.
    """
    focus_list = offer.get('focus')
    has_focus = any(f and f.strip() for f in focus_list) if focus_list else False
    
    setting_list = offer.get('setting')
    has_setting = any(s and s.strip() for s in setting_list) if setting_list else False
    
    intensity_value = offer.get('intensity')
    has_intensity = bool(intensity_value and intensity_value.strip())
    
    return has_focus or has_setting or has_intensity

def _convert_event_fields(event):
    """Convert event fields from database format to UI format.
    
    Args:
        event (dict): Event dictionary from database.
    
    Returns:
        dict: Event dictionary with converted fields:
            - trainers: Converted from JSON to list of trainer names
            - details: Copied from kurs_details if present
    
    Note:
        The database view returns trainers as JSON, we convert it to a list of names
        for easier display in the UI. Also handles field name mapping (kurs_details → details).
    """
    # Parse trainers from JSON string or use list directly
    trainers_raw = event.get('trainers', '[]')
    trainers = json.loads(trainers_raw) if isinstance(trainers_raw, str) else (trainers_raw or [])
    
    # Extract trainer names using list comprehension
    event['trainers'] = [t['name'] for t in trainers if 'name' in t]
    
    # Copy kurs_details to details if it exists
    if 'kurs_details' in event:
        event['details'] = event['kurs_details']
    
    return event

# =============================================================================
# USER MANAGEMENT
# =============================================================================
# PURPOSE: Functions for managing user data in the database

def create_or_update_user(user_data):
    """Create or update user row in users table based on OIDC sub.
    
    Implements an "upsert" pattern: update if the user exists, insert if new.
    This is needed because users can log in multiple times, and we want to update
    their last_login timestamp and other info without creating duplicates.
    
    Args:
        user_data (dict): User data dictionary containing 'sub' and other user fields.
    
    Returns:
        dict or None: Created or updated user record, or None if user_sub is missing.
    """
    user_sub = user_data.get('sub')
    if not user_sub:
        return None
    
    conn = supaconn()
    existing = conn.table("users").select("*").eq("sub", user_sub).execute()
    
    # Update if exists, insert if new
    if existing.data:
        result = conn.table("users").update(user_data).eq("sub", user_sub).execute()
    else:
        result = conn.table("users").insert(user_data).execute()
    
    return result.data[0] if result.data else None

# =============================================================================
# MACHINE LEARNING DATA
# =============================================================================
# PURPOSE: Functions for loading ML training data

def get_ml_training_data_cli():
    """Load ML training data for CLI scripts (without Streamlit).
    
    This is used by scripts that run outside of Streamlit (e.g., train.py),
    so they need to create their own connection. Reads credentials from .streamlit/secrets.toml.
    
    Returns:
        list: List of sport feature dictionaries from ml_training_data view.
    
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set in secrets.toml,
                    or if no data is found in ml_training_data view.
        
    Note:
        Creates a direct Supabase client connection (not using Streamlit's connection manager).
    """
    from supabase import create_client
    
    script_dir = Path(__file__).parent.absolute()
    # Projektwurzel (eine Ebene über utils/)
    parent_dir = script_dir.parent
    secrets_path = parent_dir / ".streamlit" / "secrets.toml"

    supabase_url = None
    supabase_key = None

    # WHY: CLI scripts use secrets.toml as standard source, same as Streamlit app
    if secrets_path.exists():
        with secrets_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("SUPABASE_URL"):
                    _, value = stripped.split("=", 1)
                    supabase_url = value.strip().strip('"').strip("'")
                elif stripped.startswith("SUPABASE_KEY"):
                    _, value = stripped.split("=", 1)
                    supabase_key = value.strip().strip('"').strip("'")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .streamlit/secrets.toml")
    
    supabase = create_client(supabase_url, supabase_key)
    response = supabase.table("ml_training_data").select("*").execute()
    
    if not response.data:
        raise ValueError("No data found in ml_training_data view")
    
    return response.data

# =============================================================================
# MAIN DATA QUERIES
# =============================================================================
# PURPOSE: Core functions for loading offers and events from the database

@st.cache_data(ttl=300)
def get_offers_complete():
    """Load all offer data from vw_offers_complete view.
    
    Database views combine data from multiple tables, making queries simpler.
    Cached for 300 seconds because offers don't change very often, reducing database load.
    Filters offers to only include those with sport features (focus/setting/intensity)
    for ML compatibility.
    
    Returns:
        list: List of offer dictionaries with sport features, or empty list on error.
        
    Note:
        Database queries can fail, so we use try/except for error handling.
    """
    try:
        conn = supaconn()
        result = conn.table("vw_offers_complete").select("*").order("name").execute()
        # Filter offers that have sport features
        filtered = []
        for o in result.data:
            if _has_sport_features(o):
                filtered.append(o)
        count = len(filtered)
        logger.info(f"Loaded {count} offers with features from vw_offers_complete")
        return filtered
    except Exception as e:
        _handle_db_error(e, "load sport offers")
        return []

@st.cache_data(ttl=300)
def get_events(offer_href=None, sport_name=None, date_start=None, date_end=None):
    """Load future events from vw_termine_full view.
    
    Supabase has a limit on how many rows it returns, so pagination is needed.
    This function handles pagination by fetching data in chunks of 1000 rows.
    Cached for 300 seconds because events don't change very often.
    
    Args:
        offer_href (str, optional): Filter events by specific offer href.
        sport_name (str, optional): Filter events by sport name (single sport only).
        date_start (date, optional): Filter events starting from this date.
        date_end (date, optional): Filter events up to this date.
    
    Returns:
        list: List of event dictionaries with converted fields, or empty list on error.
        
    Note:
        Fetches events in pages, applies direct filters (offer_href, date range),
        then applies additional filters in Python (sport_name, date_start, date_end).
        Some filtering is done in Python because Supabase views may not support
        all filter operations directly. Database queries can fail, so we use try/except.
    """
    try:
        conn = supaconn()
        now = datetime.now()
        now_string = now.isoformat()
        query = conn.table("vw_termine_full").select("*").gte("start_time", now_string).order("start_time")
        if offer_href:
            query = query.eq("offer_href", offer_href)
        # Note: sport_name, date_start, date_end filtering is done in Python after fetching
        # because Supabase views may not support all filter operations directly
        
        # Fetch events in pages of 1000
        events = []
        page_size = 1000
        offset = 0
        while True:
            end_offset = offset + page_size - 1
            page_result = query.range(offset, end_offset).execute()
            page_events = page_result.data
            if not page_events:
                break
            events.extend(page_events)
            page_count = len(page_events)
            if page_count < page_size:
                break
            offset += page_size
        
        # Convert event fields for UI
        converted_events = [_convert_event_fields(e) for e in events]
        
        # Apply additional filters in Python (if needed)
        if sport_name:
            converted_events = [e for e in converted_events if e.get('sport_name') == sport_name]
        if date_start:
            from utils.formatting import parse_event_datetime
            converted_events = [e for e in converted_events 
                              if parse_event_datetime(e.get('start_time')).date() >= date_start]
        if date_end:
            from utils.formatting import parse_event_datetime
            converted_events = [e for e in converted_events 
                              if parse_event_datetime(e.get('start_time')).date() <= date_end]
        
        return converted_events
    except Exception as e:
        _handle_db_error(e, "load events")
        return []

# =============================================================================
# UNIFIED LOAD AND FILTER FUNCTIONS
# =============================================================================
# PURPOSE: Combined functions that load and filter data in a single call

@st.cache_data(ttl=60, hash_funcs={dict: lambda x: tuple(sorted(x.items())) if x else None})
def load_and_filter_offers(filters=None, update_session_state=False):
    """Load and filter offers. ML is automatically applied if offer filters are set.
    
    This is the unified function for loading and filtering offers. It combines
    data loading, error handling, and filtering (including ML recommendations)
    into a single call.
    
    Args:
        filters (dict, optional): Filters dict from get_filter_values_from_session().
            If None or no offer filters set, returns all offers.
            If offer filters (focus/intensity/setting) are set, applies ML.
        update_session_state (bool, optional): If True, updates st.session_state['sports_data'].
            Defaults to False.
    
    Returns:
        list: List of offer dictionaries with match_score, or empty list on error.
        
    Note:
        This function is cached with filters as cache keys. When filters change,
        Streamlit will automatically invalidate the cache and reload data.
        
    Example:
        >>> # Load all offers (no filters)
        >>> offers = load_and_filter_offers(update_session_state=True)
        >>> 
        >>> # Load and filter with ML
        >>> filters = get_filter_values_from_session()
        >>> offers = load_and_filter_offers(filters=filters, update_session_state=True)
    """
    try:
        # Load offers from database
        offers_data = get_offers_complete()
        
        # Check if offer filters are set (focus, intensity, or setting)
        from utils.filters import has_offer_filters as check_offer_filters
        has_offer_filters = check_offer_filters(filters=filters) if filters else False
        
        # Get show_upcoming_only setting from filters
        show_upcoming_only = filters.get('show_upcoming_only', True) if filters else True
        
        # Apply ML filtering if offer filters are set
        if has_offer_filters:
            from utils.filters import apply_ml_recommendations_to_offers
            offers = apply_ml_recommendations_to_offers(
                offers=[],
                offers_data=offers_data,
                filters=filters
            )
        else:
            # No ML filters: return all offers with default match_score
            # But still respect show_upcoming_only filter
            offers = [
                {**offer, 'match_score': 100.0} 
                for offer in offers_data
                if not show_upcoming_only or offer.get('future_events_count', 0) > 0
            ]
        
        return offers
    except Exception as e:
        _handle_db_error(e, "load and filter offers")
        empty_list = []
        if update_session_state:
            st.session_state['sports_data'] = empty_list
        return empty_list


@st.cache_data(ttl=60, hash_funcs={dict: lambda x: tuple(sorted(x.items())) if x else None})
def load_and_filter_events(filters=None, offer_href=None, show_spinner=False):
    """Load and filter events. Applies filters if provided.
    
    This is the unified function for loading and filtering events. It combines
    data loading, error handling, and filtering into a single call.
    
    Args:
        filters (dict, optional): Filters dict from get_filter_values_from_session().
            If None, returns all events (optionally filtered by offer_href).
            If provided, applies event filters.
        offer_href (str, optional): Offer href to filter events for specific offer.
        show_spinner (bool, optional): If True, shows loading spinner. Defaults to False.
            Note: spinner is not cached.
    
    Returns:
        list: List of filtered event dictionaries, or empty list on error.
        
    Note:
        This function is cached with filters and offer_href as cache keys. When filters
        change, Streamlit will automatically invalidate the cache and reload data.
        
    Example:
        >>> # Load all events for a specific offer
        >>> events = load_and_filter_events(offer_href=selected['href'], show_spinner=True)
        >>> 
        >>> # Load and filter events
        >>> filters = get_filter_values_from_session()
        >>> events = load_and_filter_events(filters=filters, offer_href=offer_href, show_spinner=False)
    """
    try:
        # Extract filters that get_events() can handle directly to avoid redundant filtering
        sport_name = None
        date_start = None
        date_end = None
        if filters:
            selected_sports = filters.get('selected_sports')
            # get_events() accepts single sport_name, so use first if only one selected
            if selected_sports and len(selected_sports) == 1:
                sport_name = selected_sports[0]
            date_start = filters.get('date_start')
            date_end = filters.get('date_end')
        
        # Load events from database (with direct filters if applicable)
        if show_spinner:
            with st.spinner('🔄 Loading course dates...'):
                events = get_events(offer_href=offer_href, sport_name=sport_name, date_start=date_start, date_end=date_end)
        else:
            events = get_events(offer_href=offer_href, sport_name=sport_name, date_start=date_start, date_end=date_end)
        
        # Apply remaining filters (weekday, time, location, hide_cancelled, multiple sports)
        # Always apply filter_events if filters are provided, as it handles hide_cancelled
        # and other filters that get_events() doesn't handle
        if filters:
            from utils.filters import filter_events
            # get_events() already filtered by: single sport_name, date_start, date_end (if provided)
            # filter_events() handles: multiple sports, weekday, time, location, hide_cancelled
            events = filter_events(events, filters=filters)
        
        return events
    except Exception as e:
        _handle_db_error(e, "load and filter events")
        return []


# =============================================================================
# EVENT GROUPING FUNCTIONS
# =============================================================================
# PURPOSE: Functions for grouping events by different fields for efficient lookup

@st.cache_data(ttl=300)
def group_events_by(field='offer_href'):
    """Generic function to group events by specified field.
    
    Args:
        field (str, optional): Field name to group by. Defaults to 'offer_href'.
    
    Returns:
        dict: Dictionary with field values as keys and lists of events as values.
        
    Note:
        Grouping events by offer_href or sport_name allows efficient lookup
        without querying the database multiple times. Cached for 300 seconds.
    """
    events = get_events()
    grouped = defaultdict(list)
    for event in events:
        if value := event.get(field):
            grouped[value].append(event)
    return dict(grouped)

def get_events_grouped_by_offer():
    """Load all events and group them by offer_href for efficient lookup.
    
    Returns:
        dict: Dictionary with offer_href as keys and lists of events as values.
        
    Note:
        Wrapper around group_events_by() for backward compatibility.
        Used when we need to quickly find all events for a specific offer.
    """
    return group_events_by('offer_href')

def get_events_grouped_by_sport():
    """Load all events and group them by sport_name for efficient lookup.
    
    Returns:
        dict: Dictionary with sport_name as keys and lists of events as values.
        
    Note:
        Wrapper around group_events_by() for backward compatibility.
        Used when we need to quickly find all events for a specific sport.
    """
    return group_events_by('sport_name')


@st.cache_data(ttl=60)
def get_user_complete(user_sub):
    """Load complete user profile from users table.
    
    Args:
        user_sub (str): OIDC subject identifier (external user ID).
    
    Returns:
        dict or None: Complete user profile dictionary, or None if not found or on error.
        
    Note:
        Cached for 60 seconds, as profile rarely changes. Returns all user fields.
        Database queries can fail, so we use try/except for error handling.
    """
    try:
        result = supaconn().table("users").select("*").eq("sub", user_sub).execute()
        return result.data[0] if result.data else None
    except:
        return None

# =============================================================================
# ANALYTICS FUNCTIONS
# =============================================================================
# PURPOSE: Functions for generating analytics data (counts, aggregations)

@st.cache_data(ttl=300)
def count_by_field(data_source, field, _transform=None, sort_desc=False, default_keys=None, list_field=False):
    """Generic function to count items by field.
    
    Args:
        data_source (str): 'events' or 'offers' - determines which data to load.
        field (str): Field name to count by (e.g., 'location_name', 'intensity').
        _transform (callable, optional): Function to transform field value before counting.
            Example: lambda x: parse_datetime(x).hour
        sort_desc (bool, optional): If True, sort results by count descending. Defaults to False.
        default_keys (list, optional): List of default keys to include (for weekday/hour).
            Keys not present in data will have count 0.
        list_field (bool, optional): If True, field contains a list and each item should be counted.
            Defaults to False.
    
    Returns:
        dict: Dictionary mapping field values to counts, or empty dict on error.
    """
    try:
        data = get_events() if data_source == 'events' else get_offers_complete()
        counts = defaultdict(int)
        
        for item in data:
            value = item.get(field)
            if value:
                if list_field and isinstance(value, list):
                    # Handle list fields (e.g., 'focus')
                    for list_item in value:
                        if list_item:
                            transformed = _transform(list_item) if _transform else list_item
                            if transformed:
                                counts[transformed] += 1
                else:
                    # Handle single value fields
                    transformed = _transform(value) if _transform else value
                    if transformed is not None:
                        counts[transformed] += 1
        
        result = dict(counts)
        
        # Add default keys if provided (for weekday/hour)
        if default_keys:
            result = {key: result.get(key, 0) for key in default_keys}
        
        return _sort_dict_by_count_desc(result) if sort_desc else result
    except:
        return {}

# Backward compatibility wrappers
@st.cache_data(ttl=300)
def get_events_by_weekday():
    """Get count of events grouped by weekday.
    
    Returns:
        dict: Dictionary mapping weekday names to event counts.
            Keys: 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
            Values: Count of events for each weekday.
    """
    from utils.formatting import parse_event_datetime
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return count_by_field(
        'events', 'start_time',
        _transform=lambda x: parse_event_datetime(x).strftime('%A'),
        default_keys=weekdays
    )

@st.cache_data(ttl=300)
def get_events_by_hour():
    """Get count of events grouped by hour of day (0-23).
    
    Returns:
        dict: Dictionary mapping hour (0-23) to event counts.
            Keys: Integers from 0 to 23 representing hours of the day.
            Values: Count of events starting in each hour.
    """
    from utils.formatting import parse_event_datetime
    return count_by_field(
        'events', 'start_time',
        _transform=lambda x: parse_event_datetime(x).hour,
        default_keys=range(24)
    )

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.