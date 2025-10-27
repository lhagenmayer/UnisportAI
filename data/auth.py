"""
Authentifizierungsmodul für Streamlit mit Google OIDC und Supabase
"""

import streamlit as st
from datetime import datetime, timezone
import json


def check_auth():
    """Prüft die Authentifizierung und leitet zur Login-Seite um wenn nicht eingeloggt"""
    if not st.user.is_logged_in:
        show_login_page()
        st.stop()
    return True


def show_login_page():
    """Zeigt die Login-Seite mit Google OAuth"""
    st.title("🔐 Anmeldung")
    st.markdown("### Bitte melden Sie sich an, um fortzufahren")
    
    # Debug-Informationen anzeigen (nur wenn Client-ID nicht konfiguriert ist)
    if st.secrets.get("auth", {}).get("google", {}).get("client_id") == "YOUR_GOOGLE_CLIENT_ID_HERE":
        with st.expander("⚠️ Setup-Informationen", expanded=True):
            st.markdown("### Google OAuth Setup erforderlich")
            st.markdown("""
            1. Erstellen Sie OAuth-Anmeldedaten in der [Google Cloud Console](https://console.cloud.google.com/)
            2. Fügen Sie folgende Redirect URIs hinzu:
               - Für lokale Entwicklung: `http://localhost:8501/oauth2callback` bis Port 8510
               - Für Production: `https://unisportai.streamlit.app/oauth2callback`
            3. `redirect_uri` wird automatisch von Streamlit erkannt - NICHT in secrets.toml eintragen!
            """)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.button("🔵 Mit Google anmelden", on_click=st.login, args=["google"], use_container_width=True, type="primary")
    
    st.markdown("---")
    st.info("💡 Sie werden zur Google-Anmeldeseite weitergeleitet.")


def get_user_sub():
    """Gibt die eindeutige Benutzer-ID zurück (sub-Claim aus OIDC Token)"""
    if st.user.is_logged_in:
        return st.user.sub
    return None


def get_user_email():
    """Gibt die E-Mail-Adresse des eingeloggten Benutzers zurück"""
    if st.user.is_logged_in:
        return st.user.email
    return None


def check_token_expiry():
    """Prüft ob der Token abgelaufen ist und leitet zum Logout um"""
    if not st.user.is_logged_in:
        return
    
    # Prüfe ob exp-Claim vorhanden und abgelaufen
    try:
        # Extrahiere expires_at aus user object falls verfügbar
        if hasattr(st.user, 'expires_at') and st.user.expires_at:
            if datetime.now(timezone.utc) > st.user.expires_at:
                st.warning("Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.")
                st.logout()
                st.rerun()
    except Exception as e:
        st.error(f"Fehler beim Prüfen des Tokens: {e}")


def render_user_menu():
    """Rendert das Benutzermenü in der Sidebar"""
    if st.user.is_logged_in:
        st.sidebar.divider()
        
        with st.sidebar:
            st.markdown(f"### 👤 Benutzer")
            st.write(f"**{st.user.name}**")
            st.caption(st.user.email)
            
            # Links zu Profile und Admin
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📝 Profil", use_container_width=True):
                    st.switch_page("pages/profile.py")
            with col2:
                # Prüfe ob Admin
                from data.user_management import is_admin
                if is_admin():
                    if st.button("🔧 Admin", use_container_width=True):
                        st.switch_page("pages/admin.py")
            
            st.divider()
            
            if st.button("🚪 Abmelden", use_container_width=True):
                st.logout()
                st.rerun()


def get_user_info_dict():
    """Gibt die vollständigen Benutzerinformationen als Dictionary zurück"""
    if not st.user.is_logged_in:
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


def sync_user_to_supabase(supabase_client):
    """
    Synchronisiert den Benutzer mit Supabase
    
    Args:
        supabase_client: Supabase Client Instanz
        
    Returns:
        dict: Benutzerdaten aus Supabase
    """
    if not st.user.is_logged_in:
        return None
    
    user_sub = st.user.sub
    user_email = st.user.email
    user_name = st.user.name
    
    try:
        # Prüfe ob Benutzer bereits existiert (über sub)
        existing_user = supabase_client.table("users").select("*").eq("sub", user_sub).execute()
        
        if existing_user.data:
            # Benutzer existiert bereits - aktualisiere die Daten falls nötig
            user_data = existing_user.data[0]
            
            # Update falls sich etwas geändert hat
            update_data = {}
            if user_data.get('email') != user_email:
                update_data['email'] = user_email
            if user_data.get('name') != user_name:
                update_data['name'] = user_name
            if user_data.get('full_name') != user_name:  # Update deprecated full_name
                update_data['full_name'] = user_name
            
            if update_data:
                update_data['last_login'] = datetime.now().isoformat()
                supabase_client.table("users").update(update_data).eq("sub", user_sub).execute()
                return {**user_data, **update_data}
            
            # Aktualisiere last_login
            supabase_client.table("users").update({"last_login": datetime.now().isoformat()}).eq("sub", user_sub).execute()
            return user_data
        
        else:
            # Neuer Benutzer - erstelle Eintrag
            # Generiere UUID für die id (primary key)
            import uuid
            user_uuid = str(uuid.uuid4())
            
            new_user_data = {
                'id': user_uuid,
                'sub': user_sub,
                'email': user_email,
                'full_name': user_name,  # Maintain backward compatibility
                'name': user_name,
                'given_name': getattr(st.user, 'given_name', None),
                'family_name': getattr(st.user, 'family_name', None),
                'picture': getattr(st.user, 'picture', None),
                'role': 'user',  # Standard-Rolle
                'last_login': datetime.now().isoformat(),
                'provider': 'google',
                'preferences': '{}',  # Initialize empty JSON
                'is_active': True
            }
            
            result = supabase_client.table("users").insert(new_user_data).execute()
            return result.data[0] if result.data else new_user_data
            
    except Exception as e:
        st.error(f"Fehler bei der Benutzersynchronisation: {e}")
        return None

