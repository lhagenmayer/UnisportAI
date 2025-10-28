"""
E-Mail-Service für das Senden von Kalender-Event-E-Mails via Loops.io
"""
try:
    import streamlit as st
except ImportError:
    # Fallback if streamlit is not available (for testing)
    class st:
        class secrets:
            @staticmethod
            def get(path, default=None):
                return default
        
        @staticmethod
        def info(msg):
            print(f"INFO: {msg}")
        
        @staticmethod
        def warning(msg):
            print(f"WARNING: {msg}")
        
        @staticmethod
        def error(msg):
            print(f"ERROR: {msg}")
        
        @staticmethod
        def success(msg):
            print(f"SUCCESS: {msg}")

from datetime import datetime, timedelta
import requests
from typing import Dict


def generate_ical_event(event: Dict, user_email: str, user_name: str) -> str:
    """
    Generiert eine iCal-Datei für ein Event.
    
    Args:
        event: Event-Daten (mit start_time, end_time, sport_name, location_name, etc.)
        user_email: E-Mail-Adresse des Users
        user_name: Name des Users
        
    Returns:
        str: iCal-Formatierte Zeichenkette
    """
    # Parse timestamps
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
    else:
        # Default: 1 Stunde, falls kein Endzeitpunkt
        end_dt = start_dt + timedelta(hours=1)
    
    # iCal Format: YYYYMMDDTHHMMSSZ (UTC)
    start_ical = start_dt.strftime('%Y%m%dT%H%M%SZ')
    end_ical = end_dt.strftime('%Y%m%dT%H%M%SZ')
    
    # Generate unique ID
    from datetime import timezone
    event_uid = f"{int(datetime.now(timezone.utc).timestamp())}@unisport.ch"
    
    # Event details
    summary = event.get('sport_name', 'Sportkurs')
    location = event.get('location_name', 'Unisport')
    description = f"Trainer: {', '.join(event.get('trainers', []))}" if event.get('trainers') else ""
    
    # Build iCal content
    ical_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Unisport AI//EN
METHOD:REQUEST
BEGIN:VEVENT
UID:{event_uid}
DTSTAMP:{start_ical}
DTSTART:{start_ical}
DTEND:{end_ical}
SUMMARY:{summary}
LOCATION:{location}
DESCRIPTION:{description}
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Erinnerung
END:VALARM
END:VEVENT
END:VCALENDAR"""
    
    return ical_content


def send_calendar_email_via_loops(user_email: str, user_name: str, event: Dict, ical_token: str = None) -> bool:
    """
    Sendet E-Mail via Loops.io mit iCal-Feed-Link (Edge Function).
    
    Args:
        user_email: E-Mail-Adresse des Empfängers
        user_name: Name des Empfängers
        event: Event-Daten
        ical_token: Optional - Token für personalisierten iCal Feed
        
    Returns:
        bool: True wenn E-Mail erfolgreich gesendet wurde
    """
    if not user_email:
        return False
    
    try:
        # API Key aus Secrets
        try:
            api_key = st.secrets["loops"]["api_key"]
            if not api_key:
                st.error("Loops API Key ist leer")
                return False
        except (KeyError, AttributeError) as e:
            st.error(f"Loops API Key nicht gefunden in Secrets: {e}")
            return False
        
        # Get Supabase URL for Edge Function
        supabase_url = st.secrets.get("connections", {}).get("supabase", {}).get("url", "")
        project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "") if supabase_url else ""
        
        # Edge Function URL (Dynamischer iCal Feed) WITH Token
        if ical_token and project_ref:
            ical_feed_url = f"https://{project_ref}.supabase.co/functions/v1/ical-feed?token={ical_token}"
        elif project_ref:
            ical_feed_url = f"https://{project_ref}.supabase.co/functions/v1/ical-feed"
        else:
            ical_feed_url = ""
        
        if not ical_feed_url:
            st.warning("Konnte Feed-URL nicht erstellen. E-Mail wird nicht gesendet.")
            return False
        
        # Sende E-Mail via Loops.io mit dem iCal-Feed-Link
        loops_url = "https://app.loops.so/api/v1/transactional"
        
        payload = {
            "transactionalId": "cmh9rmlxm0qufwe0ia96x3tvf",
            "email": user_email,
            "dataVariables": {
                "ical": ical_feed_url,  # Template expects "ical", not "icalUrl"
                "icalUrl": ical_feed_url,
                "userName": user_name,
                "sportName": event.get('sport_name', 'Sportkurs'),
                "date": "Date placeholder",
                "time": "Time placeholder",
                "location": event.get('location_name', 'Unisport')
            }
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(loops_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code in [200, 201]:
            return True
        else:
            error_msg = f"Loops.io API Error: Status {response.status_code}"
            if response.text:
                error_msg += f" - {response.text}"
            st.error(error_msg)
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Netzwerkfehler beim E-Mail-Versand: {e}")
        return False
    except Exception as e:
        st.error(f"Unerwarteter Fehler beim E-Mail-Versand: {type(e).__name__}: {e}")
        return False

