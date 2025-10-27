"""
Terms of Service and Privacy Policy Acceptance Module
"""

import streamlit as st
from datetime import datetime
from data.supabase_client import get_supabase_client
from data.auth import get_user_sub


def check_tos_acceptance():
    """
    Check if the current user has accepted TOS and Privacy Policy
    Returns: (tos_accepted, privacy_accepted)
    """
    try:
        if not hasattr(st.user, 'is_logged_in') or not st.user.is_logged_in:
            return False, False
    except AttributeError:
        return False, False
    
    try:
        user_sub = get_user_sub()
        if not user_sub:
            return False, False
        
        client = get_supabase_client()
        user = client.table("users").select("tos_accepted, privacy_policy_accepted").eq("sub", user_sub).execute()
        
        if user.data and len(user.data) > 0:
            tos_accepted = user.data[0].get('tos_accepted', False)
            privacy_accepted = user.data[0].get('privacy_policy_accepted', False)
            return bool(tos_accepted), bool(privacy_accepted)
        
        return False, False
    except Exception as e:
        st.error(f"Fehler beim Prüfen der TOS-Akzeptanz: {e}")
        return False, False


def show_tos_acceptance_required():
    """
    Shows TOS and Privacy Policy acceptance UI
    Only shown for users who haven't accepted yet
    """
    st.title("🔐 Willkommen bei Unisport AI")
    
    st.markdown("""
    Bevor Sie fortfahren können, müssen Sie unseren Nutzungsbedingungen und Datenschutzerklärung zustimmen.
    """)
    
    # Read the TOS and Privacy Policy files
    try:
        with open('TERMS_OF_SERVICE.md', 'r', encoding='utf-8') as f:
            tos_content = f.read()
        with open('PRIVACY_POLICY.md', 'r', encoding='utf-8') as f:
            privacy_content = f.read()
    except Exception as e:
        st.error(f"Fehler beim Laden der Dokumente: {e}")
        st.stop()
    
    # Show TOS
    with st.expander("📋 Terms of Service (Nutzungsbedingungen)", expanded=False):
        st.markdown(tos_content)
    
    # Show Privacy Policy
    with st.expander("🔒 Privacy Policy (Datenschutzerklärung)", expanded=False):
        st.markdown(privacy_content)
    
    st.divider()
    
    # Acceptance checkboxes
    col1, col2 = st.columns(2)
    
    with col1:
        tos_accepted = st.checkbox(
            "✅ Ich habe die Terms of Service gelesen und akzeptiere diese",
            key="tos_checkbox",
            value=False
        )
    
    with col2:
        privacy_accepted = st.checkbox(
            "✅ Ich habe die Privacy Policy gelesen und akzeptiere diese",
            key="privacy_checkbox",
            value=False
        )
    
    st.divider()
    
    # Accept button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("📝 Akzeptieren und fortfahren", use_container_width=True, type="primary", disabled=not (tos_accepted and privacy_accepted)):
            if save_tos_acceptance():
                st.success("✅ Danke für Ihre Zustimmung!")
                st.rerun()
            else:
                st.error("❌ Fehler beim Speichern der Zustimmung. Bitte versuchen Sie es erneut.")
    
    # Info message
    if not (tos_accepted and privacy_accepted):
        st.info("💡 Bitte markieren Sie beide Checkboxen, um fortzufahren.")
    
    st.markdown("---")
    st.caption("Sie können Ihre Zustimmung jederzeit im Profil widerrufen. Ohne Zustimmung können Sie die Anwendung nicht nutzen.")


def save_tos_acceptance():
    """
    Save TOS and Privacy Policy acceptance to database
    Returns: True if successful, False otherwise
    """
    from data.auth import is_logged_in
    if not is_logged_in():
        return False
    
    try:
        user_sub = get_user_sub()
        if not user_sub:
            return False
        
        client = get_supabase_client()
        
        # Get tos_accepted checkbox value from session state
        tos_accepted = st.session_state.get("tos_checkbox", False)
        privacy_accepted = st.session_state.get("privacy_checkbox", False)
        
        if not (tos_accepted and privacy_accepted):
            return False
        
        # Update database
        update_data = {
            "tos_accepted": True,
            "privacy_policy_accepted": True,
            "tos_accepted_at": datetime.now().isoformat(),
            "privacy_policy_accepted_at": datetime.now().isoformat()
        }
        
        client.table("users").update(update_data).eq("sub", user_sub).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern der Zustimmung: {e}")
        return False


def revoke_tos_acceptance():
    """
    Allow users to revoke TOS/Privacy acceptance (deletes account)
    This is a nuclear option - the user will be logged out
    """
    from data.auth import is_logged_in
    if not is_logged_in():
        return False
    
    try:
        user_sub = get_user_sub()
        if not user_sub:
            return False
        
        client = get_supabase_client()
        
        # Delete the user from database
        client.table("users").delete().eq("sub", user_sub).execute()
        
        # Log out the user
        st.logout()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Widerrufen: {e}")
        return False

