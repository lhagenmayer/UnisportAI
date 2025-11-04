import streamlit as st
from typing import Any, List, Optional, Dict
import time


def _map_weekdays_db_to_ui(weekday_codes: List[str]) -> List[str]:
    """Maps weekday_type enum codes to UI strings used in filters.py/shared_sidebar.py"""
    code_to_en = {
        'mon': 'Monday',
        'tue': 'Tuesday',
        'wed': 'Wednesday',
        'thu': 'Thursday',
        'fri': 'Friday',
        'sat': 'Saturday',
        'sun': 'Sunday',
    }
    return [code_to_en.get(code, code) for code in (weekday_codes or [])]


def _ensure_preferences_loaded():
    """Loads user preferences from DB once into session_state for filter defaults."""
    if st.session_state.get("_prefs_loaded", False):
        return

    try:
        # Load user profile
        from data.auth import get_user_sub
        from data.supabase_client import get_user_from_db, get_offers_with_stats
        from data.user_management import get_user_favorites

        user_sub = get_user_sub()
        if not user_sub:
            st.session_state["_prefs_loaded"] = True
            return

        profile = get_user_from_db(user_sub)
        if not profile:
            st.session_state["_prefs_loaded"] = True
            return

        # Map preferred columns to sidebar filter keys
        preferred_intensities = profile.get('preferred_intensities') or []
        preferred_focus = profile.get('preferred_focus') or []
        preferred_settings = profile.get('preferred_settings') or []
        favorite_location_names = profile.get('favorite_location_names') or []
        preferred_weekdays_codes = profile.get('preferred_weekdays') or []

        # Write defaults only if not already set in session
        if 'intensity' not in st.session_state:
            st.session_state['intensity'] = preferred_intensities
        if 'focus' not in st.session_state:
            st.session_state['focus'] = preferred_focus
        if 'setting' not in st.session_state:
            st.session_state['setting'] = preferred_settings
        if 'location' not in st.session_state:
            st.session_state['location'] = favorite_location_names
        if 'weekday' not in st.session_state:
            st.session_state['weekday'] = _map_weekdays_db_to_ui(preferred_weekdays_codes)

        # Preload favorite sports into 'offers' by names (sidebar expects names)
        if 'offers' not in st.session_state:
            try:
                favorite_hrefs = get_user_favorites()  # list of hrefs
                if favorite_hrefs:
                    offers = get_offers_with_stats() or []
                    href_to_name = {o.get('href'): o.get('name') for o in offers}
                    favorite_names = [href_to_name[h] for h in favorite_hrefs if h in href_to_name]
                    if favorite_names:
                        st.session_state['offers'] = favorite_names
            except Exception as e:
                # Log but don't fail - favorites are optional
                import logging
                logging.warning(f"Failed to load favorite offers: {e}")

        st.session_state["_prefs_loaded"] = True
        
    except Exception as e:
        # Log error but mark as loaded to prevent repeated attempts
        import logging
        logging.error(f"Error loading user preferences: {e}")
        st.session_state["_prefs_loaded"] = True


def get_filter_state(key: str, default: Any) -> Any:
    """Returns filter value from session_state, preloading user prefs once."""
    _ensure_preferences_loaded()
    return st.session_state.get(key, default)


def set_filter_state(key: str, value: Any):
    """Sets a filter value into session_state."""
    st.session_state[key] = value


def init_multiple_offers_state(default_hrefs: List[str], state_key: str):
    """Initializes state for multiple offers selection, if missing."""
    if state_key not in st.session_state:
        st.session_state[state_key] = list(default_hrefs or [])


# === Navigation State Management ===

def get_selected_offer() -> Optional[Dict]:
    """Gets the currently selected offer from state."""
    return st.session_state.get('state_selected_offer')


def set_selected_offer(offer: Dict):
    """Sets the currently selected offer in state."""
    st.session_state['state_selected_offer'] = offer


