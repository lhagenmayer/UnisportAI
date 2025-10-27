import streamlit as st
from datetime import datetime
from data.supabase_client import get_offers_with_stats, count_upcoming_events_per_offer, get_trainers_for_all_offers, get_events_for_offer, get_all_events, get_events_by_offer_mapping
from data.filters import filter_offers, filter_offers_by_events, filter_events
from data.state_manager import get_filter_state, set_filter_state
from data.shared_sidebar import render_shared_sidebar
from data.rating import render_sportangebot_rating_widget, get_average_rating_for_offer

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

# Show filtered count
st.info(f"Showing {len(filtered_offers)} of {len(offers)} activities")

# Display in a responsive card layout with image backgrounds
for offer in filtered_offers:
    col1, col2 = st.columns([5, 1])
    
    with col1:
        # Check if we have an image
        image_url = offer.get('image_url')
        if image_url:
            # Create a styled container with background image
            st.markdown(f"""
            <div style="
                background-image: url('{image_url}');
                background-size: cover;
                background-position: center;
                background-color: #f0f0f0;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 10px;
                position: relative;
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
                <div style="position: relative; z-index: 1; color: white;">
                    <h3 style="color: white; margin: 0 0 10px 0;">{offer.get('icon', '')} {offer.get('name', '')}</h3>
                    <p style="color: rgba(255,255,255,0.9); margin: 0;">{offer.get('intensity', '').capitalize() if offer.get('intensity') else 'N/A'} • {offer.get('future_events_count', 0)} upcoming • {'⭐' * int(offer.get('avg_rating', 0)) if offer.get('rating_count', 0) > 0 else 'No ratings yet'}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Fallback to old style without image
            st.write(f"**{offer.get('icon', '')} {offer.get('name', '')}**")
            intensity = offer.get('intensity', '').capitalize() if offer.get('intensity') else 'N/A'
            
            # Display info in a more compact way
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
            else:
                info_parts.append("📅 No upcoming dates")
            
            # Add trainers
            trainers = offer.get('trainers', [])
            if trainers:
                trainer_names = [f"{t.get('name', '')} ({t.get('rating', 'N/A')}⭐)" if t.get('rating') != 'N/A' else t.get('name', '') for t in trainers]
                trainers_str = ', '.join(trainer_names[:2])  # Max 2 trainers shown
                if len(trainers) > 2:
                    trainers_str += f"+{len(trainers)-2}"
                info_parts.append(f"👤 {trainers_str}")
            
            rating = f"{'⭐' * int(offer.get('avg_rating', 0))} {offer.get('avg_rating', 0):.2f}" if offer.get('rating_count', 0) > 0 else "No ratings yet"
            if rating != "No ratings yet":
                info_parts.append(rating)
            
            st.caption(' • '.join(info_parts))
    
    with col2:
        col2a, col2b = st.columns([1, 1])
        with col2a:
            if st.button("View", key=f"view_{offer['href']}", use_container_width=True):
                st.session_state['state_selected_offer'] = offer
                st.switch_page("pages/details.py")
        
        # Rating button nur wenn eingeloggt
        if st.user.is_logged_in:
            with col2b:
                rating_info = get_average_rating_for_offer(offer['href'])
                if rating_info['count'] > 0:
                    st.button(f"⭐ {rating_info['avg']}", 
                              key=f"rating_{offer['href']}", 
                              use_container_width=True,
                              help=f"{rating_info['count']} Bewertungen")
        
        # Rating-Widget
        if st.user.is_logged_in:
            render_sportangebot_rating_widget(offer['href'])
    
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
                st.caption(f"... and {len(upcoming_events) - 10} more dates")
        else:
            st.info("No upcoming dates available")
    
    st.divider()

