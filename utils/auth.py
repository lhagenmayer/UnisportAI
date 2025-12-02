# Authentication helpers for Streamlit using Google OIDC and Supabase
# This module provides functions to manage login, logout, and synchronization
# of the authenticated user with Supabase

import streamlit as st
import os
from datetime import datetime, timezone


# Check if running in production (Streamlit Cloud)
# This helps ensure OAuth redirect URIs are configured correctly
def is_production():
    """
    Check if the app is running in production (Streamlit Cloud).
    
    Returns True if running on Streamlit Cloud, False otherwise.
    """
    # Streamlit Cloud sets this environment variable
    streamlit_cloud = os.environ.get("STREAMLIT_CLOUD", "").lower() == "true"
    
    # If STREAMLIT_CLOUD is set, we're definitely in production
    if streamlit_cloud:
        return True
    
    # Fallback: check if we're not on localhost
    # In production, the URL won't contain localhost
    try:
        # Check if we can access the query params (which contain the full URL in some cases)
        # Or check environment variables that might indicate production
        hostname = os.environ.get("HOSTNAME", "")
        if "streamlit.app" in hostname or "streamlit.io" in hostname:
            return True
        
        # Check if we're definitely on localhost
        if "localhost" in hostname or "127.0.0.1" in hostname:
            return False
    except:
        pass
    
    # Default: assume local development if we can't determine
    return False


# Check if a user is currently logged in
# Streamlit automatically sets st.user.is_logged_in to True after successful login
def is_logged_in():
    return st.user.is_logged_in


# Clear all user-related data from Streamlit's session state
# When a user logs out, all their data must be removed from the app's memory
# Without clearing session state, the next user might see the previous user's filters
# and selections, which is a privacy and security issue
def clear_user_session():
    # Streamlit re-runs the script on every interaction
    # If session_state keys are not cleared, ghost filters from previous users may appear
    # This explicit reset ensures clean state for each user session
    
    # Clear filter states
    filter_keys = ['intensity', 'focus', 'setting', 'location', 'weekday', 'offers', 
                   'search_text', 'date_start', 'date_end', 'start_time', 'end_time',
                   'hide_cancelled', 'show_upcoming_only']
    for key in filter_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear app states
    app_keys = ['selected_offer', 'sports_data', 'active_tab', 'user_id']
    for key in app_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear any cached data
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()
    if hasattr(st, 'cache_resource'):
        st.cache_resource.clear()


# Perform a complete logout: clear data, log out, and refresh the UI
# This does three things: clears session state, calls Streamlit's logout, and refreshes the page
# All three steps are necessary for a complete logout to prevent data leakage
def handle_logout():
    clear_user_session()
    st.logout()
    st.rerun()


# Get the unique user identifier (OIDC "sub" claim)
# "Sub" stands for "subject": it's a unique identifier provided by Google
# This is part of the OIDC (OpenID Connect) standard
# This ID is used to look up the user in the Supabase database and link their data
def get_user_sub():
    if is_logged_in():
        return st.user.sub
    return None


# Get the authenticated user's email address
# This comes directly from Google's authentication system
def get_user_email():
    if is_logged_in():
        return st.user.email
    return None


# Check if the user's authentication token has expired
# When logging in, Google provides a token: a special code that proves authentication
# Tokens expire for security reasons, so this must be checked periodically
def check_token_expiry():
    if not is_logged_in():
        return

    # Check if the identity provider returned expiration information
    # hasattr() checks if an object has a certain attribute before accessing it
    if hasattr(st.user, 'expires_at'):
        expires_at = st.user.expires_at
        if expires_at:
            # Compare current time with expiration time
            current_time = datetime.now(timezone.utc)
            if current_time > expires_at:
                st.warning("Your session has expired. Please log in again.")
                handle_logout()


# Get all available user information from Streamlit's user object
# Collects user information from Google authentication and packages it into a dictionary
def get_user_info_dict():
    if not is_logged_in():
        return None

    # Use direct access for required fields
    # Optional fields are checked with hasattr() to avoid errors if they don't exist
    result = {
        'sub': st.user.sub,
        'email': st.user.email,
        'name': st.user.name,
        'is_logged_in': True
    }
    
    # Add optional fields if they exist
    if hasattr(st.user, 'given_name'):
        result['given_name'] = st.user.given_name
    else:
        result['given_name'] = None
    
    if hasattr(st.user, 'family_name'):
        result['family_name'] = st.user.family_name
    else:
        result['family_name'] = None
    
    if hasattr(st.user, 'picture'):
        result['picture'] = st.user.picture
    else:
        result['picture'] = None
    
    return result


# Save or update user information in the Supabase database
# When a user logs in with Google, their information is retrieved and stored in the database
# Storing user info in the database enables features like favorites and user profiles
def sync_user_to_supabase():
    from utils.db import create_or_update_user
    
    user_info = get_user_info_dict()
    if not user_info:
        return
    
    # Prepare user data with last_login timestamp
    # This uses an "upsert" pattern (update if exists, insert if new)
    user_sub = user_info.get("sub")
    user_email = user_info.get("email")
    user_name = user_info.get("name")
    user_picture = user_info.get("picture")
    
    # If name is not available, use email as fallback
    if not user_name:
        user_name = user_email
    
    last_login = datetime.now()
    last_login_string = last_login.isoformat()
    
    user_data = {
        "sub": user_sub,
        "email": user_email,
        "name": user_name,
        "picture": user_picture,
        "last_login": last_login_string
    }
    
    # Attempt to save to database
    # Database operations can fail, so the result is checked
    result = create_or_update_user(user_data)
    if result is None:
        st.warning("⚠️ Error synchronizing user")

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.

