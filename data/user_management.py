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
        if "is_admin" in st.session_state:
            del st.session_state["is_admin"]
        return False
    
    # Cache das Ergebnis im Session-State für Konsistenz über Seiten-Neuladungen
    if "is_admin" in st.session_state:
        return st.session_state["is_admin"]
    
    try:
        client = get_supabase_client()
        user_sub = get_user_sub()
        if not user_sub:
            st.session_state["is_admin"] = False
            return False
            
        user = client.table("users").select("role").eq("sub", user_sub).execute()
        if user.data and len(user.data) > 0:
            is_admin_result = user.data[0].get("role") == "admin"
            st.session_state["is_admin"] = is_admin_result
            return is_admin_result
        st.session_state["is_admin"] = False
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


def get_or_create_ical_feed_token(user_sub: str) -> str:
    """
    Holt oder erstellt einen persönlichen iCal Feed Token für den User.
    
    Args:
        user_sub: Sub des Users
        
    Returns:
        str: Token für die iCal Feed URL
    """
    try:
        client = get_supabase_client()
        
        # Hole aktuelles Profil
        result = client.table("users").select("id, ical_feed_token").eq("sub", user_sub).execute()
        
        if not result.data:
            return None
        
        user = result.data[0]
        token = user.get('ical_feed_token')
        
        # Erstelle Token falls nicht vorhanden
        if not token:
            import uuid
            token = str(uuid.uuid4())
            
            # Speichere Token in DB
            client.table("users").update({
                "ical_feed_token": token,
                "updated_at": datetime.now().isoformat()
            }).eq("sub", user_sub).execute()
        
        return token
    except Exception as e:
        st.error(f"Fehler beim Erstellen des Tokens: {e}")
        return None


def update_user_preferences(preferences: Dict[str, Any]) -> bool:
    """Aktualisiert die User-Präferenzen"""
    import json
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        client = get_supabase_client()
        # Konvertiere dict zu JSON String
        preferences_json = json.dumps(preferences)
        
        client.table("users").update({
            "preferences": preferences_json,
            "updated_at": datetime.now().isoformat()
        }).eq("sub", user_sub).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Präferenzen: {e}")
        return False


def get_user_favorites() -> list:
    """Lädt die Lieblings-Sportarten des aktuellen Users aus der Datenbank"""
    user_sub = get_user_sub()
    if not user_sub:
        return []
    
    try:
        client = get_supabase_client()
        user = client.table("users").select("id").eq("sub", user_sub).execute()
        
        if not user.data:
            return []
        
        user_id = user.data[0]['id']
        
        favorites = client.table("user_favorites").select("sportangebot_href").eq("user_id", user_id).execute()
        return [fav['sportangebot_href'] for fav in favorites.data]
    except Exception as e:
        st.error(f"Fehler beim Laden der Favoriten: {e}")
        return []


