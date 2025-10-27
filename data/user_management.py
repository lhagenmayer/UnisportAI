"""
Erweiterte User-Management Features
Inspiriert von Streamlit-Authenticator, aber mit OIDC + Supabase
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any
from data.auth import get_user_sub, get_user_email
from data.supabase_client import get_supabase_client


def is_admin() -> bool:
    """Prüft ob der aktuelle User ein Admin ist"""
    if not st.user.is_logged_in:
        return False
    
    try:
        client = get_supabase_client()
        user_sub = get_user_sub()
        if not user_sub:
            return False
            
        user = client.table("users").select("role").eq("sub", user_sub).execute()
        if user.data and len(user.data) > 0:
            return user.data[0].get("role") == "admin"
        return False
    except Exception:
        return False


def get_user_profile(user_sub: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Holt das vollständige User-Profile aus der Datenbank"""
    if not user_sub:
        user_sub = get_user_sub()
        if not user_sub:
            return None
    
    try:
        client = get_supabase_client()
        result = client.table("users").select("*").eq("sub", user_sub).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Fehler beim Laden des Profiles: {e}")
        return None


def update_user_preferences(preferences: Dict[str, Any]) -> bool:
    """Aktualisiert die User-Präferenzen"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        client = get_supabase_client()
        client.table("users").update({
            "preferences": preferences,
            "updated_at": datetime.now().isoformat()
        }).eq("sub", user_sub).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Präferenzen: {e}")
        return False


def log_user_activity(activity_type: str, details: Optional[Dict] = None):
    """Loggt User-Aktivitäten (für zukünftiges Activity-Log)"""
    user_sub = get_user_sub()
    if not user_sub:
        return
    
    # Könnte eine separate activity_log Tabelle nutzen
    activity = {
        "user_sub": user_sub,
        "activity_type": activity_type,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    
    # Save to session state for now
    if "user_activities" not in st.session_state:
        st.session_state.user_activities = []
    st.session_state.user_activities.append(activity)


def render_user_profile_page():
    """Render eine User-Profile Seite"""
    if not st.user.is_logged_in:
        st.error("❌ Bitte melden Sie sich an, um Ihr Profil zu sehen.")
        return
    
    st.title("👤 Mein Profil")
    
    # Lade User-Profile
    profile = get_user_profile()
    if not profile:
        st.error("Profil nicht gefunden.")
        return
    
    # Layout mit Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Informationen", "⚙️ Präferenzen", "📊 Aktivität"])
    
    with tab1:
        st.subheader("Benutzerinformationen")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Name:** {profile.get('name', 'N/A')}")
            st.markdown(f"**E-Mail:** {profile.get('email', 'N/A')}")
            st.markdown(f"**Rolle:** {profile.get('role', 'user').capitalize()}")
        
        with col2:
            if profile.get('picture'):
                st.image(profile['picture'], width=150)
            st.markdown(f"**Registriert:** {profile.get('created_at', 'N/A')[:10]}")
            st.markdown(f"**Letzter Login:** {profile.get('last_login', 'N/A')[:10] if profile.get('last_login') else 'N/A'}")
    
    with tab2:
        st.subheader("Präferenzen")
        
        # Lade aktuelle Präferenzen
        preferences = profile.get('preferences', {}) or {}
        
        # Beispiel-Präferenzen
        favorite_sports = st.multiselect(
            "Lieblings-Sportarten",
            options=["Fitness", "Yoga", "Schwimmen", "Fußball", "Basketball"],
            default=preferences.get('favorite_sports', [])
        )
        
        notifications = st.checkbox(
            "E-Mail Benachrichtigungen",
            value=preferences.get('notifications', True)
        )
        
        theme = st.selectbox(
            "Design-Theme",
            options=["light", "dark", "auto"],
            index=["light", "dark", "auto"].index(preferences.get('theme', 'auto'))
        )
        
        if st.button("Präferenzen speichern"):
            new_preferences = {
                'favorite_sports': favorite_sports,
                'notifications': notifications,
                'theme': theme
            }
            if update_user_preferences(new_preferences):
                st.success("✅ Präferenzen wurden gespeichert!")
                st.rerun()
    
    with tab3:
        st.subheader("Meine Aktivität")
        
        # Zeige Session-Aktivitäten
        if "user_activities" in st.session_state:
            activities = st.session_state.user_activities
            for activity in activities[-10:]:  # Letzte 10 Aktivitäten
                st.text(f"{activity.get('timestamp', '')}: {activity.get('activity_type', '')}")
        else:
            st.info("Keine Aktivitäten aufgezeichnet.")


def render_admin_panel():
    """Render ein Admin-Panel für User-Verwaltung"""
    if not is_admin():
        st.error("❌ Sie haben keine Berechtigung für diese Seite.")
        return
    
    st.title("🔧 Admin Panel")
    
    try:
        client = get_supabase_client()
        users = client.table("users").select("*").order("created_at", desc=True).execute()
        
        if not users.data:
            st.info("Keine Benutzer gefunden.")
            return
        
        st.subheader(f"Benutzerverwaltung ({len(users.data)} Benutzer)")
        
        # Tabelle mit allen Usern
        for user in users.data:
            with st.expander(f"👤 {user.get('name', 'Unknown')} ({user.get('email')})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**ID:** `{user.get('id')}`")
                    st.markdown(f"**Sub:** `{user.get('sub')}`")
                    st.markdown(f"**Rolle:** {user.get('role')}")
                    st.markdown(f"**Registriert:** {user.get('created_at')}")
                    st.markdown(f"**Letzter Login:** {user.get('last_login', 'Nie')}")
                    st.markdown(f"**Aktiv:** {'✅' if user.get('is_active', True) else '❌'}")
                
                with col2:
                    # Role management
                    new_role = st.selectbox(
                        "Rolle ändern",
                        options=["user", "admin"],
                        index=0 if user.get('role') == 'user' else 1,
                        key=f"role_{user['id']}"
                    )
                    
                    if new_role != user.get('role'):
                        if st.button("💾 Speichern", key=f"save_role_{user['id']}"):
                            try:
                                client.table("users").update({
                                    "role": new_role
                                }).eq("id", user['id']).execute()
                                st.success("Rolle aktualisiert!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler: {e}")
                    
                    # Status toggle
                    is_active = user.get('is_active', True)
                    toggle = st.checkbox(
                        "Aktiv",
                        value=is_active,
                        key=f"active_{user['id']}"
                    )
                    
                    if toggle != is_active:
                        try:
                            client.table("users").update({
                                "is_active": toggle
                            }).eq("id", user['id']).execute()
                            st.success("Status aktualisiert!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Fehler: {e}")
        
        # Statistiken
        st.subheader("📊 Statistiken")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Gesamt Benutzer", len(users.data))
        with col2:
            active_users = sum(1 for u in users.data if u.get('is_active', True))
            st.metric("Aktive Benutzer", active_users)
        with col3:
            admins = sum(1 for u in users.data if u.get('role') == 'admin')
            st.metric("Admins", admins)
        with col4:
            recent_logins = sum(1 for u in users.data if u.get('last_login'))
            st.metric("Mit Login", recent_logins)
            
    except Exception as e:
        st.error(f"Fehler beim Laden der Benutzer: {e}")

