"""Streamlit application entrypoint for UnisportAI.

This module initializes authentication, synchronizes the signed-in
user with Supabase and mounts the application's top-level pages.

It is intentionally thin: each page under the ``pages/`` folder is
responsible for rendering its UI and interacting with the data layer.
"""

import streamlit as st
from data.auth import is_logged_in, show_login_page, sync_user_to_supabase, check_token_expiry

# Note: Secrets validation happens in auth modules when needed
# This prevents errors on Streamlit Cloud during deployment

# Check authentication FIRST - this will stop if not logged in
if not is_logged_in():
    # User not logged in - show login page and stop
    show_login_page()
    st.stop()

# User is logged in - continue with the rest

# Prüfe Token-Ablauf
check_token_expiry()

# Synchronisiere Benutzer mit Supabase
try:
    sync_user_to_supabase()
except Exception as e:
    st.warning(f"Fehler bei der Benutzersynchronisation: {e}")

# Note: User info is rendered by each page:
# - Pages with render_filters_sidebar() (overview, details): user info included automatically
# - Pages without render_filters_sidebar() (athletes, profile): must call render_sidebar_user_info() manually

# Define the pages (only AFTER authentication)
overview_page = st.Page("pages/overview.py", title="Sports Overview", icon="🎯")
details_page = st.Page("pages/details.py", title="Course Dates", icon="📅")
athletes_page = st.Page("pages/athletes.py", title="Athletes", icon="🤝")
profile_page = st.Page("pages/profile.py", title="My Profile", icon="⚙️")

# Set up navigation
pages = [overview_page, details_page, athletes_page, profile_page]
pg = st.navigation(pages)

# Run the selected page
pg.run()