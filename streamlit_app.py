"""
================================================================================
UNISPORTAI STREAMLIT APPLICATION
================================================================================

Purpose: Main entry point for the UnisportAI application.
Features: Content-Layer, Filter/ML-Layer, Social-Layer, Analytics-Layer.
Architecture: Browser → Streamlit → utils modules → Supabase

Main Features:
- Sports Overview: Displays filtered sport activities with ML recommendations
- Course Dates: Detailed view for selected activity with all dates
- My Profile: User profile and settings
- About: Project information and team

How it works:
1. Sidebar is rendered once at module level (before tabs)
2. Filter values are stored in st.session_state
3. Tabs read filter values from session_state
4. Data is cached for performance (60-300 seconds TTL)
5. Error Handling: Graceful degradation on DB errors
================================================================================
"""

# =============================================================================
# PART 1: IMPORTS & CONFIGURATION
# =============================================================================
# PURPOSE: Import necessary libraries and configure the Streamlit app

# Core Streamlit library - the foundation of our app
import streamlit as st

# Path for file system operations
from pathlib import Path

# datetime for handling times
from datetime import time

# Authentication functions
from utils.auth import (
    is_logged_in, 
    sync_user_to_supabase, 
    check_token_expiry, 
    handle_logout,
    get_user_sub
)

# Filtering functions
from utils.filters import (
    filter_events,
    get_filter_values_from_session,
    has_event_filters,
    initialize_session_state
)

# Formatting functions
from utils.formatting import (
    create_offer_metadata_df,
    get_match_score_style,
    render_user_avatar,
    convert_events_to_table_data
)

# Analytics functions
from utils.analytics import (
    render_analytics_section,
    render_team_contribution_matrix
)

# Database functions
from utils.db import (
    get_user_complete,
    get_events_grouped_by_offer,
    load_and_filter_offers,
    load_and_filter_events
)

# =============================================================================
# STREAMLIT PAGE CONFIGURATION
# =============================================================================
# PURPOSE: Set up the app's basic appearance and behavior
# IMPORTANT: This MUST be the first Streamlit command in your script
# COMMON MISTAKE: Calling st.write() before st.set_page_config() causes errors

st.set_page_config(
    page_title="UnisportAI",           # Browser tab title
    page_icon="🎯",                     # Browser tab icon (emoji or image URL)
    layout="wide",                      # "wide" uses full screen width, "centered" is narrower
    initial_sidebar_state="expanded"    # Sidebar visible by default
)


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# DATA LOADING (Early, before sidebar rendering)
# =============================================================================
# PURPOSE: Load raw offers data for sidebar filters (not filtered, just for dropdown options)
# WHY: Sidebar needs all available options for filter dropdowns
# HOW: Data is loaded once and cached in session_state
# IMPORTANT: Wrap in try-except to ensure tabs (especially About) are always accessible
# Note: We load raw data here for sidebar filters, actual filtering happens in tabs
# Database queries can fail, therefore try/except
# On error: Return empty list (graceful degradation)
if 'sports_data' not in st.session_state:
    from utils.db import get_offers_complete
    try:
        st.session_state['sports_data'] = get_offers_complete()
    except Exception:
        # On DB error: Empty list, so app continues running
        # About tab remains always accessible
        st.session_state['sports_data'] = []

sports_data = st.session_state.get('sports_data', [])

# Group events by offer_href for efficient lookup
# WHY: Grouping enables fast lookup by offer_href
# HOW: Dictionary with offer_href as key, list of events as value
events_by_offer = get_events_grouped_by_offer()
# Extract all events for sidebar filters
# HOW: Flat list of all events from all groups for filter dropdowns
events = [e for events_list in events_by_offer.values() for e in events_list]

# =============================================================================
# UNIFIED SIDEBAR (Rendered once at module level)
# =============================================================================
# PURPOSE: Sidebar with all filters and user information
# IMPORTANT: The sidebar must be rendered once at module level, not separately
#     inside each tab. Re-rendering it per tab would create duplicate
#     widget keys and scattered state.
#
# PATTERN: Render sidebar before tabs, read values from st.session_state in tabs
#     - Render sidebar directly here, before defining tabs.
#     - Keep user info and all filters in this single sidebar.
#     - Read the resulting values from st.session_state inside the tabs.

