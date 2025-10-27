import streamlit as st
from data.auth import check_auth, render_user_menu, sync_user_to_supabase, check_token_expiry
from data.supabase_client import get_supabase_client

# Prüfe Authentifizierung
check_auth()

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

# Define the pages
overview_page = st.Page("pages/overview.py", title="Sports Overview", icon="🎯")
details_page = st.Page("pages/details.py", title="Course Dates", icon="📅")
calendar_page = st.Page("pages/calendar.py", title="Calendar", icon="📆")
profile_page = st.Page("pages/profile.py", title="My Profile", icon="👤")

# Add admin page only if user is admin
from data.user_management import is_admin
pages = [overview_page, details_page, calendar_page, profile_page]

if is_admin():
    admin_page = st.Page("pages/admin.py", title="Admin Panel", icon="🔧")
    pages.append(admin_page)

# Set up navigation
pg = st.navigation(pages)

# Run the selected page
pg.run()