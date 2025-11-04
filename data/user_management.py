"""
Erweiterte User-Management Features
Inspiriert von Streamlit-Authenticator, aber mit OIDC + Supabase
"""

import streamlit as st
from datetime import datetime
from typing import Optional, Dict, Any
from data.auth import get_user_sub
from data.supabase_client import (
    get_user_profile as db_get_user_profile,
    update_user_preferences as db_update_user_preferences,
    save_filter_preferences as db_save_filter_preferences,
    get_user_favorites as db_get_user_favorites,
    update_user_favorites as db_update_user_favorites,
    submit_sport_rating as db_submit_sport_rating,
    submit_trainer_rating as db_submit_trainer_rating
)


def get_user_profile(user_sub: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Holt das vollständige User-Profile aus der Datenbank"""
    if not user_sub:
        user_sub = get_user_sub()
        if not user_sub:
            return None
    
    return db_get_user_profile(user_sub)


def update_user_preferences(preferences: Dict[str, Any]) -> bool:
    """Aktualisiert die User-Präferenzen"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    return db_update_user_preferences(user_sub, preferences)


def _map_weekdays_ui_to_codes(weekdays_en: list) -> list:
    """Mapt UI-Strings ('Monday'..'Sunday') auf weekday_type Codes ('mon'..'sun')."""
    en_to_code = {
        'Monday': 'mon',
        'Tuesday': 'tue',
        'Wednesday': 'wed',
        'Thursday': 'thu',
        'Friday': 'fri',
        'Saturday': 'sat',
        'Sunday': 'sun',
    }
    return [en_to_code.get(w, w) for w in (weekdays_en or [])]


def save_sidebar_preferences(
    intensities: list | None,
    focus: list | None,
    settings: list | None,
    locations: list | None,
    weekdays_en: list | None,
) -> bool:
    """Speichert die aktuellen Sidebar-Filter als Standard in public.users."""
    user_sub = get_user_sub()
    if not user_sub:
        return False

    try:
        success = db_save_filter_preferences(
            user_sub, 
            intensities, 
            focus, 
            settings, 
            locations, 
            weekdays_en
        )
        if not success:
            st.error(f"Fehler beim Speichern der Sidebar-Defaults")
        return success
    except Exception as e:
        st.error(f"Fehler beim Speichern der Sidebar-Defaults: {e}")
        return False


def get_user_favorites() -> list:
    """Lädt die Lieblings-Sportarten des aktuellen Users aus der Datenbank"""
    user_sub = get_user_sub()
    if not user_sub:
        return []
    
    try:
        return db_get_user_favorites(user_sub)
    except Exception as e:
        st.error(f"Fehler beim Laden der Favoriten: {e}")
        return []


def update_user_favorites(favorite_hrefs: list) -> bool:
    """Aktualisiert die Lieblings-Sportarten des Users in der Datenbank"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        return db_update_user_favorites(user_sub, favorite_hrefs)
    except Exception as e:
        st.error(f"Fehler beim Aktualisieren der Favoriten: {e}")
        return False


def log_user_activity(activity_type: str, details: Optional[Dict] = None):
    """Loggt User-Aktivitäten (für zukünftiges Activity-Log)"""
    from data.state_manager import add_user_activity
    
    user_sub = get_user_sub()
    if not user_sub:
        return
    
    activity = {
        "user_sub": user_sub,
        "activity_type": activity_type,
        "details": details or {},
        "timestamp": datetime.now().isoformat()
    }
    
    # Use centralized state management
    add_user_activity(activity)


def submit_sportangebot_rating(sportangebot_href: str, rating: int, comment: str = "") -> bool:
    """Speichert eine Bewertung für ein Sportangebot"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        # Basic validation
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            st.error("Ungültige Bewertung (1-5)")
            return False
        
        # Limit comment length
        if comment and len(comment) > 2000:
            st.error("Kommentar zu lang (max. 2000 Zeichen)")
            return False
        
        return db_submit_sport_rating(user_sub, sportangebot_href, rating, comment)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Bewertung: {e}")
        return False


def submit_trainer_rating(trainer_name: str, rating: int, comment: str = "") -> bool:
    """Speichert eine Bewertung für einen Trainer"""
    user_sub = get_user_sub()
    if not user_sub:
        return False
    
    try:
        # Basic validation
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            st.error("Ungültige Bewertung (1-5)")
            return False
        
        # Limit comment length
        if comment and len(comment) > 2000:
            st.error("Kommentar zu lang (max. 2000 Zeichen)")
            return False
        
        return db_submit_trainer_rating(user_sub, trainer_name, rating, comment)
    except Exception as e:
        st.error(f"Fehler beim Speichern der Bewertung: {e}")
        return False

