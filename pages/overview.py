import streamlit as st
from datetime import datetime
from data.supabase_client import get_offers_with_stats, count_upcoming_events_per_offer, get_trainers_for_all_offers, get_events_for_offer, get_events_by_offer_mapping
from data.filters import filter_offers, filter_offers_by_events, filter_events
from data.state_manager import get_filter_state, set_filter_state, set_sports_data, set_selected_offer
from data.shared_sidebar import render_filters_sidebar, render_ml_recommendations
from data.auth import is_logged_in

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Page config
st.title('🎯 Sports Overview')
st.caption('Discover and book your perfect sports activities')

# Load data with progress
with st.spinner('🔄 Loading activities...'):
    offers = get_offers_with_stats()
    
    if offers:
        # Optimize data loading
        event_counts = count_upcoming_events_per_offer()
        trainers_by_offer = get_trainers_for_all_offers()
        
        # Enrich offers with metadata
        for offer in offers:
            offer['future_events_count'] = event_counts.get(offer['href'], 0)
            offer['trainers'] = trainers_by_offer.get(offer['href'], [])

if not offers:
    st.warning("⚠️ No sports activities found.")
    st.stop()

# Store in state
set_sports_data(offers)

# Load events for detail filters (even on overview page)
from data.supabase_client import get_all_events
events = get_all_events()

# Render filter sidebar (includes user info at bottom)
render_filters_sidebar(sports_data=offers, events=events)

# Render ML recommendations (if button was clicked)
render_ml_recommendations(sports_data=offers)

# Get all filter states
show_upcoming_only = get_filter_state('show_upcoming_only', True)
search_text = get_filter_state('search_text', '')
selected_intensity = get_filter_state('intensity', [])
selected_focus = get_filter_state('focus', [])
selected_setting = get_filter_state('setting', [])

# Detail filters
selected_offers_filter = get_filter_state('offers', [])
hide_cancelled = get_filter_state('hide_cancelled', True)
date_start = get_filter_state('date_start', None)
date_end = get_filter_state('date_end', None)
selected_locations = get_filter_state('location', [])
selected_weekdays = get_filter_state('weekday', [])
time_start_filter = get_filter_state('time_start', None)
time_end_filter = get_filter_state('time_end', None)

# Check for detail filters
has_detail_filters = (
    bool(selected_offers_filter) or
    bool(date_start or date_end) or
    bool(selected_locations) or
    bool(selected_weekdays) or
    bool(time_start_filter or time_end_filter)
)

# Apply filters
filtered_offers = filter_offers(
    offers,
    show_upcoming_only=show_upcoming_only,
    search_text=search_text,
    intensity=selected_intensity or None,
    focus=selected_focus or None,
    setting=selected_setting or None
)

if has_detail_filters:
    events_mapping = get_events_by_offer_mapping()
    filtered_offers = filter_offers_by_events(
        filtered_offers,
        events_mapping,
        sport_filter=selected_offers_filter or None,
        weekday_filter=selected_weekdays or None,
        date_start=date_start,
        date_end=date_end,
        time_start=time_start_filter,
        time_end=time_end_filter,
        location_filter=selected_locations or None,
        hide_cancelled=hide_cancelled
    )

# Display activities in a clean card layout
if not filtered_offers:
    st.info("🔍 No activities match your filters. Try adjusting your search criteria.")
    st.stop()

