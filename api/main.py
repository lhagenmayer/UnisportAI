"""
FastAPI Endpoint für iCal Feed
Hosted on Vercel
"""
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import Response
from supabase import create_client
import os
from datetime import datetime, timedelta
from typing import Optional
from icalendar import Calendar, Event, Alarm, vCalAddress, vText

app = FastAPI(title="Unisport iCal Feed")

# Supabase Credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")


@app.get("/")
async def root():
    return {"message": "Unisport iCal Feed API", "version": "1.0.0"}


@app.get("/ical-feed")
async def get_ical_feed(token: str = Query(...)):
    """
    Generate personalized iCal feed for user
    Access via: https://your-app.vercel.app/ical-feed?token=YOUR_TOKEN
    """
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Lookup user by ical_feed_token
        user_result = supabase.table('users').select('id, email, name, ical_feed_token').eq('ical_feed_token', token).single().execute()
        
        if not user_result.data:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = user_result.data
        user_id = user_data['id']
        
        # Get user's "going" notifications
        notifications = supabase.table('friend_course_notifications').select('event_id, created_at').eq('user_id', user_id).execute()
        
        if not notifications.data:
            # Return empty calendar
            cal = Calendar()
            cal.add('version', '2.0')
            cal.add('prodid', '-//Unisport AI//EN')
            cal.add('calscale', 'GREGORIAN')
            cal.add('method', 'PUBLISH')
            cal.add('X-WR-CALNAME', 'Unisport Meine Kurse')
            cal.add('X-WR-TIMEZONE', 'Europe/Zurich')
            cal.add('X-WR-CALDESC', 'Meine angemeldeten Sportkurse')
            return Response(content=cal.to_ical(), media_type="text/calendar", headers={"Content-Disposition": "inline; filename=unisport.ics"})
        
        # Parse events and get course dates
        event_ids = [n['event_id'] for n in notifications.data]
        all_events = []
        
        for event_id in event_ids:
            parts = event_id.split('_')
            if len(parts) >= 2:
                kursnr = parts[0]
                last_underscore_index = event_id.rfind('_')
                if last_underscore_index > 0:
                    start_time = event_id[len(kursnr) + 1:last_underscore_index]
                else:
                    start_time = parts[1] if len(parts) > 1 else ''
                
                # Get event from kurs_termine
                result = supabase.table('kurs_termine').select('*').eq('kursnr', kursnr).eq('start_time', start_time).execute()
                
                if result.data:
                    for event_data in result.data:
                        # Add location data
                        if event_data.get('ort_href') and event_data.get('location_name'):
                            location_result = supabase.table('unisport_locations').select('lat, lng').eq('name', event_data['location_name']).execute()
                            if location_result.data and len(location_result.data) > 0:
                                event_data['lat'] = location_result.data[0].get('lat')
                                event_data['lng'] = location_result.data[0].get('lng')
                        
                        # Add sport name
                        try:
                            sport_result = supabase.table('sportkurse').select('offer_href, sportangebote(name)').eq('kursnr', kursnr).limit(1).execute()
                            if sport_result.data and sport_result.data[0].get('sportangebote'):
                                event_data['sport_name'] = sport_result.data[0]['sportangebote']['name']
                        except:
                            event_data['sport_name'] = 'Sportkurs'
                        
                        all_events.append(event_data)
        
        # Create calendar
        cal = Calendar()
        cal.add('version', '2.0')
        cal.add('prodid', '-//Unisport AI//EN')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('X-WR-CALNAME', 'Unisport Meine Kurse')
        cal.add('X-WR-TIMEZONE', 'Europe/Zurich')
        cal.add('X-WR-CALDESC', 'Meine angemeldeten Sportkurse')
        
        # Get user email
        user_email = user_data.get('email', '')
        user_name = user_data.get('name', '')
        
        # Add events
        for event_data in all_events:
            if not event_data.get('start_time'):
                continue
            
            # Parse timestamps
            start_time = datetime.fromisoformat(str(event_data['start_time']).replace('Z', '+00:00'))
            end_time = event_data.get('end_time')
            if end_time:
                end_time = datetime.fromisoformat(str(end_time).replace('Z', '+00:00'))
            else:
                end_time = start_time + timedelta(hours=1)
            
            event_id = f"{event_data.get('kursnr', '')}_{event_data.get('start_time', '')}_{event_data.get('location_name', '')}"
            
            # Get friend emails
            friend_emails = get_friends_emails_for_event(supabase, event_id, user_id)
            
            # Create event
            ical_event = Event()
            ical_event.add('uid', f"{event_data.get('kursnr', '')}_{start_time.strftime('%Y%m%dT%H%M%S')}-{user_email}")
            ical_event.add('dtstamp', datetime.utcnow())
            ical_event.add('dtstart', start_time)
            ical_event.add('dtend', end_time)
            ical_event.add('summary', event_data.get('sport_name', 'Sportkurs'))
            ical_event.add('location', event_data.get('location_name', 'Unisport'))
            
            # Add trainers as description
            trainers = event_data.get('trainers', [])
            trainers_str = ', '.join(trainers) if isinstance(trainers, list) else (trainers or 'N/A')
            ical_event.add('description', f"Trainer: {trainers_str}")
            
            # Add GEO coordinates
            if event_data.get('lat') and event_data.get('lng'):
                ical_event.add('geo', (float(event_data['lat']), float(event_data['lng'])))
            
            ical_event.add('status', 'CONFIRMED')
            ical_event.add('sequence', 0)
            
            # Add friend attendees
            if friend_emails:
                for email in friend_emails:
                    attendee = vCalAddress(f'mailto:{email}')
                    attendee.params['CN'] = vText(f"Freund: {email}")
                    attendee.params['RSVP'] = vText('TRUE')
                    ical_event.add('attendee', attendee)
            
            # Add alarm
            alarm = Alarm()
            alarm.add('action', 'DISPLAY')
            alarm.add('trigger', timedelta(minutes=-15))
            alarm.add('description', 'Erinnerung')
            ical_event.add_component(alarm)
            
            cal.add_component(ical_event)
        
        return Response(
            content=cal.to_ical(),
            media_type="text/calendar",
            headers={"Content-Disposition": "inline; filename=unisport_meine_kurse.ics"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating iCal feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_friends_emails_for_event(supabase_client, event_id: str, user_id: str) -> list:
    """Get friend emails who are also going to event"""
    try:
        # Get friendships
        friendships = supabase_client.table("user_friends").select("*").execute()
        
        if not friendships.data:
            return []
        
        # Get friend IDs
        friend_ids = []
        for friendship in friendships.data:
            if friendship['requester_id'] == user_id:
                friend_ids.append(friendship['addressee_id'])
            elif friendship['addressee_id'] == user_id:
                friend_ids.append(friendship['requester_id'])
        
        if not friend_ids:
            return []
        
        # Get friends who are also going
        notifications = supabase_client.table("friend_course_notifications").select(
            "user_id, users!user_id(email)"
        ).eq("event_id", event_id).in_("user_id", friend_ids).execute()
        
        # Extract emails
        emails = []
        for notif in notifications.data:
            if isinstance(notif.get('users'), dict) and notif['users'].get('email'):
                emails.append(notif['users']['email'])
        
        return emails
        
    except Exception:
        return []


# For Vercel
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