with st.sidebar:
        # =================================================================
        # USER INFO SECTION
        # =================================================================
        if not is_logged_in():
            with st.container():
                st.markdown("### 🎯 UnisportAI")
            
            st.button(
                "🔵 Sign in with Google",
                key="sidebar_login",
                use_container_width=True,
                type="primary",
                on_click=st.login,
                args=["google"]
            )
            
            st.markdown("")
        else:
            # WHY: st.user can be None or attributes can be missing
            # HOW: Check each attribute individually with hasattr() and try/except
            # On error: Fallback to default values (graceful degradation)
            try:
                if hasattr(st, 'user') and st.user:
                    user_name = st.user.name
                else:
                    user_name = "User"
                
                if hasattr(st, 'user') and st.user:
                    user_email = st.user.email
                else:
                    user_email = ""
                
                # Note: picture is optional, therefore additional hasattr check
                if hasattr(st, 'user') and st.user and hasattr(st.user, 'picture'):
                    user_picture = st.user.picture
                else:
                    user_picture = None
            except Exception:
                # On error: Fallback to default values
                # Ensures app continues running even if user data is missing
                user_name = "User"
                user_email = ""
                user_picture = None
            
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col2:
                    render_user_avatar(user_name, user_picture, size='large')
                    st.markdown(f"**{user_name}**")

        
        st.markdown("---")
        # =================================================================
        # SPORT FILTER
        # =================================================================
        sport_names = sorted(set([
            e.get('sport_name', '') 
            for e in events 
            if e.get('sport_name')
        ]))
        
        # WHY: If user comes from "View Details", the corresponding sport should be pre-selected
        # HOW: Check if selected_offer exists in session_state and set as default
        default_sports = []
        selected_offer = st.session_state.get('selected_offer')
        if selected_offer:
            selected_name = selected_offer.get('name', '')
            # Check if name exists in available sport names
            if selected_name and selected_name in sport_names:
                default_sports = [selected_name]
        
        selected_sports = st.multiselect(
            "🏃 Sport",
            options=sport_names,
            default=st.session_state.get('offers', default_sports),
            key="unified_sport",
            help="Filter by sport/activity"
        )
        st.session_state['offers'] = selected_sports
        
        st.markdown("")
        
        # =================================================================
        # ACTIVITY FILTERS
        # =================================================================
        with st.expander("🎯 Activity Type", expanded=True):
                intensities = sorted(set([
                    item.get('intensity') 
                    for item in sports_data 
                    if item.get('intensity')
                ]))
                
                # WHY: focus and setting are lists in the data, must be extracted to sets
                # HOW: Iterate over all items, collect all values in sets (prevents duplicates)
                all_focuses = set()
                for item in sports_data:
                    if item.get('focus'):
                        # focus is a list, therefore update() instead of add()
                        all_focuses.update(item.get('focus'))
                focuses = sorted(list(all_focuses))
                
                all_settings = set()
                for item in sports_data:
                    if item.get('setting'):
                        # setting is a list, therefore update() instead of add()
                        all_settings.update(item.get('setting'))
                settings = sorted(list(all_settings))
                
                if intensities:
                    selected_intensity = st.multiselect(
                        "💪 Intensity",
                        options=intensities,
                        default=st.session_state.get('intensity', []),
                        key="unified_intensity",
                        help="Filter by exercise intensity level"
                    )
                    st.session_state['intensity'] = selected_intensity
                
                if focuses:
                    selected_focus = st.multiselect(
                        "🎯 Focus",
                        options=focuses,
                        default=st.session_state.get('focus', []),
                        key="unified_focus",
                        help="Filter by training focus area"
                    )
                    st.session_state['focus'] = selected_focus
                
                if settings:
                    selected_setting = st.multiselect(
                        "🏠 Setting",
                        options=settings,
                        default=st.session_state.get('setting', []),
                        key="unified_setting",
                        help="Indoor or outdoor activities"
                    )
                    st.session_state['setting'] = selected_setting
                
                st.markdown("")
                
                show_upcoming = st.checkbox(
                    "📅 Show upcoming only",
                    value=st.session_state.get('show_upcoming_only', True),
                    key="unified_show_upcoming"
                )
                st.session_state['show_upcoming_only'] = show_upcoming
        
        # =================================================================
        # COURSE FILTERS
        # =================================================================
        with st.expander("📍 Location & Day", expanded=False):
                locations = sorted(set([
                    e.get('location_name', '') 
                    for e in events 
                    if e.get('location_name')
                ]))
                
                selected_locations = st.multiselect(
                    "📍 Location",
                    options=locations,
                    default=st.session_state.get('location', []),
                    key="unified_location",
                    help="Filter by location/venue"
                )
                st.session_state['location'] = selected_locations
                
                st.markdown("")
                
                weekday_options = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                                  'Friday', 'Saturday', 'Sunday']
                
                selected_weekdays = st.multiselect(
                    "📆 Weekday",
                    options=weekday_options,
                    default=st.session_state.get('weekday', []),
                    key="unified_weekday",
                    help="Filter by day of the week"
                )
                st.session_state['weekday'] = selected_weekdays
            
        with st.expander("📅 Date & Time", expanded=False):
                st.markdown("**Date Range**")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "From",
                        value=st.session_state.get('date_start', None),
                        key="unified_start_date"
                    )
                    st.session_state['date_start'] = start_date
                
                with col2:
                    end_date = st.date_input(
                        "To",
                        value=st.session_state.get('date_end', None),
                        key="unified_end_date"
                    )
                    st.session_state['date_end'] = end_date
                
                st.markdown("")
                st.markdown("**Time Range**")
                
                col1, col2 = st.columns(2)
                with col1:
                    start_time = st.time_input(
                        "From",
                        value=st.session_state.get('start_time', None),
                        key="unified_start_time"
                    )
                    # WHY: time_input returns time(0,0) when no value is set
                    # HOW: Check for time(0,0) and set None for "no filter"
                    # None means: This filter is not active
                    if start_time != time(0, 0):
                        st.session_state['start_time'] = start_time
                    else:
                        st.session_state['start_time'] = None
                
                with col2:
                    end_time = st.time_input(
                        "To",
                        value=st.session_state.get('end_time', None),
                        key="unified_end_time"
                    )
                    # WHY: time_input returns time(0,0) when no value is set
                    # HOW: Check for time(0,0) and set None for "no filter"
                    if end_time != time(0, 0):
                        st.session_state['end_time'] = end_time
                    else:
                        st.session_state['end_time'] = None
        
        # =================================================================
        # AI SETTINGS
        # =================================================================
        with st.expander("🤖 AI Recommendations Settings", expanded=False):
                ml_min_match = st.slider(
                    "Minimum Match %",
                    min_value=20,
                    max_value=100,
                    value=st.session_state.get('ml_min_match', 50),
                    step=5,
                    key="ml_min_match_slider",
                    help="Only show sports with at least this match percentage"
                )
                st.session_state['ml_min_match'] = ml_min_match

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# PURPOSE: Initialize filter-related session state variables with defaults
initialize_session_state()

