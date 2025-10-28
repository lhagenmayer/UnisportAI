import streamlit as st
from datetime import datetime, timedelta
from data.supabase_client import get_all_events
from data.state_manager import store_page_3_to_page_2_filters, get_filter_state, set_filter_state
from data.shared_sidebar import render_shared_sidebar
from data.auth import is_logged_in, get_user_sub

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

st.title("📅 Calendar View")
st.markdown("### Weekly overview of all course dates")


def get_user_id() -> str:
    """Holt die user_id aus der users Tabelle"""
    try:
        user_sub = get_user_sub()
        if not user_sub:
            return None
        
        from data.supabase_client import supaconn
        conn = supaconn()
        result = conn.table("users").select("id").eq("sub", user_sub).execute()
        return result.data[0]['id'] if result.data else None
    except Exception:
        return None


def notify_friends_about_event(user_id: str, event_id: str, event_details: dict) -> bool:
    """Benachrichtigt Freunde über einen Termin"""
    if not user_id:
        return False
        
    try:
        from data.supabase_client import supaconn
        conn = supaconn()
        
        # Hole alle Freunde
        friendships = conn.table("user_friends").select("*").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        if not friendships.data:
            return False
        
        # Bestimme welche User die Freunde sind
        friend_ids = []
        for friendship in friendships.data:
            if friendship['requester_id'] == user_id:
                friend_ids.append(friendship['addressee_id'])
            else:
                friend_ids.append(friendship['requester_id'])
        
        # Füge Notifications hinzu
        notifications = []
        for friend_id in friend_ids:
            notifications.append({
                "user_id": user_id,
                "friend_id": friend_id,
                "event_id": event_id,
                "created_at": datetime.now().isoformat()
            })
        
        if notifications:
            conn.table("friend_course_notifications").insert(notifications).execute()
        
        return True
    except Exception:
        return False


def get_friends_attending_same_events(user_id: str, event_id: str) -> list:
    """Holt Freunde, die denselben Termin besuchen"""
    if not user_id:
        return []
    
    try:
        from data.supabase_client import supaconn
        conn = supaconn()
        
        # Suche nach Notifications, wo der aktuelle User der friend ist
        notifications = conn.table("friend_course_notifications").select(
            "*, user:users!user_id(*)"
        ).eq("friend_id", user_id).eq("event_id", event_id).execute()
        
        return notifications.data or []
    except Exception:
        return []


def mark_event_attendance(event_id: str, event_details: dict) -> bool:
    """Markiert einen Termin als besucht und benachrichtigt Freunde"""
    user_id = get_user_id()
    if not user_id:
        return False
    
    return notify_friends_about_event(user_id, event_id, event_details)

# Navigation will be handled by shared sidebar

# Get user_id for friend functionality
user_id = get_user_id()

# Fetch events for ALL offers
with st.spinner('Lade alle Kurstermine...'):
    events = get_all_events()

if not events:
    st.info("Keine Kurstermine verfügbar.")
    st.stop()

# Helper function to normalize sport name (remove Level, Fortgeschritten, etc.)
def normalize_sport_name(name: str) -> str:
    """Normalizes sport names by removing qualifiers like 'Level 1', 'Fortgeschritten', etc."""
    import re
    if not name:
        return ""
    
    # Remove common qualifiers that appear after the main sport name
    patterns_to_remove = [
        r'\s+Level\s+\d+',  # "Tennis Level 1" -> "Tennis"
        r'\s+Fortgeschritten',  # "Basketball Fortgeschritten" -> "Basketball"
        r'\s+Anfänger',  # "Tennis Anfänger" -> "Tennis"
        r'\s+Beginner',  # "Tennis Beginner" -> "Tennis"
        r'\s+Advanced',  # "Tennis Advanced" -> "Tennis"
        r'\s+Intermediate',  # "Tennis Intermediate" -> "Tennis"
    ]
    
    normalized = name
    for pattern in patterns_to_remove:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    return normalized.strip()

