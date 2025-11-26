"""Authentication helpers for Streamlit using Google OIDC and Supabase.

This module provides functions to manage login, logout, redirect URIs
and synchronization of the authenticated user with Supabase. It is
designed to work in both local development and Streamlit Cloud
environments.
"""

import streamlit as st
from datetime import datetime, timezone
import json
import os


def _get_redirect_uri() -> str:
    """Return the appropriate OAuth redirect URI for the running environment.

    The function attempts to detect Streamlit Cloud vs local development
    and returns a suitable redirect URI accordingly.
    """
    # Check if running on Streamlit Cloud
    # Streamlit Cloud sets specific environment variables
    is_cloud = False
    
    # Method 1: Check for Streamlit Cloud environment variables
    if os.environ.get("STREAMLIT_SHARING_MODE"):
        is_cloud = True
    
    # Method 2: Check if we're accessing via streamlit.app domain
    try:
        # Check if we can detect the base URL
        if hasattr(st, 'get_option'):
            base_url = st.get_option("server.baseUrlPath") or ""
            if "streamlit.app" in base_url:
                is_cloud = True
    except Exception:
        pass
    
    # Method 3: Check environment variables that Streamlit Cloud sets
    if os.environ.get("STREAMLIT_SERVER_BASE_URL"):
        base_url = os.environ.get("STREAMLIT_SERVER_BASE_URL", "")
        if "streamlit.app" in base_url:
            is_cloud = True
    
    # Return appropriate URI
    if is_cloud:
        return "https://unisportai.streamlit.app/oauth2callback"
    else:
        # Local development - use localhost
        # Try to get port from config or default to 8501
        try:
            if hasattr(st, 'get_option'):
                port = st.get_option("server.port") or 8501
            else:
                port = int(os.environ.get("STREAMLIT_SERVER_PORT", "8501"))
        except Exception:
            port = 8501
        return f"http://localhost:{port}/oauth2callback"


def _update_redirect_uri_in_secrets():
    """Validate and return the expected redirect URI for the environment.

    The function compares the expected URI with the one present in
    ``st.secrets`` and warns if a likely mismatch is detected. It also
    sets an environment variable ``STREAMLIT_AUTH_REDIRECT_URI`` as a
    fallback for other OAuth helpers.
    """
    expected_uri = _get_redirect_uri()
    
    # Validate that secrets have the correct redirect_uri
    try:
        secrets_uri = st.secrets.get("auth", {}).get("redirect_uri", "")
        
        # Check if secrets URI matches expected URI
        if secrets_uri and secrets_uri != expected_uri:
            # Show a warning in development mode (local)
            if expected_uri.startswith("http://localhost"):
                # Running locally - secrets should have localhost
                if not secrets_uri.startswith("http://localhost"):
                    st.warning(
                        f"⚠️ Redirect URI mismatch detected!\n"
                        f"Expected (local): `{expected_uri}`\n"
                        f"Found in secrets: `{secrets_uri}`\n"
                        f"Please update `.streamlit/secrets.toml` to use localhost for local development."
                    )
            else:
                # Running in cloud - secrets should have cloud URL
                if secrets_uri.startswith("http://localhost"):
                    st.warning(
                        f"⚠️ Redirect URI mismatch detected!\n"
                        f"Expected (cloud): `{expected_uri}`\n"
                        f"Found in secrets: `{secrets_uri}`\n"
                        f"Please update Streamlit Cloud Secrets to use the cloud URL."
                    )
    except Exception:
        # If we can't read secrets, that's okay - they might not be set yet
        pass
    
    # Set environment variable (may be used by some OAuth implementations)
    os.environ["STREAMLIT_AUTH_REDIRECT_URI"] = expected_uri
    
    return expected_uri


def is_logged_in():
    """Return True when a user is currently authenticated in Streamlit.

    The function uses a defensive attribute access to avoid errors when
    executed in contexts without a Streamlit ``user`` object.
    """
    try:
        return hasattr(st.user, 'is_logged_in') and st.user.is_logged_in
    except AttributeError:
        return False