# =============================================================================
# AUTHENTICATION CHECK
# =============================================================================
# PURPOSE: Check authentication status and sync user with Supabase
# WHY: User data must be synchronized between Streamlit OAuth and Supabase
# HOW: Check if logged in, check token expiry, sync user data
# Error Handling: Database queries can fail, therefore try/except
# On error: Show warning, but don't stop app (graceful degradation)
# Ensures app runs even without working DB
if is_logged_in():
    check_token_expiry()
    try:
        sync_user_to_supabase()
    except Exception as e:
        # On sync error: Show warning, but app continues running
        # User can continue using app, only sync fails
        st.warning(f"Error syncing user: {e}")

# =============================================================================
# ANALYTICS SECTION
# =============================================================================
# PURPOSE: Display analytics visualizations (if available)
# WHY: Analytics is optional, app should work without it
# HOW: Wrap in try/except, on error simply skip
# Error Handling: Database queries can fail, therefore try/except
# On error: Skip analytics, but don't stop app
# Ensures About tab always remains accessible
try:
    with st.expander("Analytics", expanded=True):
        render_analytics_section()
except Exception as e:
    # On analytics error: Skip section, but app continues running
    # Important: About tab remains always accessible, even with DB problems
    pass

# =============================================================================
# CREATE TABS
# =============================================================================
# PURPOSE: Create main navigation tabs
# WHY: Tabs organize app into logical areas (Overview, Details, Profile, About)
# HOW: st.tabs() creates tab containers, code in with blocks is rendered in tabs
# LIMITATION: st.tabs() does not support programmatic tab switching
# WORKAROUND: When "View Details" is clicked, selected_offer is stored in session_state
# User must manually switch to "Course Dates" tab to see details

