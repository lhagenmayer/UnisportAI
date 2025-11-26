"""pages.details

Streamlit page that shows course dates and allows users to join or cancel
attendance. The module handles filtering of events, rendering of event
cards, and providing rating widgets for trainers and activities.

This file is executed as a Streamlit page and relies on application state
managed in `data.state_manager` and events/offers data from Supabase.
"""

import streamlit as st
from datetime import datetime, time, timedelta
from data.supabase_client import (
    get_events_for_offer, 
    get_all_events,
    get_user_id_by_sub,
    is_user_going_to_event,
    get_friends_going_to_event,
    mark_user_going_to_event,
    unmark_user_going_to_event
)
from data.state_manager import (
    get_selected_offers_for_page2, get_filter_state, set_filter_state,
    get_nav_offer_hrefs, clear_nav_offer_hrefs, clear_nav_offer_name,
    clear_selected_offers_multiselect, has_selected_offer, get_selected_offer,
    set_selected_offer, set_multiple_offers, has_multiple_offers
)
from data.shared_sidebar import render_filters_sidebar
from data.rating import render_sportangebot_rating_widget, render_trainer_rating_widget, get_average_rating_for_offer, get_average_rating_for_trainer
from data.auth import is_logged_in, get_user_sub

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Helper functions
def get_user_id():
    """Return the database user id for the currently authenticated user.

    Returns:
        int | None: The `id` value from the users table, or ``None`` when
        no authenticated user is available.
    """
    user_sub = get_user_sub()
    if not user_sub:
        return None

    return get_user_id_by_sub(user_sub)

def get_event_id(event):
    """Create a stable event identifier used for attendance tracking.

    The ID is a simple concatenation of fields that uniquely represent an
    event instance. It is used by attendance-related functions to check
    and mark users as going.

    Args:
        event (dict): Event record returned from Supabase with keys like
            ``kursnr``, ``start_time`` and ``location_name``.

    Returns:
        str: A string identifier for the event.
    """
    return f"{event.get('kursnr', '')}_{event.get('start_time', '')}_{event.get('location_name', '')}"

# Get current user
current_user_id = get_user_id()

# Handle navigation state
nav_offer_hrefs = get_nav_offer_hrefs()
if nav_offer_hrefs:
    if has_selected_offer():
        from data.state_manager import clear_selected_offer
        clear_selected_offer()
    
    from data.supabase_client import get_offers_with_stats
    all_offers = get_offers_with_stats()
    
    set_multiple_offers(nav_offer_hrefs)
    
    for offer in all_offers:
        if offer.get('href') == nav_offer_hrefs[0]:
            set_selected_offer(offer)
            break
    
    clear_nav_offer_hrefs()
    clear_nav_offer_name()
    clear_selected_offers_multiselect()

# Get selected offer
selected = get_selected_offer() if has_selected_offer() else None
showing_multiple_offers = has_multiple_offers()

# Page header
if not has_selected_offer():
    st.title("📅 Course Dates")
    st.caption("All upcoming course dates")
elif showing_multiple_offers:
    icon = selected.get('icon', '🏃')
    name = selected.get('name', 'Sports Activity').split(' Level')[0]
    st.title(f"{icon} {name}")
    st.caption("Course dates for selected activities")
else:
    st.title(f"{selected.get('icon', '🏃')} {selected.get('name', 'Sports Activity')}")
    st.caption("View and register for upcoming course dates")

# Activity info section (only for single activity view)
if has_selected_offer() and not has_multiple_offers():
    # Description
    description = selected.get('description')
    if description:
        with st.expander("📖 Activity Description", expanded=False):
            st.markdown(description, unsafe_allow_html=True)
    
    # Metrics in clean columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        intensity = (selected.get('intensity') or 'N/A').capitalize()
        color_map = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}
        intensity_icon = color_map.get(intensity, '⚪')
        st.metric("Intensity", f"{intensity_icon} {intensity}")
    
    with col2:
        focus = ', '.join([f.capitalize() for f in selected.get('focus', [])][:2])
        if len(selected.get('focus', [])) > 2:
            focus += '...'
        st.metric("Focus", focus or 'N/A')
    
    with col3:
        setting = ', '.join([s.capitalize() for s in selected.get('setting', [])][:2])
        st.metric("Setting", setting or 'N/A')
    
    with col4:
        rating_info = get_average_rating_for_offer(selected['href'])
        if rating_info['count'] > 0:
            stars = '⭐' * int(round(rating_info['avg']))
            st.metric("Rating", f"{stars} {rating_info['avg']:.1f}")
            st.caption(f"{rating_info['count']} reviews")
        else:
            st.metric("Rating", "No reviews yet")
    
    st.divider()

# Load events
with st.spinner('🔄 Loading course dates...'):
    if not has_selected_offer():
        events = get_all_events()
    elif showing_multiple_offers:
        selected_offers_to_use = get_selected_offers_for_page2()
        all_events = get_all_events()
        events = [e for e in all_events if e.get('offer_href') in selected_offers_to_use]
        
        # Remove duplicates
        seen = set()
        unique_events = []
        for e in events:
            key = (e.get('kursnr'), e.get('start_time'))
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        events = unique_events
        events.sort(key=lambda x: x.get('start_time', ''))
    else:
        events = get_events_for_offer(selected['href'])

if not events:
    st.info("📅 No course dates available.")
    st.stop()

# Load sports data for activity filters (optional)
try:
    from data.supabase_client import get_offers_with_stats
    sports_data = get_offers_with_stats()
except Exception:
    sports_data = None

# Render filter sidebar (includes user info at bottom)
render_filters_sidebar(sports_data=sports_data, events=events)

