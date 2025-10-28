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

# Check TOS and Privacy Policy acceptance (only for logged-in users)
from data.tos_acceptance import check_tos_acceptance, show_tos_acceptance_required

tos_accepted, privacy_accepted = check_tos_acceptance()

# If user hasn't accepted both, show acceptance UI
if not (tos_accepted and privacy_accepted):
    show_tos_acceptance_required()
    st.stop()

# Zeige Benutzermenü in der Sidebar
render_user_menu()

# Define the pages (only AFTER authentication and TOS acceptance)
from data.user_management import is_admin

overview_page = st.Page("pages/overview.py", title="Sports Overview", icon="🎯")
details_page = st.Page("pages/details.py", title="Course Dates", icon="📅")
calendar_page = st.Page("pages/calendar.py", title="Calendar", icon="📆")
athletes_page = st.Page("pages/athletes.py", title="Sportfreunde", icon="👥")
profile_page = st.Page("pages/profile.py", title="My Profile", icon="👤")

# Add admin page only if user is admin
pages = [overview_page, details_page, calendar_page, athletes_page, profile_page]

if is_admin():
    admin_page = st.Page("pages/admin.py", title="Admin Panel", icon="🔧")
    pages.append(admin_page)

# Set up navigation
pg = st.navigation(pages)

# Run the selected page
pg.run()