tab_overview, tab_details, tab_profile, tab_about = st.tabs([
    "🎯 Sports Overview",
    "📅 Course Dates",
    "⚙️ My Profile",
    "ℹ️ About"
])

# =============================================================================
# TAB 1: SPORTS OVERVIEW
# =============================================================================

with tab_overview:
    # =========================================================================
    # GET FILTER VALUES FROM SESSION STATE
    # =========================================================================
    # PURPOSE: Extract filter values from session state
    # WHY: Session state persists filter values across tab switches and reruns
    # HOW: Function reads all filters from session_state and returns dictionary
    # Ensures filters are consistent across all tabs
    filters = get_filter_values_from_session()
    
    selected_offers_filter = filters['selected_sports']
    hide_cancelled = filters['hide_cancelled']
    
    # =========================================================================
    # LOAD AND FILTER OFFERS
    # =========================================================================
    # PURPOSE: Load and filter offers (including ML recommendations if filters are set)
    # WHY: ML is automatically applied when offer filters (focus/intensity/setting) are set
    # HOW: Function checks if filters are set and loads ML model if necessary
    # Caching: Function is cached, automatically reloads when filters change
    # TTL: 60 seconds, as filters can change frequently
    # update_session_state=False: Prevents duplicate session state updates
    offers = load_and_filter_offers(filters=filters, update_session_state=False)
    
    # WHY: Show hint when user comes from "View Details" button
    # HOW: Check flag in session_state, show toast, delete flag after display
    # UX: Helps user understand they need to switch to another tab
    if st.session_state.get('show_details_hint'):
        st.toast("✅ Activity selected! Click the 📅 Course Dates tab to view full details.", icon="👉")
        del st.session_state['show_details_hint']
    
    # =========================================================================
    # DISPLAY MATCHING ACTIVITIES
    # =========================================================================
    # PURPOSE: Display filtered offers with events
    if offers:
        for offer in offers:
            # WHY: Use same function as Course Dates tab for consistency
            # HOW: Load events with load_and_filter_events, apply all active filters
            # Ensures events are filtered consistently (e.g. hide_cancelled)
            # show_spinner=False: No spinner in overview, as many offers are loaded
            offer_href = offer.get('href')
            if offer_href:
                # Use the same filtering logic as Course Dates tab
                # Cached for 60 seconds, as events can change more frequently
                upcoming_events = load_and_filter_events(filters=filters, offer_href=offer_href, show_spinner=False)
            else:
                # Edge Case: Offer has no href (should not occur, but safety check)
                upcoming_events = []
            
            # WHY: If sport filter is set, only show offers with matching events
            # HOW: Check if filter is set and if this offer has matching events
            # Edge Case: Offer exists, but has no events for selected sport
            if selected_offers_filter and len(selected_offers_filter) > 0:
                # Check if this offer has any events matching the selected sports
                if not upcoming_events:
                    continue  # Skip this offer if no matching events
            
            # Calculate number of filtered events for display
            filtered_count = len(upcoming_events)
            # Match Score: ML similarity score (0-100%), 100% = perfect match
            match_score = offer.get('match_score', 0)
            # Style for match score badge (color based on score)
            score_badge_style = get_match_score_style(match_score)
            
            # Create expander label with icon, name and match score
            icon = offer.get('icon', '🏃')
            name = offer.get('name', 'Activity')
            expander_label = f"{icon} {name} • {match_score:.0f}% Match"
            
            with st.expander(expander_label, expanded=False):
                image_url = offer.get('image_url')
                if image_url:
                    st.image(image_url, use_container_width=True)
                    st.markdown("")
                
                metadata_df = create_offer_metadata_df(
                    offer,
                    match_score=match_score,
                    include_trainers=True,
                    upcoming_count=filtered_count if filtered_count > 0 else 0
                )
                
                st.dataframe(
                    metadata_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                offer_href = offer.get('href')
                if offer_href:
                    st.link_button("🔗 Book this course", offer_href, use_container_width=True)
                    st.markdown("")
                
                if filtered_count > 0:
                    st.subheader(f"Upcoming Dates ({filtered_count})")
                    # WHY: Sort events by start_time for chronological display
                    # HOW: Sort list by start_time field (string comparison works for ISO format)
                    upcoming_events = sorted(upcoming_events, key=lambda x: x.get('start_time', ''))
                    
                    if upcoming_events:
                        # WHY: Show only first 10 events in overview (performance)
                        # HOW: Slice list to [:10], button shows "View all" for all events
                        # abbreviated_weekday=True: Shorter weekday display for compact table
                        events_table_data = convert_events_to_table_data(
                            upcoming_events[:10],
                            abbreviated_weekday=True,
                            include_status=False,  # Status not needed in overview
                            include_sport=False,    # Sport already in expander title
                            include_trainers=False # Trainers not needed in overview
                        )
                        # WHY: convert_events_to_table_data returns time as string
                        # HOW: Convert string back to time object for correct column formatting
                        # Edge Case: Time string can have "HH:MM - HH:MM" format (time range)
                        # On error: Ignore row (graceful degradation)
                        for row in events_table_data:
                            time_str = row['time']
                            if isinstance(time_str, str):
                                # Parse time string back to time object
                                try:
                                    # Handle time range format: "HH:MM - HH:MM" → take first time
                                    if ' - ' in time_str:
                                        time_part = time_str.split(' - ')[0]
                                    else:
                                        time_part = time_str
                                    hour, minute = map(int, time_part.split(':'))
                                    row['time'] = time(hour, minute)
                                except (ValueError, AttributeError):
                                    # On parse error: Keep original string
                                    pass
                        
                        st.dataframe(
                            events_table_data,
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "date": st.column_config.DateColumn(
                                    "Date",
                                    format="DD.MM.YYYY",
                                ),
                                "time": st.column_config.TimeColumn(
                                    "Time",
                                    format="HH:mm",
                                ),
                                "weekday": "Day",
                                "location": "Location"
                            }
                        )
                        
                        # WHY: Button saves selected offer and switches to details tab
                        # HOW: Save offer in session_state, set hint flag, rerun app
                        # Note: st.tabs() does not support programmatic tab switching
                        # User must manually switch to "Course Dates" tab
                        if st.button(
                            f"View all {len(upcoming_events)} dates →",
                            key=f"view_details_{offer['href']}",
                            use_container_width=True,
                            type="primary"
                        ):
                            st.session_state['selected_offer'] = offer
                            st.session_state['show_details_hint'] = True
                            st.rerun()
                    else:
                        st.info("No upcoming dates match your filters")
    else:
        st.info("🔍 No activities found matching your filters.")
        st.caption("Try adjusting your search or filters in the sidebar.")