for offer in filtered_offers:
    with st.container():
        # Card container
        col_content, col_action = st.columns([4, 1])
        
        with col_content:
            # Header with icon and name
            st.markdown(f"### {offer.get('icon', '🏃')} {offer.get('name', 'Activity')}")
            
            # Metadata row
            metadata = []
            
            # Intensity badge
            intensity_value = offer.get('intensity') or ''
            intensity = intensity_value.capitalize() if intensity_value else ''
            if intensity:
                color = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}.get(intensity, '⚪')
                metadata.append(f"{color} {intensity}")
            
            # Focus areas
            if offer.get('focus'):
                focus_list = [f.capitalize() if f else '' for f in offer['focus'][:2] if f]
                if len(offer['focus']) > 2:
                    focus_list.append(f"+{len(offer['focus']) - 2}")
                metadata.append(f"🎯 {', '.join(focus_list)}")
            
            # Setting
            if offer.get('setting'):
                setting_str = ', '.join([s.capitalize() if s else '' for s in offer['setting'][:2] if s])
                metadata.append(f"🏠 {setting_str}")
            
            # Events count
            events_count = offer.get('future_events_count', 0)
            if events_count > 0:
                metadata.append(f"📅 {events_count} upcoming")
            else:
                metadata.append("⏸️ No upcoming dates")
            
            st.caption(' • '.join(metadata))
            
            # Additional info row
            info_row = []
            
            # Trainers
            trainers = offer.get('trainers', [])
            if trainers:
                trainer_names = [t.get('name', '') for t in trainers[:2]]
                if len(trainers) > 2:
                    trainer_names.append(f"+{len(trainers)-2}")
                info_row.append(f"👤 {', '.join(trainer_names)}")
            
            # Rating
            if offer.get('rating_count', 0) > 0:
                rating = offer.get('avg_rating', 0)
                stars = '⭐' * int(round(rating))
                info_row.append(f"{stars} {rating:.1f} ({offer['rating_count']})")
            
            if info_row:
                st.caption(' • '.join(info_row))
        
        with col_action:
            st.write("")  # Spacing
            if st.button("View Details", key=f"view_{offer['href']}", use_container_width=True, type="primary"):
                set_selected_offer(offer)
                st.switch_page("pages/details.py")
        
        # Expandable upcoming dates section
        if events_count > 0:
            with st.expander(f"📅 Show {min(events_count, 10)} upcoming dates", expanded=False):
                events = get_events_for_offer(offer['href'])
                
                # Filter for future events only
                today = datetime.now().date()
                upcoming_events = [
                    e for e in events
                    if (datetime.fromisoformat(str(e.get('start_time')).replace('Z', '+00:00')).date() >= today
                        and not e.get('canceled'))
                ]
                
                # Apply detail filters if active
                if has_detail_filters:
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
                
                upcoming_events.sort(key=lambda x: x.get('start_time', ''))
                
                if upcoming_events:
                    # Display in clean table format
                    weekdays = {'Monday': 'Mo', 'Tuesday': 'Di', 'Wednesday': 'Mi', 
                               'Thursday': 'Do', 'Friday': 'Fr', 'Saturday': 'Sa', 'Sunday': 'So'}
                    
                    events_data = []
                    for event in upcoming_events[:10]:
                        start_dt = datetime.fromisoformat(str(event.get('start_time')).replace('Z', '+00:00'))
                        end_time = event.get('end_time')
                        
                        if end_time:
                            end_dt = datetime.fromisoformat(str(end_time).replace('Z', '+00:00'))
                            time_str = f"{start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"
                        else:
                            time_str = start_dt.strftime('%H:%M')
                        
                        weekday = weekdays.get(start_dt.strftime('%A'), start_dt.strftime('%A'))
                        
                        events_data.append({
                            'Date': f"{weekday}, {start_dt.strftime('%d.%m.%Y')}",
                            'Time': time_str,
                            'Location': event.get('location_name', 'N/A')
                        })
                    
                    st.dataframe(events_data, use_container_width=True, hide_index=True)
                    
                    if len(upcoming_events) > 10:
                        if st.button(f"View all {len(upcoming_events)} dates →", 
                                   key=f"all_{offer['href']}", 
                                   use_container_width=True):
                            set_selected_offer(offer)
                            st.switch_page("pages/details.py")
                else:
                    st.info("No upcoming dates match your filters")

# Empty state footer
if len(filtered_offers) == 0:
    st.info("💡 **Tip:** Try clearing some filters to see more activities")