# Render shared sidebar - this handles ALL filters
render_shared_sidebar(filter_type='weekly', events=events)

# Get filter states for filtering
selected_sports = get_filter_state('offers', [])
hide_cancelled = get_filter_state('hide_cancelled', True)
date_start = get_filter_state('date_start', None)
date_end = get_filter_state('date_end', None)
selected_locations = get_filter_state('location', [])
selected_weekdays = get_filter_state('weekday', [])
time_start_filter = get_filter_state('time_start', None)
time_end_filter = get_filter_state('time_end', None)

# Calculate filtered count for display
filtered_count = len(events)
for e in events:
    # Check sport filter
    if selected_sports:
        sport_name = e.get('sport_name', '')
        if sport_name not in selected_sports:
            filtered_count -= 1
            continue
    
    if hide_cancelled and e.get('canceled'):
        filtered_count -= 1
        continue
    
    if date_start or date_end:
        start_time = e.get('start_time')
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = start_time
        event_date = start_dt.date()
        
        if date_start and event_date < date_start:
            filtered_count -= 1
            continue
        if date_end and event_date > date_end:
            filtered_count -= 1
            continue
    
    if selected_locations:
        location = e.get('location_name', '')
        if location not in selected_locations:
            filtered_count -= 1
            continue
    
    if selected_weekdays:
        start_time_obj = e.get('start_time')
        if isinstance(start_time_obj, str):
            start_dt_for_weekday = datetime.fromisoformat(start_time_obj.replace('Z', '+00:00'))
        else:
            start_dt_for_weekday = start_time_obj
        event_weekday = start_dt_for_weekday.strftime('%A')
        if event_weekday not in selected_weekdays:
            filtered_count -= 1
            continue
    
    if time_start_filter or time_end_filter:
        start_time_obj = e.get('start_time')
        if isinstance(start_time_obj, str):
            start_dt_for_time = datetime.fromisoformat(start_time_obj.replace('Z', '+00:00'))
        else:
            start_dt_for_time = start_time_obj
        event_time = start_dt_for_time.time()
        
        if time_start_filter and event_time < time_start_filter:
            filtered_count -= 1
            continue
        if time_end_filter and event_time > time_end_filter:
            filtered_count -= 1
            continue

# Display count in sidebar
with st.sidebar:
    st.info(f"📅 {filtered_count} von {len(events)} Terminen")

# Apply filters
filtered_events = []
for e in events:
    # Filter by sport name
    if selected_sports:
        sport_name = e.get('sport_name', '')
        if sport_name not in selected_sports:
            continue
    
    if hide_cancelled and e.get('canceled'):
        continue
    
    if date_start or date_end:
        start_time = e.get('start_time')
        if isinstance(start_time, str):
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        else:
            start_dt = start_time
        event_date = start_dt.date()
        
        if date_start and event_date < date_start:
            continue
        if date_end and event_date > date_end:
            continue
    
    if selected_locations:
        location = e.get('location_name', '')
        if location not in selected_locations:
            continue
    
    if selected_weekdays:
        start_time_obj = e.get('start_time')
        if isinstance(start_time_obj, str):
            start_dt_for_weekday = datetime.fromisoformat(start_time_obj.replace('Z', '+00:00'))
        else:
            start_dt_for_weekday = start_time_obj
        event_weekday = start_dt_for_weekday.strftime('%A')
        if event_weekday not in selected_weekdays:
            continue
    
    if time_start_filter or time_end_filter:
        start_time_obj = e.get('start_time')
        if isinstance(start_time_obj, str):
            start_dt_for_time = datetime.fromisoformat(start_time_obj.replace('Z', '+00:00'))
        else:
            start_dt_for_time = start_time_obj
        event_time = start_dt_for_time.time()
        
        if time_start_filter and event_time < time_start_filter:
            continue
        if time_end_filter and event_time > time_end_filter:
            continue
    
    filtered_events.append(e)

