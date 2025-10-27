import streamlit as st
import json
from datetime import datetime
from collections import defaultdict
from st_supabase_connection import SupabaseConnection

def supaconn():
    """Returns Supabase connection"""
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=url, key=key)
    return conn

def _parse_trainers_json(trainers_data):
    """Converts trainer data from JSON to Python list"""
    if isinstance(trainers_data, str):
        return json.loads(trainers_data)
    return trainers_data

def _convert_event_fields(event):
    """Converts trainer data from view into expected format"""
    # Get trainers from JSON
    trainers = _parse_trainers_json(event.get('trainers', []))
    
    # Convert to lists
    event['trainers'] = [t['name'] for t in trainers if 'name' in t]
    event['trainer_ratings'] = [t.get('rating', 'N/A') for t in trainers]
    
    # Add details if needed
    if 'kurs_details' in event:
        event['details'] = event['kurs_details']
    
    return event

@st.cache_data(ttl=600)
def get_offers_with_stats():
    """Loads all offers with stats"""
    conn = supaconn()
    
    # Use sportangebote_with_ratings base view
    result = conn.table("sportangebote_with_ratings").select("*").order("avg_rating", desc=True).order("name").execute()
    return result.data

@st.cache_data(ttl=300)
def get_all_events():
    """Loads all future events with all data"""
    conn = supaconn()
    now = datetime.now().isoformat()
    
    # Use vw_termine_full view (returns data in correct format)
    events_result = conn.table("vw_termine_full").select("*").gte("start_time", now).order("start_time").execute()
    events = events_result.data
    
    return [_convert_event_fields(event) for event in events]

@st.cache_data(ttl=300)
def get_events_for_offer(offer_href):
    """Loads all future events for a specific offer"""
    conn = supaconn()
    now = datetime.now().isoformat()
    
    # Use vw_termine_full view
    events_result = conn.table("vw_termine_full").select("*").eq("offer_href", offer_href).gte("start_time", now).order("start_time").execute()
    events = events_result.data
    
    return [_convert_event_fields(event) for event in events]

@st.cache_data(ttl=300)
def count_upcoming_events_per_offer():
    """Counts upcoming events for all offers"""
    conn = supaconn()
    now = datetime.now().isoformat()
    events_result = conn.table("vw_termine_full").select("offer_href, canceled").gte("start_time", now).execute()
    
    counts = defaultdict(int)
    for event in events_result.data:
        if not event.get('canceled', False):
            offer_href = event.get('offer_href')
            if offer_href:
                counts[offer_href] += 1
    return dict(counts)

@st.cache_data(ttl=300, show_spinner=False)
def get_events_by_offer_mapping():
    """Loads all future events grouped by offer_href"""
    conn = supaconn()
    now = datetime.now().isoformat()
    events_result = conn.table("vw_termine_full").select("*").gte("start_time", now).order("start_time").execute()
    events = events_result.data
    
    mapping = defaultdict(list)
    for event in events:
        offer_href = event.get('offer_href')
        if offer_href:
            mapped_event = _convert_event_fields(event)
            mapping[offer_href].append(mapped_event)
    return dict(mapping)

@st.cache_data(ttl=600)
def get_trainers_for_all_offers():
    """Loads trainers for all offers"""
    conn = supaconn()
    events_result = conn.table("vw_termine_full").select("offer_href, trainers").execute()
    
    href_to_trainers = defaultdict(lambda: defaultdict(dict))
    for event in events_result.data:
        offer_href = event.get('offer_href')
        trainers = _parse_trainers_json(event.get('trainers', []))
        for trainer in trainers:
            if 'name' in trainer:
                href_to_trainers[offer_href][trainer['name']]['name'] = trainer['name']
                href_to_trainers[offer_href][trainer['name']]['rating'] = trainer.get('rating', 'N/A')
    return {href: list(trainer_dict.values()) for href, trainer_dict in href_to_trainers.items()}


def get_supabase_client():
    """Returns a direct Supabase client for advanced operations"""
    conn = supaconn()
    return conn


@st.cache_resource
def get_user_from_db(user_sub: str):
    """Gets a user from the database by their OIDC sub claim"""
    conn = supaconn()
    result = conn.table("users").select("*").eq("sub", user_sub).execute()
    return result.data[0] if result.data else None


def create_or_update_user(user_data: dict):
    """Creates or updates a user in the database"""
    conn = supaconn()
    
    user_sub = user_data.get('sub')
    if not user_sub:
        return None
    
    # Check if user exists
    existing = conn.table("users").select("*").eq("sub", user_sub).execute()
    
    if existing.data:
        # Update existing user
        result = conn.table("users").update(user_data).eq("sub", user_sub).execute()
    else:
        # Create new user
        result = conn.table("users").insert(user_data).execute()
    
    return result.data[0] if result.data else None


def get_user_role(user_sub: str):
    """Gets the role of a user"""
    user = get_user_from_db(user_sub)
    return user.get('role', 'user') if user else 'user'
