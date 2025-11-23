import streamlit as st
from datetime import datetime
from data.supabase_client import get_offers_with_stats, count_upcoming_events_per_offer, get_trainers_for_all_offers, get_events_for_offer, get_events_by_offer_mapping
from data.filters import filter_offers, filter_offers_by_events, filter_events
from data.state_manager import get_filter_state, set_filter_state, set_sports_data, set_selected_offer
from data.shared_sidebar import render_filters_sidebar, render_ml_recommendations_section
from data.auth import is_logged_in

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Page config
st.title('🎯 Sports Overview')
st.caption('Discover and book your perfect sports activities')

# Get all sports data
sports_data = get_sports_data()

# Render sidebar with filters
offers = render_filters_sidebar(sports_data=sports_data, events=None)

# Main content area
st.title("🎯 Sports Overview")
st.write("Discover and book your perfect sports activities")

# Show logic-based filter results
if offers:
    st.subheader(f"📋 Matching Activities ({len(offers)})")
    # Display activities in a clean card layout
    if not offers:
        st.info("🔍 No activities match your filters. Try adjusting your search criteria.")
        st.stop()

    for offer in offers:
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
else:
    st.info("No activities match your selected filters.")

# NEW: ML-based recommendations section
st.markdown("---")
st.subheader("✨ You Might Also Like")
render_ml_recommendations_section(
    sports_data=sports_data,
    current_filter_results=offers  # Exclude already shown sports
)

# Empty state footer
if len(filtered_offers) == 0:
    st.info("💡 **Tip:** Try clearing some filters to see more activities")

