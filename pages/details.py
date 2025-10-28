import streamlit as st
from datetime import datetime, time, timedelta
from data.supabase_client import get_events_for_offer, get_all_events, supaconn
from data.state_manager import get_selected_offers_for_page2, get_filter_state, set_filter_state
from data.shared_sidebar import render_shared_sidebar
from data.rating import render_sportangebot_rating_widget, render_trainer_rating_widget, get_average_rating_for_offer, get_average_rating_for_trainer
from data.auth import is_logged_in, get_user_sub, get_user_email
from data.email_service import generate_ical_event, send_calendar_email_via_loops

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()


def get_user_id():
    """Holt die user_id aus der users Tabelle"""
    try:
        user_sub = get_user_sub()
        if not user_sub:
            return None
        
        conn = supaconn()
        result = conn.table("users").select("id").eq("sub", user_sub).execute()
        return result.data[0]['id'] if result.data else None
    except Exception:
        return None


def get_event_id(event):
    """Erstellt eine eindeutige Event-ID"""
    start_time = event.get('start_time', '')
    kursnr = event.get('kursnr', '')
    location = event.get('location_name', '')
    return f"{kursnr}_{start_time}_{location}"


def is_user_going_to_event(user_id, event):
    """Prüft, ob der User zu einem Event geht"""
    if not user_id:
        return False
    
    try:
        conn = supaconn()
        event_id = get_event_id(event)
        result = conn.table("friend_course_notifications").select("*").eq(
            "user_id", user_id
        ).eq("event_id", event_id).execute()
        return len(result.data) > 0
    except Exception:
        return False


def get_friends_going_to_event(user_id, event):
    """Holt Freunde, die zu einem Event gehen"""
    if not user_id:
        return []
    
    try:
        conn = supaconn()
        
        # Hole die user_id des aktuellen Benutzers
        current_user_data = conn.table("users").select("id").eq("id", user_id).execute()
        if not current_user_data.data:
            return []
        
        # Hole alle Freundschaften
        friendships = conn.table("user_friends").select("*").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        if not friendships.data:
            return []
        
        # Bestimme Freunde-IDs
        friend_ids = []
        for friendship in friendships.data:
            if friendship['requester_id'] == user_id:
                friend_ids.append(friendship['addressee_id'])
            else:
                friend_ids.append(friendship['requester_id'])
        
        if not friend_ids:
            return []
        
        # Hole Notifications von Freunden für dieses Event
        event_id = get_event_id(event)
        notifications = conn.table("friend_course_notifications").select(
            "*, user:users!user_id(*)"
        ).eq("event_id", event_id).in_("user_id", friend_ids).execute()
        
        return notifications.data or []
    except Exception:
        return []


