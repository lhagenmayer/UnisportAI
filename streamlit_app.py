"""
================================================================================
UNISPORTAI STREAMLIT APPLICATION
================================================================================

WHY THIS FILE EXISTS:
This is the canonical entry point for the entire UnisportAI system.
It serves as the main application file that renders UI widgets and
orchestrates the data flow for a data-heavy Streamlit app.

FEATURE CHECKLIST:
1. Content layer - sport offers, timetable events, trainer info
2. Filter + ML layer - rule-based filters plus KNN recommendations
3. Social layer - authentication, user cards, profile visibility
4. Analytics layer - aggregated charts (weekday/hour/location stats)

ARCHITECTURE MAP:
Browser ↔ Streamlit widgets
           ↓
    streamlit_app.py
           ↓
    utils service modules (auth/db/ml/filters/rating/formatting)
           ↓
    Supabase (managed Postgres + cached views)

DEVELOPER ROADMAP FOR THIS FILE:
- PART 1: imports + global configuration
- PART 2: helper sections referencing utils modules (separation of concerns)
- PART 3: sidebar + session-state logic (single source of truth for filters)
- PART 4: view functions (dashboard tabs, analytics, recommendations)
- PART 5: page orchestration (routing, gating on auth state)

HOW TO STUDY THIS DOCUMENT:
- Read comments as design justifications. Every large block explains
  why the pattern was chosen (cache vs. no cache, columns vs. tabs, etc.).
- Trace the data loop: Input widgets → session_state → filters/ml →
  UI render. Understanding this loop is crucial for understanding the app.
- Comments throughout highlight best practices and design decisions.
================================================================================
"""

# =============================================================================
# PART 1: IMPORTS & CONFIGURATION
# =============================================================================
# PURPOSE: Import necessary libraries and configure the Streamlit app

# Core Streamlit library - the foundation of our app
import streamlit as st

# Plotly for interactive charts and visualizations
import plotly.graph_objects as go

# pandas for data manipulation and DataFrame display
import pandas as pd

# Path for file system operations
from pathlib import Path

# datetime for handling dates and times
from datetime import datetime, time

# Our custom authentication functions
from utils.auth import (
    is_production,
    is_logged_in, 
    sync_user_to_supabase, 
    check_token_expiry, 
    handle_logout,
    get_user_sub
)

# Database connection and query functions are imported from utils below

# Utility functions (refactored from this file)
from utils import (
    test_database_connection,
    get_data_timestamp,
    load_knn_model,
    build_user_preferences_from_filters,
    get_ml_recommendations,
    check_event_matches_filters,
    filter_offers,
    filter_events,
    create_user_info_card_html
)
# Also import db functions directly for convenience
from utils.db import get_supabase_client, get_offers_complete, get_events

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
# PART 2: ML INTEGRATION (moved to utils/ml_utils.py)
# =============================================================================
# NOTE: ML functions are now imported from utils.ml_utils
# - load_knn_model()
# - build_user_preferences_from_filters()
# - get_ml_recommendations()

# =============================================================================
# PART 3: FILTER UTILITIES (moved to utils/filters.py)
# =============================================================================
# NOTE: Filter functions are now imported from utils.filters
# - check_event_matches_filters()
# - filter_offers()
# - filter_events()

# =============================================================================
# PART 4: SIDEBAR COMPONENTS (UNIFIED VERSION)
# =============================================================================
# PURPOSE: Create a consistent sidebar that works across all tabs
# SIMPLIFICATION: Original had complex context-dependent logic, this is unified
# STREAMLIT CONCEPT: st.sidebar creates a sidebar, session_state persists data
# FOR BEGINNERS: Session state is KEY - it remembers user selections between reruns

