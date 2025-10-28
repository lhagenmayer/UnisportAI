"""
iCal Generator für dynamische Kalender-Feeds
Generiert iCal-Feeds mit Friend ATTENDEE Support
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from data.supabase_client import supaconn
from data.auth import get_user_sub


def format_ical_date(date: datetime) -> str:
    """
    Format date for iCal: YYYYMMDDTHHMMSSZ
    
    Args:
        date: Datetime object
        
    Returns:
        str: Formatted date string
    """
    return date.strftime('%Y%m%dT%H%M%SZ')


def get_friends_emails_for_event(event_id: str, user_id: str) -> List[str]:
    """
    Holt E-Mail Adressen von Freunden die auch zu einem Event gehen.
    
    Args:
        event_id: Event-ID
        user_id: ID des aktuellen Users
        
    Returns:
        List[str]: Liste von E-Mail Adressen
    """
    try:
        conn = supaconn()
        
        # Hole Freundschaften
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
        
        # Hole Freunde die auch gehen
        notifications = conn.table("friend_course_notifications").select(
            "user_id, users!user_id(email)"
        ).eq("event_id", event_id).in_("user_id", friend_ids).execute()
        
        # Extrahiere E-Mail Adressen
        emails = []
        for notif in notifications.data:
            if isinstance(notif.get('users'), dict) and notif['users'].get('email'):
                emails.append(notif['users']['email'])
        
        return emails
        
    except Exception as e:
        st.error(f"Fehler beim Holen von Freund-E-Mails: {e}")
        return []


def generate_dynamic_ical_with_attendees(user_id: Optional[str] = None) -> str:
    """
    Generiert eine dynamische iCal-Datei mit allen "going" Events des Users
    inklusive Freunde als ATTENDEE.
    
    Args:
        user_id: Optional - user_id. Falls None, wird current user verwendet.
        
    Returns:
        str: iCal-Formatierte Zeichenkette
    """
    try:
        # Hole user_id falls nicht gegeben
        if not user_id:
            user_sub = get_user_sub()
            if not user_sub:
                return "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
            
            conn = supaconn()
            user = conn.table("users").select("id").eq("sub", user_sub).execute()
            if not user.data:
                return "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
            user_id = user.data[0]['id']
        
        conn = supaconn()
        
        # Hole alle "going" Notifications des Users
        notifications = conn.table("friend_course_notifications").select(
            "event_id, created_at"
        ).eq("user_id", user_id).execute()
        
        if not notifications.data:
            # Leere Kalender wenn keine Events
            return """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Unisport AI//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Unisport Meine Kurse
X-WR-TIMEZONE:Europe/Zurich
X-WR-CALDESC:Meine angemeldeten Sportkurse
END:VCALENDAR"""
        
        # Hole die aktuellen Termine
        event_ids = [n['event_id'] for n in notifications.data]
        
        # Hole Events aus kurs_termine
        # Parse event_id format: "kursnr_starttime_location"
        # Example: "200-101_2025-11-03 18:45:00+00_Sprachheilschule, Turnhalle"
        all_events = []
        for event_id in event_ids:
            parts = event_id.split('_')
            if len(parts) >= 2:
                kursnr = parts[0]
                
                # Find start_time (everything between kursnr and location)
                # Location is the last part after the last underscore
                last_underscore_index = event_id.rfind('_')
                if last_underscore_index > 0:
                    start_time = event_id[len(kursnr) + 1:last_underscore_index]
                else:
                    start_time = parts[1] if len(parts) > 1 else ''
                
                # Hole Event aus kurs_termine
                result = conn.table("kurs_termine").select("*").eq('kursnr', kursnr).eq('start_time', start_time).execute()
                if result.data:
                    # Join with unisport_locations to get lat/lng
                    for event_data in result.data:
                        lat, lng = None, None
                        if event_data.get('ort_href') and event_data.get('location_name'):
                            # Try exact match first
                            location_result = conn.table("unisport_locations").select("lat, lng, ort_href").eq("ort_href", event_data['ort_href']).execute()
                            
                            # If no exact match, try by location name
                            if not location_result.data or len(location_result.data) == 0:
                                location_result = conn.table("unisport_locations").select("lat, lng").eq("name", event_data['location_name']).execute()
                            
                            if location_result.data and len(location_result.data) > 0:
                                location_info = location_result.data[0]
                                lat = location_info.get('lat')
                                lng = location_info.get('lng')
                        
                        # Add lat/lng to event
                        event_data['lat'] = lat
                        event_data['lng'] = lng
                        all_events.append(event_data)
        
        # Verwende all_events direkt
        events_list = all_events
        
        if not events_list:
            return "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"
        
        # Generiere iCal
        ical_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Unisport AI//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:Unisport Meine Kurse",
            "X-WR-TIMEZONE:Europe/Zurich",
            "X-WR-CALDESC:Meine angemeldeten Sportkurse",
        ]
        
        for event in events_list:
            if not event.get('start_time'):
                continue
            
            start_time = datetime.fromisoformat(str(event['start_time']).replace('Z', '+00:00'))
            end_time = event.get('end_time')
            if end_time:
                end_time = datetime.fromisoformat(str(end_time).replace('Z', '+00:00'))
            else:
                end_time = start_time + timedelta(hours=1)
            
            # Event ID (gleiche Logik wie in Edge Function)
            event_id = f"{event.get('kursnr', '')}_{event.get('start_time', '')}_{event.get('location_name', '')}"
            
            # UID
            uid = f"{event.get('kursnr', '')}_{event.get('start_time', '')}_{user_id}"
            
            # Trainer info
            trainers = event.get('trainers', [])
            trainers_str = ', '.join(trainers) if isinstance(trainers, list) else (trainers or 'N/A')
            
            # Hole Freunde-E-Mails
            friend_emails = get_friends_emails_for_event(event_id, user_id)
            
            # Hole sport_name aus sportangebote via sportkurse
            sport_name = 'Sportkurs'
            try:
                result = conn.table("sportkurse").select("offer_href, sportangebote(name)").eq("kursnr", event.get('kursnr', '')).limit(1).execute()
                if result.data and result.data[0].get('sportangebote'):
                    sport_name = result.data[0]['sportangebote']['name']
            except:
                pass
            
            # Erstelle Event
            event_lines = [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{format_ical_date(datetime.utcnow())}",
                f"DTSTART:{format_ical_date(start_time)}",
                f"DTEND:{format_ical_date(end_time)}",
                f"SUMMARY:{sport_name}",
                f"LOCATION:{event.get('location_name', 'Unisport')}",
                f"DESCRIPTION:Trainer: {trainers_str}",
            ]
            
            # Add GEO coordinates if available (format: lat;long)
            if event.get('lat') and event.get('lng'):
                event_lines.append(f"GEO:{event['lat']};{event['lng']}")
            
            # Füge Freunde als ATTENDEE hinzu
            for email in friend_emails:
                event_lines.append(f"ATTENDEE;RSVP=TRUE;CN=Freund:mailto:{email}")
            
            event_lines.extend([
                "STATUS:CONFIRMED",
                "SEQUENCE:0",
                "BEGIN:VALARM",
                "TRIGGER:-PT15M",
                "ACTION:DISPLAY",
                "DESCRIPTION:Erinnerung",
                "END:VALARM",
                "END:VEVENT"
            ])
            
            ical_lines.extend(event_lines)
        
        ical_lines.append("END:VCALENDAR")
        
        return "\r\n".join(ical_lines)
        
    except Exception as e:
        st.error(f"Fehler beim Generieren des iCal Feeds: {e}")
        return "BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR"