if not filtered_events:
    st.info("Keine Termine entsprechen den gewählten Filtern.")
    st.stop()

# German weekday names
weekdays_de = {
    'Monday': 'Mo',
    'Tuesday': 'Di',
    'Wednesday': 'Mi',
    'Thursday': 'Do',
    'Friday': 'Fr',
    'Saturday': 'Sa',
    'Sunday': 'So'
}

# Group events by date, time, and sport_name (deduplicate same sport at same time)
grouped_by_key = {}
for event in filtered_events:
    start_time = event.get('start_time')
    if isinstance(start_time, str):
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        start_dt = start_time
    
    date_str = start_dt.strftime('%Y-%m-%d')
    time_str = start_dt.strftime('%H:%M')
    sport_name = event.get('sport_name', '')
    normalized_sport_name = normalize_sport_name(sport_name)
    sport_icon = event.get('sport_icon', '')
    location = event.get('location_name', '') or ''
    
    # Create unique key for grouping: same normalized sport at same time = one card
    # Use normalized sport name instead of offer_href to group all levels together
    key = f"{date_str}_{time_str}_{normalized_sport_name}"
    
    # Collect all offer_hrefs for this normalized sport
    if key not in grouped_by_key:
        grouped_by_key[key] = {
            'dt': start_dt,
            'date_str': date_str,
            'time_str': time_str,
            'sport_name': normalized_sport_name,  # Use normalized name for display
            'original_sport_name': sport_name,    # Keep original for reference
            'sport_icon': sport_icon,
            'location': location,
            'offer_href': event.get('offer_href', ''),  # Store first offer_href for navigation
            'all_offer_hrefs': [event.get('offer_href', '')] if event.get('offer_href') else [],  # Store all for potential filtering
            'event': event
        }
    else:
        # Add this offer_href to the list if not already there
        existing_item = grouped_by_key[key]
        current_href = event.get('offer_href', '')
        if current_href and current_href not in existing_item['all_offer_hrefs']:
            existing_item['all_offer_hrefs'].append(current_href)

# Group by date for display
grouped_by_date = {}
for key, item in grouped_by_key.items():
    date_str = item['date_str']
    if date_str not in grouped_by_date:
        grouped_by_date[date_str] = []
    grouped_by_date[date_str].append(item)

# Sort dates
sorted_dates = sorted(grouped_by_date.keys())

if not sorted_dates:
    st.info("Keine Termine zum Anzeigen vorhanden.")
    st.stop()

# Display weekly view
st.markdown("## 📅 Weekly Calendar")

# Get the week range
first_date = datetime.strptime(sorted_dates[0], '%Y-%m-%d')
if len(sorted_dates) > 1:
    last_date = datetime.strptime(sorted_dates[-1], '%Y-%m-%d')
else:
    last_date = first_date

# Get the Monday of the first week
monday_of_first_week = first_date - timedelta(days=first_date.weekday())

