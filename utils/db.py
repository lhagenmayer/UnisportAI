# Supabase data access layer for UnisportAI
# This module centralizes all database access operations
# Centralizing database queries in one place improves maintainability and consistency
# Architecture: Streamlit UI → utils.* service helpers → utils.db → Supabase REST API
# Other modules should not import Supabase directly, they should use functions from this module

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

# CONNECTION

# Get a cached Supabase database connection
# Streamlit reruns the script on each interaction, so opening a new DB connection every time
# would kill performance. The @st.cache_resource decorator turns this function into
# a singleton per user session, ensuring we only create one connection
@st.cache_resource
def supaconn():
    return st.connection("supabase", type=SupabaseConnection)

# INTERNAL HELPERS

# Helper function to sort a dictionary by values in descending order
# Returns a new dictionary sorted by count (highest first)
def _sort_dict_by_count_desc(counts_dict):
    """Sort dictionary by values in descending order."""
    # Convert to list of tuples (value, key) and sort by value descending
    sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_items)

# Helper function to resolve user_id from user_sub
# Returns None if not found
# Database queries can fail, so error handling is important
def _get_user_id(user_sub):
    result = supaconn().table("users").select("id").eq("sub", user_sub).execute()
    if result.data:
        return result.data[0]['id']
    return None

# Helper function to check if offer has at least one sport feature
# Some offers don't have focus, setting, or intensity, so we filter those out
def _has_sport_features(offer):
    # Check if focus has any non-empty values using any() with generator expression
    focus_list = offer.get('focus')
    has_focus = any(f and f.strip() for f in focus_list) if focus_list else False
    
    # Check if setting has any non-empty values using any() with generator expression
    setting_list = offer.get('setting')
    has_setting = any(s and s.strip() for s in setting_list) if setting_list else False
    
    # Check if intensity exists and is not empty
    intensity_value = offer.get('intensity')
    has_intensity = bool(intensity_value and intensity_value.strip())
    
    return has_focus or has_setting or has_intensity

# Helper function to convert trainer data from view format to UI format
# The database view returns trainers as JSON, we convert it to a list of names
def _convert_event_fields(event):
    # Parse trainers from JSON string or use list directly
    trainers_raw = event.get('trainers', '[]')
    if isinstance(trainers_raw, str):
        trainers = json.loads(trainers_raw)
    else:
        trainers = trainers_raw or []
    
    # Extract trainer names
    trainer_names = []
    for t in trainers:
        if 'name' in t:
            trainer_names.append(t['name'])
    event['trainers'] = trainer_names
    
    
    # Copy kurs_details to details if it exists
    if 'kurs_details' in event:
        event['details'] = event['kurs_details']
    
    return event

# USER MANAGEMENT

# Get minimal public user profile by internal user UUID
def get_user_by_id(user_id):
    conn = supaconn()
    result = conn.table("users").select("name, picture, email, bio, created_at").eq("id", user_id).execute()
    if result.data:
        return result.data[0]
    return None

# Create or update user row in users table based on OIDC sub
# This implements an "upsert" pattern: update if the user exists, insert if new
def create_or_update_user(user_data):
    user_sub = user_data.get('sub')
    if not user_sub:
        return None
    
    conn = supaconn()
    # Check if user already exists
    existing = conn.table("users").select("*").eq("sub", user_sub).execute()
    
    if existing.data:
        # User exists, update them
        result = conn.table("users").update(user_data).eq("sub", user_sub).execute()
    else:
        # User doesn't exist, create new record
        result = conn.table("users").insert(user_data).execute()
    
    if result.data:
        return result.data[0]
    return None

# Resolve internal user UUID for a given OIDC sub
def get_user_id_by_sub(user_sub):
    return _get_user_id(user_sub)


# FAVORITES

# MACHINE LEARNING DATA

# Load ML training data for CLI scripts (without Streamlit)
# This is used by scripts that run outside of Streamlit, so they need to create their own connection
def get_ml_training_data_cli():
    from supabase import create_client
    
    script_dir = Path(__file__).parent.absolute()
    # Projektwurzel (eine Ebene über utils/)
    parent_dir = script_dir.parent
    secrets_path = parent_dir / ".streamlit" / "secrets.toml"

    supabase_url = None
    supabase_key = None

    # Standard-Quelle für CLI-Skripte ist secrets.toml – exakt wie bei der Streamlit-App.
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

