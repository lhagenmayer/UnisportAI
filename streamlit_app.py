import streamlit as st
from data.auth import is_logged_in, show_login_page, render_user_menu, sync_user_to_supabase, check_token_expiry
from data.supabase_client import get_supabase_client

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
    client = get_supabase_client()
    sync_user_to_supabase(client)
except Exception as e:
    st.warning(f"Fehler bei der Benutzersynchronisation: {e}")

# Zeige Benutzermenü in der Sidebar
render_user_menu()

# Define the pages (only AFTER authentication)
overview_page = st.Page("pages/overview.py", title="Sports Overview", icon="🎯")
details_page = st.Page("pages/details.py", title="Course Dates", icon="📅")
athletes_page = st.Page("pages/athletes.py", title="Sportfreunde", icon="👥")
profile_page = st.Page("pages/profile.py", title="My Profile", icon="👤")

# Set up navigation
pages = [overview_page, details_page, athletes_page, profile_page]
pg = st.navigation(pages)

# Run the selected page
pg.run()