def mark_event_going(user_id, event):
    """Markiert, dass der User zu einem Event geht"""
    if not user_id:
        return False
    
    try:
        conn = supaconn()
        event_id = get_event_id(event)
        
        # Prüfe ob bereits vorhanden
        existing = conn.table("friend_course_notifications").select("*").eq(
            "user_id", user_id
        ).eq("event_id", event_id).execute()
        
        if existing.data:
            return True  # Bereits vorhanden
        
        # Hole alle Freundschaften, um Freunden zu benachrichtigen
        friendships = conn.table("user_friends").select("*").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        # Erstelle Notifications für alle Freunde
        notifications = []
        friends_to_notify_ids = []
        
        if friendships.data:
            friend_ids = []
            for friendship in friendships.data:
                if friendship['requester_id'] == user_id:
                    friend_ids.append(friendship['addressee_id'])
                else:
                    friend_ids.append(friendship['requester_id'])
            
            # Finde Freunde die bereits "going" sind - diese bekommen eine Kalendereinladung
            existing_going = conn.table("friend_course_notifications").select("*").eq(
                "event_id", event_id
            ).in_("user_id", friend_ids).execute()
            
            if existing_going.data:
                friends_to_notify_ids = [notif['user_id'] for notif in existing_going.data]
            
            for friend_id in friend_ids:
                notifications.append({
                    "user_id": user_id,
                    "friend_id": friend_id,
                    "event_id": event_id,
                    "created_at": datetime.now().isoformat()
                })
        
        # IMPORTANT: Add self-notification even if there are no friends
        # This creates the "going" status for the user
        self_notification = {
            "user_id": user_id,
            "friend_id": user_id,  # Self-notification
            "event_id": event_id,
            "created_at": datetime.now().isoformat()
        }
        
        # Füge hinzu
        all_notifications = notifications + [self_notification]
        conn.table("friend_course_notifications").insert(all_notifications).execute()
        
        # Wenn Freunde bereits going sind, sende ihnen Kalendereinladungs-Update
        if friends_to_notify_ids:
            # Importiere die Funktion
            from data.email_service import send_calendar_invitation_update
            
            # Hole Info des aktuellen Users
            current_user_info = conn.table("users").select("name, email").eq("id", user_id).execute()
            if current_user_info.data:
                current_user_name = current_user_info.data[0].get('name', 'Freund')
                current_user_email = current_user_info.data[0].get('email', '')
                
                # Sende Updates an alle Freunde die bereits going sind
                for friend_id in friends_to_notify_ids:
                    friend_info = conn.table("users").select("email").eq("id", friend_id).execute()
                    if friend_info.data:
                        friend_email = friend_info.data[0].get('email')
                        if friend_email:
                            send_calendar_invitation_update(
                                recipient_email=friend_email,
                                event=event,
                                attendee_name=current_user_name,
                                attendee_email=current_user_email
                            )
        
        # Sende E-Mail mit Kalendereintrag
        user_email = get_user_email()
        user_name = conn.table("users").select("name").eq("id", user_id).execute()
        user_name = user_name.data[0]['name'] if user_name.data else "Sportliebhaber"
        
        if user_email:
            # Generate iCal content
            ical_content = generate_ical_event(event, user_email, user_name)
            
            # Get user's ical_feed_token for personalized Feed URL in email
            from data.user_management import get_or_create_ical_feed_token
            from data.auth import get_user_sub
            
            user_sub = get_user_sub()
            ical_token = get_or_create_ical_feed_token(user_sub) if user_sub else None
            
            # Sende E-Mail via Loops.io mit iCal Feed Link
            from data.email_service import send_calendar_email_via_loops
            # Send email with Edge Function feed link (no Storage needed anymore)
            email_sent = send_calendar_email_via_loops(user_email, user_name, event, ical_token=ical_token)
            
            if email_sent:
                st.success(f"✅ E-Mail mit iCal Feed Link wurde an {user_email} gesendet!")
            else:
                st.success(f"✅ Anmeldung erfolgreich!")
            
            # Zeige zusätzlich Download-Button als Fallback
            with st.expander("📥 Alternative: iCal Datei lokal herunterladen"):
                st.download_button(
                    label="📥 .ics Datei lokal herunterladen",
                    data=ical_content,
                    file_name=f"unisport_{event.get('sport_name', 'event').replace(' ', '_')}.ics",
                    mime="text/calendar"
                )
        
        return True
    except Exception as e:
        st.error(f"Fehler: {e}")
        return False


def unmark_event_going(user_id, event):
    """Entfernt die Markierung, dass der User zu einem Event geht"""
    if not user_id:
        return False
    
    try:
        conn = supaconn()
        event_id = get_event_id(event)
        
        # Löschen
        conn.table("friend_course_notifications").delete().eq(
            "user_id", user_id
        ).eq("event_id", event_id).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler: {e}")
        return False


# Get current user_id
current_user_id = get_user_id()

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
    
    # Get average rating
    rating_info = get_average_rating_for_offer(selected['href'])
    
    # Display info in responsive columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Intensity", intensity)
    with col2:
        st.metric("Focus", focus if focus else 'N/A')
    with col3:
        st.metric("Setting", setting if setting else 'N/A')
    with col4:
        if rating_info['count'] > 0:
            st.metric("Rating", f"{rating_info['avg']}/5 ⭐ ({rating_info['count']} Bewertungen)")
        else:
            st.metric("Rating", "Noch keine Bewertungen")
    
    # Rating-Widget für das Sportangebot
    if st.user.is_logged_in:
        render_sportangebot_rating_widget(selected['href'])

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

