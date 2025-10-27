"""
Authentifizierungsmodul für Streamlit mit Google OIDC und Supabase
"""

import streamlit as st
from datetime import datetime, timezone
import json


def is_logged_in():
    """Safely check if user is logged in"""
    try:
        return hasattr(st.user, 'is_logged_in') and st.user.is_logged_in
    except AttributeError:
        return False


def check_auth():
    """Prüft die Authentifizierung und leitet zur Login-Seite um wenn nicht eingeloggt"""
    if not is_logged_in():
        show_login_page()
        st.stop()
    return True


def show_login_page():
    """Zeigt die Login-Seite mit Google OAuth"""
    
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
    
    # Main title
    st.title("Willkommen bei UnisportAI")
    st.markdown("### Entdecken Sie die Sportangebote der Universität St.Gallen")
    
    st.markdown("---")
    
    # Info section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🎯 Was ist UnisportAI?
        Eine intelligente Plattform zur Entdeckung und Verwaltung von Sportangeboten an der HSG.
        
        **Features:**
        - 📅 Übersicht aller Kurse und Termine
        - ⭐ Bewertungssystem für Kurse und Trainer
        - ❤️ Favoriten für Ihre Lieblingssportarten
        - 📆 Kalender-Integration (iCal)
        - 🔍 Erweiterte Such- und Filterfunktionen
        """)
    
    with col2:
        st.markdown("""
        #### 🔐 Sicherheit & Datenschutz
        Ihre Daten sind bei uns sicher:
        - ✅ Google OAuth Authentifizierung
        - ✅ GDPR-konforme Datenverarbeitung
        - ✅ Verschlüsselte Datenübertragung
        - ✅ Sichere Datenbank-Infrastruktur
        
        **Keine Passwörter nötig** - einfach mit Google anmelden!
        """)
    
    st.markdown("---")
    
    # Login button (centered and prominent)
    st.markdown("#### Anmeldung mit Google")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        login_button = st.button(
            "🔵 Mit Google anmelden",
            on_click=st.login, 
            args=["google"], 
            use_container_width=True, 
            type="primary",
            key="google_login_button"
        )
    
    st.markdown("---")
    
    # Additional info
    st.info("💡 Nach der Anmeldung werden Sie zur Google-Anmeldeseite weitergeleitet. Ihre Daten werden sicher verarbeitet und nur für diese Anwendung verwendet.")
    
    # Debug information (only if needed)
    if st.secrets.get("auth", {}).get("google", {}).get("client_id") == "YOUR_GOOGLE_CLIENT_ID_HERE":
        with st.expander("⚠️ Setup-Informationen für Entwickler", expanded=False):
            st.markdown("### Google OAuth Setup erforderlich")
            st.markdown("""
            1. Erstellen Sie OAuth-Anmeldedaten in der [Google Cloud Console](https://console.cloud.google.com/)
            2. Fügen Sie folgende Redirect URIs hinzu:
               - Lokal: `http://localhost:8501/oauth2callback`
               - Production: `https://unisportai.streamlit.app/oauth2callback`
            """)


def get_user_sub():
    """Gibt die eindeutige Benutzer-ID zurück (sub-Claim aus OIDC Token)"""
    if is_logged_in():
        return st.user.sub
    return None


def get_user_email():
    """Gibt die E-Mail-Adresse des eingeloggten Benutzers zurück"""
    if is_logged_in():
        return st.user.email
    return None


def check_token_expiry():
    """Prüft ob der Token abgelaufen ist und leitet zum Logout um"""
    if not is_logged_in():
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
    if is_logged_in():
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


def sync_user_to_supabase(supabase_client):
    """
    Synchronisiert den Benutzer mit Supabase
    
    Args:
        supabase_client: Supabase Client Instanz
        
    Returns:
        dict: Benutzerdaten aus Supabase
    """
    if not is_logged_in():
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

