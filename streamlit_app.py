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
    utils service modules (auth/db/ml/filters/formatting)
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
    is_logged_in, 
    sync_user_to_supabase, 
    check_token_expiry, 
    handle_logout,
    get_user_sub
)

# Database connection and query functions are imported from utils below

# Utility functions (refactored from this file)
from utils import (
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
        
        # Data states (will be populated from database)
        'sports_data': None,
    }
    
    # Only set defaults if key doesn't exist (preserve user selections)
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# =============================================================================
# DATA LOADING (Early, before sidebar rendering)
# =============================================================================
# Load data early so it's available for sidebar filters and all tabs
# IMPORTANT: Wrap in try-except to ensure tabs (especially About) are always accessible
from utils.db import get_offers_complete, get_events

if 'sports_data' not in st.session_state:
    try:
        st.session_state['sports_data'] = get_offers_complete()
    except Exception as e:
        # If data loading fails, use empty list to allow app to continue
        # This ensures About tab and other tabs remain accessible
        st.session_state['sports_data'] = []

if 'events_data' not in st.session_state:
    try:
        st.session_state['events_data'] = get_events()
    except Exception as e:
        # If data loading fails, use empty list to allow app to continue
        st.session_state['events_data'] = []

sports_data = st.session_state.get('sports_data', [])
events = st.session_state.get('events_data', [])

# =============================================================================
# UNIFIED SIDEBAR (Rendered once at module level)
# =============================================================================
# IMPORTANT:
#     The sidebar must be rendered once at module level, not separately
#     inside each tab. Re-rendering it per tab would create duplicate
#     widget keys and scattered state.
#
# PATTERN:
#     - Render sidebar directly here, before defining tabs.
#     - Keep user info and all filters in this single sidebar.
#     - Read the resulting values from st.session_state inside the tabs.

with st.sidebar:
        # =================================================================
        # USER INFO SECTION (Always shown first)
        # =================================================================
        # DESIGN NOTE: User info lives directly in the sidebar instead of
        # a nested helper to avoid nested sidebar contexts and duplicate keys.
        
        if not is_logged_in():
            # === NOT LOGGED IN: Show login UI ===
            with st.container():
                st.markdown("### 🎯 UnisportAI")
                st.markdown("Sign in to access all features")
            
            # Login button using Streamlit's authentication
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
            
            # Display compact, centered user info
            if user_picture and str(user_picture).startswith('http'):
                st.image(user_picture, width=50, use_container_width=False)
            else:
                # Create initials avatar with circular background
                name_words = user_name.split()[:2]
                initials = ''.join([word[0].upper() for word in name_words if word])
                st.markdown(
                    f"<div style='text-align: center; font-size: 20px; font-weight: bold; padding: 12px; background-color: #667eea; color: white; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin: 0 auto 8px;'>{initials}</div>",
                    unsafe_allow_html=True
                )
            
            st.markdown(f"<div style='text-align: center;'><strong>{user_name}</strong></div>", unsafe_allow_html=True)
            st.caption(f"<div style='text-align: center;'>{user_email}</div>", unsafe_allow_html=True)
            st.markdown("")
        
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
        
        st.markdown("")
        
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
                
                st.markdown("")
                
                # --- Show Upcoming Only Checkbox ---
                show_upcoming = st.checkbox(
                    "📅 Show upcoming only",
                    value=st.session_state.get('show_upcoming_only', True),
                    key="unified_show_upcoming"
                )
                st.session_state['show_upcoming_only'] = show_upcoming
        
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
                
                st.markdown("")
                
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
                
                st.markdown("")
                
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
                
                st.markdown("")
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
# AUTHENTICATION CHECK
# =============================================================================
# If user is logged in, sync with database and check token
if is_logged_in():
    check_token_expiry()  # Make sure authentication hasn't expired
    try:
        sync_user_to_supabase()  # Sync user data to our database
    except Exception as e:
        st.warning(f"Error syncing user: {e}")