# =============================================================================
# TAB 2: COURSE DATES
# =============================================================================

with tab_details:
    # =========================================================================
    # GET SELECTED OFFER
    # =========================================================================
    # PURPOSE: Load selected offer from session state
    selected = st.session_state.get('selected_offer', None)
    
    # =========================================================================
    # ACTIVITY INFO SECTION
    # =========================================================================
    # PURPOSE: Display activity information (image, description, metadata)
    if selected:
        image_url = selected.get('image_url')
        if image_url:
            st.image(image_url, use_container_width=True)
            st.markdown("")
        
        description = selected.get('description')
        if description:
            with st.expander("📖 Activity Description", expanded=False):
                st.markdown(description, unsafe_allow_html=True)
        
        metadata_df = create_offer_metadata_df(
            selected,
            match_score=None,
            include_trainers=False
        )
        
        st.dataframe(
            metadata_df,
            use_container_width=True,
            hide_index=True
        )
        
        offer_href = selected.get('href')
        if offer_href:
            st.link_button("🔗 Book this course", offer_href, use_container_width=True)
            st.markdown("")
    
    # =========================================================================
    # GET FILTER STATES
    # =========================================================================
    # PURPOSE: Extract filter values from session state
    # WHY: Filters are set in sidebar, must be read here
    # HOW: Function reads all filters from session_state and returns dictionary
    filters = get_filter_values_from_session()
    
    # =========================================================================
    # LOAD AND FILTER EVENTS
    # =========================================================================
    # PURPOSE: Load and filter events for selected offer
    # WHY: Events can change more frequently than offers (e.g. cancellations)
    # HOW: Function loads events from DB, filters by all active filters
    # Caching: Cached for 60 seconds, as events can change more frequently
    # Spinner: Displayed while data is being loaded (better UX)
    offer_href = selected['href'] if selected else None
    filtered_events = load_and_filter_events(filters=filters, offer_href=offer_href, show_spinner=True)
    
    if not filtered_events:
        st.info("📅 No course dates available.")
    else:
        # =====================================================================
        # DISPLAY FILTERED EVENTS
        # =====================================================================
            table_data = convert_events_to_table_data(
                filtered_events,
                abbreviated_weekday=False,
                include_status=True,
                include_sport=True,
                include_trainers=True
            )
            
            st.dataframe(
                    table_data,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "date": st.column_config.DateColumn("Date", format="DD.MM.YYYY"),
                        "time": "Time",
                        "weekday": "Day",
                        "sport": "Sport",
                        "location": "Location",
                        "trainers": "Trainers",
                        "status": st.column_config.TextColumn(
                            "Status",
                            help="Course status",
                            validate="^(Active|Cancelled)$"
                        )
                    }
                )
            
