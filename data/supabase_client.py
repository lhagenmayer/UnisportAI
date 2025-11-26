"""Supabase data access layer for UnisportAI.

This module centralizes database access operations used by the Streamlit
application. It exposes convenience functions for loading offers, events,
user data, ratings and social/friend operations. Most read functions use
``st.cache_data`` or ``st.cache_resource`` to reduce repeated network
calls and improve UI responsiveness.

Notes:
- Functions must avoid side effects beyond database reads/writes.
- Caching decorators are tuned for typical UI patterns (short TTLs).
"""

import streamlit as st
import json
from datetime import datetime
from collections import defaultdict
from typing import Optional, Dict, List, Any
from st_supabase_connection import SupabaseConnection
import logging

# Setup logging
logger = logging.getLogger(__name__)

@st.cache_resource
def supaconn():
    """Returns cached Supabase connection"""
    url = st.secrets["connections"]["supabase"]["url"]
    key = st.secrets["connections"]["supabase"]["key"]
    conn = st.connection("supabase", type=SupabaseConnection, url=url, key=key)
    return conn

def _parse_trainers_json(trainers_data):
    """Converts trainer data from JSON to Python list"""
    if isinstance(trainers_data, str):
        try:
            return json.loads(trainers_data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse trainers JSON: {trainers_data}")
            return []
    return trainers_data if trainers_data else []

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

# === Sports Offers & Events ===

@st.cache_data(ttl=300)  # Reduced from 600s to 300s for fresher ratings
def get_offers_with_stats():
    """Loads all offers with stats"""
    try:
        conn = supaconn()
        result = conn.table("sportangebote_with_ratings").select("*").order("avg_rating", desc=True).order("name").execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching offers with stats: {e}")
        st.error("Failed to load sport offers")
        return []

@st.cache_data(ttl=300)
def get_all_events():
    """Loads all future events with all data"""
    try:
        conn = supaconn()
        now = datetime.now().isoformat()
        events_result = conn.table("vw_termine_full").select("*").gte("start_time", now).order("start_time").execute()
        events = events_result.data
        return [_convert_event_fields(event) for event in events]
    except Exception as e:
        logger.error(f"Error fetching all events: {e}")
        st.error("Failed to load events")
        return []

@st.cache_data(ttl=300)
def get_events_for_offer(offer_href):
    """Loads all future events for a specific offer"""
    try:
        conn = supaconn()
        now = datetime.now().isoformat()
        events_result = conn.table("vw_termine_full").select("*").eq("offer_href", offer_href).gte("start_time", now).order("start_time").execute()
        events = events_result.data
        return [_convert_event_fields(event) for event in events]
    except Exception as e:
        logger.error(f"Error fetching events for offer {offer_href}: {e}")
        return []

@st.cache_data(ttl=300)
def count_upcoming_events_per_offer():
    """Counts upcoming events for all offers"""
    try:
        conn = supaconn()
        now = datetime.now().isoformat()
        # Only fetch needed fields for counting
        events_result = conn.table("vw_termine_full").select("offer_href, canceled").gte("start_time", now).execute()
        
        counts = defaultdict(int)
        for event in events_result.data:
            if not event.get('canceled', False):
                offer_href = event.get('offer_href')
                if offer_href:
                    counts[offer_href] += 1
        return dict(counts)
    except Exception as e:
        logger.error(f"Error counting upcoming events: {e}")
        return {}

@st.cache_data(ttl=300, show_spinner=False)
def get_events_by_offer_mapping():
    """Loads all future events grouped by offer_href"""
    try:
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
    except Exception as e:
        logger.error(f"Error fetching events mapping: {e}")
        return {}

@st.cache_data(ttl=300)  # Reduced from 600s
def get_trainers_for_all_offers():
    """Loads trainers for all offers"""
    try:
        conn = supaconn()
        # Only fetch needed fields
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
    except Exception as e:
        logger.error(f"Error fetching trainers: {e}")
        return {}

# === User Management ===

@st.cache_data(ttl=60)  # Cache user data for 1 minute
def get_user_from_db(user_sub: str):
    """Gets a user from the database by their OIDC sub claim"""
    try:
        conn = supaconn()
        result = conn.table("users").select("*").eq("sub", user_sub).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error fetching user {user_sub}: {e}")
        return None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Gets user information by user ID"""
    try:
        conn = supaconn()
        result = conn.table("users").select("name, picture, email, bio, created_at").eq("id", user_id).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error fetching user by ID {user_id}: {e}")
        return None

def create_or_update_user(user_data: dict):
    """Creates or updates a user in the database"""
    try:
        conn = supaconn()
        
        user_sub = user_data.get('sub')
        if not user_sub:
            logger.warning("Attempted to create/update user without sub")
            return None
        
        # Check if user exists
        existing = conn.table("users").select("*").eq("sub", user_sub).execute()
        
        if existing.data:
            # Update existing user
            result = conn.table("users").update(user_data).eq("sub", user_sub).execute()
        else:
            # Create new user
            result = conn.table("users").insert(user_data).execute()
        
        # Clear user cache
        get_user_from_db.clear()
        
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error creating/updating user: {e}")
        return None

def get_user_id_by_sub(user_sub: str) -> Optional[int]:
    """Gets user ID from database by sub"""
    try:
        conn = supaconn()
        result = conn.table("users").select("id").eq("sub", user_sub).execute()
        return result.data[0]['id'] if result.data else None
    except Exception as e:
        logger.error(f"Error fetching user ID for {user_sub}: {e}")
        return None

def get_user_profile(user_sub: str) -> Optional[Dict[str, Any]]:
    """Gets complete user profile from database"""
    try:
        conn = supaconn()
        result = conn.table("users").select("*").eq("sub", user_sub).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error loading profile for {user_sub}: {e}")
        st.error(f"Error loading profile: {e}")
        return None

def update_user_bio(user_sub: str, bio: str) -> bool:
    """Updates user bio"""
    try:
        conn = supaconn()
        conn.table("users").update({
            "bio": bio,
            "updated_at": datetime.now().isoformat()
        }).eq("sub", user_sub).execute()
        get_user_from_db.clear()
        return True
    except Exception as e:
        logger.error(f"Error updating bio for {user_sub}: {e}")
        return False

def update_user_preferences(user_sub: str, preferences: Dict[str, Any]) -> bool:
    """Updates user preferences"""
    try:
        conn = supaconn()
        preferences_json = json.dumps(preferences)
        conn.table("users").update({
            "preferences": preferences_json,
            "updated_at": datetime.now().isoformat()
        }).eq("sub", user_sub).execute()
        get_user_from_db.clear()
        return True
    except Exception as e:
        logger.error(f"Error updating preferences for {user_sub}: {e}")
        return False

def update_user_visibility(user_sub: str, is_public: bool) -> bool:
    """Updates user profile visibility"""
    try:
        conn = supaconn()
        conn.table("users").update({
            "is_public": is_public,
            "updated_at": datetime.now().isoformat()
        }).eq("sub", user_sub).execute()
        get_user_from_db.clear()
        return True
    except Exception as e:
        logger.error(f"Error updating visibility for {user_sub}: {e}")
        return False

def save_filter_preferences(user_sub: str, intensities: list, focus: list, 
                           settings: list, locations: list, weekdays: list) -> bool:
    """Saves filter preferences to database"""
    try:
        # Map weekdays to codes
        en_to_code = {
            'Monday': 'mon', 'Tuesday': 'tue', 'Wednesday': 'wed',
            'Thursday': 'thu', 'Friday': 'fri', 'Saturday': 'sat', 'Sunday': 'sun',
        }
        weekday_codes = [en_to_code.get(w, w) for w in (weekdays or [])]
        
        conn = supaconn()
        conn.table("users").update({
            "preferred_intensities": intensities or None,
            "preferred_focus": focus or None,
            "preferred_settings": settings or None,
            "favorite_location_names": locations or None,
            "preferred_weekdays": weekday_codes,
            "updated_at": datetime.now().isoformat(),
        }).eq("sub", user_sub).execute()
        get_user_from_db.clear()
        return True
    except Exception as e:
        logger.error(f"Error saving filter preferences for {user_sub}: {e}")
        return False

# === User Favorites ===

@st.cache_data(ttl=60)
def get_user_favorites(user_sub: str) -> List[str]:
    """Gets user's favorite sport hrefs"""
    try:
        conn = supaconn()
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        
        if not user.data:
            return []
        
        user_id = user.data[0]['id']
        favorites = conn.table("user_favorites").select("sportangebot_href").eq("user_id", user_id).execute()
        return [fav['sportangebot_href'] for fav in favorites.data]
    except Exception as e:
        logger.error(f"Error fetching favorites for {user_sub}: {e}")
        return []

def update_user_favorites(user_sub: str, favorite_hrefs: List[str]) -> bool:
    """Updates user's favorite sports"""
    try:
        conn = supaconn()
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        
        if not user.data:
            return False
        
        user_id = user.data[0]['id']
        
        # Delete existing favorites
        conn.table("user_favorites").delete().eq("user_id", user_id).execute()
        
        # Insert new favorites
        if favorite_hrefs:
            favorites_data = [
                {"user_id": user_id, "sportangebot_href": href}
                for href in favorite_hrefs
            ]
            conn.table("user_favorites").insert(favorites_data).execute()
        
        get_user_favorites.clear()
        return True
    except Exception as e:
        logger.error(f"Error updating favorites for {user_sub}: {e}")
        return False

# === Ratings ===

def submit_sport_rating(user_sub: str, sportangebot_href: str, rating: int, comment: str = "") -> bool:
    """Submits or updates a sport activity rating"""
    try:
        conn = supaconn()
        
        # Get user_id
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            logger.warning(f"User not found for sub {user_sub}")
            return False
        
        user_id = user.data[0]['id']
        
        # Check for existing rating
        existing = conn.table("sportangebote_user_ratings").select("*").eq(
            "user_id", user_id
        ).eq("sportangebot_href", sportangebot_href).execute()
        
        rating_data = {
            "user_id": user_id,
            "sportangebot_href": sportangebot_href,
            "rating": rating,
            "comment": comment,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing.data:
            conn.table("sportangebote_user_ratings").update(rating_data).eq(
                "user_id", user_id
            ).eq("sportangebot_href", sportangebot_href).execute()
        else:
            rating_data["created_at"] = datetime.now().isoformat()
            conn.table("sportangebote_user_ratings").insert(rating_data).execute()
        
        # Clear related caches
        get_offers_with_stats.clear()
        get_average_rating_for_offer.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error submitting sport rating: {e}")
        return False

def submit_trainer_rating(user_sub: str, trainer_name: str, rating: int, comment: str = "") -> bool:
    """Submits or updates a trainer rating"""
    try:
        conn = supaconn()
        
        # Get user_id
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            logger.warning(f"User not found for sub {user_sub}")
            return False
        
        user_id = user.data[0]['id']
        
        # Check for existing rating
        existing = conn.table("trainer_user_ratings").select("*").eq(
            "user_id", user_id
        ).eq("trainer_name", trainer_name).execute()
        
        rating_data = {
            "user_id": user_id,
            "trainer_name": trainer_name,
            "rating": rating,
            "comment": comment,
            "updated_at": datetime.now().isoformat()
        }
        
        if existing.data:
            conn.table("trainer_user_ratings").update(rating_data).eq(
                "user_id", user_id
            ).eq("trainer_name", trainer_name).execute()
        else:
            rating_data["created_at"] = datetime.now().isoformat()
            conn.table("trainer_user_ratings").insert(rating_data).execute()
        
        # Clear related caches
        get_trainers_for_all_offers.clear()
        get_average_rating_for_trainer.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error submitting trainer rating: {e}")
        return False

# === Event Registration (Going/Not Going) ===

def is_user_going_to_event(user_id: int, event_id: str) -> bool:
    """Checks if user is registered for an event"""
    try:
        conn = supaconn()
        result = conn.table("friend_course_notifications").select("id").eq(
            "user_id", user_id
        ).eq("event_id", event_id).limit(1).execute()
        return len(result.data) > 0
    except Exception as e:
        logger.error(f"Error checking event registration: {e}")
        return False

def get_friends_going_to_event(user_id: int, event_id: str) -> List[Dict]:
    """Gets friends who are going to an event"""
    try:
        conn = supaconn()
        
        # Optimized: Single query with join
        # Get notifications for the event, then filter for friends in app logic
        notifications = conn.table("friend_course_notifications").select(
            "*, user:users!user_id(*)"
        ).eq("event_id", event_id).execute()
        
        if not notifications.data:
            return []
        
        # Get friend IDs
        friendships = conn.table("user_friends").select("requester_id, addressee_id").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        friend_ids = set()
        for friendship in friendships.data:
            if friendship['requester_id'] == user_id:
                friend_ids.add(friendship['addressee_id'])
            else:
                friend_ids.add(friendship['requester_id'])
        
        # Filter notifications for friends only
        friend_notifications = [
            n for n in notifications.data 
            if n.get('user_id') in friend_ids
        ]
        
        return friend_notifications
    except Exception as e:
        logger.error(f"Error fetching friends going to event: {e}")
        return []

def mark_user_going_to_event(user_id: int, event_id: str) -> bool:
    """Marks user as going to an event"""
    try:
        conn = supaconn()
        
        # Check if already exists
        existing = conn.table("friend_course_notifications").select("id").eq(
            "user_id", user_id
        ).eq("event_id", event_id).limit(1).execute()
        
        if existing.data:
            return True
        
        # Get friendships
        friendships = conn.table("user_friends").select("requester_id, addressee_id").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        notifications = []
        
        # Create notifications for friends
        if friendships.data:
            friend_ids = []
            for friendship in friendships.data:
                if friendship['requester_id'] == user_id:
                    friend_ids.append(friendship['addressee_id'])
                else:
                    friend_ids.append(friendship['requester_id'])
            
            timestamp = datetime.now().isoformat()
            for friend_id in friend_ids:
                notifications.append({
                    "user_id": user_id,
                    "friend_id": friend_id,
                    "event_id": event_id,
                    "created_at": timestamp
                })
        
        # Add self-notification
        self_notification = {
            "user_id": user_id,
            "friend_id": user_id,
            "event_id": event_id,
            "created_at": datetime.now().isoformat()
        }
        
        all_notifications = notifications + [self_notification]
        conn.table("friend_course_notifications").insert(all_notifications).execute()
        
        # Clear cache
        get_user_registered_events.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error marking user going to event: {e}")
        return False

def unmark_user_going_to_event(user_id: int, event_id: str) -> bool:
    """Removes user registration from an event"""
    try:
        conn = supaconn()
        conn.table("friend_course_notifications").delete().eq(
            "user_id", user_id
        ).eq("event_id", event_id).execute()
        
        # Clear cache
        get_user_registered_events.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error unmarking user going to event: {e}")
        return False

@st.cache_data(ttl=60)
def get_user_registered_events(user_id: int) -> List[str]:
    """Gets all event IDs user is registered for"""
    try:
        conn = supaconn()
        notifications = conn.table("friend_course_notifications").select(
            "event_id"
        ).eq("user_id", user_id).eq("friend_id", user_id).execute()
        return [n['event_id'] for n in notifications.data] if notifications.data else []
    except Exception as e:
        logger.error(f"Error fetching registered events: {e}")
        return []

# === Friends & Social ===

@st.cache_data(ttl=120)
def get_public_users() -> List[Dict]:
    """Gets all public user profiles"""
    try:
        conn = supaconn()
        result = conn.table("users").select(
            "id, name, email, picture, bio, created_at"
        ).eq("is_public", True).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error fetching public users: {e}")
        return []

def get_friend_status(user_id: int, other_user_id: int) -> str:
    """Checks friendship status between two users"""
    try:
        conn = supaconn()
        
        # Check if already friends (single query with OR)
        friendship = conn.table("user_friends").select("*").or_(
            f"and(requester_id.eq.{user_id},addressee_id.eq.{other_user_id}),and(requester_id.eq.{other_user_id},addressee_id.eq.{user_id})"
        ).limit(1).execute()
        
        if friendship.data:
            return "friends"
        
        # Check for pending request sent
        request_sent = conn.table("friend_requests").select("id").eq(
            "requester_id", user_id
        ).eq("addressee_id", other_user_id).eq("status", "pending").limit(1).execute()
        
        if request_sent.data:
            return "request_sent"
        
        # Check for pending request received
        request_received = conn.table("friend_requests").select("id").eq(
            "requester_id", other_user_id
        ).eq("addressee_id", user_id).eq("status", "pending").limit(1).execute()
        
        if request_received.data:
            return "request_received"
        
        return "none"
    except Exception as e:
        logger.error(f"Error checking friend status: {e}")
        return "none"

def send_friend_request(requester_id: int, addressee_id: int) -> bool:
    """Sends a friend request"""
    try:
        conn = supaconn()
        
        # Check if request already exists
        existing = conn.table("friend_requests").select("id, status").eq(
            "requester_id", requester_id
        ).eq("addressee_id", addressee_id).limit(1).execute()
        
        if existing.data:
            if existing.data[0]['status'] == 'pending':
                return False
        else:
            timestamp = datetime.now().isoformat()
            conn.table("friend_requests").insert({
                "requester_id": requester_id,
                "addressee_id": addressee_id,
                "status": "pending",
                "created_at": timestamp,
                "updated_at": timestamp
            }).execute()
            
            # Clear caches
            get_pending_friend_requests.clear()
            
            return True
    except Exception as e:
        logger.error(f"Error sending friend request: {e}")
        return False

def accept_friend_request(request_id: str, requester_id: int, addressee_id: int) -> bool:
    """Accepts a friend request"""
    try:
        conn = supaconn()
        
        timestamp = datetime.now().isoformat()
        
        # Update request status
        conn.table("friend_requests").update({
            "status": "accepted",
            "updated_at": timestamp
        }).eq("id", request_id).execute()
        
        # Create bidirectional friendship
        conn.table("user_friends").insert([
            {
                "requester_id": requester_id,
                "addressee_id": addressee_id,
                "created_at": timestamp
            },
            {
                "requester_id": addressee_id,
                "addressee_id": requester_id,
                "created_at": timestamp
            }
        ]).execute()
        
        # Clear caches
        get_pending_friend_requests.clear()
        get_user_friends.clear()
        get_friend_count.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error accepting friend request: {e}")
        return False

def reject_friend_request(request_id: str) -> bool:
    """Rejects a friend request"""
    try:
        conn = supaconn()
        conn.table("friend_requests").update({
            "status": "rejected",
            "updated_at": datetime.now().isoformat()
        }).eq("id", request_id).execute()
        
        # Clear cache
        get_pending_friend_requests.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error rejecting friend request: {e}")
        return False

def unfollow_user(user_id: int, friend_id: int) -> bool:
    """Removes a friendship"""
    try:
        conn = supaconn()
        
        # Delete friendship in both directions with single query
        conn.table("user_friends").delete().or_(
            f"and(requester_id.eq.{user_id},addressee_id.eq.{friend_id}),and(requester_id.eq.{friend_id},addressee_id.eq.{user_id})"
        ).execute()
        
        # Clear caches
        get_user_friends.clear()
        get_friend_count.clear()
        
        return True
    except Exception as e:
        logger.error(f"Error unfollowing user: {e}")
        return False

@st.cache_data(ttl=60)
def get_pending_friend_requests(user_id: int) -> List[Dict]:
    """Gets all pending friend requests for a user"""
    try:
        conn = supaconn()
        result = conn.table("friend_requests").select(
            "*, requester:users!requester_id(*), addressee:users!addressee_id(*)"
        ).eq("addressee_id", user_id).eq("status", "pending").execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error fetching pending friend requests: {e}")
        return []

@st.cache_data(ttl=60)
def get_user_friends(user_id: int) -> List[Dict]:
    """Gets all friends of a user"""
    try:
        conn = supaconn()
        
        friendships = conn.table("user_friends").select(
            "*, requester:users!requester_id(*), addressee:users!addressee_id(*)"
        ).or_(f"requester_id.eq.{user_id},addressee_id.eq.{user_id}").execute()
        
        friends = []
        for friendship in friendships.data or []:
            if friendship['requester_id'] == user_id:
                friend = friendship.get('addressee')
            else:
                friend = friendship.get('requester')
            
            if friend:
                friends.append(friend)
        
        return friends
    except Exception as e:
        logger.error(f"Error fetching user friends: {e}")
        return []

@st.cache_data(ttl=60)
def get_friend_count(user_id: int) -> int:
    """Gets count of user's friends"""
    try:
        conn = supaconn()
        # Use count for efficiency - only fetch IDs
        friendships = conn.table("user_friends").select("id", count="exact").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        return friendships.count if hasattr(friendships, 'count') else len(friendships.data or [])
    except Exception as e:
        logger.error(f"Error counting friends: {e}")
        return 0

# === Rating Queries ===

@st.cache_data(ttl=60)
def get_user_sport_rating(user_sub: str, sportangebot_href: str) -> Optional[Dict]:
    """Gets user's existing rating for a sport"""
    try:
        conn = supaconn()
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            return None
        
        user_id = user.data[0]['id']
        existing = conn.table("sportangebote_user_ratings").select("*").eq(
            "user_id", user_id
        ).eq("sportangebot_href", sportangebot_href).execute()
        
        return existing.data[0] if existing.data else None
    except Exception as e:
        logger.error(f"Error fetching user sport rating: {e}")
        return None

@st.cache_data(ttl=60)
def get_user_trainer_rating(user_sub: str, trainer_name: str) -> Optional[Dict]:
    """Gets user's existing rating for a trainer"""
    try:
        conn = supaconn()
        user = conn.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            return None
        
        user_id = user.data[0]['id']
        existing = conn.table("trainer_user_ratings").select("*").eq(
            "user_id", user_id
        ).eq("trainer_name", trainer_name).execute()
        
        return existing.data[0] if existing.data else None
    except Exception as e:
        logger.error(f"Error fetching user trainer rating: {e}")
        return None

@st.cache_data(ttl=120)
def get_average_rating_for_offer(offer_href: str) -> Dict[str, float]:
    """Gets average rating for a sport offer"""
    try:
        conn = supaconn()
        ratings = conn.table("sportangebote_user_ratings").select("rating").eq(
            "sportangebot_href", offer_href
        ).execute()
        
        if not ratings.data:
            return {"avg": 0, "count": 0}
        
        avg_rating = sum(r['rating'] for r in ratings.data) / len(ratings.data)
        return {"avg": round(avg_rating, 1), "count": len(ratings.data)}
    except Exception as e:
        logger.error(f"Error fetching average rating for offer: {e}")
        return {"avg": 0, "count": 0}

@st.cache_data(ttl=120)
def get_average_rating_for_trainer(trainer_name: str) -> Dict[str, float]:
    """Gets average rating for a trainer"""
    try:
        conn = supaconn()
        ratings = conn.table("trainer_user_ratings").select("rating").eq(
            "trainer_name", trainer_name
        ).execute()
        
        if not ratings.data:
            return {"avg": 3, "count": 0}  # Default rating
        
        avg_rating = sum(r['rating'] for r in ratings.data) / len(ratings.data)
        return {"avg": round(avg_rating, 1), "count": len(ratings.data)}
    except Exception as e:
        logger.error(f"Error fetching average rating for trainer: {e}")
        return {"avg": 3, "count": 0}


def get_supabase_client():
    """Returns a direct Supabase client for advanced operations"""
    conn = supaconn()
    return conn