# Create week view - show up to 2 weeks
weeks_to_show = min(3, (last_date - monday_of_first_week).days // 7 + 2)

for week_num in range(weeks_to_show):
    week_start = monday_of_first_week + timedelta(weeks=week_num)
    
    # Header for this week
    week_end = week_start + timedelta(days=6)
    week_label = f"Kalenderwoche {week_start.isocalendar()[1]}"
    st.markdown(f"### 📅 {week_label} ({week_start.strftime('%d.%m.')} - {week_end.strftime('%d.%m.%Y')})")
    
    # Create columns for each day of the week
    cols = st.columns(7)
    
    day_names = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
    
    # Header row with day names
    for i, col in enumerate(cols):
        with col:
            day_date = week_start + timedelta(days=i)
            is_today = day_date.date() == datetime.now().date()
            day_name = day_names[i]
            
            # Highlight today
            if is_today:
                st.markdown(f"**🟢 {day_name}<br>{day_date.strftime('%d.%m.')}**", unsafe_allow_html=True)
            else:
                st.markdown(f"**{day_name}<br>{day_date.strftime('%d.%m.')}**", unsafe_allow_html=True)
    
    # Group events by day for this week
    events_by_day = {}
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        date_str = day_date.strftime('%Y-%m-%d')
        events_by_day[i] = []
    
    # Populate with actual events
    for date_str in sorted_dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        days_diff = (date_obj - week_start).days
        
        if 0 <= days_diff < 7:
            for item in grouped_by_date[date_str]:
                events_by_day[days_diff].append(item)
    
    # Display events for each day
    for i, col in enumerate(cols):
        with col:
            day_events = sorted(events_by_day[i], key=lambda x: x['dt'])
            
            if day_events:
                for idx, item in enumerate(day_events):
                    # Get grouped data
                    time_str = item['time_str']
                    sport_icon = item['sport_icon']
                    sport_name = item['sport_name']
                    location = item['location']
                    offer_href = item['offer_href']
                    start_dt = item['dt']
                    date_str = item['date_str']
                    all_offer_hrefs = item['all_offer_hrefs']
                    
                    # Create sport display
                    sport_display = f"{sport_icon} {sport_name}" if sport_icon and sport_name else sport_name
                    
                    # Create unique key for button - include week_num, day, index and sport to ensure uniqueness
                    hrefs_str = '_'.join(str(h) for h in sorted(all_offer_hrefs))
                    button_key = f"btn_w{week_num}_d{i}_i{idx}_{time_str}_{sport_name}_{hash(hrefs_str)}"
                    
                    # Get the original event to check cancelled status
                    event = item['event']
                    is_cancelled = event.get('canceled', False)
                    
                    # Color based on cancelled status
                    if is_cancelled:
                        color = "🔴"
                        bg_color = "#ffebee"
                        border_color = "red"
                    else:
                        color = "🟢"
                        bg_color = "#e8f5e9"
                        border_color = "green"
                    
                    # Check if friends are attending
                    event_id = f"{date_str}_{time_str}_{sport_name}"
                    friends_attending = []
                    if user_id:
                        friends_attending = get_friends_attending_same_events(user_id, event_id)
                    
                    # Create clickable card
                    with st.container():
                        col1, col2 = st.columns([6, 1])
                        with col1:
                            # Show friend indicator
                            friend_indicator = ""
                            if friends_attending:
                                friend_names = [f.get('user', {}).get('name', 'Freund') if isinstance(f.get('user'), dict) else 'Freund' for f in friends_attending]
                                friend_indicator = f"<small>👥 {len(friends_attending)} {'Freund' if len(friends_attending) == 1 else 'Freunde'}</small><br>"
                            
                            st.markdown(f"""<div style="background-color: {bg_color}; padding: 8px; border-radius: 5px; margin-bottom: 5px; border-left: 3px solid {border_color}; cursor: pointer;">
                                {color} <b>{time_str}</b><br>
                                {friend_indicator}
                                <small><b>{sport_display}</b></small><br>
                                <small>{location}</small>
                            </div>""", unsafe_allow_html=True)
                        with col2:
                            if st.button("→", key=button_key, use_container_width=True):
                                # Use all_offer_hrefs from the grouped item
                                all_offer_hrefs_to_send = item['all_offer_hrefs']
                                
                                # Set filter in session state using state manager
                                store_page_3_to_page_2_filters(
                                    date_str=date_str,
                                    time_obj=start_dt.time(),
                                    offer_name=item['sport_name'],
                                    all_offer_hrefs=all_offer_hrefs_to_send
                                )
                                st.switch_page("pages/details.py")
            
            # Show empty state for days without events
            # (No markdown needed as columns handle this)
    
    st.divider()