def clear_user_session():
    """Clear application session state related to the current user.

    This helper removes filter/navigation state, cached sports data and
    any stored user activities. It is intended to run during logout to
    ensure a clean session for the next user.
    """
    # Clear filter states
    filter_keys = ['intensity', 'focus', 'setting', 'location', 'weekday', 'offers', 
                   'search_text', 'date_start', 'date_end', 'start_time', 'end_time',
                   'hide_cancelled', 'show_upcoming_only']
    for key in filter_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear navigation states
    nav_keys = ['state_selected_offer', 'state_nav_offer_hrefs', 'state_nav_offer_name',
                'state_page2_multiple_offers', 'state_selected_offers_multiselect',
                'state_sports_data', 'state_nav_date']
    for key in nav_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear user activity states
    activity_keys = ['user_activities', 'user_id', '_prefs_loaded']
    for key in activity_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    # Clear any cached data
    if hasattr(st, 'cache_data'):
        st.cache_data.clear()
    if hasattr(st, 'cache_resource'):
        st.cache_resource.clear()


def handle_logout():
    """Perform logout with cleanup and rerun the Streamlit app.

    This function clears user state, calls ``st.logout()`` and triggers
    a rerun so the UI returns to an unauthenticated state.
    """
    clear_user_session()
    st.logout()
    st.rerun()


def check_auth():
    """Ensure the user is authenticated and show the login page otherwise.

    Returns True when authentication is valid. When the user is not
    logged in the function displays the login UI and stops Streamlit's
    execution flow.
    """
    if not is_logged_in():
        show_login_page()
        st.stop()
    return True