def update_user_favorites(favorite_hrefs: list) -> bool:
    """Aktualisiert die Lieblings-Sportarten des Users in der Datenbank"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        client = get_supabase_client()
        user = client.table("users").select("id").eq("sub", user_sub).execute()
        
        if not user.data:
            return False
        
        user_id = user.data[0]['id']
        
        # Lösche alle bestehenden Favoriten
        client.table("user_favorites").delete().eq("user_id", user_id).execute()
        
        # Füge neue Favoriten hinzu
        if favorite_hrefs:
            favorites_data = [
                {"user_id": user_id, "sportangebot_href": href}
                for href in favorite_hrefs
            ]
            client.table("user_favorites").insert(favorites_data).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Favoriten: {e}")
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
    from data.auth import is_logged_in
    if not is_logged_in():
        st.error("❌ Bitte melden Sie sich an, um Ihr Profil zu sehen.")
        return
    
    st.title("👤 Mein Profil")
    
    # Lade User-Profile
    profile = get_user_profile()
    if not profile:
        st.error("Profil nicht gefunden.")
        return
    
    # Layout mit Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Informationen", "⚙️ Präferenzen", "📅 Kalender", "🌐 Sichtbarkeit", "📊 Aktivität"])
    
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
        
        # Show TOS/Privacy acceptance status
        st.divider()
        st.subheader("📋 Legal & Compliance")
        
        tos_accepted = profile.get('tos_accepted', False)
        privacy_accepted = profile.get('privacy_policy_accepted', False)
        tos_accepted_at = profile.get('tos_accepted_at')
        privacy_accepted_at = profile.get('privacy_policy_accepted_at')
        
        col1, col2 = st.columns(2)
        
        with col1:
            if tos_accepted:
                st.success(f"✅ Terms of Service akzeptiert")
                if tos_accepted_at:
                    st.caption(f"Akzeptiert am: {tos_accepted_at[:10]}")
            else:
                st.warning("⚠️ Terms of Service nicht akzeptiert")
        
        with col2:
            if privacy_accepted:
                st.success(f"✅ Privacy Policy akzeptiert")
                if privacy_accepted_at:
                    st.caption(f"Akzeptiert am: {privacy_accepted_at[:10]}")
            else:
                st.warning("⚠️ Privacy Policy nicht akzeptiert")
        
        st.info("💡 Diese Zustimmungen sind erforderlich, um die Anwendung zu nutzen.")
        
        # Bio Editing
        st.divider()
        st.subheader("📝 Über mich")
        
        current_bio = profile.get('bio', '') or ''
        new_bio = st.text_area("Biographie", value=current_bio, max_chars=500, help="Beschreiben Sie sich selbst")
        
        if st.button("Bio speichern"):
            try:
                client = get_supabase_client()
                user_sub = get_user_sub()
                client.table("users").update({
                    "bio": new_bio,
                    "updated_at": datetime.now().isoformat()
                }).eq("sub", user_sub).execute()
                st.success("✅ Bio wurde aktualisiert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
        
    
    with tab2:
        st.subheader("Präferenzen")
        
        # Lade aktuelle Präferenzen (für andere Einstellungen)
        import json
        preferences_raw = profile.get('preferences', {}) or {}
        
        # Parse JSON falls es ein String ist
        if isinstance(preferences_raw, str):
            try:
                preferences = json.loads(preferences_raw)
            except json.JSONDecodeError:
                preferences = {}
        else:
            preferences = preferences_raw or {}
        
        # Lade Sportarten aus der Datenbank
        try:
            from data.supabase_client import get_offers_with_stats
            sportangebote = get_offers_with_stats()
            # Erstelle Mapping von Name zu href
            sportarten_dict = {sport['name']: sport['href'] for sport in sportangebote}
            sportarten_options = list(sportarten_dict.keys())
        except Exception as e:
            st.error(f"Fehler beim Laden der Sportarten: {e}")
            sportarten_dict = {}
            sportarten_options = ["Fitness", "Yoga", "Schwimmen", "Fußball", "Basketball"]
        
        # Lade Favoriten aus der Datenbank (als hrefs)
        current_favorite_hrefs = get_user_favorites()
        # Konvertiere hrefs zu Namen für das Multiselect
        current_favorite_names = [
            sport['name'] for sport in sportangebote 
            if sport['href'] in current_favorite_hrefs
        ] if sportangebote else []
        
        # Lieblings-Sportarten aus Datenbank (als Name)
        favorite_sports = st.multiselect(
            "Lieblings-Sportarten",
            options=sportarten_options,
            default=current_favorite_names
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
            # Speichere Favoriten als hrefs in der Datenbank
            favorite_hrefs = [sportarten_dict[sport] for sport in favorite_sports if sport in sportarten_dict]
            if update_user_favorites(favorite_hrefs):
                # Speichere andere Präferenzen
                new_preferences = {
                    'notifications': notifications,
                    'theme': theme
                }
                update_user_preferences(new_preferences)
                st.success("✅ Präferenzen wurden gespeichert!")
                st.rerun()
            else:
                st.error("Fehler beim Speichern der Favoriten")
    
    # New tab for calendar and additional settings
    with tab3:
        st.subheader("📅 Meine Kalender")
        
        # === iCal Feed für angemeldete Kurse ===
        st.markdown("#### 📅 iCal Feed für angemeldete Kurse")
        
        try:
            from data.ical_generator import generate_dynamic_ical_with_attendees
            
            # Get user sub and create/retrieve token
            user_sub = get_user_sub()
            ical_token = get_or_create_ical_feed_token(user_sub)
            
            if ical_token:
                # Get Supabase URL for Edge Function
                supabase_url = st.secrets.get("connections", {}).get("supabase", {}).get("url", "")
                project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "") if supabase_url else ""
                
                if project_ref:
                    # Generate personalized Feed URL with token
                    ical_feed_url = f"https://{project_ref}.supabase.co/functions/v1/ical-feed?token={ical_token}"
                    
                    st.text_input("🔗 Deine persönliche iCal Feed URL", ical_feed_url, disabled=True, label_visibility="visible")
                    st.caption("💡 Kopiere diese URL und füge sie zu deinem Kalender hinzu")
                    
                    # Generate iCal content for optional download
                    ical_content = generate_dynamic_ical_with_attendees()
                    st.download_button(
                        "📥 .ics als Fallback herunterladen",
                        data=ical_content,
                        file_name="unisport_meine_kurse.ics",
                        mime="text/calendar",
                        use_container_width=False
                    )
                    
                    st.markdown("""
                    **📋 So abonnierst du den Feed:**
                    - **Google Calendar**: Einstellungen → "Kalender hinzufügen" → "Von URL" 
                    - **Outlook**: Kalender → "Abonnieren" → "Von Internet"
                    - **Apple Calendar**: Kalender → "Abonnieren"
                    
                    **✨ Dynamischer Feed:** 
                    - Deine "going" Events werden **sofort** nach dem Klick hinzugefügt
                    - Freunde die später auch teilnehmen erscheinen **automatisch** als ATTENDEE
                    - Alle neuen Events syncen **automatisch** mit deinem Kalender
                    """)
                    
                    st.success("✅ Dein persönlicher iCal Feed ist bereit!")
                else:
                    st.warning("⚠️ Edge Function nicht verfügbar - nutze Download als Alternative")
                    # Fallback: Nur Download
                    ical_content = generate_dynamic_ical_with_attendees()
                    st.download_button(
                        "📥 .ics Datei herunterladen",
                        data=ical_content,
                        file_name="unisport_meine_kurse.ics",
                        mime="text/calendar"
                    )
            else:
                st.error("❌ Konnte keinen Token erstellen. Bitte versuche es erneut.")
        except Exception as e:
            st.error(f"Fehler beim Laden des iCal Feeds: {e}")
        
        st.divider()
        
        # === Privater Kalender URL Eingabe ===
        st.markdown("#### 🔗 Privater Kalender (optional)")
        st.info("💡 Füge hier die URL zu deinem externen Kalender hinzu.")
        
        # iCal URL Eingabe
        ical_url = profile.get('ical_url', '') or ''
        new_ical_url = st.text_input(
            "iCal URL",
            value=ical_url,
            help="Geben Sie die URL zu Ihrem privaten Kalender (iCal) ein",
            placeholder="https://example.com/calendar.ics"
        )
        
        if st.button("Kalender speichern"):
            try:
                client = get_supabase_client()
                user_sub = get_user_sub()
                client.table("users").update({
                    "ical_url": new_ical_url,
                    "updated_at": datetime.now().isoformat()
                }).eq("sub", user_sub).execute()
                st.success("✅ Kalender-URL wurde gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
    
    # Visibility settings tab
    with tab4:
        st.subheader("🌐 Profil-Sichtbarkeit")
        st.info("📌 Bestimmen Sie, ob andere Sportfreunde Ihr Profil sehen und Ihnen folgen können.")
        
        current_is_public = profile.get('is_public', False)
        is_public = st.checkbox(
            "Profil öffentlich machen",
            value=current_is_public,
            help="Wenn aktiviert, können andere Benutzer Ihr Profil auf der 'Sportfreunde'-Seite sehen und Ihnen folgen."
        )
        
        if st.button("Sichtbarkeit speichern"):
            try:
                client = get_supabase_client()
                user_sub = get_user_sub()
                client.table("users").update({
                    "is_public": is_public,
                    "updated_at": datetime.now().isoformat()
                }).eq("sub", user_sub).execute()
                st.success("✅ Sichtbarkeit wurde aktualisiert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
        
        st.divider()
        
        # Show friend count
        try:
            client = get_supabase_client()
            user_sub = get_user_sub()
            user_result = client.table("users").select("id").eq("sub", user_sub).execute()
            
            if user_result.data:
                user_id = user_result.data[0]['id']
                
                # Zähle Freundschaften
                friendships = client.table("user_friends").select("*").or_(
                    f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
                ).execute()
                
                friend_count = len(friendships.data) if friendships.data else 0
                st.metric("Freunde", friend_count)
        except Exception as e:
            pass
    
    # Activity tab
    with tab5:
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
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Benutzer: {e}")


def submit_sportangebot_rating(sportangebot_href: str, rating: int, comment: str = "") -> bool:
    """Speichert eine Bewertung für ein Sportangebot"""
    # Security validation
    from data.security import validate_rating, validate_comment, sanitize_html, rate_limit_check
    from data.auth import get_user_sub
    
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        # Rate limiting
        if not rate_limit_check("rating", user_sub, max_actions=20, time_window=300):
            st.error("Zu viele Bewertungen in kurzer Zeit. Bitte warten Sie einen Moment.")
            return False
        
        # Validate rating
        if not validate_rating(rating):
            st.error("Ungültige Bewertung")
            return False
        
        # Validate and sanitize comment
        if comment:
            is_valid, error_msg = validate_comment(comment)
            if not is_valid:
                st.error(error_msg)
                return False
            comment = sanitize_html(comment)
        
        import json
        client = get_supabase_client()
        
        # Hole user_id zuerst
        user_id = st.session_state.get("user_id")
        if not user_id:
            # Get user_id from sub
            user = client.table("users").select("id").eq("sub", user_sub).execute()
            if user.data:
                user_id = user.data[0]['id']
                st.session_state["user_id"] = user_id
            else:
                return False
        
        # Prüfe ob User bereits eine Bewertung hat
        existing = client.table("sportangebote_user_ratings").select("*").eq("user_id", user_id).eq("sportangebot_href", sportangebot_href).execute()
        
        rating_data = {
            "user_id": user_id,
            "sportangebot_href": sportangebot_href,
            "rating": rating,
            "comment": comment,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing.data:
            # Update existing rating
            client.table("sportangebote_user_ratings").update(rating_data).eq("user_id", user_id).eq("sportangebot_href", sportangebot_href).execute()
        else:
            # Create new rating
            rating_data["created_at"] = datetime.now().isoformat()
            client.table("sportangebote_user_ratings").insert(rating_data).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern der Bewertung: {e}")
        return False


def submit_trainer_rating(trainer_name: str, rating: int, comment: str = "") -> bool:
    """Speichert eine Bewertung für einen Trainer"""
    # Security validation
    from data.security import validate_rating, validate_comment, sanitize_html, rate_limit_check
    from data.auth import get_user_sub
    
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        # Rate limiting
        if not rate_limit_check("trainer_rating", user_sub, max_actions=20, time_window=300):
            st.error("Zu viele Bewertungen in kurzer Zeit. Bitte warten Sie einen Moment.")
            return False
        
        # Validate rating
        if not validate_rating(rating):
            st.error("Ungültige Bewertung")
            return False
        
        # Validate and sanitize comment
        if comment:
            is_valid, error_msg = validate_comment(comment)
            if not is_valid:
                st.error(error_msg)
                return False
            comment = sanitize_html(comment)
        
        client = get_supabase_client()
        
        # Get user_id
        user = client.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            return False
        
        user_id = user.data[0]['id']
        st.session_state["user_id"] = user_id
        
        # Prüfe ob User bereits eine Bewertung hat
        existing = client.table("trainer_user_ratings").select("*").eq("user_id", user_id).eq("trainer_name", trainer_name).execute()
        
        rating_data = {
            "user_id": user_id,
            "trainer_name": trainer_name,
            "rating": rating,
            "comment": comment,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing.data:
            # Update existing rating
            client.table("trainer_user_ratings").update(rating_data).eq("user_id", user_id).eq("trainer_name", trainer_name).execute()
        else:
            # Create new rating
            rating_data["created_at"] = datetime.now().isoformat()
            client.table("trainer_user_ratings").insert(rating_data).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern der Bewertung: {e}")
        return False

