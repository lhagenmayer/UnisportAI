import streamlit as st
from datetime import datetime, time, timedelta
from data.supabase_client import get_events_for_offer, get_all_events
from data.state_manager import get_selected_offers_for_page2, get_filter_state, set_filter_state
from data.shared_sidebar import render_shared_sidebar

# Check if we should pre-select an offer based on filter from page_3
if 'state_nav_offer_hrefs' in st.session_state:
    # We came from page_3 with a specific sport filter
    if 'state_selected_offer' in st.session_state:
        del st.session_state['state_selected_offer']
    
    from data.supabase_client import get_offers_with_stats
    all_offers = get_offers_with_stats()
    all_offer_hrefs = st.session_state['state_nav_offer_hrefs']
    
    # Store info that we came from page_3
    st.session_state['state_page2_multiple_offers'] = all_offer_hrefs
    
    # Set the selected offer from the first href
    for offer in all_offers:
        if offer.get('href') == all_offer_hrefs[0]:
            st.session_state['state_selected_offer'] = offer
            break
    
    # Clean up filter keys
    del st.session_state['state_nav_offer_hrefs']
    if 'state_nav_offer_name' in st.session_state:
        del st.session_state['state_nav_offer_name']
    if 'state_selected_offers_multiselect' in st.session_state:
        del st.session_state['state_selected_offers_multiselect']

# Check if an offer is selected, if not, show all
has_selected_offer = 'state_selected_offer' in st.session_state
if has_selected_offer:
    selected = st.session_state['state_selected_offer']
else:
    selected = None

# Display title - handle multiple offers
showing_multiple_offers = 'state_page2_multiple_offers' in st.session_state
if not has_selected_offer:
    st.title("📅 Course Dates")
    st.markdown("### All upcoming course dates")
elif showing_multiple_offers:
    # Show title - use sport icon and base name
    icon = selected.get('icon', '')
    name_without_level = selected.get('name', 'Sports Activity').split(' Level')[0]
    st.title(f"{icon} {name_without_level}")
    st.markdown("### Course dates for selected activities")
else:
    st.title(f"{selected.get('icon', '')} {selected.get('name', 'Sports Activity')}")
    st.markdown("### Course dates and details")

# Navigation will be handled by shared sidebar

# Display description if we have one and NOT showing multiple offers and have a selected offer
if has_selected_offer and 'state_page2_multiple_offers' not in st.session_state:
    description = selected.get('description')
    if description:
        st.markdown("---")
        st.markdown("### Description")
        # Render HTML description
        st.markdown(description, unsafe_allow_html=True)
        st.markdown("---")

# Display info only if not showing multiple offers and have a selected offer
if has_selected_offer and 'state_page2_multiple_offers' not in st.session_state:
    # Handle None values safely
    intensity = (selected.get('intensity') or '').capitalize()
    focus = ', '.join([f.capitalize() for f in selected.get('focus', [])]) if selected.get('focus') else ''
    setting = ', '.join([s.capitalize() for s in selected.get('setting', [])]) if selected.get('setting') else ''
    
    # Display info in responsive columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Intensity", intensity)
    with col2:
        st.metric("Focus", focus if focus else 'N/A')
    with col3:
        st.metric("Setting", setting if setting else 'N/A')

# Fetch events - handle multiple offers if we came from page_3
with st.spinner('Loading course dates...'):
    if not has_selected_offer:
        # No specific offer selected - show all events
        events = get_all_events()
    elif showing_multiple_offers:
        # Get selected offers from session state using state manager
        selected_offers_to_use = get_selected_offers_for_page2()
        
        # Load ALL events and filter by selected offers - optimiert!
        all_events = get_all_events()
        events = [
            e for e in all_events 
            if e.get('offer_href') in selected_offers_to_use
        ]
        
        # Remove duplicates (same kursnr and time)
        seen = set()
        unique_events = []
        for e in events:
            key = (e.get('kursnr'), e.get('start_time'))
            if key not in seen:
                seen.add(key)
                unique_events.append(e)
        events = unique_events
        # Sort by start_time
        events.sort(key=lambda x: x.get('start_time', ''))
    else:
        events = get_events_for_offer(selected['href'])