# Get filter states
selected_sports = get_filter_state('offers', [])
hide_cancelled = get_filter_state('hide_cancelled', True)
date_start = get_filter_state('date_start', None)
date_end = get_filter_state('date_end', None)
selected_locations = get_filter_state('location', [])
selected_weekdays = get_filter_state('weekday', [])
time_start_filter = get_filter_state('time_start', None)
time_end_filter = get_filter_state('time_end', None)

# Apply filters
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
        start_dt = datetime.fromisoformat(str(start_time).replace('Z', '+00:00'))
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
        start_dt = datetime.fromisoformat(str(e.get('start_time')).replace('Z', '+00:00'))
        if start_dt.strftime('%A') not in selected_weekdays:
            continue
    
    # Time filter
    if time_start_filter or time_end_filter:
        start_dt = datetime.fromisoformat(str(e.get('start_time')).replace('Z', '+00:00'))
        event_time = start_dt.time()
        
        if time_start_filter and event_time < time_start_filter:
            continue
        if time_end_filter and event_time > time_end_filter:
            continue
    
    filtered_events.append(e)

if not filtered_events:
    st.info("🔍 No events match the selected filters.")
    st.stop()

# Display events in modern card layout
weekdays_de = {
    'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch',
    'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'
}

for idx, event in enumerate(filtered_events):
    # Parse datetime
    start_dt = datetime.fromisoformat(str(event.get('start_time')).replace('Z', '+00:00'))
    end_time = event.get('end_time')
    
    if end_time:
        end_dt = datetime.fromisoformat(str(end_time).replace('Z', '+00:00'))
        time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
    else:
        time_str = start_dt.strftime('%H:%M')
    
    weekday = weekdays_de.get(start_dt.strftime('%A'), start_dt.strftime('%A'))
    date_str = f"{weekday}, {start_dt.strftime('%d.%m.%Y')}"
    
    # Check status
    is_cancelled = event.get('canceled', False)
    event_id = get_event_id(event)
    user_going = is_user_going_to_event(current_user_id, event_id) if current_user_id else False
    friends_going = get_friends_going_to_event(current_user_id, event_id) if current_user_id else []
    
    # Status styling
    if is_cancelled:
        status_color = "#ffebee"
        border_color = "#f44336"
        status_icon = "🔴"
        status_text = "Cancelled"
    elif user_going:
        status_color = "#e8f5e9"
        border_color = "#4caf50"
        status_icon = "✅"
        status_text = "You're going"
    else:
        status_color = "#fafafa"
        border_color = "#e0e0e0"
        status_icon = "⚪"
        status_text = ""
    
    # Event card
    with st.container():
        col_info, col_action = st.columns([5, 1])
        
        with col_info:
            # Use native Streamlit container styling
            st.markdown(f"""
            <div style="padding: 16px; border-radius: 8px; border-left: 4px solid {border_color}; 
                        background-color: {status_color}; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 20px;">{status_icon}</span>
                    <h4 style="margin: 0;">{event.get('sport_name', 'Course')}</h4>
                </div>
                <p style="margin: 4px 0;"><b>📅 {date_str}</b> • <b>⏰ {time_str}</b></p>
                <p style="margin: 4px 0;">📍 {event.get('location_name', 'N/A')}</p>
                {f"<p style='margin: 4px 0;'>👤 {', '.join(event.get('trainers', []))}</p>" if event.get('trainers') else ""}
                {f"<p style='margin: 4px 0; color: {border_color}; font-weight: 600;'>{status_text}</p>" if status_text else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Friends going
            if friends_going:
                friend_names = [
                    friend.get('user', {}).get('name', '') 
                    for friend in friends_going 
                    if isinstance(friend.get('user'), dict) and friend.get('user', {}).get('name')
                ]
                
                if friend_names:
                    st.info(f"👥 {len(friend_names)} friend{'s' if len(friend_names) != 1 else ''} going: {', '.join(friend_names[:3])}")
        
        with col_action:
            if current_user_id and not is_cancelled:
                if user_going:
                    if st.button("❌ Cancel", key=f"going_{idx}", use_container_width=True):
                        if unmark_user_going_to_event(current_user_id, event_id):
                            st.success("✅ Cancelled successfully")
                            st.rerun()
                        else:
                            st.error("❌ Failed to cancel. Please try again.")
                else:
                    if st.button("✅ Join", key=f"going_{idx}", use_container_width=True, type="primary"):
                        if mark_user_going_to_event(current_user_id, event_id):
                            st.success("🎉 You're now attending!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to join event. Please try again.")

# Rating section (only for single activity view)
if is_logged_in() and has_selected_offer() and not showing_multiple_offers:
    # Collect trainers
    all_trainers = set()
    for event in filtered_events:
        trainers = event.get('trainers', [])
        for trainer_name in trainers:
            if trainer_name:
                all_trainers.add(trainer_name)
    
    if all_trainers:
        st.divider()
        st.subheader("⭐ Rate Trainers")
        st.caption("Share your experience with trainers you know")
        
        for trainer_name in sorted(all_trainers):
            rating_info = get_average_rating_for_trainer(trainer_name)
            
            if rating_info['count'] > 0:
                stars = '⭐' * int(round(rating_info['avg']))
                st.markdown(f"**{trainer_name}** {stars} {rating_info['avg']:.1f}/5 ({rating_info['count']} reviews)")
            else:
                st.markdown(f"**{trainer_name}** - No reviews yet")
            
            render_trainer_rating_widget(trainer_name)
            st.divider()
    
    # Activity rating
    st.subheader("⭐ Rate This Activity")
    render_sportangebot_rating_widget(selected['href'])