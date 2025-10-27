"""
Geteilte Sidebar für alle Seiten
Enthält alle Filter in einer gemeinsamen Sidebar
"""

import streamlit as st
from datetime import datetime, time
from data.state_manager import get_filter_state, set_filter_state


def render_shared_sidebar(filter_type='main', sports_data=None, events=None):
    """
    Renders a shared sidebar with all filters.
    
    Args:
        filter_type: 'main', 'detail', 'weekly' - determines which additional options are shown
        sports_data: Data for main page filters (only for filter_type='main')
        events: Event data for detail filters (for filter_type='detail' or 'weekly')
    """
    
    # If no events were passed, load them
    if not events:
        from data.supabase_client import get_all_events
        events = get_all_events()
    
    with st.sidebar:
        st.header("🔍 Filter")
        
        # === MAIN PAGE FILTERS (from main_page.py) ===
        st.subheader("📋 Hauptseiten-Filter")
        
        # Only show activities with upcoming dates
        show_upcoming_only_state = get_filter_state('show_upcoming_only', True)
        show_upcoming_only = st.checkbox(
            "Nur kommende Termine", 
            value=show_upcoming_only_state, 
            key="global_show_upcoming_only"
        )
        set_filter_state('show_upcoming_only', show_upcoming_only)
        
        # Search text
        search_text_state = get_filter_state('search_text', '')
        search_text = st.text_input(
            "Suche nach Name", 
            value=search_text_state, 
            placeholder="Tippe zum Suchen...", 
            key="global_search_text"
        )
        set_filter_state('search_text', search_text)
        
        # Intensity, Focus, Setting - nur wenn sports_data vorhanden ist
        # Versuche auch aus session state zu holen
        if not sports_data and 'state_sports_data' in st.session_state:
            sports_data = st.session_state['state_sports_data']
            
        if sports_data and len(sports_data) > 0:
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
            
            # Intensity filter
            selected_intensity = st.multiselect(
                "Intensität",
                options=intensities,
                default=get_filter_state('intensity', []),
                key="global_intensity"
            )
            set_filter_state('intensity', selected_intensity)
            
            # Focus filter
            selected_focus = st.multiselect(
                "Fokus",
                options=focuses,
                default=get_filter_state('focus', []),
                key="global_focus"
            )
            set_filter_state('focus', selected_focus)
            
            # Setting filter
            selected_setting = st.multiselect(
                "Setting",
                options=settings,
                default=get_filter_state('setting', []),
                key="global_setting"
            )
            set_filter_state('setting', selected_setting)
        
        st.divider()
        
        # === DETAIL FILTERS (from page_2.py and page_3.py) ===
        # Show detail filters if we have events data available (regardless of page)
        if events:
            st.subheader("📅 Details-Filter")
            
            # Sport Activity filter
            sport_names = sorted(set([e.get('sport_name', '') for e in events if e.get('sport_name')]))
            
            # Check for pre-selected sports from other pages
            default_sports = []
            if 'state_selected_offer' in st.session_state:
                selected_name = st.session_state['state_selected_offer'].get('name', '')
                if selected_name and selected_name in sport_names:
                    default_sports = [selected_name]
            
            sport_state = get_filter_state('offers', default_sports)
            selected_sports = st.multiselect(
                "Sportaktivität", 
                options=sport_names, 
                default=sport_state, 
                key="global_sport_input"
            )
            set_filter_state('offers', selected_sports)
            
            # Hide cancelled events filter
            hide_cancelled_state = get_filter_state('hide_cancelled', True)
            hide_cancelled_checkbox = st.checkbox(
                "Nur nicht stornierte Termine", 
                value=hide_cancelled_state, 
                key="global_hide_cancelled"
            )
            set_filter_state('hide_cancelled', hide_cancelled_checkbox)
            
            # Date range
            st.markdown("**Datumsspanne**")
            date_col1, date_col2 = st.columns(2)
            
            # Check for pre-selected date from other pages (navigation)
            preset_start_date = None
            preset_end_date = None
            if 'state_nav_date' in st.session_state:
                preset_start_date = datetime.strptime(st.session_state['state_nav_date'], '%Y-%m-%d').date()
                preset_end_date = preset_start_date
            
            # Get date states from filter state or use defaults
            start_date_state = get_filter_state('date_start', preset_start_date)
            end_date_state = get_filter_state('date_end', preset_end_date)
            
            with date_col1:
                start_date = st.date_input("Von", value=start_date_state, key="global_start_date")
                set_filter_state('date_start', start_date)
            with date_col2:
                end_date = st.date_input("Bis", value=end_date_state, key="global_end_date")
                set_filter_state('date_end', end_date)
            
            # Location filter
            locations = sorted(set([e.get('location_name', '') for e in events if e.get('location_name')]))
            location_state = get_filter_state('location', [])
            selected_locations = st.multiselect(
                "Standort", 
                options=locations, 
                default=location_state, 
                key="global_location"
            )
            set_filter_state('location', selected_locations)
            
            # Weekday filter
            weekdays_de = {
                'Monday': 'Montag',
                'Tuesday': 'Dienstag',
                'Wednesday': 'Mittwoch',
                'Thursday': 'Donnerstag',
                'Friday': 'Freitag',
                'Saturday': 'Samstag',
                'Sunday': 'Sonntag'
            }
            weekdays_options = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_state = get_filter_state('weekday', [])
            selected_weekdays = st.multiselect(
                "Wochentag", 
                options=weekdays_options, 
                default=weekday_state, 
                format_func=lambda x: weekdays_de.get(x, x), 
                key="global_weekday"
            )
            set_filter_state('weekday', selected_weekdays)
            
            # Time range
            st.markdown("**Uhrzeit**")
            time_col1, time_col2 = st.columns(2)
            
            # Check for pre-selected time from other pages (navigation)
            preset_start_time = None
            if 'page_2_filter_time' in st.session_state:
                preset_start_time = st.session_state['page_2_filter_time']
            
            start_time_state = get_filter_state('start_time', preset_start_time)
            end_time_state = get_filter_state('end_time', None)
            
            with time_col1:
                start_time_filter = st.time_input("Von", value=start_time_state, key="global_start_time")
                # Nur speichern wenn nicht Default (00:00)
                if start_time_filter != time(0, 0):
                    set_filter_state('start_time', start_time_filter)
                else:
                    set_filter_state('start_time', None)
            with time_col2:
                end_time_filter = st.time_input("Bis", value=end_time_state, key="global_end_time")
                # Nur speichern wenn nicht Default (00:00)
                if end_time_filter != time(0, 0):
                    set_filter_state('end_time', end_time_filter)
                else:
                    set_filter_state('end_time', None)
            
            st.divider()
        
        # === PAGE_2 ONLY: Multiple Offers Multiselect ===
        if filter_type == 'detail' and 'state_page2_multiple_offers' in st.session_state:
            st.subheader("🎯 Aktivitäten-Auswahl")
            
            from data.supabase_client import get_offers_with_stats
            all_offers_for_select = get_offers_with_stats()
            all_offer_hrefs = st.session_state['state_page2_multiple_offers']
            
            # Build mapping of href to offer
            href_to_offer = {}
            offer_options = []
            for offer_href in all_offer_hrefs:
                for offer in all_offers_for_select:
                    if offer.get('href') == offer_href:
                        href_to_offer[offer_href] = offer
                        offer_options.append(offer_href)
                        break
            
            from data.state_manager import init_multiple_offers_state
            multiselect_key = "state_selected_offers_multiselect"
            init_multiple_offers_state(all_offer_hrefs, multiselect_key)
            current_selected = st.session_state.get(multiselect_key, all_offer_hrefs.copy())
            
            selected_offers = st.multiselect(
                "Wähle Aktivitäten:",
                options=offer_options,
                default=current_selected,
                format_func=lambda href: href_to_offer[href].get('name', 'Unknown'),
                key=multiselect_key
            )
            
            if selected_offers:
                selected_names = [href_to_offer[h].get('name', '') for h in selected_offers]
                st.info(f"📋 {len(selected_names)} ausgewählt")
            else:
                st.warning("⚠️ Keine Aktivitäten ausgewählt")
            
            st.divider()
        
        # === Navigation Buttons ===
        st.subheader("🔄 Navigation")
        
        if filter_type == 'main':
            if st.button("📅 Alle Termine (Wochenansicht)", use_container_width=True):
                st.switch_page("pages/calendar.py")
        elif filter_type == 'detail':
            if st.button("📅 Wochenansicht", use_container_width=True):
                st.switch_page("pages/calendar.py")
            if st.button("🏠 Zur Hauptseite", use_container_width=True):
                st.switch_page("pages/overview.py")
        elif filter_type == 'weekly':
            if st.button("🏠 Zur Hauptseite", use_container_width=True):
                st.switch_page("pages/overview.py")