if not events:
    st.info("No course dates available.")
    st.stop()

# Render shared sidebar - this handles ALL filters including the multiselect for multiple offers
render_shared_sidebar(filter_type='detail', events=events)

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
    
    # Check cancelled filter
    if hide_cancelled and e.get('canceled'):
        filtered_count -= 1
        continue
    
    # Check date range filter
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
    
    # Check location filter
    if selected_locations:
        location = e.get('location_name', '')
        if location not in selected_locations:
            filtered_count -= 1
            continue
    
    # Check weekday filter
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
    
    # Check time range filter
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
    # Filter: Sport name
    if selected_sports:
        sport_name = e.get('sport_name', '')
        if sport_name not in selected_sports:
            continue
    
    # Filter 1: Non-cancelled
    if hide_cancelled and e.get('canceled'):
        continue
    
    # Filter 2: Date range
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
    
    # Filter 3: Location
    if selected_locations:
        location = e.get('location_name', '')
        if location not in selected_locations:
            continue
    
    # Filter 4: Weekday
    if selected_weekdays:
        start_time_obj = e.get('start_time')
        if isinstance(start_time_obj, str):
            start_dt_for_weekday = datetime.fromisoformat(start_time_obj.replace('Z', '+00:00'))
        else:
            start_dt_for_weekday = start_time_obj
        event_weekday = start_dt_for_weekday.strftime('%A')
        if event_weekday not in selected_weekdays:
            continue
    
    # Filter 5: Time range
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

# Check if any filtered results
if not filtered_events:
    st.info("No events match the selected filters.")
    st.stop()

# German weekday names
weekdays_de = {
    'Monday': 'Montag',
    'Tuesday': 'Dienstag',
    'Wednesday': 'Mittwoch',
    'Thursday': 'Donnerstag',
    'Friday': 'Freitag',
    'Saturday': 'Samstag',
    'Sunday': 'Sonntag'
}

# Prepare display data
display_data = []
for event in filtered_events:
    # Format timestamps
    start_time = event.get('start_time')
    end_time = event.get('end_time')
    
    # Format start time
    if isinstance(start_time, str):
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        start_dt = start_time
    
    # Format end time
    if end_time:
        if isinstance(end_time, str):
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end_dt = end_time
        end_formatted = end_dt.strftime('%H:%M')
    else:
        end_formatted = ''
    
    # Format date and time separately
    weekday_en = start_dt.strftime('%A')
    weekday_de = weekdays_de.get(weekday_en, weekday_en)
    date_formatted = start_dt.strftime('%d.%m.%Y')
    time_formatted = start_dt.strftime('%H:%M')
    
    # Create date string with weekday
    date_string = f"{weekday_de}, {date_formatted}"
    
    # Create time string
    if end_formatted:
        time_string = f"{time_formatted} - {end_formatted}"
    else:
        time_string = time_formatted
    
    # Handle new fields from sportkurse
    preis = event.get('preis', '') or ''
    buchung = event.get('buchung', '') or ''
    details = event.get('details', '') or ''
    
    # Handle trainer info
    trainers = event.get('trainers', []) or []
    trainer_ratings = event.get('trainer_ratings', []) or []
    # Format: "Name (Rating⭐)" oder "Name"
    trainer_display = []
    for i, trainer_name in enumerate(trainers):
        if i < len(trainer_ratings):
            rating = trainer_ratings[i]
            if rating != 'N/A':
                trainer_display.append(f"{trainer_name} ({rating}⭐)")
            else:
                trainer_display.append(trainer_name)
        else:
            trainer_display.append(trainer_name)
    trainer_string = ', '.join(trainer_display) if trainer_display else ''
    
    row = {
        'Date': date_string,
        'Time': time_string,
        'Canceled': '✓' if event.get('canceled') else '',
        'Kurs Nr': event.get('kursnr', ''),
        'Location': event.get('location_name', ''),
        'Trainer': trainer_string,
        'Preis': preis,
        'Buchung': buchung,
        'Details': details
    }
    display_data.append(row)

st.dataframe(display_data, use_container_width=True, height=500)