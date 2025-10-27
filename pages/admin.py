import streamlit as st
from data.user_management import render_admin_panel, is_admin

# Prüfe Admin-Berechtigung
if not st.user.is_logged_in:
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

if not is_admin():
    st.error("❌ Sie haben keine Berechtigung für diese Seite.")
    st.stop()

# Zeige Admin Panel
render_admin_panel()

