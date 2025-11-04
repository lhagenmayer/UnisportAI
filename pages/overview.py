import streamlit as st
from datetime import datetime
from data.supabase_client import get_offers_with_stats, count_upcoming_events_per_offer, get_trainers_for_all_offers, get_events_for_offer, get_all_events, get_events_by_offer_mapping
from data.filters import filter_offers, filter_offers_by_events, filter_events
from data.state_manager import get_filter_state, set_filter_state
from data.shared_sidebar import render_shared_sidebar
from data.rating import render_sportangebot_rating_widget, get_average_rating_for_offer
from data.auth import is_logged_in

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

st.title('🎯 Sports Overview')
st.markdown('### Browse all available activities')

with st.spinner('Loading sports activities...'):
    offers = get_offers_with_stats()
    
    # Count upcoming events for all offers at once (optimized)
    event_counts = count_upcoming_events_per_offer()
    
    # Get trainers for all offers at once (optimized)
    trainers_by_offer = get_trainers_for_all_offers()
    
    # Add counts and trainers to each offer
    for offer in offers:
        offer['future_events_count'] = event_counts.get(offer['href'], 0)
        offer['trainers'] = trainers_by_offer.get(offer['href'], [])

if not offers:
    st.warning("No sports activities found.")
    st.stop()

# Store offers in session state for later use
st.session_state['state_sports_data'] = offers

# Render shared sidebar with all filters
render_shared_sidebar(filter_type='main', sports_data=offers)

# Get filter states for filtering
show_upcoming_only = get_filter_state('show_upcoming_only', True)
search_text = get_filter_state('search_text', '')
selected_intensity = get_filter_state('intensity', [])
selected_focus = get_filter_state('focus', [])
selected_setting = get_filter_state('setting', [])

# Get detail filter states
selected_offers_filter = get_filter_state('offers', [])
hide_cancelled = get_filter_state('hide_cancelled', True)
date_start = get_filter_state('date_start', None)
date_end = get_filter_state('date_end', None)
selected_locations = get_filter_state('location', [])
selected_weekdays = get_filter_state('weekday', [])
time_start_filter = get_filter_state('time_start', None)
time_end_filter = get_filter_state('time_end', None)

# Check if any detail filters are active
has_detail_filters = (
    (selected_offers_filter and len(selected_offers_filter) > 0) or
    (date_start or date_end) or
    (selected_locations and len(selected_locations) > 0) or
    (selected_weekdays and len(selected_weekdays) > 0) or
    (time_start_filter or time_end_filter)
)

# Apply base filters first
filtered_offers = filter_offers(
    offers,
    show_upcoming_only=show_upcoming_only,
    search_text=search_text,
    intensity=selected_intensity if selected_intensity else None,
    focus=selected_focus if selected_focus else None,
    setting=selected_setting if selected_setting else None
)

# Apply detail filters if any are set
if has_detail_filters:
    # Load all events grouped by offer_href - optimiert durch neue Funktion!
    events_mapping = get_events_by_offer_mapping()
    
    # Apply events-based filtering
    filtered_offers = filter_offers_by_events(
        filtered_offers,
        events_mapping,
        sport_filter=selected_offers_filter if selected_offers_filter else None,
        weekday_filter=selected_weekdays if selected_weekdays else None,
        date_start=date_start,
        date_end=date_end,
        time_start=time_start_filter if time_start_filter else None,
        time_end=time_end_filter if time_end_filter else None,
        location_filter=selected_locations if selected_locations else None,
        hide_cancelled=hide_cancelled
    )

# Personalisierungs-Sortierung entfernt; Standardreihenfolge beibehalten

# Show filtered count
st.info(f"Showing {len(filtered_offers)} of {len(offers)} activities")