def show_login_page():
    """Render the application login page with Google OAuth instructions.

    The function displays helpful instructions and a prominent sign-in
    button. It also validates redirect URI configuration and warns when
    secrets appear misconfigured for the detected environment.
    """
    
    # Validate redirect URI configuration
    # Note: Streamlit's st.login() reads redirect_uri from secrets (immutable)
    # For local development: secrets.toml should have http://localhost:8501/oauth2callback
    # For production: Streamlit Cloud secrets should have https://unisportai.streamlit.app/oauth2callback
    expected_uri = _update_redirect_uri_in_secrets()
    
    # Beautiful header with university images
    st.markdown(
        """
        <div style="position: relative; height: 280px; border-radius: 10px; overflow: hidden; margin-bottom: 2rem;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 4px; height: 100%;">
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/5/c/csm_HSG_Bibliothek_1_182bdcd9cf.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/e/f/csm_HSG_Hauptgebaeude_2_e959f946be.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/d/2/csm_HSG_SQUARE_1_43e4002cea.jpg'); background-size:cover; background-position:center;"></div>
            <div style="background-image:url('https://www.unisg.ch/fileadmin/_processed_/3/c/csm_HSG_SQUARE_2_2426171a5d.jpg'); background-size:cover; background-position:center;"></div>
          </div>
          <div style="position:absolute; bottom:12px; left:12px; 
                      background: rgba(0,0,0,0.65); color:#fff; padding:12px 18px; border-radius: 8px; 
                      font-weight: 700; font-size: 24px; backdrop-filter: blur(4px);">
            🎯 UnisportAI
          </div>
          <div style="position:absolute; bottom:12px; right:12px; 
                      background: rgba(0,0,0,0.55); color:#fff; padding:6px 12px; border-radius: 6px; 
                      font-size: 12px; backdrop-filter: blur(4px);">
            © Universität St.Gallen (HSG)
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # Main title with modern styling
    st.title("🎯 Welcome to UnisportAI")
    st.caption("Discover and manage sports activities at the University of St.Gallen")
    
    st.divider()
    
    # Feature highlights in columns
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏃 What We Offer")
        st.markdown("""
        - **📅 Complete Overview** - All courses and dates in one place
        - **⭐ Rating System** - Review courses and trainers
        - **❤️ Personal Favorites** - Save your preferred activities
        """)
    
    with col2:
        st.markdown("### ✨ Smart Features")
        st.markdown("""
        - **🔍 Advanced Filters** - Find exactly what you need
        - **📆 Calendar Integration** - Sync with your calendar
        - **👥 Social Connection** - Connect with other athletes
        """)
    
    st.divider()
    
    # Login section with clean card design
    st.markdown("### 🔐 Get Started")
    st.caption("Sign in with your Google account - no password needed!")
    
    # Set redirect URI dynamically based on environment
    # Note: Streamlit's st.login() reads redirect_uri from secrets
    # Since secrets are immutable, we set it in secrets.toml for local dev
    # and in Streamlit Cloud secrets for production
    # This function call ensures we're using the correct one
    dynamic_redirect_uri = _update_redirect_uri_in_secrets()
    
    # Login button with prominent styling
    # st.login uses the redirect_uri from secrets automatically
    # We've set the environment variable as a fallback
    if st.button(
        "🔵 Sign in with Google",
        use_container_width=True, 
        type="primary",
        key="google_login_button"
    ):
        try:
            st.login("google")
        except Exception as e:
            st.error(f"Login failed: {e}")
            st.info("Please try again or contact support if the problem persists.")
    
    st.divider()
    
    # Security and privacy info
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info("🔒 Your data is processed securely and used only for this application")
    
    with col2:
        if st.button("📄 Privacy Policy", use_container_width=True):
            st.info("View our privacy policy for details on data handling")
    
    # Debug information (only if needed)
    if st.secrets.get("auth", {}).get("google", {}).get("client_id") == "YOUR_GOOGLE_CLIENT_ID_HERE":
        with st.expander("⚠️ Developer Setup Required", expanded=False):
            st.warning("**Google OAuth Configuration Needed**")
            st.markdown("""
            1. Create OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/)
            2. Add these redirect URIs:
               - Local: `http://localhost:8501/oauth2callback`
               - Production: `https://unisportai.streamlit.app/oauth2callback`
            3. Update `.streamlit/secrets.toml` with your credentials
            """)


def get_user_sub():
    """Return the OIDC ``sub`` claim for the authenticated user.

    Returns ``None`` when no user is logged in.
    """
    if is_logged_in():
        return st.user.sub
    return None


def get_user_email():
    """Return the authenticated user's email address or ``None``.
    """
    if is_logged_in():
        return st.user.email
    return None


def check_token_expiry():
    """Check whether the user's token has expired and force logout.

    If the token is expired the function triggers the logout workflow.
    It silently returns when no user is logged in.
    """
    if not is_logged_in():
        return

    try:
        # Extract expires_at from the st.user object if available
        if hasattr(st.user, 'expires_at') and st.user.expires_at:
            if datetime.now(timezone.utc) > st.user.expires_at:
                st.warning("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
                handle_logout()
    except Exception as e:
        st.error(f"Error checking token expiry: {e}")




def get_user_info_dict():
    """Return a dictionary with basic user information from Streamlit.

    Returns ``None`` when no user is authenticated.
    """
    if not is_logged_in():
        return None

    return {
        'sub': st.user.sub,
        'email': st.user.email,
        'name': st.user.name,
        'given_name': getattr(st.user, 'given_name', None),
        'family_name': getattr(st.user, 'family_name', None),
        'picture': getattr(st.user, 'picture', None),
        'is_logged_in': True
    }


def sync_user_to_supabase():
    """Synchronize the authenticated user record into Supabase.

    This creates or updates a user row in the ``users`` table using the
    information available from the Streamlit user object.
    """
    from data.supabase_client import create_or_update_user
    
    user_info = get_user_info_dict()
    if not user_info:
        return
    
    try:
        user_data = {
            "sub": user_info.get("sub"),
            "email": user_info.get("email"),
            "name": user_info.get("name", user_info.get("email")),
            "picture": user_info.get("picture"),
            "last_login": datetime.now().isoformat()
        }
        
        create_or_update_user(user_data)
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Synchronisieren des Benutzers: {e}")