# UTILITIES

# Return underlying Supabase connection for advanced operations
def get_supabase_client():
    return supaconn()

# Get when database was last updated (ETL run timestamp)
# Returns formatted string or 'unknown'
# Timezone conversion is important when displaying times to users
def get_data_timestamp():
    # Database queries and date parsing can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        resp = conn.table("etl_runs").select("ran_at").order("ran_at", desc=True).limit(1).execute()
        if not resp.data:
            return "unknown"
        last_run = resp.data[0].get("ran_at")
        if not last_run:
            return "unknown"
        # Convert date string to datetime object
        last_run_str = str(last_run)
        date_str = last_run_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(date_str)
        # Make sure it has timezone info
        if dt.tzinfo is None:
            utc_timezone = ZoneInfo("UTC")
            dt = dt.replace(tzinfo=utc_timezone)
        # Convert to Swiss time
        swiss_timezone = ZoneInfo("Europe/Zurich")
        dt_swiss = dt.astimezone(swiss_timezone)
        # Format as string
        formatted_date = dt_swiss.strftime("%d.%m.%Y %H:%M")
        return formatted_date
    except:
        # If there's an error, return "unknown"
        return "unknown"

# MAIN DATA QUERIES

# Load all offer data from vw_offers_complete view
# Database views combine data from multiple tables, making queries simpler
# This is cached for 300 seconds because offers don't change very often
@st.cache_data(ttl=300)
def get_offers_complete():
    # Database queries can fail, so we use try/except for error handling
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
        # The "as e" syntax lets us access the error message
        # If there's an error, log it and show message to user
        error_message = str(e)
        logger.error(f"Error fetching offers: {error_message}")
        
        # Check what kind of error it was
        has_url_error = "URL not provided" in error_message or "url" in error_message.lower()
        has_key_error = "key not provided" in error_message or "api key" in error_message.lower()
        has_auth_error = "authentication" in error_message.lower() or "unauthorized" in error_message.lower()
        
        if has_url_error or has_key_error:
            st.error("⚠️ **Database Configuration Error**\n\nPlease check your Supabase credentials in Streamlit Cloud secrets.")
        elif has_auth_error:
            st.error("⚠️ **Database Authentication Error**\n\nPlease verify your Supabase API key has the correct permissions.")
        else:
            st.error(f"⚠️ **Failed to load sport offers**\n\nError: {error_message[:200]}")
        return []

# Load future events from vw_termine_full view
# Supabase has a limit on how many rows it returns, so pagination is needed
# This function handles pagination by fetching data in chunks of 1000 rows
@st.cache_data(ttl=300)
def get_events(offer_href=None):
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        now = datetime.now()
        now_string = now.isoformat()
        query = conn.table("vw_termine_full").select("*").gte("start_time", now_string).order("start_time")
        if offer_href:
            query = query.eq("offer_href", offer_href)
        
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
        converted_events = []
        for e in events:
            converted_event = _convert_event_fields(e)
            converted_events.append(converted_event)
        return converted_events
    except Exception as e:
        # The "as e" syntax lets us access the error message
        # If there's an error, log it and show message to user
        error_message = str(e)
        logger.error(f"Error fetching events: {error_message}")
        
        # Check what kind of error it was
        has_url_error = "URL not provided" in error_message or "url" in error_message.lower()
        has_key_error = "key not provided" in error_message or "api key" in error_message.lower()
        has_auth_error = "authentication" in error_message.lower() or "unauthorized" in error_message.lower()
        
        if has_url_error or has_key_error:
            st.error("⚠️ **Database Configuration Error**\n\nPlease check your Supabase credentials in Streamlit Cloud secrets.")
        elif has_auth_error:
            st.error("⚠️ **Database Authentication Error**\n\nPlease verify your Supabase API key has the correct permissions.")
        else:
            st.error(f"⚠️ **Failed to load events**\n\nError: {error_message[:200]}")
        return []

# Load complete user profile from users table
@st.cache_data(ttl=60)
def get_user_complete(user_sub):
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        result = conn.table("users").select("*").eq("sub", user_sub).execute()
        if result.data:
            return result.data[0]
        return None
    except:
        # If there's an error, return None (user not found)
        return None

