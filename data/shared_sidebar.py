"""
Shared Sidebar for all pages
Clean and organized filter interface following Streamlit best practices
"""
import streamlit as st
from datetime import datetime, time
from data.state_manager import (
    get_filter_state, set_filter_state, init_multiple_offers_state,
    get_sports_data, get_selected_offer, has_multiple_offers, get_nav_date
)
from data.user_management import save_sidebar_preferences


def render_shared_sidebar(filter_type='main', sports_data=None, events=None):
    """
    Renders a clean, organized sidebar with collapsible filter sections.
    
    Args:
        filter_type: 'main' or 'detail' - determines which filters are shown
        sports_data: Data for main page filters
        events: Event data for detail filters
    """
    
    with st.sidebar:
        st.title("🔍 Filters")
        
        # Quick search at the top (always visible)
        search_text = st.text_input(
            "🔎 Quick Search",
            value=get_filter_state('search_text', ''),
            placeholder="Search activities...",
            key="global_search_text",
            label_visibility="collapsed"
        )
        set_filter_state('search_text', search_text)
        
        # Load sports data if needed
        if not sports_data:
            sports_data = get_sports_data()
        
        # Load events if needed
        if not events and filter_type == 'detail':
            from data.supabase_client import get_all_events
            events = get_all_events()
        
        # === ACTIVITY FILTERS (Main Page) ===
        if sports_data and len(sports_data) > 0:
            with st.expander("🎯 Activity Type", expanded=True):
                # Extract unique values
                intensities = sorted(set([item.get('intensity') for item in sports_data if item.get('intensity')]))
                all_focuses = set()
                all_settings = set()
                for item in sports_data:
                    if item.get('focus'):
                        all_focuses.update(item.get('focus'))
                    if item.get('setting'):
                        all_settings.update(item.get('setting'))
                
                focuses = sorted(list(all_focuses))
                settings = sorted(list(all_settings))
                
                # Intensity
                if intensities:
                    selected_intensity = st.multiselect(
                        "💪 Intensity",
                        options=intensities,
                        default=get_filter_state('intensity', []),
                        key="global_intensity"
                    )
                    set_filter_state('intensity', selected_intensity)
                
                # Focus
                if focuses:
                    selected_focus = st.multiselect(
                        "🎯 Focus",
                        options=focuses,
                        default=get_filter_state('focus', []),
                        key="global_focus"
                    )
                    set_filter_state('focus', selected_focus)
                
                # Setting
                if settings:
                    selected_setting = st.multiselect(
                        "🏠 Setting",
                        options=settings,
                        default=get_filter_state('setting', []),
                        key="global_setting"
                    )
                    set_filter_state('setting', selected_setting)
                
                # Show upcoming only
                show_upcoming_only = st.checkbox(
                    "Show upcoming only",
                    value=get_filter_state('show_upcoming_only', True),
                    key="global_show_upcoming_only"
                )
                set_filter_state('show_upcoming_only', show_upcoming_only)
        
        # === COURSE FILTERS (Detail Page) ===
        if events and filter_type == 'detail':
            # Multiple Activities Selection (if applicable)
            if has_multiple_offers():
                with st.expander("🎯 Selected Activities", expanded=True):
                    from data.supabase_client import get_offers_with_stats
                    from data.state_manager import get_multiple_offers
                    
                    all_offers_for_select = get_offers_with_stats()
                    all_offer_hrefs = get_multiple_offers()
                    
                    # Build mapping
                    href_to_offer = {}
                    offer_options = []
                    for offer_href in all_offer_hrefs:
                        for offer in all_offers_for_select:
                            if offer.get('href') == offer_href:
                                href_to_offer[offer_href] = offer
                                offer_options.append(offer_href)
                                break
                    
                    multiselect_key = "state_selected_offers_multiselect"
                    init_multiple_offers_state(all_offer_hrefs, multiselect_key)
                    current_selected = st.session_state.get(multiselect_key, all_offer_hrefs.copy())
                    
                    selected_offers = st.multiselect(
                        "Activities",
                        options=offer_options,
                        default=current_selected,
                        format_func=lambda href: href_to_offer[href].get('name', 'Unknown'),
                        key=multiselect_key,
                        label_visibility="collapsed"
                    )
                    
                    if selected_offers:
                        st.caption(f"✓ {len(selected_offers)} selected")
            
            # Sport filter (if not using multiple offers)
            if not has_multiple_offers():
                with st.expander("🏃 Sport & Status", expanded=True):
                    sport_names = sorted(set([e.get('sport_name', '') for e in events if e.get('sport_name')]))
                    
                    # Check for pre-selected sports
                    default_sports = []
                    selected_offer = get_selected_offer()
                    if selected_offer:
                        selected_name = selected_offer.get('name', '')
                        if selected_name and selected_name in sport_names:
                            default_sports = [selected_name]
                    
                    selected_sports = st.multiselect(
                        "Sport",
                        options=sport_names,
                        default=get_filter_state('offers', default_sports),
                        key="global_sport_input"
                    )
                    set_filter_state('offers', selected_sports)
                    
                    # Hide cancelled
                    hide_cancelled = st.checkbox(
                        "Hide cancelled courses",
                        value=get_filter_state('hide_cancelled', True),
                        key="global_hide_cancelled"
                    )
                    set_filter_state('hide_cancelled', hide_cancelled)
            
            # Date & Time filters
            with st.expander("📅 Date & Time", expanded=False):
                # Date range
                nav_date = get_nav_date()
                preset_date = None
                if nav_date:
                    preset_date = datetime.strptime(nav_date, '%Y-%m-%d').date()
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "From",
                        value=get_filter_state('date_start', preset_date),
                        key="global_start_date"
                    )
                    set_filter_state('date_start', start_date)
                
                with col2:
                    end_date = st.date_input(
                        "To",
                        value=get_filter_state('date_end', preset_date),
                        key="global_end_date"
                    )
                    set_filter_state('date_end', end_date)
                
                st.divider()
                
                # Time range
                col1, col2 = st.columns(2)
                with col1:
                    start_time_filter = st.time_input(
                        "From",
                        value=get_filter_state('start_time', None),
                        key="global_start_time"
                    )
                    if start_time_filter != time(0, 0):
                        set_filter_state('start_time', start_time_filter)
                    else:
                        set_filter_state('start_time', None)
                
                with col2:
                    end_time_filter = st.time_input(
                        "To",
                        value=get_filter_state('end_time', None),
                        key="global_end_time"
                    )
                    if end_time_filter != time(0, 0):
                        set_filter_state('end_time', end_time_filter)
                    else:
                        set_filter_state('end_time', None)
            
            # Location & Weekday filters
            with st.expander("📍 Location & Day", expanded=False):
                # Location
                locations = sorted(set([e.get('location_name', '') for e in events if e.get('location_name')]))
                selected_locations = st.multiselect(
                    "Location",
                    options=locations,
                    default=get_filter_state('location', []),
                    key="global_location"
                )
                set_filter_state('location', selected_locations)
                
                # Weekdays
                weekdays_de = {
                    'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch',
                    'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'
                }
                weekdays_options = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                selected_weekdays = st.multiselect(
                    "Weekday",
                    options=weekdays_options,
                    default=get_filter_state('weekday', []),
                    format_func=lambda x: weekdays_de.get(x, x),
                    key="global_weekday"
                )
                set_filter_state('weekday', selected_weekdays)
        
        # === ACTIONS ===
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True, help="Save current filters as defaults"):
                try:
                    intensities = get_filter_state('intensity', [])
                    focus = get_filter_state('focus', [])
                    settings = get_filter_state('setting', [])
                    locations = get_filter_state('location', [])
                    weekdays = get_filter_state('weekday', [])
                    if save_sidebar_preferences(intensities, focus, settings, locations, weekdays):
                        st.success("✅ Saved")
                    else:
                        st.warning("⚠️ Login required")
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col2:
            if filter_type == 'detail':
                if st.button("🏠 Home", use_container_width=True):
                    st.switch_page("pages/overview.py")