# Display events with "Going" buttons
for idx, event in enumerate(filtered_events):
    with st.container():
        col1, col2 = st.columns([5, 1])
        
        with col1:
            # Get display info
            start_time = event.get('start_time')
            end_time = event.get('end_time')
            
            if isinstance(start_time, str):
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            else:
                start_dt = start_time
            
            if end_time:
                if isinstance(end_time, str):
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                else:
                    end_dt = end_time
                end_formatted = end_dt.strftime('%H:%M')
            else:
                end_formatted = ''
            
            weekday_en = start_dt.strftime('%A')
            weekday_de = weekdays_de.get(weekday_en, weekday_en)
            date_formatted = start_dt.strftime('%d.%m.%Y')
            time_formatted = start_dt.strftime('%H:%M')
            
            date_string = f"{weekday_de}, {date_formatted}"
            time_string = f"{time_formatted} - {end_formatted}" if end_formatted else time_formatted
            
            # Check if cancelled
            is_cancelled = event.get('canceled', False)
            
            # Check if user is going
            user_going = is_user_going_to_event(current_user_id, event)
            
            # Get friends going
            friends_going = get_friends_going_to_event(current_user_id, event) if current_user_id else []
            
            # Display event info
            status_icon = "🔴" if is_cancelled else ("✅" if user_going else "⚪")
            status_text = "Abgesagt" if is_cancelled else ("Ich gehe hin" if user_going else "")
            
            st.markdown(f"""
            <div style="padding: 12px; border-radius: 8px; border-left: 4px solid {"red" if is_cancelled else "green" if user_going else "gray"}; background-color: {"#ffebee" if is_cancelled else "#e8f5e9" if user_going else "#f5f5f5"}; margin-bottom: 8px;">
                <h4>{status_icon} {event.get('sport_name', 'Kurs')} - {event.get('location_name', 'Ort')}</h4>
                <p><b>📅 {date_string}</b> | <b>⏰ {time_string}</b></p>
                <p>📍 {event.get('location_name', 'N/A')}</p>
                {f"<p>👤 Trainer: {', '.join(event.get('trainers', []))}</p>" if event.get('trainers') else ""}
                {f"<p>💰 Preis: {event.get('preis', 'N/A')}</p>" if event.get('preis') else ""}
                {"<p style='color: green;'>" + status_text + "</p>" if status_text else ""}
            </div>
            """, unsafe_allow_html=True)
            
            # Show friends going
            if friends_going:
                friend_names = []
                for friend in friends_going:
                    user_info = friend.get('user', {})
                    if isinstance(user_info, dict) and 'name' in user_info:
                        friend_names.append(user_info['name'])
                
                if friend_names:
                    st.info(f"👥 **{len(friend_names)} {'Freund' if len(friend_names) == 1 else 'Freunde'} gehen hin:** {', '.join(friend_names)}")
        
        with col2:
            if current_user_id and not is_cancelled:
                if user_going:
                    if st.button("❌ Abmelden", key=f"going_{idx}", use_container_width=True):
                        if unmark_event_going(current_user_id, event):
                            st.success("Erfolgreich abgemeldet!")
                            st.rerun()
                else:
                    if st.button("✅ Hin", key=f"going_{idx}", use_container_width=True):
                        if mark_event_going(current_user_id, event):
                            st.success("Du gehst jetzt hin! Deine Freunde wurden benachrichtigt.")
                            st.rerun()
        
        st.divider()

# Rating für Trainer (nur wenn eingeloggt und Trainer vorhanden)
if st.user.is_logged_in and has_selected_offer:
    # Sammle alle Trainer
    all_trainers = set()
    for event in filtered_events:
        trainers = event.get('trainers', [])
        for trainer_name in trainers:
            if trainer_name:
                all_trainers.add(trainer_name)
    
    if all_trainers:
        st.divider()
        st.subheader("⭐ Trainer bewerten")
        st.caption("Bewerten Sie Trainer, die Sie kennen")
        
        for trainer_name in sorted(all_trainers):
            # Get average rating for this trainer
            rating_info = get_average_rating_for_trainer(trainer_name)
            if rating_info['count'] > 0:
                st.text(f"{trainer_name}: {'⭐' * int(rating_info['avg'])} {rating_info['avg']}/5 ({rating_info['count']} Bewertungen)")
            
            render_trainer_rating_widget(trainer_name)