# Update user settings (bio)
# Multiple fields can be updated at once by building a dictionary
def update_user_settings(user_sub, bio=None):
    # Database operations can fail, so we use try/except for error handling
    try:
        now = datetime.now()
        timestamp = now.isoformat()
        update_data = {"updated_at": timestamp}
        if bio is not None:
            update_data["bio"] = bio
        conn = supaconn()
        conn.table("users").update(update_data).eq("sub", user_sub).execute()
        return True
    except:
        # If there's an error, return False (update failed)
        return False

# ANALYTICS FUNCTIONS

# Analytics function: Get count of events grouped by weekday
# defaultdict makes it easy to count things without checking if keys exist
@st.cache_data(ttl=300)
def get_events_by_weekday():
    # Date parsing can fail, so we use try/except for error handling
    try:
        events = get_events()
        weekdays_english = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        counts = defaultdict(int)
        for event in events:
            start_time = event.get('start_time')
            if start_time:
                # Parse the date string
                start_time_str = str(start_time)
                date_str = start_time_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(date_str)
                # Use strftime('%A') to get English weekday name directly
                weekday = dt.strftime('%A')
                counts[weekday] += 1
        # Build result dictionary with English weekday names using dict comprehension
        return {day: counts.get(day, 0) for day in weekdays_english}
    except:
        # If there's an error, return empty dictionary
        return {}

# Analytics function: Get count of events grouped by hour of day (0 23)
@st.cache_data(ttl=300)
def get_events_by_hour():
    # Date parsing can fail, so we use try/except for error handling
    try:
        events = get_events()
        counts = defaultdict(int)
        for event in events:
            start_time = event.get('start_time')
            if start_time:
                # Parse the date string
                start_time_str = str(start_time)
                date_str = start_time_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(date_str)
                hour = dt.hour
                counts[hour] += 1
        # Build result dictionary for all 24 hours using dict comprehension
        return {h: counts.get(h, 0) for h in range(24)}
    except:
        # If there's an error, return empty dictionary
        return {}

# Analytics function: Get count of events grouped by location
@st.cache_data(ttl=300)
def get_events_by_location():
    # Operations can fail, so we use try/except for error handling
    try:
        events = get_events()
        counts = defaultdict(int)
        for event in events:
            if event.get('location_name'):
                location = event['location_name']
                counts[location] += 1
        # Sort by count (descending) using helper function
        return _sort_dict_by_count_desc(counts)
    except:
        # If there's an error, return empty dictionary
        return {}

# Analytics function: Get count of events grouped by location type (indoor/outdoor)
@st.cache_data(ttl=300)
def get_events_by_location_type():
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        events = get_events()
        # Get location types from database
        loc_result = conn.table("unisport_locations").select("name, indoor_outdoor").execute()
        locations = {}
        if loc_result.data:
            for loc in loc_result.data:
                loc_name = loc['name']
                loc_type = loc.get('indoor_outdoor')
                locations[loc_name] = loc_type
        
        counts = defaultdict(int)
        for event in events:
            location = event.get('location_name')
            if location and location in locations:
                loc_type = locations[location]
                if loc_type:
                    loc_type_capitalized = loc_type.capitalize()
                else:
                    loc_type_capitalized = 'Unknown'
                counts[loc_type_capitalized] += 1
            else:
                counts['Unknown'] += 1
        result = dict(counts)
        return result
    except:
        # If there's an error, return empty dictionary
        return {}

# Analytics function: Get count of offers grouped by intensity level
@st.cache_data(ttl=300)
def get_offers_by_intensity():
    # Operations can fail, so we use try/except for error handling
    try:
        offers = get_offers_complete()
        counts = defaultdict(int)
        for offer in offers:
            if offer.get('intensity'):
                intensity = offer['intensity'].capitalize()
                counts[intensity] += 1
        return dict(counts)
    except:
        # If there's an error, return empty dictionary
        return {}

# Analytics function: Get count of offers grouped by focus areas
@st.cache_data(ttl=300)
def get_offers_by_focus():
    # Operations can fail, so we use try/except for error handling
    try:
        offers = get_offers_complete()
        counts = defaultdict(int)
        for offer in offers:
            focus_list = offer.get('focus', [])
            for focus_item in focus_list:
                if focus_item:
                    # Use English focus names directly (capitalized)
                    key = focus_item.capitalize()
                    counts[key] += 1
        # Sort by count (descending) using helper function
        return _sort_dict_by_count_desc(counts)
    except:
        # If there's an error, return empty dictionary
        return {}

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.