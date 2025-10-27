"""
State Manager für Streamlit App

Verwaltet den session_state für die Kommunikation zwischen den Seiten.
"""

import streamlit as st

# Global filter state keys - using state_filter_* prefix
FILTER_KEYS = {
    'show_upcoming_only': 'state_filter_upcoming_only',
    'search_text': 'state_filter_search_text',
    'intensity': 'state_filter_intensity',
    'focus': 'state_filter_focus',
    'setting': 'state_filter_setting',
    'offers': 'state_filter_offers',
    'hide_cancelled': 'state_filter_hide_cancelled',
    'date_start': 'state_filter_date_start',
    'date_end': 'state_filter_date_end',
    'location': 'state_filter_location',
    'weekday': 'state_filter_weekday',
    'time_start': 'state_filter_time_start',
    'time_end': 'state_filter_time_end',
}

def get_filter_state(filter_name: str, default=None):
    """Gets a filter state"""
    key = FILTER_KEYS.get(filter_name, f'filter_{filter_name}')
    return st.session_state.get(key, default)

def set_filter_state(filter_name: str, value):
    """Sets a filter state"""
    key = FILTER_KEYS.get(filter_name, f'filter_{filter_name}')
    st.session_state[key] = value

def clear_filter_states():
    """Clears all filter states"""
    for key in FILTER_KEYS.values():
        if key in st.session_state:
            del st.session_state[key]

def init_multiple_offers_state(offer_hrefs: list, multiselect_key: str = "state_selected_offers_multiselect"):
    """Initializes state for multiple offers"""
    if multiselect_key not in st.session_state or not st.session_state.get(multiselect_key):
        st.session_state[multiselect_key] = offer_hrefs.copy()

def get_multiselect_value(multiselect_key: str = "state_selected_offers_multiselect", default=None):
    """Gets the current multiselect value"""
    return st.session_state.get(multiselect_key, default)

def set_multiselect_value(multiselect_key: str, value):
    """Sets the multiselect value"""
    st.session_state[multiselect_key] = value

def get_selected_offers_for_page2(multiple_offers_key: str = "state_page2_multiple_offers", 
                                   multiselect_key: str = "state_selected_offers_multiselect",
                                   default=None):
    """Gets selected offers for page_2, either from multiselect or all if not set"""
    
    # Zuerst prüfen, ob Multiselect-Wert vorhanden ist
    multiselect_value = get_multiselect_value(multiselect_key)
    if multiselect_value is not None and len(multiselect_value) > 0:
        return multiselect_value
    
    # Fallback auf state_page2_multiple_offers
    return st.session_state.get(multiple_offers_key, default)

def store_page_3_to_page_2_filters(date_str, time_obj, offer_name, all_offer_hrefs):
    """Stores filter information from page_3 for page_2"""
    st.session_state['state_nav_date'] = date_str
    st.session_state['state_nav_time'] = time_obj
    st.session_state['state_nav_offer_name'] = offer_name
    st.session_state['state_nav_offer_hrefs'] = all_offer_hrefs
    st.session_state['state_page2_multiple_offers'] = all_offer_hrefs

def clear_page_3_filters():
    """Removes filters from page_3"""
    
    keys_to_remove = [
        'state_nav_date',
        'state_nav_time',
        'state_nav_offer_name',
        'state_nav_offer_hrefs'
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]