# =============================================================================
# TAB 3: MY PROFILE
# =============================================================================

with tab_profile:
    # =========================================================================
    # AUTHENTICATION CHECK
    # =========================================================================
    # PURPOSE: Check if user is logged in before loading profile
    # WHY: Profile data is only available for logged-in users
    # HOW: Check is_logged_in(), show info message if not logged in
    if not is_logged_in():
        st.info("🔒 **Login required** - Sign in with Google in the sidebar")
    else:
        # =========================================================================
        # LOAD USER PROFILE
        # =========================================================================
        # PURPOSE: Load complete user profile from database
        # WHY: Profile changes rarely, therefore caching makes sense
        # HOW: Get user_sub (Google OAuth ID), then load profile from DB
        # Error Handling: Database queries can fail, therefore checks
        # On error: Show error message, but don't stop app
        user_sub = get_user_sub()
        if not user_sub:
            # Edge Case: User is logged in, but user_sub is missing
            st.error("❌ Login required.")
        else:
            profile = get_user_complete(user_sub)
            if not profile:
                # Edge Case: User exists in OAuth, but not in DB
                st.error("❌ Profile not found.")
            else:
                st.subheader("User Information")
                
                col_pic, col_info = st.columns([1, 3])
                
                with col_pic:
                    render_user_avatar(profile.get('name', 'U'), profile.get('picture'), size='small')
                
                with col_info:
                    st.markdown(f"### {profile.get('name', 'N/A')}")
                    
                # Show profile information (only if available)
                # WHY: Check each field individually, as not all fields are always present
                # HOW: Use .get() with default value, check if value exists
                if profile.get('email'):
                    st.markdown(f"📧 {profile['email']}")
                if profile.get('created_at'):
                    # [:10] extracts only date (YYYY-MM-DD) from ISO timestamp
                    st.markdown(f"📅 Member since {profile['created_at'][:10]}")
                if profile.get('last_login'):
                    # [:10] extracts only date (YYYY-MM-DD) from ISO timestamp
                    st.markdown(f"🕐 Last login {profile['last_login'][:10]}")
                
                st.markdown("")
                st.markdown("---")
                
                # WHY: Logout button calls handle_logout(), which clears session
                # HOW: Button click triggers handle_logout(), which logs out user
                if st.button("🚪 Logout", type="secondary", use_container_width=True):
                    handle_logout()

