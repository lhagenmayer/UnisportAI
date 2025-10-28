"""
FastAPI iCal Feed für Vercel
"""

from fastapi import FastAPI, Query
from fastapi.responses import Response
import os
from supabase import create_client
from datetime import datetime, timedelta
from typing import Optional
from icalendar import Calendar, Event, Alarm, vCalAddress, vText

app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "Unisport iCal Feed API", "version": "1.0.0"}


@app.get("/ical-feed")
async def get_ical_feed(token: Optional[str] = Query(None)):
    if not token:
        return {"error": "Missing token parameter"}
    
    # Get Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    
    if not supabase_url or not supabase_key:
        return {"error": "Missing Supabase credentials"}
    
    try:
        # Generate iCal feed
        ical_content = generate_ical_feed(supabase_url, supabase_key, token)
        
        return Response(
            content=ical_content,
            media_type="text/calendar; charset=utf-8",
            headers={"Content-Disposition": "inline; filename=unisport_meine_kurse.ics"}
        )
    except Exception as e:
        return {"error": str(e)}


def generate_ical_feed(supabase_url: str, supabase_key: str, token: str) -> str:
    """Generate iCal feed content"""
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # Lookup user by ical_feed_token
        user_result = supabase.table('users').select('id, email, name, ical_feed_token').eq('ical_feed_token', token).single().execute()
        
        if not user_result.data:
            # Return empty calendar
            cal = Calendar()
            cal.add('version', '2.0')
            cal.add('prodid', '-//Unisport AI//EN')
            return cal.to_ical().decode('utf-8')
        
        user_data = user_result.data
        user_id = user_data['id']
        
        # Get user's "going" notifications
        notifications = supabase.table('friend_course_notifications').select('event_id, created_at').eq('user_id', user_id).execute()
        
        if not notifications.data:
            cal = Calendar()
            cal.add('version', '2.0')
            cal.add('prodid', '-//Unisport AI//EN')
            return cal.to_ical().decode('utf-8')
        
        # Get all unique event_ids
        event_ids = list(set([n['event_id'] for n in notifications.data]))
        
        # Create calendar
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//Unisport AI//EN')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('X-WR-CALNAME', 'Unisport Meine Kurse')
        cal.add('X-WR-TIMEZONE', 'Europe/Zurich')
        cal.add('X-WR-CALDESC', 'Meine angemeldeten Sportkurse')
        
        # Fetch event details for each event_id
        for event_id_str in event_ids:
            try:
                # Parse event_id to extract kursnr and start_time
                parts = event_id_str.split('_', 2)
                if len(parts) < 3:
                    continue
                
                kursnr = parts[0]
                start_time_str = parts[1].replace('%20', ' ')
                
                # Fetch event details
                result = supabase.table('kurs_termine').select('*, unisport_locations(*)').eq('kursnr', kursnr).eq('start_time', start_time_str).limit(1).execute()
                
                if not result.data:
                    continue
                
                event = result.data[0]
                
                # Parse dates
                start_time = datetime.fromisoformat(str(event['start_time']).replace('Z', '+00:00'))
                end_time = event.get('end_time')
                if end_time:
                    end_time = datetime.fromisoformat(str(end_time).replace('Z', '+00:00'))
                else:
                    end_time = start_time + timedelta(hours=1)
                
                # Get location
                location = event.get('unisport_locations')
                location_name = location.get('name', 'Unisport') if location else event.get('location_name', 'Unisport')
                lat = location.get('lat') if location else None
                lng = location.get('lng') if location else None
                
                # Get sport name
                sport_name = 'Sportkurs'
                try:
                    sport_result = supabase.table("sportkurse").select("sportangebote(name)").eq("kursnr", kursnr).limit(1).execute()
                    if sport_result.data and sport_result.data[0].get('sportangebote'):
                        sport_name = sport_result.data[0]['sportangebote']['name']
                except:
                    pass
                
                # Get trainers
                trainers = event.get('trainers', [])
                trainers_str = ', '.join(trainers) if isinstance(trainers, list) else (trainers or 'N/A')
                
                # Create iCal event
                ical_event = Event()
                ical_event.add('uid', f"{kursnr}_{start_time_str}_{user_data['email']}")
                ical_event.add('dtstamp', datetime.utcnow())
                ical_event.add('dtstart', start_time)
                ical_event.add('dtend', end_time)
                ical_event.add('summary', sport_name)
                ical_event.add('location', location_name)
                ical_event.add('description', f"Trainer: {trainers_str}")
                
                # GEO coordinates
                if lat and lng:
                    ical_event.add('geo', (float(lat), float(lng)))
                
                # Status
                ical_event.add('status', 'CONFIRMED')
                
                # Alarm
                alarm = Alarm()
                alarm.add('action', 'DISPLAY')
                alarm.add('trigger', timedelta(minutes=-15))
                alarm.add('description', 'Erinnerung')
                ical_event.add_component(alarm)
                
                cal.add_component(ical_event)
            except Exception as e:
                continue
        
        return cal.to_ical().decode('utf-8')
    except Exception as e:
        # Return empty calendar on error
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//Unisport AI//EN')
        return cal.to_ical().decode('utf-8')
