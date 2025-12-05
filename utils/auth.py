"""
================================================================================
AUTHENTICATION MODULE
================================================================================

Purpose: Authentication helpers for Streamlit using Google OIDC and Supabase.
Provides functions to manage login, logout, and synchronization of authenticated
users with Supabase.
================================================================================
"""

import streamlit as st
from datetime import datetime, timezone

# =============================================================================
# AUTHENTICATION STATUS
# =============================================================================
# PURPOSE: Check if user is currently logged in


def is_logged_in():
    """
    Check if a user is currently logged in.
    
    WHY: Streamlit automatically sets st.user.is_logged_in to True after successful login.
    """
    return st.user.is_logged_in

# =============================================================================
# SESSION MANAGEMENT
# =============================================================================
# PURPOSE: Functions for managing user session state

def clear_user_session():
    """
    Clear all user-related data from Streamlit's session state.
    
    WHY: When a user logs out, all their data must be removed from the app's memory.
    Without clearing session state, the next user might see the previous user's filters
    and selections, which is a privacy and security issue.
    
    HOW: Clears filter states, app states, and cached data. Streamlit re-runs the script
    on every interaction, so if session_state keys are not cleared, ghost filters from
    previous users may appear.
    """
    # Clear filter states
    from utils.filters import get_filter_session_keys
    filter_keys = get_filter_session_keys()
    for key in filter_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear app states
    app_keys = ['selected_offer', 'sports_data', 'active_tab', 'user_id']
    for key in app_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear any cached data
    for cache_attr in ('cache_data', 'cache_resource'):
        if hasattr(st, cache_attr):
            getattr(st, cache_attr).clear()

def handle_logout():
    """
    Perform a complete logout: clear data, log out, and refresh the UI.
    
    WHY: This does three things: clears session state, calls Streamlit's logout, and
    refreshes the page. All three steps are necessary for a complete logout to prevent
    data leakage.
    """
    clear_user_session()
    st.logout()
    st.rerun()

# =============================================================================
# USER INFORMATION
# =============================================================================
# PURPOSE: Functions for retrieving user information from authentication

def get_user_sub():
    """
    Get the unique user identifier (OIDC "sub" claim).
    
    WHY: "Sub" stands for "subject": it's a unique identifier provided by Google.
    This is part of the OIDC (OpenID Connect) standard. This ID is used to look up
    the user in the Supabase database and link their data.
    """
    return st.user.sub if is_logged_in() else None

def get_user_email():
    """
    Get the authenticated user's email address.
    
    WHY: This comes directly from Google's authentication system.
    """
    return st.user.email if is_logged_in() else None

def check_token_expiry():
    """
    Check if the user's authentication token has expired.
    
    WHY: When logging in, Google provides a token: a special code that proves authentication.
    Tokens expire for security reasons, so this must be checked periodically.
    """
    if not is_logged_in():
        return

    # Check if the identity provider returned expiration information
    expires_at = getattr(st.user, 'expires_at', None)
    if expires_at and datetime.now(timezone.utc) > expires_at:
        st.warning("Your session has expired. Please log in again.")
        handle_logout()

def get_user_info_dict():
    """
    Get all available user information from Streamlit's user object.
    
    WHY: Collects user information from Google authentication and packages it into a dictionary.
    Use direct access for required fields. Optional fields use getattr() with None as default
    to avoid errors.
    """
    if not is_logged_in():
        return None

    return {
        'sub': st.user.sub,
        'email': st.user.email,
        'name': st.user.name,
        'is_logged_in': True,
        'given_name': getattr(st.user, 'given_name', None),
        'family_name': getattr(st.user, 'family_name', None),
        'picture': getattr(st.user, 'picture', None)
    }

# =============================================================================
# DATABASE SYNCHRONIZATION
# =============================================================================
# PURPOSE: Functions for syncing user data with Supabase

def sync_user_to_supabase():
    """
    Save or update user information in the Supabase database.
    
    WHY: When a user logs in with Google, their information is retrieved and stored in the database.
    Storing user info in the database enables features like favorites and user profiles.
    
    HOW: This uses an "upsert" pattern (update if exists, insert if new). If name is not available,
    use email as fallback. Database operations can fail, so the result is checked.
    """
    from utils.db import create_or_update_user
    
    user_info = get_user_info_dict()
    if not user_info:
        return
    
    # Prepare user data with last_login timestamp
    user_data = {
        "sub": user_info["sub"],
        "email": user_info["email"],
        "name": user_info.get("name") or user_info["email"],
        "picture": user_info.get("picture"),
        "last_login": datetime.now().isoformat()
    }
    
    # Attempt to save to database
    if create_or_update_user(user_data) is None:
        st.warning("⚠️ Error synchronizing user")

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.