# =============================================================================
# TAB 4: ABOUT
# =============================================================================

with tab_about:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("How This App Works")
        st.markdown("""
        **What's happening behind the scenes?**
        
        1. **Automated Data Collection:** Python scripts automatically scrape Unisport websites 
           (offers, courses, dates, locations) via GitHub Actions on a regular schedule.
        
        2. **Data Storage:** All data is stored in Supabase, our hosted PostgreSQL database.
        
        3. **Real-time Display:** This Streamlit app loads data directly from Supabase and 
           displays it here in real-time.
        
        4. **Smart Features:** AI-powered recommendations using Machine Learning (KNN algorithm), 
           advanced filtering system.
        
        **Tech Stack:**
        - **Frontend:** Streamlit (Python web framework)
        - **Database:** Supabase (PostgreSQL)
        - **ML:** scikit-learn (KNN recommender)
        - **Visualization:** Plotly (interactive charts)
        - **Authentication:** Google OAuth via Streamlit
        """)
    
    with col_right:
        st.subheader("Project Team")
        
        # WHY: Path to team images relative to current file
        # HOW: Use Path(__file__) to get absolute path to current file
        # .parent goes up one directory, then / "assets" / "images"
        assets_path = Path(__file__).resolve().parent / "assets" / "images"
        team_members = [
            {"name": "Tamara Nessler", "url": "https://www.linkedin.com/in/tamaranessler/", "avatar": str(assets_path / "tamara.jpeg")},
            {"name": "Till Banerjee", "url": "https://www.linkedin.com/in/till-banerjee/", "avatar": str(assets_path / "till.jpeg")},
            {"name": "Sarah Bugg", "url": "https://www.linkedin.com/in/sarah-bugg/", "avatar": str(assets_path / "sarah.jpeg")},
            {"name": "Antonia Büttiker", "url": "https://www.linkedin.com/in/antonia-büttiker-895713254/", "avatar": str(assets_path / "antonia.jpeg")},
            {"name": "Luca Hagenmayer", "url": "https://www.linkedin.com/in/lucahagenmayer/", "avatar": str(assets_path / "luca.jpeg")},
        ]
        
        cols = st.columns(5)
        for idx, member in enumerate(team_members):
            with cols[idx]:
                st.image(member["avatar"], width=180)
                st.markdown(f"[{member['name']}]({member['url']})")
        
        render_team_contribution_matrix(team_members, assets_path)
    
    st.divider()
    st.subheader("Project Background")
    st.markdown("""
    This project was created for the course **"Fundamentals and Methods of Computer Science"** 
    at the University of St.Gallen, taught by:
    - [Prof. Dr. Stephan Aier](https://www.unisg.ch/de/universitaet/ueber-uns/organisation/detail/person-id/32344c07-5d2e-41f0-9ba8-d9f379bb05ee/)
    - [Dr. Bernhard Bermeitinger](https://www.unisg.ch/de/universitaet/ueber-uns/organisation/detail/person-id/1fa3d0cd-cb80-410a-b2b4-dbc3f1a4ee27/)
    - [Prof. Dr. Simon Mayer](https://www.unisg.ch/de/universitaet/ueber-uns/organisation/detail/person-id/b7d5efc7-55f2-4b97-9e31-ac097b6d15e1/)
    
    **Status:** Still in development and not yet reviewed by professors.
    
    **Feedback?** Have feature requests or found bugs? Please contact one of the team members 
    via LinkedIn (see above).
    """)


# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.