def clear_selected_offer():
    """Clears the currently selected offer from state."""
    if 'state_selected_offer' in st.session_state:
        del st.session_state['state_selected_offer']


def has_selected_offer() -> bool:
    """Checks if an offer is currently selected."""
    return 'state_selected_offer' in st.session_state


def get_nav_offer_hrefs() -> Optional[List[str]]:
    """Gets navigation offer hrefs from state."""
    return st.session_state.get('state_nav_offer_hrefs')


def set_nav_offer_hrefs(hrefs: List[str]):
    """Sets navigation offer hrefs in state."""
    st.session_state['state_nav_offer_hrefs'] = hrefs


def clear_nav_offer_hrefs():
    """Clears navigation offer hrefs from state."""
    if 'state_nav_offer_hrefs' in st.session_state:
        del st.session_state['state_nav_offer_hrefs']


def get_nav_offer_name() -> Optional[str]:
    """Gets navigation offer name from state."""
    return st.session_state.get('state_nav_offer_name')


def clear_nav_offer_name():
    """Clears navigation offer name from state."""
    if 'state_nav_offer_name' in st.session_state:
        del st.session_state['state_nav_offer_name']


def get_multiple_offers() -> Optional[List[str]]:
    """Gets multiple offers from state."""
    return st.session_state.get('state_page2_multiple_offers')


def set_multiple_offers(offers: List[str]):
    """Sets multiple offers in state."""
    st.session_state['state_page2_multiple_offers'] = offers


def has_multiple_offers() -> bool:
    """Checks if multiple offers are set in state."""
    return 'state_page2_multiple_offers' in st.session_state


def clear_multiple_offers():
    """Clears multiple offers from state."""
    if 'state_page2_multiple_offers' in st.session_state:
        del st.session_state['state_page2_multiple_offers']


def get_selected_offers_multiselect() -> Optional[List[str]]:
    """Gets selected offers from multiselect state."""
    return st.session_state.get('state_selected_offers_multiselect')


def clear_selected_offers_multiselect():
    """Clears selected offers multiselect from state."""
    if 'state_selected_offers_multiselect' in st.session_state:
        del st.session_state['state_selected_offers_multiselect']


def get_selected_offers_for_page2() -> List[str]:
    """Gets selected offers for page 2 (details page)."""
    # Try multiselect state first
    selected = get_selected_offers_multiselect()
    if selected:
        return selected
    
    # Fallback to multiple offers state
    multiple = get_multiple_offers()
    if multiple:
        return multiple
    
    return []


def get_sports_data() -> Optional[List[Dict]]:
    """Gets sports data from state."""
    return st.session_state.get('state_sports_data')


def set_sports_data(data: List[Dict]):
    """Sets sports data in state."""
    st.session_state['state_sports_data'] = data


def get_nav_date() -> Optional[str]:
    """Gets navigation date from state."""
    return st.session_state.get('state_nav_date')


def set_nav_date(date: str):
    """Sets navigation date in state."""
    st.session_state['state_nav_date'] = date


def clear_nav_date():
    """Clears navigation date from state."""
    if 'state_nav_date' in st.session_state:
        del st.session_state['state_nav_date']


# === User Activity State Management ===

def get_user_activities() -> List[Dict]:
    """Gets user activities from state."""
    if "user_activities" not in st.session_state:
        st.session_state.user_activities = []
    return st.session_state.user_activities


def add_user_activity(activity: Dict):
    """Adds a user activity to state."""
    if "user_activities" not in st.session_state:
        st.session_state.user_activities = []
    st.session_state.user_activities.append(activity)


def clear_user_activities():
    """Clears user activities from state."""
    st.session_state.user_activities = []


def get_user_id() -> Optional[int]:
    """Gets user ID from state."""
    return st.session_state.get("user_id")


def set_user_id(user_id: int):
    """Sets user ID in state."""
    st.session_state["user_id"] = user_id


def clear_user_id():
    """Clears user ID from state."""
    if "user_id" in st.session_state:
        del st.session_state["user_id"]