# Display in a responsive card layout with image backgrounds
for offer in filtered_offers:
    # Create a card with better visual hierarchy
    st.markdown("---")
    
    image_url = offer.get('image_url')
    
    # Two column layout: left for details, right for image or button
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        st.markdown(f"### {offer.get('icon', '')} {offer.get('name', '')}")
        intensity = offer.get('intensity', '').capitalize() if offer.get('intensity') else 'N/A'
        
        # Display info
        info_parts = [f"Intensity: {intensity}"]
        
        if offer.get('focus'):
            focus_short = ', '.join([f.capitalize() for f in offer.get('focus', [])[:2]])
            if len(offer.get('focus', [])) > 2:
                focus_short += '+'
            info_parts.append(focus_short)
        
        # Add future events count
        events_count = offer.get('future_events_count', 0)
        if events_count > 0:
            info_parts.append(f"📅 {events_count} upcoming")
        
        st.caption(' • '.join(info_parts))
        
        # Trainers
        trainers = offer.get('trainers', [])
        if trainers:
            trainer_names = [t.get('name', '') for t in trainers[:2]]
            trainers_str = ', '.join(trainer_names)
            if len(trainers) > 2:
                trainers_str += f" +{len(trainers)-2}"
            st.caption(f"👤 {trainers_str}")
        
        # Rating
        if offer.get('rating_count', 0) > 0:
            rating = offer.get('avg_rating', 0)
            st.caption(f"{'⭐' * int(rating)} {rating:.1f}/5 ({offer.get('rating_count', 0)} Bewertungen)")
    
    with col_right:
        if image_url:
            # Display image with gradient overlay and clickable button
            st.markdown(f"""
            <div style="
                background-image: url('{image_url}');
                background-size: cover;
                background-position: center;
                background-color: #f0f0f0;
                padding: 20px;
                border-radius: 10px;
                min-height: 150px;
                position: relative;
                margin-bottom: 10px;
            ">
                <div style="
                    background: linear-gradient(to bottom, rgba(0,0,0,0.3), rgba(0,0,0,0.7));
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    border-radius: 10px;
                "></div>
            </div>
            """, unsafe_allow_html=True)
        
        # View details button
        if st.button("📋 Details anzeigen", key=f"view_{offer['href']}", use_container_width=True):
            st.session_state['state_selected_offer'] = offer
            st.switch_page("pages/details.py")
    
    # Add expander with upcoming dates for each activity
    with st.expander("📅 Upcoming Dates", expanded=False):
        # Get events for this activity
        events = get_events_for_offer(offer['href'])
        
        # Filter for future events only
        today = datetime.now().date()
        upcoming_events = []
        for event in events:
            start_time = event.get('start_time')
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = start_time
            event_date = start_dt.date()
            
            # Only include future dates and non-cancelled
            if event_date >= today and not event.get('canceled'):
                upcoming_events.append(event)
        
        # Apply detail filters if any are active
        if has_detail_filters:
            upcoming_events = filter_events(
                upcoming_events,
                sport_filter=selected_offers_filter if selected_offers_filter else None,
                weekday_filter=selected_weekdays if selected_weekdays else None,
                date_start=date_start,
                date_end=date_end,
                time_start=time_start_filter if time_start_filter else None,
                time_end=time_end_filter if time_end_filter else None,
                location_filter=selected_locations if selected_locations else None,
                hide_cancelled=hide_cancelled
            )
        
        # Sort by date
        upcoming_events.sort(key=lambda x: x.get('start_time', ''))
        
        if upcoming_events:
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
            
            # Display events
            events_display_data = []
            for event in upcoming_events[:10]:  # Show up to 10 upcoming dates
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
                
                weekday_en = start_dt.strftime('%A')
                weekday_de_short = weekdays_de.get(weekday_en, weekday_en)
                date_formatted = start_dt.strftime('%d.%m.%Y')
                time_formatted = start_dt.strftime('%H:%M')
                
                # Create date string
                date_string = f"{weekday_de_short}, {date_formatted}"
                
                # Create time string
                if end_formatted:
                    time_string = f"{time_formatted} - {end_formatted}"
                else:
                    time_string = time_formatted
                
                # Get course details - this is the actual course name/description
                course_details = event.get('details', '')
                kursnr = event.get('kursnr', '')
                
                # Combine kursnr and details: always show kursnr, append details if available
                if course_details:
                    course_display = f"{kursnr} {course_details}" if kursnr else course_details
                else:
                    course_display = kursnr
                
                row = {
                    'Date': date_string,
                    'Time': time_string,
                    'Course': course_display,
                    'Location': event.get('location_name', '')
                }
                events_display_data.append(row)
            
            st.dataframe(events_display_data, use_container_width=True, hide_index=True)
            if len(upcoming_events) > 10:
                remaining_count = len(upcoming_events) - 10
                # Create a clickable link to view all dates
                if st.button(f"📋 Show all {len(upcoming_events)} dates", key=f"show_all_{offer['href']}", use_container_width=True):
                    st.session_state['state_selected_offer'] = offer
                    st.switch_page("pages/details.py")
        else:
            st.info("No upcoming dates available")
    
    st.divider()

