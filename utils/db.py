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
    
    # Extract trainer ratings
    trainer_ratings = []
    for t in trainers:
        rating = t.get('rating', 'N/A')
        trainer_ratings.append(rating)
    event['trainer_ratings'] = trainer_ratings
    
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

# FRIENDS & SOCIAL

# Return all user profiles marked as public
# This is cached for 120 seconds because user profiles don't change often
@st.cache_data(ttl=120)
def get_public_users():
    # Database queries can fail, so we use try/except for error handling
    # If something goes wrong, we return an empty list
    try:
        result = supaconn().table("users").select("id, name, email, picture, bio, created_at, is_public").eq("is_public", True).execute()
        if result.data:
            return result.data
        return []
    except:
        # If there's an error, return empty list
        return []

# Return friendship status between two users
# Returns: 'friends', 'request_sent', 'request_received', or 'none'
# Both directions must be checked because friendships are bidirectional
def get_friend_status(user_id, other_user_id):
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        # Check if they are already friends
        friendship = conn.table("user_friends").select("*").or_(
            f"and(requester_id.eq.{user_id},addressee_id.eq.{other_user_id}),and(requester_id.eq.{other_user_id},addressee_id.eq.{user_id})"
        ).limit(1).execute()
        if friendship.data:
            return "friends"
        
        # Check if user sent a request to other_user
        request_sent = conn.table("friend_requests").select("id").eq("requester_id", user_id).eq("addressee_id", other_user_id).eq("status", "pending").limit(1).execute()
        if request_sent.data:
            return "request_sent"
        
        # Check if user received a request from other_user
        request_received = conn.table("friend_requests").select("id").eq("requester_id", other_user_id).eq("addressee_id", user_id).eq("status", "pending").limit(1).execute()
        if request_received.data:
            return "request_received"
        
        return "none"
    except:
        # If there's an error, return "none" (no relationship)
        return "none"

# Create friend request if none is pending yet
def send_friend_request(requester_id, addressee_id):
    # Database operations can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        # Check if a request already exists
        existing = conn.table("friend_requests").select("id, status").eq("requester_id", requester_id).eq("addressee_id", addressee_id).limit(1).execute()
        if existing.data:
            # If request exists and is pending, don't create another one
            existing_status = existing.data[0]['status']
            if existing_status == 'pending':
                return False
        
        # Create new friend request
        now = datetime.now()
        timestamp = now.isoformat()
        request_data = {
            "requester_id": requester_id,
            "addressee_id": addressee_id,
            "status": "pending",
            "created_at": timestamp,
            "updated_at": timestamp
        }
        conn.table("friend_requests").insert(request_data).execute()
        return True
    except:
        # If there's an error, return False (request not sent)
        return False

# Accept friend request and create bidirectional friendship
# Friendships need to be stored in both directions so queries work both ways
def accept_friend_request(request_id, requester_id, addressee_id):
    # Database operations can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        now = datetime.now()
        timestamp = now.isoformat()
        # Mark the request as accepted
        update_data = {"status": "accepted", "updated_at": timestamp}
        conn.table("friend_requests").update(update_data).eq("id", request_id).execute()
        # Create friendship in both directions
        friendship1 = {"requester_id": requester_id, "addressee_id": addressee_id, "created_at": timestamp}
        friendship2 = {"requester_id": addressee_id, "addressee_id": requester_id, "created_at": timestamp}
        friendships_list = [friendship1, friendship2]
        conn.table("user_friends").insert(friendships_list).execute()
        return True
    except:
        # If there's an error, return False (request not accepted)
        return False

# Reject friend request without creating friendship
def reject_friend_request(request_id):
    # Database operations can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        now = datetime.now()
        timestamp = now.isoformat()
        update_data = {
            "status": "rejected",
            "updated_at": timestamp
        }
        conn.table("friend_requests").update(update_data).eq("id", request_id).execute()
        return True
    except:
        # If there's an error, return False (request not rejected)
        return False

# Remove friendship in both directions for two users
def unfollow_user(user_id, friend_id):
    # Database operations can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        # Build query string for both directions
        query_string = f"and(requester_id.eq.{user_id},addressee_id.eq.{friend_id}),and(requester_id.eq.{friend_id},addressee_id.eq.{user_id})"
        conn.table("user_friends").delete().or_(query_string).execute()
        return True
    except:
        # If there's an error, return False (friendship not removed)
        return False