# NOTE: create_user_info_card_html() is now imported from utils.formatting

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# BEST PRACTICE: Initialize all session state variables in one place
# This ensures consistent state management and prevents KeyError issues
def initialize_session_state():
    """
    Initialize all session state variables with default values.
    
    STREAMLIT BEST PRACTICE:
    ------------------------
    Session state should be initialized in a dedicated function to:
    1. Avoid KeyError when accessing state variables
    2. Make it clear what state variables exist
    3. Ensure consistent defaults across the app
    4. Make testing easier
    
    This function should be called early in the app execution.
    """
    # All session state keys are explicitly enumerated to ensure consistent
    # state management. Missing keys can cause KeyError and inconsistent UI state.
    # Centralizing defaults provides a single checklist when debugging.
    defaults = {
        # Filter states
        'search_text': '',
        'intensity': [],
        'focus_areas': [],
        'settings': [],
        'selected_sport': None,
        'selected_weekday': None,
        'selected_location': None,
        'selected_time': None,
        'hide_cancelled': False,
        'min_match_score': 0,
        
        # UI states
        'show_activity_rating': False,
        'show_trainer_rating': False,
        
        # Data states (will be populated from database)
        'sports_data': None,
    }
    
    # Only set defaults if key doesn't exist (preserve user selections)
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_unified_sidebar(sports_data=None, events=None):
    """
    Render a unified sidebar with all filters.
    
    PURPOSE:
        Provide a single, reusable sidebar that works consistently across
        all tabs, so filter state is managed in exactly one place.
    STREAMLIT CONCEPT:
        Session state stores filter values, widgets update them, and all
        tabs read from the same shared state.
    
    PATTERN:
        1. Show user info (login/profile)
        2. Load data if not provided
        3. Render activity filters (if sports_data available)
        4. Render course filters (if events available)
        5. Store all selections in session_state
    
    Args:
        sports_data: List of sports offers (optional, will load if None)
        events: List of events (optional, will load if None)
    """
    with st.sidebar:
        # =================================================================
        # USER INFO SECTION (Always shown first)
        # =================================================================
        # DESIGN NOTE: User info lives directly in the sidebar instead of
        # a nested helper to avoid nested sidebar contexts and duplicate keys.
        
        if not is_logged_in():
            # === NOT LOGGED IN: Show login UI ===
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 16px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            ">
                <div style="color: white; font-size: 18px; font-weight: 700; margin-bottom: 12px;">
                    🎯 UnisportAI
                </div>
                <div style="color: rgba(255,255,255,0.9); font-size: 14px; margin-bottom: 16px;">
                    Sign in to access all features
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Login button using Streamlit's authentication
            st.button(
                "🔵 Sign in with Google",
                key="sidebar_login",
                use_container_width=True,
                type="primary",
                on_click=st.login,
                args=["google"]
            )
            
            # Show production OAuth configuration reminder
            if is_production():
                with st.expander("⚠️ OAuth Configuration Check", expanded=False):
                    st.info("""
                    **If login fails with a redirect error:**
                    
                    Ensure your Google OAuth redirect URI in Google Cloud Console is set to:
                    ```
                    https://your-app-name.streamlit.app/oauth2callback
                    ```
                    
                    **Important:** Remove any `localhost` redirect URIs from production OAuth credentials.
                    """)
            
            st.markdown("<br>", unsafe_allow_html=True)
        else:
            # === LOGGED IN: Show user profile card ===
            try:
                if hasattr(st, 'user') and st.user:
                    user_name = st.user.name
                else:
                    user_name = "User"
                
                if hasattr(st, 'user') and st.user:
                    user_email = st.user.email
                else:
                    user_email = ""
                
                if hasattr(st, 'user') and st.user and hasattr(st.user, 'picture'):
                    user_picture = st.user.picture
                else:
                    user_picture = None
            except Exception:
                user_name = "User"
                user_email = ""
                user_picture = None
            
            # Display user card with profile picture (ohne zusätzlichen violetten Balken)
            with st.container():
                # Use columns for picture and info
                col_pic, col_info = st.columns([1, 3])
                
                with col_pic:
                    if user_picture and str(user_picture).startswith('http'):
                        st.image(user_picture, width=60)
                    else:
                        # Create initials avatar
                        name_words = user_name.split()[:2]
                        initials_list = []
                        for word in name_words:
                            if word:
                                initials_list.append(word[0].upper())
                        initials = ''.join(initials_list)
                        st.markdown(f"""
                        <div style="width: 60px; height: 60px; border-radius: 50%; 
                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                    display: flex; align-items: center; justify-content: center;
                                    color: white; font-size: 20px; font-weight: bold;
                                    border: 3px solid white;">
                            {initials}
                        </div>
                        """, unsafe_allow_html=True)
                
                with col_info:
                    st.markdown(f"""
                    <div style="color: #333; font-size: 12px; font-weight: 600; margin-bottom: 4px;">
                        👤 Signed in as
                    </div>
                    <div style="color: #333; font-size: 14px; font-weight: 700; margin-bottom: 2px;">
                        {user_name}
                    </div>
                    <div style="color: #666; font-size: 11px;">
                        {user_email}
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
        
        # Separator after user section
        st.markdown("---")
        # =================================================================
        # QUICK SEARCH (Always visible)
        # =================================================================
        # This simple search box is always shown at the top
        search_text = st.text_input(
            "🔎 Quick Search",
            value=st.session_state.get('search_text', ''),
            placeholder="Search activities...",
            key="unified_search_text",
            help="Search by activity name, location, or trainer"
        )
        # IMPORTANT: Store in session_state so other tabs can access it
        st.session_state['search_text'] = search_text
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # =================================================================
        # LOAD DATA (immer laden, ohne Error Handling)
        # =================================================================
        from utils.db import get_offers_complete, get_events

        if sports_data is None:
            sports_data = st.session_state.get('sports_data')
        if sports_data is None:
            sports_data = get_offers_complete()
            st.session_state['sports_data'] = sports_data

        if events is None:
            events = st.session_state.get('events_data')
        if events is None:
            events = get_events()
            st.session_state['events_data'] = events

        # Fallbacks, damit die Filter immer gerendert werden können
        sports_data = sports_data or []
        events = events or []
        
        # =================================================================
        # ACTIVITY FILTERS (immer anzeigen)
        # =================================================================
        with st.expander("🎯 Activity Type", expanded=True):
                # Extract unique intensity values from all sports
                intensities = sorted(set([
                    item.get('intensity') 
                    for item in sports_data 
                    if item.get('intensity')
                ]))
                
                # Extract all unique focus areas
                all_focuses = set()
                for item in sports_data:
                    if item.get('focus'):
                        all_focuses.update(item.get('focus'))
                focuses = sorted(list(all_focuses))
                
                # Extract all unique settings
                all_settings = set()
                for item in sports_data:
                    if item.get('setting'):
                        all_settings.update(item.get('setting'))
                settings = sorted(list(all_settings))
                
                # --- Intensity Filter ---
                if intensities:
                    selected_intensity = st.multiselect(
                        "💪 Intensity",
                        options=intensities,
                        default=st.session_state.get('intensity', []),
                        key="unified_intensity",
                        help="Filter by exercise intensity level"
                    )
                    st.session_state['intensity'] = selected_intensity
                
                # --- Focus Filter ---
                if focuses:
                    selected_focus = st.multiselect(
                        "🎯 Focus",
                        options=focuses,
                        default=st.session_state.get('focus', []),
                        key="unified_focus",
                        help="Filter by training focus area"
                    )
                    st.session_state['focus'] = selected_focus
                
                # --- Setting Filter ---
                if settings:
                    selected_setting = st.multiselect(
                        "🏠 Setting",
                        options=settings,
                        default=st.session_state.get('setting', []),
                        key="unified_setting",
                        help="Indoor or outdoor activities"
                    )
                    st.session_state['setting'] = selected_setting
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Show Upcoming Only Checkbox ---
                show_upcoming = st.checkbox(
                    "📅 Show upcoming only",
                    value=st.session_state.get('show_upcoming_only', True),
                    key="unified_show_upcoming"
                )
        
        # =================================================================
        # COURSE FILTERS (immer anzeigen)
        # =================================================================
        # --- Location & Weekday Filters (TOP) ---
        with st.expander("📍 Location & Day", expanded=False):
                # Location filter
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
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Weekday filter - use English names directly
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
            
        # --- Sport Filter ---
        with st.expander("🏃 Sport & Status", expanded=True):
                # Get all unique sport names from events
                sport_names = sorted(set([
                    e.get('sport_name', '') 
                    for e in events 
                    if e.get('sport_name')
                ]))
                
                # Check for pre-selected sports from Sports Overview tab
                default_sports = []
                selected_offer = st.session_state.get('selected_offer')
                if selected_offer:
                    selected_name = selected_offer.get('name', '')
                    if selected_name and selected_name in sport_names:
                        default_sports = [selected_name]
                
                selected_sports = st.multiselect(
                    "Sport",
                    options=sport_names,
                    default=st.session_state.get('offers', default_sports),
                    key="unified_sport"
                )
                st.session_state['offers'] = selected_sports
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Hide Cancelled Checkbox ---
                hide_cancelled = st.checkbox(
                    "🚫 Hide cancelled courses",
                    value=st.session_state.get('hide_cancelled', True),
                    key="unified_hide_cancelled"
                )
                st.session_state['hide_cancelled'] = hide_cancelled
            
        # --- Date & Time Filters ---
        with st.expander("📅 Date & Time", expanded=False):
                st.markdown("**Date Range**")
                
                # Date range inputs (two columns)
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
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Time Range**")
                
                # Time range inputs (two columns)
                col1, col2 = st.columns(2)
                with col1:
                    start_time = st.time_input(
                        "From",
                        value=st.session_state.get('start_time', None),
                        key="unified_start_time"
                    )
                    # Only store if not default midnight
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
                    # Only store if not default midnight
                    if end_time != time(0, 0):
                        st.session_state['end_time'] = end_time
                    else:
                        st.session_state['end_time'] = None
        
        # =================================================================
        # AI SETTINGS (immer anzeigen)
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


# NOTE: get_data_timestamp() is now imported from utils.db

# =============================================================================
# PART 5: MAIN APP - AUTHENTICATION & DATABASE CHECK
# =============================================================================
# PURPOSE: Handle user authentication and verify database connection
# STREAMLIT CONCEPT: Code at module level runs on every page load
# FOR BEGINNERS: This section runs BEFORE the tabs
# 
# NOTE: User info section is now part of unified sidebar (no separate call needed)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================
# BEST PRACTICE: Initialize session state early, before any UI rendering
initialize_session_state()

# =============================================================================
# DATABASE CONNECTION CHECK
# =============================================================================
# DESIGN NOTE:
#     External dependencies are validated early so configuration issues are
#     surfaced before any complex UI logic is executed.
db_ok, db_message = test_database_connection()

if not db_ok:
    # Show database error prominently at the top
    st.error("⚠️ **Database Connection Failed**")
    st.info("🔧 **This is a configuration issue, not a login requirement.**\n\nThe app cannot connect to the Supabase database. Please check your database credentials.")
    with st.expander("📚 How to fix this", expanded=True):
        st.markdown(db_message)
        st.markdown("""
        ### Why does this matter?
        
        This app uses **Supabase** (a PostgreSQL database) to store:
        - Sports activities and courses
        - User profiles and preferences  
        - Ratings and social connections
        - ETL run timestamps
        
        **Without the database, the app can't load data.**
        
        ### For Streamlit Cloud:
        1. Go to your app settings in Streamlit Cloud
        2. Navigate to "Secrets" section
        3. Add your Supabase credentials in this format:
        
        ```toml
        [connections.supabase]
        url = "https://your-project-id.supabase.co"
        key = "your-anon-or-service-key"
        ```
        
        ### For local development:
        - Verify the configuration in `.streamlit/secrets.toml`
        - Check your Supabase project status
        - Review the connection details shown in the error message above
        
        As a fallback, you can still study the code structure and UI patterns
        even when live data is not available.
        """)
    
    st.info("💡 The app will continue, but database-dependent features will not be available.")

# =============================================================================
# AUTHENTICATION CHECK
# =============================================================================
# If user is logged in, sync with database and check token
if is_logged_in():
    check_token_expiry()  # Make sure authentication hasn't expired
    try:
        sync_user_to_supabase()  # Sync user data to our database
    except Exception as e:
        # Only show warning if database is supposed to be working
        if db_ok:
            st.warning(f"Error syncing user: {e}")

# =============================================================================
# RENDER UNIFIED SIDEBAR (ONCE FOR ALL TABS)
# =============================================================================
# IMPORTANT:
#     The sidebar must be rendered once at module level, not separately
#     inside each tab. Re-rendering it per tab would create duplicate
#     widget keys and scattered state.
#
# PATTERN:
#     - Call render_unified_sidebar() once here, before defining tabs.
#     - Keep user info and all filters in this single sidebar.
#     - Read the resulting values from st.session_state inside the tabs.

render_unified_sidebar()

# =============================================================================
# ML RECOMMENDATIONS VISUALIZATION
# =============================================================================
# PURPOSE: Display AI-powered recommendations as a dedicated visualization section
# STREAMLIT CONCEPT: This appears above all tabs, making it always visible
# FOR BEGINNERS: This shows how to create interactive charts with Plotly

# =============================================================================
# ANALYTICS SECTION
# =============================================================================
# PURPOSE: Display analytics visualizations above the tabs
# STREAMLIT CONCEPT: This appears above all tabs, making it always visible
# FOR BEGINNERS: This shows how to create multiple charts in a grid layout

def render_analytics_section():
    """
    Render analytics visualizations with AI recommendations and 6 charts.
    
    This function displays:
    - AI-powered sport recommendations (if filters are selected)
    - Kursverfügbarkeit nach Wochentag (Bar chart)
    - Kursverfügbarkeit nach Tageszeit (Histogram)
    - Kursverteilung nach Standort (Bar chart)
    - Indoor vs. Outdoor (Pie chart)
    - Intensitäts-Verteilung (Bar chart)
    - Fokus-Verteilung (Bar chart)
    """
    from utils.db import (
        get_events_by_weekday,
        get_events_by_hour,
        get_events_by_location,
        get_events_by_location_type,
        get_offers_by_intensity,
        get_offers_by_focus,
        get_offers_complete
    )
    
    # Get filter state from session_state for AI recommendations
    selected_focus = st.session_state.get('focus', [])
    selected_intensity = st.session_state.get('intensity', [])
    selected_setting = st.session_state.get('setting', [])
    
    # Check if any ML-relevant filters are selected
    has_filters = bool(selected_focus or selected_intensity or selected_setting)
    
    # =========================================================================
    # STATISTICS CHARTS SECTION
    # =========================================================================
    
    # Get all analytics data
    try:
        weekday_data = get_events_by_weekday()
        hour_data = get_events_by_hour()
        location_data = get_events_by_location()
        location_type_data = get_events_by_location_type()
        intensity_data = get_offers_by_intensity()
        focus_data = get_offers_by_focus()
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Laden der Analytics-Daten: {e}")
        return
    
    # Create 3 columns for the first row (3 charts)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 1. Kursverfügbarkeit nach Wochentag
        if weekday_data:
            weekdays = list(weekday_data.keys())
            counts = list(weekday_data.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=weekdays,
                    y=counts,
                    marker_color='#2E86AB',
                    text=counts,
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title=dict(text="Course Availability by Weekday", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Weekday",
                yaxis_title="Number of Courses",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    with col2:
        # 2. Kursverfügbarkeit nach Tageszeit
        if hour_data:
            hours = list(hour_data.keys())
            counts = list(hour_data.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=hours,
                    y=counts,
                    marker_color='#F77F00',
                    text=counts,
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title=dict(text="Course Availability by Time of Day", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Hour (0-23)",
                yaxis_title="Number of Courses",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(tickmode='linear', tick0=0, dtick=2, gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    with col3:
        # 3. Indoor vs. Outdoor
        if location_type_data:
            types = list(location_type_data.keys())
            counts = list(location_type_data.values())
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=types,
                    values=counts,
                    marker_colors=['#2E86AB', '#06A77D', '#F77F00']
                )
            ])
            fig.update_layout(
                title=dict(text="Indoor vs. Outdoor", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12)
            )
            st.plotly_chart(fig, width="stretch")
    
    # Create 3 columns for the second row (3 charts)
    col4, col5, col6 = st.columns(3)
    
    with col4:
        # 4. Kursverteilung nach Standort (Top 10)
        if location_data:
            # Get top 10 locations
            top_locations = dict(list(location_data.items())[:10])
            locations = list(top_locations.keys())
            counts = list(top_locations.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=counts,
                    y=locations,
                    orientation='h',
                    marker_color='#FCBF49',
                    text=counts,
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title=dict(text="Top 10 Locations", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Number of Courses",
                yaxis_title="Location",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    with col5:
        # 5. Intensitäts-Verteilung
        if intensity_data:
            intensities = list(intensity_data.keys())
            counts = list(intensity_data.values())
            
            # Sort by intensity order
            intensity_order = ['Low', 'Moderate', 'High']
            # Create list of tuples for sorting
            intensity_count_pairs = [(intensities[i], counts[i]) for i in range(len(intensities))]
            
            # Sort by intensity order using Python's sorted()
            sorted_pairs = sorted(intensity_count_pairs, key=lambda x: intensity_order.index(x[0]) if x[0] in intensity_order else 999)
            
            # Extract sorted values
            if sorted_pairs:
                intensities_list = []
                counts_list = []
                for pair in sorted_pairs:
                    intensities_list.append(pair[0])
                    counts_list.append(pair[1])
                intensities = intensities_list
                counts = counts_list
            else:
                intensities = []
                counts = []
            
            # Create gradient colors for intensity levels
            intensity_colors = []
            for intensity in intensities:
                if intensity == 'Low':
                    intensity_colors.append('#06A77D')
                elif intensity == 'Moderate':
                    intensity_colors.append('#FCBF49')
                else:  # High
                    intensity_colors.append('#D62828')
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(intensities),
                    y=list(counts),
                    marker_color=intensity_colors,
                    text=list(counts),
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title=dict(text="Intensity Distribution", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Intensity",
                yaxis_title="Number of Offers",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    with col6:
        # 6. Fokus-Verteilung
        if focus_data:
            focus_areas = list(focus_data.keys())
            counts = list(focus_data.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=focus_areas,
                    y=counts,
                    marker_color='#2E86AB',
                    text=counts,
                    textposition='auto',
                )
            ])
            fig.update_layout(
                title=dict(text="Focus Distribution", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Focus Area",
                yaxis_title="Number of Offers",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(tickangle=-45, gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    # =========================================================================
    # AI RECOMMENDATIONS SECTION (appears naturally after statistics if filters are selected)
    # =========================================================================
    if has_filters:
        # Get sports data to exclude already-shown sports
        try:
            sports_data = st.session_state.get('sports_data')
            if not sports_data:
                sports_data = get_offers_complete()
                st.session_state['sports_data'] = sports_data
        except Exception:
            st.warning("⚠️ Could not load sports data for recommendations")
            sports_data = []
        
        if sports_data:
            # Get current filtered results to exclude from recommendations
            search_text = st.session_state.get('search_text', '')
            show_upcoming_only = st.session_state.get('show_upcoming_only', True)
            
            current_filtered = filter_offers(
                sports_data,
                show_upcoming_only=show_upcoming_only,
                search_text=search_text,
                intensity=selected_intensity if selected_intensity else None,
                focus=selected_focus if selected_focus else None,
                setting=selected_setting if selected_setting else None,
                min_match_score=0,
                max_results=1000  # Get all filtered results
            )
            
            # Get default settings from session state
            min_match = st.session_state.get('ml_min_match', 50)
            max_results = st.session_state.get('ml_max_results', 10)
            
            # Get ML recommendations with fallback logic (return ALL recommendations, even 100% matches)
            with st.spinner("🤖 AI is analyzing sports..."):
                recommendations = []
                fallback_thresholds = [min_match, 40, 30, 20, 0]
                
                for threshold in fallback_thresholds:
                    recommendations = get_ml_recommendations(
                        selected_focus=selected_focus,
                        selected_intensity=selected_intensity,
                        selected_setting=selected_setting,
                        min_match_score=threshold,
                        max_results=max_results,
                        exclude_sports=None  # Return all recommendations, even those already in filtered list
                    )
                    if recommendations:
                        break
            
            # Show AI recommendations if available
            if recommendations:
                # Combine filtered results and ML recommendations for Top 3
                all_offers_for_top3 = []
                
                # Add filtered results (they have match_score=100.0)
                for offer in current_filtered:
                    all_offers_for_top3.append({
                        'name': offer.get('name'),
                        'match_score': offer.get('match_score', 100.0),
                        'offer': offer
                    })
                
                # Add ML recommendations
                for rec in recommendations:
                    sport_name = rec['sport']
                    match_score = rec['match_score']
                    # Find full offer data
                    matching_offer = None
                    for offer in sports_data:
                        if offer.get('name') == sport_name:
                            matching_offer = offer
                            break
                    if matching_offer:
                        all_offers_for_top3.append({
                            'name': sport_name,
                            'match_score': match_score,
                            'offer': matching_offer
                        })
                
                # Sort by match score (highest first) and get top 3
                all_offers_for_top3 = sorted(all_offers_for_top3, key=lambda x: x['match_score'], reverse=True)
                top3_combined = all_offers_for_top3[:3]
                
                # Calculate match scores for ALL sports using ML model
                from utils.ml_utils import load_knn_model, build_user_preferences_from_filters, ML_FEATURE_COLUMNS
                import numpy as np
                
                model_data = load_knn_model()
                all_sports_scores = []
                
                if model_data:
                    knn_model = model_data['knn_model']
                    scaler = model_data['scaler']
                    sports_df = model_data['sports_df']
                    
                    # Build user preferences from filters
                    user_prefs = build_user_preferences_from_filters(
                        selected_focus, selected_intensity, selected_setting
                    )
                    
                    # Build feature vector
                    feature_values = []
                    for col in ML_FEATURE_COLUMNS:
                        value = user_prefs.get(col, 0.0)
                        feature_values.append(value)
                    user_vector = np.array(feature_values)
                    user_vector = user_vector.reshape(1, -1)
                    
                    # Scale
                    user_vector_scaled = scaler.transform(user_vector)
                    
                    # Get all sports as neighbors
                    n_sports = len(sports_df)
                    distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
                    
                    # Calculate match scores for all sports
                    for distance, idx in zip(distances[0], indices[0]):
                        sport_name = sports_df.iloc[idx]['Angebot']
                        match_score = (1 - distance) * 100
                        
                        # Find full offer data
                        matching_offer = None
                        for offer in sports_data:
                            if offer.get('name') == sport_name:
                                matching_offer = offer
                                break
                        
                        if matching_offer:
                            # Respect the show_upcoming_only filter (same as main list)
                            if show_upcoming_only and matching_offer.get('future_events_count', 0) == 0:
                                continue  # Skip sports without upcoming events if filter is enabled
                            
                            # Check if sport is in filtered list
                            is_filtered = False
                            for o in current_filtered:
                                if o.get('name') == sport_name:
                                    is_filtered = True
                                    break
                            
                            all_sports_scores.append({
                                'name': sport_name,
                                'match_score': round(match_score, 1),
                                'offer': matching_offer,
                                'is_filtered': is_filtered
                            })
                else:
                    # Fallback: if model not available, use filtered results only
                    for offer in current_filtered:
                        all_sports_scores.append({
                            'name': offer.get('name'),
                            'match_score': offer.get('match_score', 100.0),
                            'offer': offer,
                            'is_filtered': True
                        })
                
                # Prepare data for chart - use all sports with scores
                chart_data = all_sports_scores
                
                # Sort by match score (highest first)
                chart_data = sorted(chart_data, key=lambda x: x['match_score'], reverse=True)
                
                # Limit to top 10 for the graph
                chart_data_top10 = chart_data[:10]
                
                # Calculate average score for chart (using top 10)
                if chart_data_top10:
                    avg_score = sum(d['match_score'] for d in chart_data_top10) / len(chart_data_top10)
                else:
                    avg_score = 0
                
                # Create two columns: left for podest, right for graph
                col_podest, col_graph = st.columns([1, 1])
                
                # Left column: Podest (Top 3 vertically) - compact version
                with col_podest:
                    # Add title above podest (consistent with graph titles)
                    st.markdown("""
                    <div style="text-align: center; margin-bottom: 15px;">
                        <h3 style="color: #000000; font-family: Arial; font-size: 18px; margin: 0;">Top Recommendations</h3>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if len(top3_combined) >= 3:
                        medals = ['🥇', '🥈', '🥉']
                        
                        # Create compact podest using Streamlit components
                        for idx, top_item in enumerate(top3_combined):
                            medal = medals[idx]
                            offer = top_item['offer']
                            sport_name = top_item['name']
                            match_score = top_item['match_score']
                            
                            # Quality indicator with new color palette
                            if match_score >= 90:
                                quality_emoji = "🟢"
                                quality_text = "Excellent"
                                quality_color = "#06A77D"  # Teal
                            elif match_score >= 65:
                                quality_emoji = "🟠"
                                quality_text = "Good"
                                quality_color = "#FCBF49"  # Light orange
                            else:
                                quality_emoji = "🔴"
                                quality_text = "Fair"
                                quality_color = "#D62828"  # Warm red
                            
                            # Get additional features not in user's selection (simplified)
                            additional_focus = []
                            # Check if balance is not in selected focus
                            balance_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'balance':
                                        balance_in_selected = True
                                        break
                            if offer.get('balance') and not balance_in_selected:
                                additional_focus.append('Balance')
                            
                            # Check if flexibility is not in selected focus
                            flexibility_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'flexibility':
                                        flexibility_in_selected = True
                                        break
                            if offer.get('flexibility') and not flexibility_in_selected:
                                additional_focus.append('Flexibility')
                            
                            # Check if strength is not in selected focus
                            strength_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'strength':
                                        strength_in_selected = True
                                        break
                            if offer.get('strength') and not strength_in_selected:
                                additional_focus.append('Strength')
                            
                            # Check if endurance is not in selected focus
                            endurance_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'endurance':
                                        endurance_in_selected = True
                                        break
                            if offer.get('endurance') and not endurance_in_selected:
                                additional_focus.append('Endurance')
                            
                            additional_setting = []
                            # Check if team is not in selected setting
                            team_in_selected = False
                            if selected_setting:
                                for s in selected_setting:
                                    if s.lower() == 'team':
                                        team_in_selected = True
                                        break
                            if offer.get('setting_team') and not team_in_selected:
                                additional_setting.append('Team')
                            
                            # Check if solo is not in selected setting
                            solo_in_selected = False
                            if selected_setting:
                                for s in selected_setting:
                                    if s.lower() == 'solo':
                                        solo_in_selected = True
                                        break
                            if offer.get('setting_solo') and not solo_in_selected:
                                additional_setting.append('Solo')
                            
                            # Build compact features text
                            features_parts = []
                            if additional_focus:
                                features_parts.append(', '.join(additional_focus[:2]))
                            if additional_setting:
                                features_parts.append(', '.join(additional_setting[:2]))
                            if features_parts:
                                features_text = " | ".join(features_parts)
                            else:
                                features_text = "Matches preferences"
                            
                            # Compact container with minimal padding using custom CSS (no shadow, blends with graphs)
                            st.markdown(f"""
                            <div style="border: 1px solid rgba(108, 117, 125, 0.2); border-radius: 6px; padding: 8px; background: rgba(255,255,255,0.8); margin-bottom: 6px;">
                                <div style="font-size: 18px; font-weight: bold; margin-bottom: 2px;">{medal}</div>
                                <div style="font-size: 13px; font-weight: bold; margin-bottom: 2px;">{sport_name}</div>
                                <div style="font-size: 15px; font-weight: bold; margin-bottom: 2px;"><span style="color: #2E86AB;">{match_score:.1f}%</span> <span style="color: {quality_color};">{quality_emoji} {quality_text}</span></div>
                                <div style="font-size: 10px; color: #6C757D; line-height: 1.2;">{features_text}</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Right column: Graph (Top 10)
                with col_graph:
                    # Only show chart if data is available
                    if not chart_data_top10:
                        st.info("No recommendations to display in chart.")
                    else:
                        # Prepare data for chart (top 10)
                        sport_names = []
                        match_scores = []
                        for d in chart_data_top10:
                            sport_names.append(d['name'])
                            match_scores.append(d['match_score'])
                        
                        # Ensure valid data is available
                        has_sport_names = bool(sport_names)
                        has_match_scores = bool(match_scores)
                        lengths_match = len(sport_names) == len(match_scores)
                        if not has_sport_names or not has_match_scores or not lengths_match:
                            st.warning("Data mismatch in chart data.")
                        else:
                            # Build hover tooltips with additional features
                            hover_texts = []
                            for chart_item in chart_data_top10:
                                offer = chart_item['offer']
                                sport_name = chart_item['name']
                                match_score = chart_item['match_score']
                                
                                # Get additional focus tags not in user's selection
                                additional_focus = []
                                focus_map = {
                                    'balance': 'Balance',
                                    'flexibility': 'Flexibility',
                                    'coordination': 'Coordination',
                                    'relaxation': 'Relaxation',
                                    'strength': 'Strength',
                                    'endurance': 'Endurance',
                                    'longevity': 'Longevity'
                                }
                                
                                for key, label in focus_map.items():
                                    label_in_selected = False
                                    if selected_focus:
                                        for f in selected_focus:
                                            if f.lower() == label.lower():
                                                label_in_selected = True
                                                break
                                    if offer.get(key) and not label_in_selected:
                                        additional_focus.append(label)
                                
                                # Get additional intensity if different
                                additional_intensity = None
                                offer_intensity_raw = offer.get('intensity')
                                if offer_intensity_raw:
                                    if isinstance(offer_intensity_raw, str):
                                        offer_intensity = offer_intensity_raw.lower()
                                    else:
                                        offer_intensity = str(offer_intensity_raw).lower()
                                    
                                    intensity_in_selected = False
                                    if selected_intensity:
                                        for i in selected_intensity:
                                            if i.lower() == offer_intensity:
                                                intensity_in_selected = True
                                                break
                                    if offer_intensity and not intensity_in_selected:
                                        additional_intensity = offer_intensity.capitalize()
                                
                                # Get additional setting tags not in user's selection
                                additional_setting = []
                                setting_map = {
                                    'setting_team': 'Team',
                                    'setting_fun': 'Fun',
                                    'setting_duo': 'Duo',
                                    'setting_solo': 'Solo',
                                    'setting_competitive': 'Competitive'
                                }
                                
                                for key, label in setting_map.items():
                                    label_in_selected = False
                                    if selected_setting:
                                        for s in selected_setting:
                                            if s.lower() == label.lower():
                                                label_in_selected = True
                                                break
                                    if offer.get(key) and not label_in_selected:
                                        additional_setting.append(label)
                                
                                # Build hover text
                                hover_parts = [f"<b>{sport_name}</b>", f"Match: {match_score:.1f}%"]
                                
                                if additional_focus:
                                    hover_parts.append(f"<br>Additional Focus: {', '.join(additional_focus[:3])}")
                                if additional_intensity:
                                    hover_parts.append(f"<br>Intensity: {additional_intensity}")
                                if additional_setting:
                                    hover_parts.append(f"<br>Additional Setting: {', '.join(additional_setting[:3])}")
                                
                                hover_texts.append("<br>".join(hover_parts))
                            
                            # Create beautiful horizontal bar chart
                            fig = go.Figure()
                            
                            # Prepare data for horizontal bars
                            display_names = []
                            for name in sport_names:
                                if len(name) > 30:
                                    display_name = f"{name[:30]}..."
                                else:
                                    display_name = name
                                display_names.append(display_name)
                            
                            # Create hover tooltips with additional sport features (only show NON-selected tags)
                            recommendation_hover_tooltips = []
                            for chart_item in chart_data_top10:
                                offer = chart_item['offer']
                                sport_name = chart_item['name']
                                match_score = chart_item['match_score']
                                is_filtered = chart_item.get('is_filtered', False)
                                
                                additional_feature_tags = []
                                
                                # Show NON-selected focus tags that this sport has
                                focus_tag_names = ['balance', 'flexibility', 'coordination', 'relaxation', 'strength', 'endurance', 'longevity']
                                for focus_tag in focus_tag_names:
                                    focus_tag_in_selected = False
                                    if selected_focus:
                                        for f in selected_focus:
                                            if f.lower() == focus_tag:
                                                focus_tag_in_selected = True
                                                break
                                    if offer.get(focus_tag, 0) == 1 and not focus_tag_in_selected:
                                        additional_feature_tags.append(f"🎯 {focus_tag.capitalize()}")
                                
                                # Show intensity if different from selected (handle both numeric and string values)
                                sport_intensity = offer.get('intensity')
                                if sport_intensity is not None:
                                    # Convert numeric intensity to string
                                    if isinstance(sport_intensity, (int, float)):
                                        if sport_intensity <= 0.4:
                                            intensity_level = "low"
                                        elif sport_intensity <= 0.7:
                                            intensity_level = "moderate"
                                        else:
                                            intensity_level = "high"
                                    else:
                                        intensity_level = str(sport_intensity).lower()
                                    
                                    # Check if this intensity is different from selected
                                    intensity_in_selected = False
                                    if selected_intensity:
                                        for i in selected_intensity:
                                            if i.lower() == intensity_level:
                                                intensity_in_selected = True
                                                break
                                    if not selected_intensity or not intensity_in_selected:
                                        additional_feature_tags.append(f"⚡ {intensity_level.capitalize()} Intensity")
                                
                                # Show NON-selected setting tags that this sport has
                                setting_tag_names = ['setting_team', 'setting_fun', 'setting_duo', 'setting_solo', 'setting_competitive']
                                for setting_tag in setting_tag_names:
                                    if offer.get(setting_tag, 0) == 1:
                                        setting_display_name = setting_tag.replace('setting_', '')
                                        setting_in_selected = False
                                        if selected_setting:
                                            for s in selected_setting:
                                                if s.lower() == setting_display_name:
                                                    setting_in_selected = True
                                                    break
                                        if not setting_in_selected:
                                            additional_feature_tags.append(f"🏃 {setting_display_name.capitalize()}")
                                
                                # Build hover text
                                if additional_feature_tags:
                                    tooltip_tags_text = "<br>".join(additional_feature_tags[:6])  # Limit to 6 tags for readability
                                    recommendation_hover_tooltips.append(f"<b>{sport_name}</b><br>" +
                                                      f"Match Score: <b>{match_score:.1f}%</b><br>" +
                                                      f"<br><i>Additional Features:</i><br>{tooltip_tags_text}")
                                else:
                                    recommendation_hover_tooltips.append(f"<b>{sport_name}</b><br>" +
                                                      f"Match Score: <b>{match_score:.1f}%</b><br>")
                            
                            # Add horizontal bars with gradient colors based on match scores
                            bar_colors = []
                            for item in chart_data_top10:
                                bar_colors.append(item['match_score'])
                            
                            # Build text labels for bars
                            text_labels = []
                            for score in match_scores:
                                text_labels.append(f"<b>{score:.1f}%</b>")
                            
                            fig.add_trace(go.Bar(
                                y=display_names,
                                x=match_scores,
                                orientation='h',
                                marker=dict(
                                    color=bar_colors,
                                    colorscale=[[0, '#D62828'], [0.5, '#FCBF49'], [1, '#06A77D']],  # Warm gradient: red -> orange -> teal
                                    cmin=min(match_scores) if match_scores else 0,
                                    cmax=max(match_scores) if match_scores else 100,
                                    line=dict(color='rgba(255,255,255,0.8)', width=2),
                                    opacity=0.85
                                ),
                                text=text_labels,
                                textposition='inside',
                                textfont=dict(color='white', size=12, family='Arial Black'),
                                hovertemplate="%{customdata}<extra></extra>",
                                customdata=recommendation_hover_tooltips,
                                name="AI Recommendations"
                            ))
                            
                            # Calculate dynamic range for x-axis
                            if match_scores:
                                min_score = min(match_scores)
                                max_score = max(match_scores)
                            else:
                                min_score = 0
                                max_score = 100
                            range_min = max(0, (int(min_score) // 10) * 10 - 5)
                            range_max = min(105, ((int(max_score) // 10) + 1) * 10 + 5)
                            
                            # Configure chart layout and styling
                            fig.update_layout(
                                title=dict(
                                    text="Sports you might also like",
                                    x=0.5,
                                    xanchor='center',
                                    font=dict(size=18, family='Arial', color='#000000')
                                ),
                                xaxis=dict(
                                    title="Match Score (%)",
                                    range=[range_min, range_max],
                                    gridcolor='rgba(108, 117, 125, 0.1)',
                                    showgrid=True,
                                    tickfont=dict(size=12, color='#666')
                                ),
                                yaxis=dict(
                                    title="Recommended Sports",
                                    tickfont=dict(size=11, color='#666'),
                                    autorange='reversed',  # Show highest scores at top
                                    gridcolor='rgba(108, 117, 125, 0.1)',
                                    showgrid=True
                                ),
                                height=max(400, len(chart_data_top10) * 35),
                                margin=dict(l=30, r=30, t=70, b=30),
                                paper_bgcolor='#FFFFFF',
                                plot_bgcolor='rgba(0,0,0,0)',
                                showlegend=False,
                                font=dict(family='Inter, system-ui, sans-serif')
                            )
                            
                            # Add average line
                            fig.add_vline(
                                x=avg_score,
                                line_dash="dash",
                                line_color="#F77F00",
                                line_width=2,
                                annotation_text=f"Avg. {avg_score:.1f}%",
                                annotation_position="top",
                                annotation_font_color="#F77F00",
                                annotation_font_size=11
                            )
                            
                            # Display chart with key based on filter values to ensure updates on filter changes
                            filter_key = f"ai_recommendations_{hash(tuple(sorted(selected_focus or [])))}_{hash(tuple(sorted(selected_intensity or [])))}_{hash(tuple(sorted(selected_setting or [])))}"
                            st.plotly_chart(fig, width="stretch", key=filter_key)
            else:
                # Show helpful message when no recommendations found
                # First check if model was loaded successfully
                from utils.ml_utils import load_knn_model
                model_data = load_knn_model()
                if model_data is None:
                    st.warning("⚠️ **KI-Empfehlungen**: Das ML-Modell konnte nicht geladen werden. Bitte stellen Sie sicher, dass das Modell trainiert wurde (führen Sie `ml/train.py` aus).")
                else:
                    st.info(f"🤖 **KI-Empfehlungen**: Keine Empfehlungen gefunden mit einem Match-Score ≥ {min_match}%. Versuchen Sie, den Mindest-Match-Score zu senken oder andere Filter auszuwählen.")

# Call the function to render analytics inside an expander (open by default)
with st.expander("Analytics", expanded=True):
    render_analytics_section()

# =============================================================================
# CREATE TABS
# =============================================================================
# STREAMLIT CONCEPT:
#     st.tabs() creates a tabbed interface; each tab is a context manager
#     entered with a ``with`` block.
#
# LIMITATION:
#     st.tabs() does not support programmatic tab switching. When a user
#     clicks a button, tabs cannot be switched programmatically.
#
# PRACTICAL WORKAROUND:
#     - Store the selected offer in st.session_state when "View Details"
#       is clicked.
#     - The details tab reads that value and shows the corresponding data.
#     - The user then manually switches to the "📅 Course Dates" tab.

tab_overview, tab_details, tab_athletes, tab_profile, tab_about = st.tabs([
    "🎯 Sports Overview",
    "📅 Course Dates",
    "👥 Athletes",
    "⚙️ My Profile",
    "ℹ️ About"
])

# =============================================================================
# PART 6: TAB 1 - SPORTS OVERVIEW
# =============================================================================
# PURPOSE:
#     Show all sports activities with filters and ML recommendations.
# STREAMLIT CONCEPT:
#     Use containers, columns, buttons and expanders to build a structured
#     “list view” over the filtered offers.

with tab_overview:
    # Import database functions
    from utils.db import get_offers_complete, get_events
    
    # =========================================================================
    # LOAD DATA
    # =========================================================================
    # Get all sports offers from database (includes event counts and trainers)
    # BEST PRACTICE: Load data once at the top, not repeatedly in loops
    # ERROR HANDLING: Gracefully handle database connection issues
    try:
        offers_data = get_offers_complete()
    except Exception as e:
        st.error("❌ **Database Connection Error**")
        st.info("""
        This error occurs when the database is not reachable.
        
        **How to investigate:**
        1. Check that `.streamlit/secrets.toml` has valid Supabase credentials.
        2. Verify that your Supabase project is active.
        3. Confirm that your internet connection is working.
        
        You can still explore the code structure even if live data is not available.
        """)
        st.stop()
    
    # Store in session state so other tabs can use it.
    # This makes the data available globally without re-querying the database.
    st.session_state['sports_data'] = offers_data
    
    # =========================================================================
    # GET FILTER VALUES FROM SESSION STATE
    # =========================================================================
    # WHY SESSION STATE IS ESSENTIAL (even with unified sidebar):
    # 
    # 1. Streamlit reruns the ENTIRE script on every interaction
    # 2. Widget values are ephemeral - they reset without session_state
    # 3. When switching tabs, all widgets are recreated from scratch
    # 4. Filter values must be SHARED between sidebar and tab content
    # 5. Without session_state, filters would reset every time you interact
    # 
    # EXAMPLE: User selects "strength" focus → clicks tab → without session_state,
    # the filter would disappear! Session state PERSISTS the value.
    # 
    # PATTERN: Get values with .get() and provide defaults
    search_text = st.session_state.get('search_text', '')
    selected_intensity = st.session_state.get('intensity', [])
    selected_focus = st.session_state.get('focus', [])
    selected_setting = st.session_state.get('setting', [])
    show_upcoming_only = st.session_state.get('show_upcoming_only', True)
    
    # Additional filters for event filtering (if user drills down)
    selected_offers_filter = st.session_state.get('offers', [])
    selected_weekdays = st.session_state.get('weekday', [])
    date_start = st.session_state.get('date_start', None)
    date_end = st.session_state.get('date_end', None)
    time_start_filter = st.session_state.get('start_time', None)
    time_end_filter = st.session_state.get('end_time', None)
    selected_locations = st.session_state.get('location', [])
    hide_cancelled = st.session_state.get('hide_cancelled', True)
    
    # =========================================================================
    # APPLY FILTERS TO OFFERS
    # =========================================================================
    # Use our filter_offers function to get matching activities
    # Never limit results - show all matching activities
    offers = filter_offers(
        offers_data,
        show_upcoming_only=show_upcoming_only,
        search_text=search_text,
        intensity=selected_intensity if selected_intensity else None,
        focus=selected_focus if selected_focus else None,
        setting=selected_setting if selected_setting else None,
        min_match_score=st.session_state.get('min_match_score', 0),
        max_results=100000  # Effectively unlimited - show all results
    )
    
    # =========================================================================
    # ADD ML RECOMMENDATIONS TO THE LIST
    # =========================================================================
    # If filters are selected, get ML recommendations and add them to the list
    has_filters = bool(selected_focus or selected_intensity or selected_setting)
    if has_filters:
        # Get ML recommendations
        min_match = st.session_state.get('ml_min_match', 50)
        max_results = st.session_state.get('ml_max_results', 10)
        
        # Get names of already displayed offers (to avoid duplicates)
        existing_offer_names = {offer.get('name') for offer in offers}
        
        # Calculate match scores for ALL sports using ML model (same as graph)
        # This ensures the list shows the same sports as the graph
        from utils.ml_utils import load_knn_model, build_user_preferences_from_filters, ML_FEATURE_COLUMNS
        import numpy as np
        
        model_data = load_knn_model()
        all_sports_scores = []
        
        if model_data:
            knn_model = model_data['knn_model']
            scaler = model_data['scaler']
            sports_df = model_data['sports_df']
            
            # Build user preferences from filters
            user_prefs = build_user_preferences_from_filters(
                selected_focus, selected_intensity, selected_setting
            )
            
            # Build feature vector using list comprehension
            feature_values = [user_prefs.get(col, 0.0) for col in ML_FEATURE_COLUMNS]
            user_vector = np.array(feature_values)
            user_vector = user_vector.reshape(1, -1)
            
            # Scale
            user_vector_scaled = scaler.transform(user_vector)
            
            # Get all sports as neighbors
            n_sports = len(sports_df)
            distances, indices = knn_model.kneighbors(user_vector_scaled, n_neighbors=n_sports)
            
            # Calculate match scores for all sports
            for distance, idx in zip(distances[0], indices[0]):
                sport_name = sports_df.iloc[idx]['Angebot']
                match_score = (1 - distance) * 100
                
                # Find full offer data
                matching_offer = None
                for offer in offers_data:
                    if offer.get('name') == sport_name:
                        matching_offer = offer.copy()
                        break
                
                if matching_offer:
                    all_sports_scores.append({
                        'name': sport_name,
                        'match_score': round(match_score, 1),
                        'offer': matching_offer
                    })
        
        # Sort by match score and get top recommendations (same as graph)
        all_sports_scores = sorted(all_sports_scores, key=lambda x: x['match_score'], reverse=True)
        # Filter by min_match_score before limiting to max_results
        filtered_scores = []
        for rec in all_sports_scores:
            if rec['match_score'] >= min_match:
                filtered_scores.append(rec)
        if filtered_scores:
            top_ml_recommendations = filtered_scores[:max_results]
        else:
            top_ml_recommendations = []
        
        # Add ML recommendations to the offers list
        # Respect the show_upcoming_only filter from session state
        for rec in top_ml_recommendations:
            sport_name = rec['name']
            match_score = rec['match_score']
            matching_offer = rec['offer']
            
            # Respect the show_upcoming_only filter
            if show_upcoming_only and matching_offer.get('future_events_count', 0) == 0:
                continue  # Skip sports without upcoming events if filter is enabled
            
            # Check if already in the list
            if sport_name not in existing_offer_names:
                # Not in list yet - add it with ML match score
                matching_offer['match_score'] = match_score
                matching_offer['is_ml_recommendation'] = True
                offers.append(matching_offer)
                existing_offer_names.add(sport_name)
            else:
                # Already in list - update match score if ML score is higher
                # This ensures ML recommendations get proper scoring even if they match filters
                for existing_offer in offers:
                    if existing_offer.get('name') == sport_name:
                        # Update with ML match score (which may be more accurate than filter score)
                        existing_offer['match_score'] = match_score
                        existing_offer['is_ml_recommendation'] = True
                        break
    
    # Sort offers by match score (highest first) so ML recommendations appear at the top
    offers = sorted(offers, key=lambda x: x.get('match_score', 0), reverse=True)
    
    # Show toast notification if user just clicked "View Details"
    if st.session_state.get('show_details_hint'):
        st.toast("✅ Activity selected! Click the 📅 Course Dates tab to view full details.", icon="👉")
        # Clear the flag so hint doesn't persist
        del st.session_state['show_details_hint']
    
    # =========================================================================
    # DISPLAY MATCHING ACTIVITIES
    # =========================================================================
    if offers:
        # Loop through each matching offer
        for offer in offers:
            # Load and filter events to get accurate count (needed for expander label)
            events = get_events(offer_href=offer['href'])
            today = datetime.now().date()
            upcoming_events = []
            for e in events:
                event_date = datetime.fromisoformat(
                    str(e.get('start_time')).replace('Z', '+00:00')
                ).date()
                if event_date >= today and not e.get('canceled'):
                    upcoming_events.append(e)
            
            # Apply detail filters if any are set
            has_offer_filter = bool(selected_offers_filter)
            has_weekday_filter = bool(selected_weekdays)
            has_date_start = date_start is not None
            has_date_end = date_end is not None
            has_time_start = time_start_filter is not None
            has_time_end = time_end_filter is not None
            has_location_filter = bool(selected_locations)
            has_any_filter = (has_offer_filter or has_weekday_filter or has_date_start or 
                           has_date_end or has_time_start or has_time_end or has_location_filter)
            if has_any_filter:
                upcoming_events = filter_events(
                    upcoming_events,
                    sport_filter=selected_offers_filter or None,
                    weekday_filter=selected_weekdays or None,
                    date_start=date_start,
                    date_end=date_end,
                    time_start=time_start_filter,
                    time_end=time_end_filter,
                    location_filter=selected_locations or None,
                    hide_cancelled=hide_cancelled
                )
            
            filtered_count = len(upcoming_events)
            
            # Match score badge (for expander label)
            match_score = offer.get('match_score', 0)
            if match_score >= 90:
                score_badge_style = 'background-color: #dcfce7; color: #166534;'
            elif match_score >= 70:
                score_badge_style = 'background-color: #fef9c3; color: #854d0e;'
            else:
                score_badge_style = 'background-color: #f3f4f6; color: #374151;'
            
            # Create expander label with title and match score (without count)
            icon = offer.get('icon', '🏃')
            name = offer.get('name', 'Activity')
            expander_label = f"{icon} {name} • {match_score:.0f}% Match"
            
            # STREAMLIT CONCEPT: st.expander makes the whole card expandable
            with st.expander(expander_label, expanded=False):
                # Compact metadata display using DataFrame table
                # Prepare data
                intensity_value = offer.get('intensity') or ''
                if intensity_value:
                    intensity = intensity_value.capitalize()
                else:
                    intensity = 'N/A'
                if intensity != 'N/A':
                    color_map = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}
                    color_emoji = color_map.get(intensity, '⚪')
                    intensity_display = f"{color_emoji} {intensity}"
                else:
                    intensity_display = "N/A"
                
                focus_display = "N/A"
                if offer.get('focus'):
                    focus_list = []
                    focus_items = offer['focus'][:2]
                    for f in focus_items:
                        if f:
                            focus_list.append(f.capitalize())
                    if len(offer['focus']) > 2:
                        focus_list.append(f"+{len(offer['focus']) - 2}")
                    focus_display = ', '.join(focus_list)
                
                setting_display = "N/A"
                if offer.get('setting'):
                    setting_list = []
                    setting_items = offer['setting'][:2]
                    for s in setting_items:
                        if s:
                            setting_list.append(s.capitalize())
                    setting_display = ', '.join(setting_list)
                
                trainers_display = "N/A"
                trainers = offer.get('trainers', [])
                if trainers:
                    trainer_names = []
                    trainer_items = trainers[:2]
                    for t in trainer_items:
                        trainer_name = t.get('name', '')
                        if trainer_name:
                            trainer_names.append(trainer_name)
                    if len(trainers) > 2:
                        trainer_names.append(f"+{len(trainers)-2}")
                    trainers_display = ', '.join(trainer_names)
                
                rating_display = "No reviews"
                if offer.get('rating_count', 0) > 0:
                    rating = offer.get('avg_rating', 0)
                    rating_display = f"{rating:.1f} ({offer['rating_count']})"
                
                # Create DataFrame with single row
                metadata_df = pd.DataFrame({
                    'Match': [f"{match_score:.0f}%"],
                    'Intensity': [intensity_display],
                    'Focus': [focus_display],
                    'Setting': [setting_display],
                    'Upcoming': [filtered_count if filtered_count > 0 else 0],
                    'Trainers': [trainers_display],
                    'Rating': [rating_display]
                })
                
                # Display as compact table
                st.dataframe(
                    metadata_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Show upcoming dates (now directly in the expander, no nested expander)
                if filtered_count > 0:
                    st.divider()
                    st.subheader(f"Upcoming Dates ({filtered_count})")
                    
                    # Sort by start time (events are already filtered above)
                    upcoming_events = sorted(upcoming_events, key=lambda x: x.get('start_time', ''))
                    
                    if upcoming_events:
                        # English weekday abbreviations
                        weekdays = {
                            'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
                            'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 'Sunday': 'Sun'
                        }
                        
                        # Build table data
                        events_table_data = []
                        for event in upcoming_events[:10]:  # Show max 10
                            start_dt = datetime.fromisoformat(
                                str(event.get('start_time')).replace('Z', '+00:00')
                            )
                            
                            # Format time range
                            end_time = event.get('end_time')
                            if end_time:
                                end_time_str = str(end_time)
                                end_time_clean = end_time_str.replace('Z', '+00:00')
                                end_dt = datetime.fromisoformat(end_time_clean)
                                time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                            else:
                                time_str = start_dt.strftime('%H:%M')
                            
                            # Get weekday abbreviation
                            weekday = weekdays.get(start_dt.strftime('%A'), start_dt.strftime('%A'))
                            
                            events_table_data.append({
                                'date': start_dt.date(),
                                'time': time(start_dt.hour, start_dt.minute),
                                'weekday': weekday,
                                'location': event.get('location_name', 'N/A')
                            })
                        
                        # Display as dataframe with column config
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
                        
                        # Button to view all dates (replaces the red "View Details" button)
                        if len(upcoming_events) > 10:
                            if st.button(
                                f"View all {len(upcoming_events)} dates →",
                                key=f"all_dates_{offer['href']}",
                                use_container_width=True,
                                type="primary"
                            ):
                                # Store selected offer in session state so the details tab
                                # can pick it up and render the corresponding course dates.
                                st.session_state['selected_offer'] = offer
                                st.session_state['show_details_hint'] = True  # Flag to show hint
                        else:
                            # Even if 10 or fewer, show button to view in details tab
                            if st.button(
                                f"View all {len(upcoming_events)} dates in details →",
                                key=f"view_details_{offer['href']}",
                                use_container_width=True,
                                type="primary"
                            ):
                                st.session_state['selected_offer'] = offer
                                st.session_state['show_details_hint'] = True
                    else:
                        st.info("No upcoming dates match your filters")
    else:
        st.info("🔍 No activities found matching your filters.")
        st.caption("Try adjusting your search or filters in the sidebar.")

# =============================================================================
# PART 7: TAB 2 - COURSE DATES
# =============================================================================
# PURPOSE: Show detailed course dates and event information
# STREAMLIT CONCEPT: Event filtering, date/time displays, rating widgets
# FOR BEGINNERS: This shows how to display detailed, filterable event lists

with tab_details:
    # Import necessary functions
    from utils.db import (
        get_events,
        get_user_id_by_sub,
        get_offers_complete
    )
    from utils.rating import (
        render_sportangebot_rating_widget,
        render_trainer_rating_widget,
        get_average_rating_for_offer,
        get_average_rating_for_trainer
    )
    
    # =========================================================================
    # GET SELECTED OFFER (if coming from Overview tab)
    # =========================================================================
    # Check if the user clicked "View Details" on a specific activity.
    # Tabs cannot switch automatically, but they can share data via session_state.
    selected = st.session_state.get('selected_offer', None)
    
    # =========================================================================
    # PAGE HEADER
    # =========================================================================
    # No header text - cleaner design
    
    # =========================================================================
    # ACTIVITY INFO SECTION (only for single activity view)
    # =========================================================================
    if selected:
        # Description in expandable section
        description = selected.get('description')
        if description:
            with st.expander("📖 Activity Description", expanded=False):
                st.markdown(description, unsafe_allow_html=True)
        
        # Compact metadata display using DataFrame table (same style as activity cards)
        intensity_value = selected.get('intensity') or ''
        intensity = intensity_value.capitalize() if intensity_value else 'N/A'
        if intensity != 'N/A':
            color_map = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}
            color_emoji = color_map.get(intensity, '⚪')
            intensity_display = f"{color_emoji} {intensity}"
        else:
            intensity_display = "N/A"
        
        focus_display = "N/A"
        if selected.get('focus'):
            focus_list = []
            focus_items = selected.get('focus', [])[:2]
            for f in focus_items:
                if f:
                    focus_list.append(f.capitalize())
            if len(selected.get('focus', [])) > 2:
                focus_list.append(f"+{len(selected.get('focus', [])) - 2}")
            focus_display = ', '.join(focus_list)
        
        setting_display = "N/A"
        if selected.get('setting'):
            setting_list = []
            setting_items = selected.get('setting', [])[:2]
            for s in setting_items:
                if s:
                    setting_list.append(s.capitalize())
            setting_display = ', '.join(setting_list)
        
        rating_info = get_average_rating_for_offer(selected['href'])
        rating_display = "No reviews"
        if rating_info['count'] > 0:
            rating_display = f"{rating_info['avg']:.1f} ({rating_info['count']})"
        
        # Create DataFrame with single row
        metadata_df = pd.DataFrame({
            'Intensity': [intensity_display],
            'Focus': [focus_display],
            'Setting': [setting_display],
            'Rating': [rating_display]
        })
        
        # Display as compact table
        st.dataframe(
            metadata_df,
            use_container_width=True,
            hide_index=True
        )
        
        # ================================================================
        # RATING SECTION (only for logged-in users, placed prominently)
        # ================================================================
        if is_logged_in():
            # Collect trainers from selected offer (events loaded later)
            all_trainers = set()
            if selected.get('trainers'):
                for trainer in selected.get('trainers', []):
                    if isinstance(trainer, dict):
                        trainer_name = trainer.get('name')
                    else:
                        trainer_name = trainer
                    if trainer_name:
                        all_trainers.add(trainer_name)
            
            # Show ratings in a compact section (no expander to avoid nesting)
            if all_trainers or selected:
                st.markdown("### ⭐ Rate & Review")
                
                # Trainer ratings section
                if all_trainers:
                    st.markdown("**Trainers**")
                    for idx, trainer_name in enumerate(sorted(all_trainers)):
                        rating_info = get_average_rating_for_trainer(trainer_name)
                        
                        # Compact trainer display with rating info
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if rating_info['count'] > 0:
                                stars = '⭐' * int(round(rating_info['avg']))
                                st.markdown(f"**{trainer_name}** {stars} {rating_info['avg']:.1f}/5 ({rating_info['count']})")
                            else:
                                st.markdown(f"**{trainer_name}** - No reviews yet")
                        
                        with col2:
                            if st.button("Rate", key=f"rate_trainer_btn_{trainer_name}", use_container_width=True):
                                st.session_state[f"show_trainer_rating_{trainer_name}"] = not st.session_state.get(f"show_trainer_rating_{trainer_name}", False)
                                st.rerun()
                        
                        # Show rating widget if button was clicked
                        if st.session_state.get(f"show_trainer_rating_{trainer_name}", False):
                            render_trainer_rating_widget(trainer_name)
                        
                        if idx < len(sorted(all_trainers)) - 1:  # Don't show divider after last trainer
                            st.divider()
                    
                    if selected:
                        st.divider()
                
                # Activity rating section
                if selected:
                    st.markdown("**Activity**")
                    rating_info = get_average_rating_for_offer(selected['href'])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if rating_info['count'] > 0:
                            stars = '⭐' * int(round(rating_info['avg']))
                            st.markdown(f"**{selected.get('name', 'Activity')}** {stars} {rating_info['avg']:.1f}/5 ({rating_info['count']} reviews)")
                        else:
                            st.markdown(f"**{selected.get('name', 'Activity')}** - No reviews yet")
                    
                    with col2:
                        if st.button("Rate", key="rate_activity_btn", use_container_width=True):
                            st.session_state["show_activity_rating"] = not st.session_state.get("show_activity_rating", False)
                            st.rerun()
                    
                    # Show rating widget if button was clicked
                    if st.session_state.get("show_activity_rating", False):
                        render_sportangebot_rating_widget(selected['href'])
        
        st.divider()
    
    # =========================================================================
    # LOAD EVENTS
    # =========================================================================
    # Load events - either for specific offer or all events
    # ERROR HANDLING: Gracefully handle database connection issues
    try:
        with st.spinner('🔄 Loading course dates...'):
            if selected:
                events = get_events(offer_href=selected['href'])
            else:
                events = get_events()
    except Exception as e:
        st.error("❌ **Database Connection Error**")
        st.info("""
        Events cannot be loaded because the database connection failed.
        
        **Checklist:**
        - Verify Supabase credentials in `.streamlit/secrets.toml`
        - Make sure the Supabase project is reachable
        """)
        st.stop()
    
    if not events:
        st.info("📅 No course dates available.")
    else:
        # =====================================================================
        # NOTE: Sidebar is already rendered at module level
        # =====================================================================
        # The sidebar is created only once before the tabs; here the filter
        # values that were stored in session_state are read.
        # =====================================================================
        # GET FILTER STATES
        # =====================================================================
        selected_sports = st.session_state.get('offers', [])
        hide_cancelled = st.session_state.get('hide_cancelled', False)  # Show all events by default
        date_start = st.session_state.get('date_start', None)
        date_end = st.session_state.get('date_end', None)
        selected_locations = st.session_state.get('location', [])
        selected_weekdays = st.session_state.get('weekday', [])
        time_start_filter = st.session_state.get('start_time', None)
        time_end_filter = st.session_state.get('end_time', None)
        
        # =====================================================================
        # APPLY FILTERS
        # =====================================================================
        # Filter events step by step for clarity
        filtered_events = []
        
        for e in events:
            # Sport filter
            if selected_sports and e.get('sport_name', '') not in selected_sports:
                continue
            
            # Cancelled filter
            if hide_cancelled and e.get('canceled'):
                continue
            
            # Date filter
            if date_start or date_end:
                start_time = e.get('start_time')
                start_time_str = str(start_time)
                start_time_clean = start_time_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(start_time_clean)
                event_date = start_dt.date()
                
                if date_start and event_date < date_start:
                    continue
                if date_end and event_date > date_end:
                    continue
            
            # Location filter
            if selected_locations and e.get('location_name', '') not in selected_locations:
                continue
            
            # Weekday filter
            if selected_weekdays:
                event_start_time = e.get('start_time')
                event_start_str = str(event_start_time)
                event_start_clean = event_start_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(event_start_clean)
                if start_dt.strftime('%A') not in selected_weekdays:
                    continue
            
            # Time filter
            if time_start_filter or time_end_filter:
                event_start_time = e.get('start_time')
                event_start_str = str(event_start_time)
                event_start_clean = event_start_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(event_start_clean)
                event_time = start_dt.time()
                
                if time_start_filter and event_time < time_start_filter:
                    continue
                if time_end_filter and event_time > time_end_filter:
                    continue
            
            # Event passed all filters
            filtered_events.append(e)
        
        # =====================================================================
        # DISPLAY FILTERED EVENTS
        # =====================================================================
        if not filtered_events:
            st.info("🔍 No events match the selected filters.")
        else:
            # Standardansicht: Tabelle (Cards-Ansicht entfernt)
            # Table View
            table_data = []
            for event in filtered_events:
                event_start_time = event.get('start_time')
                event_start_str = str(event_start_time)
                event_start_clean = event_start_str.replace('Z', '+00:00')
                start_dt = datetime.fromisoformat(event_start_clean)
                end_time = event.get('end_time')
                
                if end_time:
                    end_time_str = str(end_time)
                    end_time_clean = end_time_str.replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(end_time_clean)
                    time_val = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                else:
                    time_val = start_dt.strftime('%H:%M')
                
                # Use English weekday names directly
                weekday = start_dt.strftime('%A')
                
                # Determine event status
                if event.get('canceled'):
                    event_status = "Cancelled"
                else:
                    event_status = "Active"
                
                table_data.append({
                    "date": start_dt.date(),
                    "time": time_val, # Keep as string for range
                    "weekday": weekday,
                    "sport": event.get('sport_name', 'Course'),
                    "location": event.get('location_name', 'N/A'),
                    "trainers": ", ".join(event.get('trainers', [])),
                    "status": event_status
                })
            
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
# PART 8: TAB 3 - ATHLETES
# =============================================================================
# PURPOSE: Social features - discover athletes, send/receive athlete requests
# STREAMLIT CONCEPT: Authentication gates, database queries, user interactions
# FOR BEGINNERS: This shows how to build social features in Streamlit

with tab_athletes:
    # =========================================================================
    # CHECK LOGIN STATUS
    # =========================================================================
    # This tab requires authentication - check if user is logged in
    # PATTERN: Early return pattern for authentication gates
    
    if not is_logged_in():
        # User is NOT logged in - show info message and stop
        st.info("🔒 **Login required** - Sign in with Google in the sidebar to connect with other athletes!")
        
        st.markdown("""
        ### Why sign in?
        - 👥 **Discover Athletes** - Find and connect with other sports enthusiasts
        - 📩 **Athlete Requests** - Send and receive athlete requests
        - 🤝 **Build Your Network** - Connect with your sports community
        - ⭐ **Rate & Review** - Share your experience with courses and trainers
        """)
        st.stop()  # Stop execution here - don't show rest of tab content
    
    # =========================================================================
    # IMPORT FUNCTIONS (only if logged in)
    # =========================================================================
    from utils.db import (
        get_user_id_by_sub,
        get_public_users,
        get_friend_status,
        send_friend_request,
        accept_friend_request,
        reject_friend_request,
        unfollow_user,
        get_pending_friend_requests,
        get_user_friends,
        get_user_by_id
    )
    
    # =========================================================================
    # GET CURRENT USER ID
    # =========================================================================
    # Helper function to get current user's database ID
    def get_current_user_id():
        """
        Get the current user's database ID.
        
        PURPOSE: Convert authentication sub to database user ID
        PATTERN: Try to get existing, sync if missing
        
        Returns:
            User ID (int) or None if error
        """
        user_sub = get_user_sub()
        if not user_sub:
            return None
        
        # Try to get existing user from database
        user_id = get_user_id_by_sub(user_sub)
        
        # If user doesn't exist, try to sync
        if not user_id:
            try:
                sync_user_to_supabase()
                user_id = get_user_id_by_sub(user_sub)
            except:
                pass
        
        return user_id
    
    # Get current user's ID
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            st.error("❌ Error loading your profile. User not found in database.")
            st.info("💡 Try logging out and logging back in.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error loading your profile: {str(e)}")
        st.stop()
    
    # =========================================================================
    # PAGE HEADER
    # =========================================================================
    # No header text - cleaner design
    
    # =========================================================================
    # TWO-COLUMN LAYOUT WITH SEPARATOR
    # =========================================================================
    # STREAMLIT CONCEPT: Three-column layout with narrow middle column for separator
    col_left, col_sep, col_right = st.columns([1, 0.03, 1])
    
    # Vertical separator in middle column
    with col_sep:
        st.markdown("""
        <div style="border-left: 2px solid #e0e0e0; height: 100%; min-height: 500px; margin: 0;"></div>
        """, unsafe_allow_html=True)
    
    # =========================================================================
    # LEFT COLUMN: DISCOVER ATHLETES
    # =========================================================================
    with col_left:
        st.subheader("🔍 Discover Athletes")
        
        # Load public users from database
        with st.spinner('🔄 Loading athletes...'):
            public_users = get_public_users()
        
        if not public_users:
            st.info("📭 No public profiles available yet.")
            st.caption("Be the first to make your profile public in Settings!")
        else:
            # Filter out own profile
            filtered_public_users = []
            for u in public_users:
                if u['id'] != current_user_id:
                    filtered_public_users.append(u)
            public_users = filtered_public_users
            
            if not public_users:
                st.info("📭 No other public profiles available yet.")
                st.caption("Check back later as more athletes join the community!")
            else:
                # Display each user as a card
                for user in public_users:
                    with st.container(border=True):
                        # Three columns: picture, info, action
                        col_pic, col_info, col_action = st.columns([1, 4, 2])
                        
                        with col_pic:
                            # Show profile picture or initials
                            if user.get('picture') and str(user['picture']).startswith('http'):
                                st.image(user['picture'], width=100)
                            else:
                                # Create initials avatar
                                name = user.get('name', 'U')
                                name_words = name.split()[:2]
                                initials_list = []
                                for word in name_words:
                                    if word:
                                        initials_list.append(word[0].upper())
                                initials = ''.join(initials_list)
                                st.markdown(f"""
                                <div style="width: 100px; height: 100px; border-radius: 50%; 
                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                            display: flex; align-items: center; justify-content: center;
                                            color: white; font-size: 32px; font-weight: bold;">
                                    {initials}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col_info:
                            st.markdown(f"### {user.get('name', 'Unknown')}")
                            
                            # Bio preview (first 120 characters)
                            if user.get('bio'):
                                bio = user['bio']
                                if len(bio) > 120:
                                    preview = bio[:120] + "..."
                                else:
                                    preview = bio
                                st.caption(preview)
                            
                            # Metadata (email and join date)
                            metadata = []
                            if user.get('email'):
                                metadata.append(f"📧 {user['email']}")
                            if user.get('created_at'):
                                join_date = user['created_at'][:10]
                                metadata.append(f"📅 Joined {join_date}")
                            
                            if metadata:
                                st.caption(' • '.join(metadata))
                        
                        with col_action:
                            st.write("")  # Spacing
                            
                            # Check friendship status
                            status = get_friend_status(current_user_id, user['id'])
                            
                            # Show different UI based on status
                            if status == "friends":
                                st.success("✓ Connected")
                                if st.button("🗑️ Unfriend", key=f"unfollow_{user['id']}", use_container_width=True):
                                    if unfollow_user(current_user_id, user['id']):
                                        st.success("✅ Unfriended")
                                        st.rerun()
                            
                            elif status == "request_sent":
                                st.info("⏳ Pending")
                            
                            elif status == "request_received":
                                st.warning("📨 Respond")
                            
                            else:
                                # No relationship - show add friend button
                                if st.button(
                                    "➕ Add Friend",
                                    key=f"request_{user['id']}",
                                    use_container_width=True,
                                    type="primary"
                                ):
                                    if send_friend_request(current_user_id, user['id']):
                                        st.success("✅ Request sent!")
                                        st.rerun()
                                    else:
                                        st.warning("Request already pending")
    
    # =========================================================================
    # RIGHT COLUMN: MY ATHLETES
    # =========================================================================
    with col_right:
        # My Athletes section
        st.subheader("👥 My Athletes")
        
        # Athlete Requests Expander under the title
        with st.expander("📩 Athlete Requests", expanded=False):
            # Load pending athlete requests
            with st.spinner('🔄 Loading requests...'):
                requests = get_pending_friend_requests(current_user_id)
            
            if not requests:
                st.info("📭 No pending athlete requests.")
                st.caption("You'll see requests here when other athletes want to connect with you.")
            else:
                request_count = len(requests)
                if request_count != 1:
                    request_text = "requests"
                else:
                    request_text = "request"
                st.caption(f"**{request_count}** pending {request_text}")
                
                # Display each request
                for req in requests:
                    with st.container(border=True):
                        # Extract requester info (with fallback)
                        requester = req.get('requester', {})
                        if isinstance(requester, dict) and len(requester) > 0:
                            requester_name = requester.get('name', 'Unknown')
                            requester_picture = requester.get('picture')
                            requester_email = requester.get('email', '')
                        else:
                            # Fallback: query user separately
                            try:
                                requester_data = get_user_by_id(req['requester_id'])
                                if requester_data:
                                    requester_name = requester_data.get('name', 'Unknown')
                                    requester_picture = requester_data.get('picture')
                                    requester_email = requester_data.get('email', '')
                                else:
                                    requester_name = "Unknown"
                                    requester_picture = None
                                    requester_email = ""
                            except:
                                requester_name = "Unknown"
                                requester_picture = None
                                requester_email = ""
                        
                        # Three columns: picture, info, action
                        col_pic, col_info, col_action = st.columns([1, 4, 2])
                        
                        with col_pic:
                            if requester_picture and str(requester_picture).startswith('http'):
                                st.image(requester_picture, width=80)
                            else:
                                # Create initials avatar
                                initials = ''.join([word[0].upper() for word in requester_name.split()[:2]])
                                st.markdown(f"""
                                <div style="width: 80px; height: 80px; border-radius: 50%; 
                                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                            display: flex; align-items: center; justify-content: center;
                                            color: white; font-size: 28px; font-weight: bold;">
                                    {initials}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        with col_info:
                            st.markdown(f"### {requester_name}")
                            
                            # Metadata
                            metadata = []
                            if requester_email:
                                metadata.append(f"📧 {requester_email}")
                            if req.get('created_at'):
                                request_date = req['created_at'][:10]
                                metadata.append(f"📅 Requested {request_date}")
                            
                            if metadata:
                                st.caption(' • '.join(metadata))
                        
                        with col_action:
                            st.write("")  # Spacing
                            
                            # Accept button
                            if st.button(
                                "✅ Accept",
                                key=f"accept_{req['id']}",
                                use_container_width=True,
                                type="primary"
                            ):
                                if accept_friend_request(req['id'], req['requester_id'], req['addressee_id']):
                                    st.success("✅ Athlete request accepted!")
                                    st.rerun()
                            
                            # Decline button
                            if st.button("❌ Decline", key=f"reject_{req['id']}", use_container_width=True):
                                if reject_friend_request(req['id']):
                                    st.success("Request declined")
                                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Load friends list
        with st.spinner('🔄 Loading athletes...'):
            friends = get_user_friends(current_user_id)
        
        if not friends:
            st.info("👋 No athletes connected yet - start connecting with other athletes!")
            st.caption("Browse the Discover Athletes section to send athlete requests.")
        else:
            # Remove duplicates by tracking unique IDs
            seen_ids = set()
            unique_friends = []
            for friend in friends:
                friend_id = friend.get('id')
                if friend_id and friend_id not in seen_ids:
                    seen_ids.add(friend_id)
                    unique_friends.append(friend)
            
            friend_count = len(unique_friends)
            if friend_count != 1:
                athlete_text = "athletes"
            else:
                athlete_text = "athlete"
            st.caption(f"**{friend_count}** {athlete_text}")
            
            # Display each friend
            for friend in unique_friends:
                with st.container(border=True):
                    # Two columns: picture and info
                    col_pic, col_info = st.columns([1, 5])
                    
                    with col_pic:
                        if friend.get('picture') and str(friend['picture']).startswith('http'):
                            st.image(friend['picture'], width=80)
                        else:
                            # Create initials avatar
                            name = friend.get('name', 'U')
                            initials = ''.join([word[0].upper() for word in name.split()[:2]])
                            st.markdown(f"""
                            <div style="width: 80px; height: 80px; border-radius: 50%; 
                                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                        display: flex; align-items: center; justify-content: center;
                                        color: white; font-size: 28px; font-weight: bold;">
                                {initials}
                            </div>
                            """, unsafe_allow_html=True)
                    
                    with col_info:
                        st.markdown(f"### {friend.get('name', 'Unknown')}")
                        
                        # Metadata
                        metadata = []
                        if friend.get('email'):
                            metadata.append(f"📧 {friend['email']}")
                        if friend.get('bio'):
                            friend_bio = friend['bio']
                            if len(friend_bio) > 80:
                                bio_preview = friend_bio[:80] + "..."
                            else:
                                bio_preview = friend_bio
                            metadata.append(bio_preview)
                        
                        if metadata:
                            st.caption(' • '.join(metadata))

# =============================================================================
# PART 9: TAB 4 - MY PROFILE
# =============================================================================
# PURPOSE: User profile management - view info, set preferences, control visibility
# STREAMLIT CONCEPT: Forms, state management, database updates
# FOR BEGINNERS: This shows how to build user settings pages

with tab_profile:
    # =========================================================================
    # CHECK LOGIN STATUS
    # =========================================================================
    if not is_logged_in():
        st.info("🔒 **Login required** - Sign in with Google in the sidebar to manage your profile!")
        
        st.markdown("""
        ### What you can do with a profile:
        - 📋 **View Your Info** - See your account details and activity
        - ⚙️ **Set Preferences** - Choose your favorite sports and activities  
        - 🌐 **Control Visibility** - Decide who can see your profile
        - 👥 **Track Social Stats** - See your athletes and social connections
        - ⭐ **Rate Activities** - Share your experience with courses and trainers
        """)
        st.stop()
    
    # =========================================================================
    # IMPORTS
    # =========================================================================
    import json
    from utils.db import (
        get_user_complete,
        get_offers_complete,
        update_user_settings
    )
    
    # =========================================================================
    # PAGE HEADER
    # =========================================================================
    # No header text - cleaner design
    
    # =========================================================================
    # LOAD USER PROFILE
    # =========================================================================
    user_sub = get_user_sub()
    if not user_sub:
        st.error("❌ Login required.")
        st.stop()
    
    profile = get_user_complete(user_sub)
    if not profile:
        st.error("❌ Profile not found.")
        st.stop()
    
    # =========================================================================
    # TWO COLUMN LAYOUT WITH SEPARATOR
    # =========================================================================
    col_left, col_separator, col_right = st.columns([1, 0.05, 1])
    
    # =========================================================================
    # LEFT COLUMN: USER INFORMATION & LOGOUT
    # =========================================================================
    with col_left:
        st.subheader("User Information")
        
        # User info card (no border)
        col_pic, col_info = st.columns([1, 3])
        
        with col_pic:
            # Profile picture with fallback
            if profile.get('picture') and str(profile['picture']).startswith('http'):
                st.image(profile['picture'], width=120)
            else:
                # Create initials avatar
                name = profile.get('name', 'U')
                initials = ''.join([word[0].upper() for word in name.split()[:2]])
                st.markdown(f"""
                <div style="width: 120px; height: 120px; border-radius: 50%; 
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            display: flex; align-items: center; justify-content: center;
                            color: white; font-size: 40px; font-weight: bold;">
                    {initials}
                </div>
                """, unsafe_allow_html=True)
        
        with col_info:
            st.markdown(f"### {profile.get('name', 'N/A')}")
            
            # Metadata - structured in separate lines
            if profile.get('email'):
                st.markdown(f"📧 {profile['email']}")
            if profile.get('created_at'):
                st.markdown(f"📅 Member since {profile['created_at'][:10]}")
            if profile.get('last_login'):
                st.markdown(f"🕐 Last login {profile['last_login'][:10]}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Logout option
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            handle_logout()
    
    # =========================================================================
    # SEPARATOR COLUMN: VERTICAL LINE
    # =========================================================================
    with col_separator:
        st.markdown(
            """
            <style>
            .vertical-separator {
                border-left: 2px solid #e0e0e0;
                height: 100vh;
                position: relative;
            }
            </style>
            <div style="border-left: 2px solid #e0e0e0; height: 800px; margin: 0;"></div>
            """,
            unsafe_allow_html=True
        )
    
    # =========================================================================
    # RIGHT COLUMN: SETTINGS
    # =========================================================================
    with col_right:
        st.subheader("Settings")
        
        # =========================================================================
        # FAVORITE SPORTS
        # =========================================================================
        # =========================================================================
        # PROFILE VISIBILITY
        # =========================================================================
        st.markdown("#### Profile Visibility")
        
        # Get current visibility setting
        current_is_public = profile.get('is_public', False)
        
        # Toggle for public/private
        is_public = st.toggle(
            "Make profile public",
            value=current_is_public,
            help="Allow other users to see your profile on the Athletes page"
        )
        
        # Show status message integrated with toggle
        if is_public:
            st.caption("Other users can find you, send athlete requests, and see when you attend courses")
        else:
            st.warning("🔒 Your profile is **private**")
            st.caption("Only you can see your profile and activity")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # =========================================================================
        # SAVE ALL CHANGES BUTTON
        # =========================================================================
        if st.button("💾 Save All Changes", type="secondary", use_container_width=True):
            user_sub = get_user_sub()
            success_count = 0
            error_messages = []
            
            # Save visibility
            try:
                if update_user_settings(user_sub, visibility=is_public):
                    success_count += 1
                else:
                    error_messages.append("Failed to update visibility")
            except Exception as e:
                error_messages.append(f"Error updating visibility: {str(e)}")
            
            # Show results
            if success_count > 0 and not error_messages:
                st.success("✅ All changes saved successfully!")
                st.rerun()
            elif success_count > 0:
                st.warning(f"⚠️ Some changes saved, but errors occurred: {', '.join(error_messages)}")
                st.rerun()
            else:
                st.error(f"❌ Failed to save changes: {', '.join(error_messages)}")

# =============================================================================
# PART 10: TAB 5 - ABOUT
# =============================================================================
# PURPOSE: Information about the app, data sources, and project team
# STREAMLIT CONCEPT: Simple information display, formatting
# FOR BEGINNERS: This shows how to create informational pages

with tab_about:
    # No header text - cleaner design
    
    # (Data status section removed on request)
    
    # =========================================================================
    # TWO COLUMN LAYOUT WITH SEPARATOR
    # =========================================================================
    col_left, col_separator, col_right = st.columns([1, 0.05, 1])
    
    # =========================================================================
    # LEFT COLUMN: HOW IT WORKS
    # =========================================================================
    with col_left:
        st.subheader("💡 How This App Works")
        st.markdown("""
        **What's happening behind the scenes?**
        
        1. **Automated Data Collection:** Python scripts automatically scrape Unisport websites 
           (offers, courses, dates, locations) via GitHub Actions on a regular schedule.
        
        2. **Data Storage:** All data is stored in Supabase, our hosted PostgreSQL database.
        
        3. **Real-time Display:** This Streamlit app loads data directly from Supabase and 
           displays it here in real-time.
        
        4. **Smart Features:** AI-powered recommendations using Machine Learning (KNN algorithm), 
           advanced filtering system, ratings, and social networking.
        
        **Tech Stack:**
        - **Frontend:** Streamlit (Python web framework)
        - **Database:** Supabase (PostgreSQL)
        - **ML:** scikit-learn (KNN recommender)
        - **Visualization:** Plotly (interactive charts)
        - **Authentication:** Google OAuth via Streamlit
        """)
    
    # =========================================================================
    # SEPARATOR COLUMN: VERTICAL LINE
    # =========================================================================
    with col_separator:
        st.markdown(
            """
            <style>
            .vertical-separator {
                border-left: 2px solid #e0e0e0;
                height: 100vh;
                position: relative;
            }
            </style>
            <div style="border-left: 2px solid #e0e0e0; height: 800px; margin: 0;"></div>
            """,
            unsafe_allow_html=True
        )
    
    # =========================================================================
    # RIGHT COLUMN: PROJECT TEAM AND PROJECT BACKGROUND
    # =========================================================================
    with col_right:
        # =========================================================================
        # PROJECT TEAM
        # =========================================================================
        st.subheader("👥 Project Team")
        
        # Team members with LinkedIn profiles
        # Use local images from assets/images folder
        assets_path = Path(__file__).resolve().parent / "assets" / "images"
        team = [
            (
                "Tamara Nessler",
                "https://www.linkedin.com/in/tamaranessler/",
                str(assets_path / "tamara.jpeg"),
            ),
            (
                "Till Banerjee",
                "https://www.linkedin.com/in/till-banerjee/",
                str(assets_path / "till.jpeg"),
            ),
            (
                "Sarah Bugg",
                "https://www.linkedin.com/in/sarah-bugg/",
                str(assets_path / "sarah.jpeg"),
            ),
            (
                "Antonia Büttiker",
                "https://www.linkedin.com/in/antonia-büttiker-895713254/",
                str(assets_path / "antonia.jpeg"),
            ),
            (
                "Luca Hagenmayer",
                "https://www.linkedin.com/in/lucahagenmayer/",
                str(assets_path / "luca.jpeg"),
            ),
        ]
        
        # Display team in a grid (5 columns)
        cols = st.columns(5)
        for idx, (name, url, avatar) in enumerate(team):
            with cols[idx]:
                st.image(avatar, width=180)
                st.markdown(f"**[{name}]({url})**", unsafe_allow_html=True)
        
        st.divider()
        
        # =========================================================================
        # PROJECT CONTEXT
        # =========================================================================
        st.subheader("🎓 Project Background")
        st.markdown("""
        This project was created for the course **"Fundamentals and Methods of Computer Science"** 
        at the University of St.Gallen, taught by:
        - Prof. Dr. Stephan Aier
        - Dr. Bernhard Bermeitinger
        - Prof. Dr. Simon Mayer
        
        **Status:** Still in development and not yet reviewed by professors.
        
        **Feedback?** Have feature requests or found bugs? Please contact one of the team members 
        via LinkedIn (see above).
        """)


# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.