# Sidebar is already rendered above at module level

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
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Laden der Analytics-Daten: {e}")
        return
    
    # Create 2 columns for the charts
    col1, col2 = st.columns(2)
    
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
            # Filter: Nur Stunden zwischen 6 und 22 Uhr
            filtered_hours = {h: hour_data.get(h, 0) for h in range(6, 23)}
            
            # Formatierung: Stunden als "06:00", "07:00", etc.
            hours_formatted = [f"{h:02d}:00" for h in range(6, 23)]
            counts = [filtered_hours[h] for h in range(6, 23)]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=hours_formatted,
                    y=counts,
                    marker_color='#F77F00',
                )
            ])
            fig.update_layout(
                title=dict(text="Course Availability by Time of Day", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Time",
                yaxis_title="Number of Courses",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=2,
                    gridcolor='rgba(108, 117, 125, 0.1)',
                    showgrid=True,
                    tickangle=-45
                ),
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
            # Get filter values from session state
            search_text = st.session_state.get('search_text', '')
            show_upcoming_only = st.session_state.get('show_upcoming_only', True)
            min_match = st.session_state.get('ml_min_match', 50)
            
            # Get event filters from session state (for soft filtering)
            event_filters = {}
            selected_weekdays = st.session_state.get('weekday', [])
            date_start = st.session_state.get('date_start', None)
            date_end = st.session_state.get('date_end', None)
            time_start = st.session_state.get('start_time', None)
            time_end = st.session_state.get('end_time', None)
            selected_locations = st.session_state.get('location', [])
            
            if selected_weekdays:
                event_filters['weekday'] = selected_weekdays
            if date_start:
                event_filters['date_start'] = date_start
            if date_end:
                event_filters['date_end'] = date_end
            if time_start:
                event_filters['time_start'] = time_start
            if time_end:
                event_filters['time_end'] = time_end
            if selected_locations:
                event_filters['location'] = selected_locations
            
            # Get merged recommendations using the new unified function
            with st.spinner("🤖 AI is analyzing sports..."):
                from utils.ml_utils import get_merged_recommendations
                
                # Try with user's min_match, then fallback to lower thresholds
                fallback_thresholds = [min_match, 40, 30, 20, 0]
                all_recommendations = []
                
                for threshold in fallback_thresholds:
                    all_recommendations = get_merged_recommendations(
                        sports_data=sports_data,
                        selected_focus=selected_focus,
                        selected_intensity=selected_intensity,
                        selected_setting=selected_setting,
                        search_text=search_text,
                        show_upcoming_only=show_upcoming_only,
                        event_filters=event_filters if event_filters else None,
                        min_match_score=threshold
                    )
                    if all_recommendations:
                        break
            
            # Show AI recommendations if available
            if all_recommendations:
                # Get top 3 for podest
                top3_combined = all_recommendations[:3]
                
                # Get next 10 for graph (excluding top 3)
                top3_names = {item['name'] for item in top3_combined}
                chart_data_filtered = [item for item in all_recommendations if item['name'] not in top3_names]
                chart_data_top10 = chart_data_filtered[:10]
                
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
                    st.markdown("### Top Recommendations")
                    
                    if top3_combined:
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
                            
                            # Compact container using Streamlit-native components
                            with st.container(border=True):
                                st.markdown(f"**{medal} {sport_name}**")
                                st.markdown(f"**{match_score:.1f}%** {quality_emoji} {quality_text}")
                                st.caption(features_text)
                
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
# Only show analytics if user is logged in or if we can safely access the database
try:
    with st.expander("Analytics", expanded=True):
        render_analytics_section()
except Exception as e:
    # If analytics fails, don't stop the app - just skip it
    # This ensures the About tab is always accessible
    pass

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

tab_overview, tab_details, tab_profile, tab_about = st.tabs([
    "🎯 Sports Overview",
    "📅 Course Dates",
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
    from utils.filters import filter_offers, filter_events
    
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
        # Don't stop execution - allow other tabs (like About) to still work
        offers_data = []
    
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
    # APPLY EVENT FILTERS TO FILTER OFFERS BY THEIR EVENTS
    # =========================================================================
    # If any event filters are selected, filter offers to only show those
    # that have matching events
    has_event_filters = bool(
        selected_offers_filter or selected_weekdays or date_start or date_end or
        time_start_filter or time_end_filter or selected_locations or hide_cancelled
    )
    
    if has_event_filters:
        # Load events to check which offers have matching events
        try:
            all_events = get_events()
            
            # Filter events based on event filters
            filtered_events = filter_events(
                all_events,
                sport_filter=selected_offers_filter if selected_offers_filter else None,
                weekday_filter=selected_weekdays if selected_weekdays else None,
                date_start=date_start,
                date_end=date_end,
                time_start=time_start_filter,
                search_text=search_text,
                time_end=time_end_filter,
                location_filter=selected_locations if selected_locations else None,
                hide_cancelled=hide_cancelled
            )
            
            # Get set of sport names that have matching events
            sports_with_matching_events = set()
            for event in filtered_events:
                sport_name = event.get('sport_name', '')
                if sport_name:
                    sports_with_matching_events.add(sport_name)
            
            # Filter offers to only include those with matching events
            if sports_with_matching_events:
                offers = [offer for offer in offers if offer.get('name', '') in sports_with_matching_events]
            else:
                # No events match the filters, so no offers should be shown
                offers = []
        except Exception as e:
            # If event loading fails, continue with offers filtered by offer filters only
            st.warning(f"⚠️ Could not apply event filters: {e}")
    
    # =========================================================================
    # MERGE FILTERED RESULTS WITH ML RECOMMENDATIONS
    # =========================================================================
    # If filters are selected, use merged recommendations (combines filtered + ML)
    has_filters = bool(selected_focus or selected_intensity or selected_setting)
    if has_filters:
        # Get merged recommendations using the unified function
        min_match = st.session_state.get('ml_min_match', 50)
        
        # Prepare event filters for get_merged_recommendations
        event_filters = {}
        if selected_weekdays:
            event_filters['weekday'] = selected_weekdays
        if date_start:
            event_filters['date_start'] = date_start
        if date_end:
            event_filters['date_end'] = date_end
        if time_start_filter:
            event_filters['time_start'] = time_start_filter
        if time_end_filter:
            event_filters['time_end'] = time_end_filter
        if selected_locations:
            event_filters['location'] = selected_locations
        
        # Get merged recommendations (combines filtered + ML, applies all filters)
        from utils.ml_utils import get_merged_recommendations
        
        # Try with user's min_match, then fallback to lower thresholds
        fallback_thresholds = [min_match, 40, 30, 20, 0]
        merged_recommendations = []
        
        for threshold in fallback_thresholds:
            merged_recommendations = get_merged_recommendations(
                sports_data=offers_data,
                selected_focus=selected_focus,
                selected_intensity=selected_intensity,
                selected_setting=selected_setting,
                search_text=search_text,
                show_upcoming_only=show_upcoming_only,
                event_filters=event_filters if event_filters else None,
                min_match_score=threshold
            )
            if merged_recommendations:
                break
        
        # Convert merged recommendations to offers format
        # The merged recommendations already have match_score and are sorted
        offers = []
        for rec in merged_recommendations:
            offer = rec['offer'].copy()
            offer['match_score'] = rec['match_score']
            offers.append(offer)
    else:
        # No ML filters selected - just use filtered results
        # Sort by match score (highest first)
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
                    search_text=search_text,
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
                
                # Create DataFrame with single row
                metadata_df = pd.DataFrame({
                    'Match': [f"{match_score:.0f}%"],
                    'Intensity': [intensity_display],
                    'Focus': [focus_display],
                    'Setting': [setting_display],
                    'Upcoming': [filtered_count if filtered_count > 0 else 0],
                    'Trainers': [trainers_display]
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
                                st.rerun()
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
                                st.rerun()
                    else:
                        st.info("No upcoming dates match your filters")
    else:
        st.info("🔍 No activities found matching your filters.")
        st.caption("Try adjusting your search or filters in the sidebar.")

# =============================================================================
# PART 7: TAB 2 - COURSE DATES
# =============================================================================
# PURPOSE: Show detailed course dates and event information
# STREAMLIT CONCEPT: Event filtering, date/time displays
# FOR BEGINNERS: This shows how to display detailed, filterable event lists

with tab_details:
    # Import necessary functions
    from utils.db import (
        get_events,
        get_user_id_by_sub,
        get_offers_complete
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
        
        # Create DataFrame with single row
        metadata_df = pd.DataFrame({
            'Intensity': [intensity_display],
            'Focus': [focus_display],
            'Setting': [setting_display]
        })
        
        # Display as compact table
        st.dataframe(
            metadata_df,
            use_container_width=True,
            hide_index=True
        )
        
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
        # Don't stop execution - allow other tabs (like About) to still work
        events = []
    
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
        search_text = st.session_state.get('search_text', '')
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
            # Search text filter (check first for performance)
            if search_text:
                search_text_lower = search_text.lower()
                # Search in sport name
                sport_name = e.get('sport_name', '').lower()
                # Search in location name
                location_name = e.get('location_name', '').lower()
                # Search in trainer names
                trainers = e.get('trainers', [])
                trainer_names = []
                for trainer in trainers:
                    if isinstance(trainer, dict):
                        trainer_names.append(trainer.get('name', '').lower())
                    else:
                        trainer_names.append(str(trainer).lower())
                trainer_names_str = ' '.join(trainer_names)
                
                # Check if search text matches any field
                if (search_text_lower not in sport_name and 
                    search_text_lower not in location_name and 
                    search_text_lower not in trainer_names_str):
                    continue
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
        st.info("🔒 **Login required** - Sign in with Google in the sidebar")
        
        st.markdown("""
        ### What you can do with a profile:
        - 📋 **View Your Info** - See your account details (name, email, member since)
        """)
        # Don't use st.stop() - it stops the entire app, preventing other tabs from loading
    else:
        # =========================================================================
        # IMPORTS
        # =========================================================================
        import json
        from utils.db import (
            get_user_complete,
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
        else:
            profile = get_user_complete(user_sub)
            if not profile:
                st.error("❌ Profile not found.")
            else:
                # =========================================================================
                # TWO COLUMN LAYOUT
                # =========================================================================
                col_left, col_right = st.columns(2)
                
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
                            # Create initials avatar using Streamlit-native approach
                            name = profile.get('name', 'U')
                            initials = ''.join([word[0].upper() for word in name.split()[:2]])
                            st.markdown(f"## {initials}")
                    
                    with col_info:
                        st.markdown(f"### {profile.get('name', 'N/A')}")
                        
                        # Metadata - structured in separate lines
                        if profile.get('email'):
                            st.markdown(f"📧 {profile['email']}")
                        if profile.get('created_at'):
                            st.markdown(f"📅 Member since {profile['created_at'][:10]}")
                        if profile.get('last_login'):
                            st.markdown(f"🕐 Last login {profile['last_login'][:10]}")
                    
                    st.markdown("")
                
                # Logout-Button ganz unten in der rechten Spalte
                with col_right:
                    st.markdown("---")
                    if st.button("🚪 Logout", type="secondary", use_container_width=True):
                        handle_logout()

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
    # TWO COLUMN LAYOUT
    # =========================================================================
    col_left, col_right = st.columns(2)
    
    # =========================================================================
    # LEFT COLUMN: HOW IT WORKS
    # =========================================================================
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
    
    # =========================================================================
    # RIGHT COLUMN: PROJECT TEAM AND PROJECT BACKGROUND
    # =========================================================================
    with col_right:
        # =========================================================================
        # PROJECT TEAM
        # =========================================================================
        st.subheader("Project Team")
        
        # Team members with LinkedIn profiles
        # Use local images from assets/images folder
        assets_path = Path(__file__).resolve().parent / "assets" / "images"
        team_members = [
            {"name": "Tamara Nessler", "url": "https://www.linkedin.com/in/tamaranessler/", "avatar": str(assets_path / "tamara.jpeg")},
            {"name": "Till Banerjee", "url": "https://www.linkedin.com/in/till-banerjee/", "avatar": str(assets_path / "till.jpeg")},
            {"name": "Sarah Bugg", "url": "https://www.linkedin.com/in/sarah-bugg/", "avatar": str(assets_path / "sarah.jpeg")},
            {"name": "Antonia Büttiker", "url": "https://www.linkedin.com/in/antonia-büttiker-895713254/", "avatar": str(assets_path / "antonia.jpeg")},
            {"name": "Luca Hagenmayer", "url": "https://www.linkedin.com/in/lucahagenmayer/", "avatar": str(assets_path / "luca.jpeg")},
        ]
        
        # Display team in a grid (5 columns)
        cols = st.columns(5)
        for idx, member in enumerate(team_members):
            with cols[idx]:
                st.image(member["avatar"], width=180)
                st.markdown(f"[{member['name']}]({member['url']})")
        
        # Define tasks (reversed order so first task appears at top)
        tasks = [
            "Video & Cut",
            "Testing & Bug-Fixing",
            "Code Documentation",
            "Backend incl. DB",
            "Machine Learning",
            "Frontend",
            "Requirements mapping & prototyping",
            "Project organization & planning"
        ]
        
        # Contribution matrix: each row = task, each column = team member
        # Values: 3 = Main Contribution, 2 = Contribution, 1 = Supporting Role
        # Order: Tamara, Till, Sarah, Antonia, Luca
        # Note: Matrix is reversed to match reversed tasks list
        contribution_matrix = [
            [1, 1, 3, 3, 1],  # Video & Cut
            [2, 3, 2, 2, 3],  # Testing & Bug-Fixing
            [2, 2, 1, 1, 2],  # Code Documentation
            [1, 2, 1, 1, 3],  # Backend incl. DB
            [2, 3, 1, 1, 2],  # Machine Learning
            [1, 2, 1, 1, 3],  # Frontend
            [3, 1, 2, 2, 1],  # Requirements mapping & prototyping
            [3, 3, 3, 3, 3],  # Project organization & planning
        ]
        
        # Text labels for hover tooltips
        label_map = {3: "Main Contribution", 2: "Contribution", 1: "Supporting Role"}
        matrix_text = [[label_map[val] for val in row] for row in contribution_matrix]
        
        member_names = [member["name"].split()[0] for member in team_members]  # First names only
        
        # Create Plotly heatmap
        # Simple approach: directly use numeric values (3, 2, 1) for colors
        fig = go.Figure(data=go.Heatmap(
            z=contribution_matrix,
            x=member_names,
            y=tasks,
            text=matrix_text,
            colorscale=[
                [0.0, '#F77F00'],   # 1 = Supporting Role (Orange)
                [0.5, '#06A77D'],   # 2 = Contribution (Green)
                [1.0, '#2E86AB']    # 3 = Main Contribution (Blue)
            ],
            hovertemplate='<b>%{y}</b><br>%{x}: <b>%{text}</b><extra></extra>',
            showscale=True,  # Hide color scale
            xgap=2,
            ygap=2
        ))
        
        fig.update_layout(
            title=dict(text='Team Contribution Matrix', x=0.5, xanchor='center', font=dict(size=20, family='Arial, sans-serif')),
            xaxis_title="Team Members",
            yaxis_title="",
            margin=dict(l=220, r=120, t=100, b=80),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(size=12),
            xaxis=dict(tickfont=dict(size=12)),
            yaxis=dict(tickfont=dict(size=11))
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # =========================================================================
    # PROJECT CONTEXT (Full width below the two columns)
    # =========================================================================
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