# Return all pending friend requests where user is the addressee
# This is cached for 60 seconds because friend requests don't change very often
@st.cache_data(ttl=60)
def get_pending_friend_requests(user_id):
    # Database queries can fail, so we use try/except for error handling
    try:
        result = supaconn().table("friend_requests").select(
            "*, requester:users!requester_id(*), addressee:users!addressee_id(*)"
        ).eq("addressee_id", user_id).eq("status", "pending").execute()
        if result.data:
            return result.data
        return []
    except:
        # If there's an error, return empty list
        return []

# Return list of user's friends with basic profile information
# Supabase can join related tables using the foreign key syntax
@st.cache_data(ttl=60)
def get_user_friends(user_id):
    # Database queries can fail, so we use try/except for error handling
    try:
        friendships = supaconn().table("user_friends").select(
            "*, requester:users!requester_id(*), addressee:users!addressee_id(*)"
        ).or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}").execute()
        friends = []
        if friendships.data:
            for friendship in friendships.data:
                # Figure out which user is the friend (not the current user)
                if friendship['requester_id'] == user_id:
                    friend = friendship.get('addressee')
                else:
                    friend = friendship.get('requester')
                if friend:
                    friends.append(friend)
        return friends
    except:
        # If there's an error, return empty list
        return []

# RATINGS

# Return current user's rating record for a given sport, if any
@st.cache_data(ttl=60)
def get_user_sport_rating(user_sub, sportangebot_href):
    # Database queries can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return None
        result = supaconn().table("sportangebote_user_ratings").select("*").eq("user_id", user_id).eq("sportangebot_href", sportangebot_href).execute()
        if result.data:
            return result.data[0]
        return None
    except:
        # If there's an error, return None (no rating found)
        return None

# Return current user's rating record for a given trainer, if any
@st.cache_data(ttl=60)
def get_user_trainer_rating(user_sub, trainer_name):
    # Database queries can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return None
        result = supaconn().table("trainer_user_ratings").select("*").eq("user_id", user_id).eq("trainer_name", trainer_name).execute()
        if result.data:
            return result.data[0]
        return None
    except:
        # If there's an error, return None (no rating found)
        return None

# Compute average rating and count for a sport offer
# The average must be calculated manually because Supabase doesn't do aggregations easily
@st.cache_data(ttl=120)
def get_average_rating_for_offer(offer_href):
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        ratings = conn.table("sportangebote_user_ratings").select("rating").eq("sportangebot_href", offer_href).execute()
        if not ratings.data:
            return {"avg": 0, "count": 0}
        # Calculate average by adding all ratings and dividing by count
        total = 0
        count = len(ratings.data)
        for r in ratings.data:
            rating_value = r['rating']
            total += rating_value
        avg_rating = total / count
        rounded_avg = round(avg_rating, 1)
        return {"avg": rounded_avg, "count": count}
    except:
        # If there's an error, return default values
        return {"avg": 0, "count": 0}

# Compute average rating and count for a trainer
@st.cache_data(ttl=120)
def get_average_rating_for_trainer(trainer_name):
    # Database queries can fail, so we use try/except for error handling
    try:
        conn = supaconn()
        ratings = conn.table("trainer_user_ratings").select("rating").eq("trainer_name", trainer_name).execute()
        if not ratings.data:
            return {"avg": 3, "count": 0}
        # Calculate average by adding all ratings and dividing by count
        total = 0
        count = len(ratings.data)
        for r in ratings.data:
            rating_value = r['rating']
            total += rating_value
        avg_rating = total / count
        rounded_avg = round(avg_rating, 1)
        return {"avg": rounded_avg, "count": count}
    except:
        # If there's an error, return default values
        return {"avg": 3, "count": 0}

# FAVORITES

# Return list of favorite sport hrefs for current user
@st.cache_data(ttl=60)
def get_user_favorite_sports(user_sub):
    # Database queries can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return []
        result = supaconn().table("user_favorite_sports").select("sportangebot_href").eq("user_id", user_id).execute()
        if result.data:
            # Extract hrefs from result
            return [item['sportangebot_href'] for item in result.data]
        return []
    except:
        # If there's an error, return empty list
        return []

# Return favorite sports with full details (name, icon, etc.) for current user
@st.cache_data(ttl=60)
def get_favorite_sports_with_details(user_sub):
    # Database queries can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return []
        # Get favorite hrefs
        favorites_result = supaconn().table("user_favorite_sports").select("sportangebot_href").eq("user_id", user_id).execute()
        if not favorites_result.data:
            return []
        
        favorite_hrefs = [item['sportangebot_href'] for item in favorites_result.data]
        
        # Get full details for each favorite sport
        conn = supaconn()
        offers = []
        for href in favorite_hrefs:
            offer_result = conn.table("sportangebote").select("*").eq("href", href).execute()
            if offer_result.data:
                offers.append(offer_result.data[0])
        
        return offers
    except:
        # If there's an error, return empty list
        return []

# Add a favorite sport for current user
def add_favorite_sport(user_sub, sportangebot_href):
    # Database operations can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return False
        
        conn = supaconn()
        # Check if already exists (unique constraint will also prevent duplicates)
        existing = conn.table("user_favorite_sports").select("id").eq("user_id", user_id).eq("sportangebot_href", sportangebot_href).execute()
        if existing.data:
            # Already exists, return True (success but no change)
            return True
        
        # Insert new favorite
        favorite_data = {
            "user_id": user_id,
            "sportangebot_href": sportangebot_href
        }
        conn.table("user_favorite_sports").insert(favorite_data).execute()
        
        return True
    except:
        # If there's an error, return False (favorite not added)
        return False

# Remove a favorite sport for current user
def remove_favorite_sport(user_sub, sportangebot_href):
    # Database operations can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return False
        
        conn = supaconn()
        conn.table("user_favorite_sports").delete().eq("user_id", user_id).eq("sportangebot_href", sportangebot_href).execute()
        
        return True
    except:
        # If there's an error, return False (favorite not removed)
        return False

# Return list of favorite sport hrefs for a user by user_id (for viewing other users' favorites)
@st.cache_data(ttl=60)
def get_user_favorite_sports_by_id(user_id):
    # Database queries can fail, so we use try/except for error handling
    try:
        result = supaconn().table("user_favorite_sports").select("sportangebot_href").eq("user_id", user_id).execute()
        if result.data:
            # Extract hrefs from result
            return [item['sportangebot_href'] for item in result.data]
        return []
    except:
        # If there's an error, return empty list
        return []

# Return favorite sports with full details for a user by user_id
@st.cache_data(ttl=60)
def get_favorite_sports_with_details_by_id(user_id):
    # Database queries can fail, so we use try/except for error handling
    try:
        # Get favorite hrefs
        favorites_result = supaconn().table("user_favorite_sports").select("sportangebot_href").eq("user_id", user_id).execute()
        if not favorites_result.data:
            return []
        
        favorite_hrefs = [item['sportangebot_href'] for item in favorites_result.data]
        
        # Get full details for each favorite sport
        conn = supaconn()
        offers = []
        for href in favorite_hrefs:
            offer_result = conn.table("sportangebote").select("*").eq("href", href).execute()
            if offer_result.data:
                offers.append(offer_result.data[0])
        
        return offers
    except:
        # If there's an error, return empty list
        return []

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
        result = conn.table("vw_offers_complete").select("*").order("avg_rating", desc=True).order("name").execute()
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

# Update user settings (bio, visibility)
# Multiple fields can be updated at once by building a dictionary
def update_user_settings(user_sub, bio=None, visibility=None):
    # Database operations can fail, so we use try/except for error handling
    try:
        now = datetime.now()
        timestamp = now.isoformat()
        update_data = {"updated_at": timestamp}
        if bio is not None:
            update_data["bio"] = bio
        if visibility is not None:
            update_data["is_public"] = visibility
        conn = supaconn()
        conn.table("users").update(update_data).eq("sub", user_sub).execute()
        return True
    except:
        # If there's an error, return False (update failed)
        return False

# Submit ratings for sports or trainers
# The same function can be used for different types by using different table names
def submit_rating(user_sub, target_type, target_id, rating, comment=""):
    # Database operations can fail, so we use try/except for error handling
    try:
        user_id = _get_user_id(user_sub)
        if not user_id:
            return False
        
        # Choose the right table and field based on target type
        if target_type == "sport":
            table_name = "sportangebote_user_ratings"
            id_field = "sportangebot_href"
        elif target_type == "trainer":
            table_name = "trainer_user_ratings"
            id_field = "trainer_name"
        else:
            return False
        
        conn = supaconn()
        # Check if rating already exists
        existing = conn.table(table_name).select("*").eq("user_id", user_id).eq(id_field, target_id).execute()
        
        now = datetime.now()
        timestamp = now.isoformat()
        rating_data = {
            "user_id": user_id,
            "rating": rating,
            "comment": comment,
            "updated_at": timestamp
        }
        rating_data[id_field] = target_id
        
        if existing.data:
            # Update existing rating
            conn.table(table_name).update(rating_data).eq("user_id", user_id).eq(id_field, target_id).execute()
        else:
            # Create new rating
            created_timestamp = now.isoformat()
            rating_data["created_at"] = created_timestamp
            conn.table(table_name).insert(rating_data).execute()
        
        return True
    except:
        # If there's an error, return False (rating not saved)
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
