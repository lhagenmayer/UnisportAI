import streamlit as st
from data.user_management import get_user_profile
from data.auth import get_user_sub, get_user_email, is_logged_in
from data.supabase_client import get_supabase_client
from datetime import datetime
from typing import Optional, Dict, List


def get_user_id(user_sub: Optional[str] = None) -> Optional[int]:
    """Holt die user_id aus der users Tabelle"""
    if not user_sub:
        user_sub = get_user_sub()
        if not user_sub:
            return None
    
    try:
        client = get_supabase_client()
        result = client.table("users").select("id").eq("sub", user_sub).execute()
        return result.data[0]['id'] if result.data else None
    except Exception as e:
        st.error(f"Fehler beim Laden der User-ID: {e}")
        return None


def get_public_users() -> List[Dict]:
    """Holt alle öffentlichen Benutzer"""
    try:
        client = get_supabase_client()
        result = client.table("users").select("id, name, email, picture, bio, created_at").eq("is_public", True).execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der öffentlichen Profile: {e}")
        return []


def get_friend_status(user_id: int, other_user_id: int) -> str:
    """Prüft den Status der Freundschaft zwischen zwei Benutzern"""
    try:
        client = get_supabase_client()
        
        # Prüfe ob bereits befreundet
        # Two separate queries to check both directions
        friendship1 = client.table("user_friends").select("*").eq("requester_id", user_id).eq("addressee_id", other_user_id).execute()
        friendship2 = client.table("user_friends").select("*").eq("requester_id", other_user_id).eq("addressee_id", user_id).execute()
        
        if friendship1.data or friendship2.data:
            return "friends"
        
        # Prüfe auf ausstehende Anfrage - der User hat Anfrage gesendet
        request_sent = client.table("friend_requests").select("*").eq("requester_id", user_id).eq("addressee_id", other_user_id).eq("status", "pending").execute()
        
        if request_sent.data:
            return "request_sent"
        
        # Prüfe auf Anfrage erhalten
        request_received = client.table("friend_requests").select("*").eq("requester_id", other_user_id).eq("addressee_id", user_id).eq("status", "pending").execute()
        
        if request_received.data:
            return "request_received"
        
        return "none"
    except Exception as e:
        st.error(f"Fehler beim Prüfen des Freundschaftsstatus: {e}")
        import traceback
        st.code(traceback.format_exc())
        return "none"


def send_friend_request(requester_id: int, addressee_id: int) -> bool:
    """Sendet eine Freundschaftsanfrage"""
    try:
        client = get_supabase_client()
        
        # Prüfe ob bereits eine Anfrage existiert
        existing = client.table("friend_requests").select("*").eq("requester_id", requester_id).eq("addressee_id", addressee_id).execute()
        
        if existing.data:
            if existing.data[0]['status'] == 'pending':
                st.warning("Anfrage ist bereits ausstehend")
                return False
        else:
            # Erstelle neue Anfrage
            client.table("friend_requests").insert({
                "requester_id": requester_id,
                "addressee_id": addressee_id,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            return True
    except Exception as e:
        st.error(f"Fehler beim Senden der Anfrage: {e}")
        return False


def accept_friend_request(request_id: str, requester_id: int, addressee_id: int) -> bool:
    """Akzeptiert eine Freundschaftsanfrage"""
    try:
        client = get_supabase_client()
        
        # Aktualisiere die Anfrage
        client.table("friend_requests").update({
            "status": "accepted",
            "updated_at": datetime.now().isoformat()
        }).eq("id", request_id).execute()
        
        # Erstelle Freundschaft in beide Richtungen (bidirectional)
        client.table("user_friends").insert([
            {"requester_id": requester_id, "addressee_id": addressee_id, "created_at": datetime.now().isoformat()},
            {"requester_id": addressee_id, "addressee_id": requester_id, "created_at": datetime.now().isoformat()}
        ]).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Akzeptieren der Anfrage: {e}")
        return False


def reject_friend_request(request_id: str) -> bool:
    """Lehnt eine Freundschaftsanfrage ab"""
    try:
        client = get_supabase_client()
        client.table("friend_requests").update({
            "status": "rejected",
            "updated_at": datetime.now().isoformat()
        }).eq("id", request_id).execute()
        return True
    except Exception as e:
        st.error(f"Fehler beim Ablehnen der Anfrage: {e}")
        return False


def unfollow_user(user_id: int, friend_id: int) -> bool:
    """Entfernt eine Freundschaft"""
    try:
        client = get_supabase_client()
        
        # Lösche Freundschaft in beide Richtungen
        # Use .or() to handle both directions
        result1 = client.table("user_friends").delete().eq("requester_id", user_id).eq("addressee_id", friend_id).execute()
        result2 = client.table("user_friends").delete().eq("requester_id", friend_id).eq("addressee_id", user_id).execute()
        
        return True
    except Exception as e:
        st.error(f"Fehler beim Entfernen der Freundschaft: {e}")
        import traceback
        st.code(traceback.format_exc())
        return False


def get_pending_requests(user_id: int) -> List[Dict]:
    """Holt alle ausstehenden Freundschaftsanfragen"""
    try:
        client = get_supabase_client()
        result = client.table("friend_requests").select("*, requester:users!requester_id(*), addressee:users!addressee_id(*)").eq(
            "addressee_id", user_id
        ).eq("status", "pending").execute()
        return result.data or []
    except Exception as e:
        st.error(f"Fehler beim Laden der Anfragen: {e}")
        return []


def get_user_friends(user_id: int) -> List[Dict]:
    """Holt alle Freunde eines Benutzers"""
    try:
        client = get_supabase_client()
        
        # Hole alle Freunde (in beide Richtungen)
        friendships = client.table("user_friends").select("*, requester:users!requester_id(*), addressee:users!addressee_id(*)").or_(
            f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
        ).execute()
        
        friends = []
        for friendship in friendships.data or []:
            # Bestimme welcher der Freunde ist
            if friendship['requester_id'] == user_id:
                friend = friendship['addressee'] if 'addressee' in friendship else friendship.get('addressee')
            else:
                friend = friendship['requester'] if 'requester' in friendship else friendship.get('requester')
            
            if friend:
                friends.append(friend)
        
        return friends
    except Exception as e:
        st.error(f"Fehler beim Laden der Freunde: {e}")
        return []


def render_athletes_page():
    """Rendert die Athleten-Seite mit öffentlichen Profilen"""
    from data.auth import is_logged_in
    
    if not is_logged_in():
        st.error("❌ Bitte melden Sie sich an, um Sportfreunde zu finden.")
        return
    
    current_user_id = get_user_id()
    if not current_user_id:
        st.error("❌ Fehler beim Laden Ihres Profiles.")
        return
    
    st.title("👥 Sportfreunde finden")
    
    # Tabs für Übersicht, Anfragen und Freunde
    tab1, tab2, tab3 = st.tabs(["🔍 Alle Athleten", "📩 Anfragen", "👥 Meine Freunde"])
    
    with tab1:
        st.subheader("Öffentliche Profile")
        
        public_users = get_public_users()
        
        if not public_users:
            st.info("Keine öffentlichen Profile verfügbar.")
            return
        
        # Filter own profile
        public_users = [u for u in public_users if u['id'] != current_user_id]
        
        if not public_users:
            st.info("Noch keine anderen öffentlichen Profile verfügbar.")
            return
        
        for user in public_users:
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 2])
                
                with col1:
                    if user.get('picture'):
                        st.image(user['picture'], width=100)
                    else:
                        st.image("https://via.placeholder.com/100", width=100)
                
                with col2:
                    st.markdown(f"### {user.get('name', 'Unbekannt')}")
                    if user.get('bio'):
                        st.caption(user['bio'][:100] + "..." if len(user.get('bio', '')) > 100 else user['bio'])
                    st.caption(f"💪 Aktiv seit: {user.get('created_at', '')[:10] if user.get('created_at') else 'Unbekannt'}")
                
                with col3:
                    status = get_friend_status(current_user_id, user['id'])
                    
                    if status == "friends":
                        st.success("✓ Bereits befreundet")
                        if st.button("🗑️ Entfolgen", key=f"unfollow_{user['id']}"):
                            if unfollow_user(current_user_id, user['id']):
                                st.success("Freundschaft entfernt")
                                st.rerun()
                    
                    elif status == "request_sent":
                        st.info("⏳ Anfrage gesendet")
                    
                    elif status == "request_received":
                        st.warning("📨 Anfrage erhalten")
                    
                    else:
                        if st.button("➕ Anfrage senden", key=f"request_{user['id']}"):
                            if send_friend_request(current_user_id, user['id']):
                                st.success("Freundschaftsanfrage gesendet!")
                                st.rerun()
                            else:
                                st.error("Fehler beim Senden der Anfrage")
                
                st.divider()
    
    with tab2:
        st.subheader("Ausstehende Freundschaftsanfragen")
        
        requests = get_pending_requests(current_user_id)
        
        if not requests:
            st.info("Keine ausstehenden Anfragen.")
        else:
            for req in requests:
                with st.container():
                    # Extract user info from requester (the person who sent the request)
                    requester = req.get('requester', {})
                    if isinstance(requester, dict) and len(requester) > 0:
                        requester_name = requester.get('name', 'Unbekannt')
                        requester_picture = requester.get('picture')
                    else:
                        # Fallback: query user separately
                        try:
                            client = get_supabase_client()
                            requester_data = client.table("users").select("name, picture").eq("id", req['requester_id']).execute()
                            requester_name = requester_data.data[0]['name'] if requester_data.data else 'Unbekannt'
                            requester_picture = requester_data.data[0].get('picture') if requester_data.data else None
                        except:
                            requester_name = "Unbekannt"
                            requester_picture = None
                    
                    col1, col2, col3 = st.columns([1, 3, 2])
                    
                    with col1:
                        if requester_picture:
                            st.image(requester_picture, width=80)
                        else:
                            st.image("https://via.placeholder.com/80", width=80)
                    
                    with col2:
                        st.markdown(f"### {requester_name}")
                        st.caption(f"Anfrage vor {req['created_at'][:10] if req.get('created_at') else 'Unbekannt'}")
                    
                    with col3:
                        col_accept, col_reject = st.columns(2)
                        
                        with col_accept:
                            if st.button("✅ Akzeptieren", key=f"accept_{req['id']}"):
                                if accept_friend_request(req['id'], req['requester_id'], req['addressee_id']):
                                    st.success("Freundschaftsanfrage akzeptiert!")
                                    st.rerun()
                        
                        with col_reject:
                            if st.button("❌ Ablehnen", key=f"reject_{req['id']}"):
                                if reject_friend_request(req['id']):
                                    st.success("Anfrage abgelehnt")
                                    st.rerun()
                    
                    st.divider()
    
    with tab3:
        st.subheader("Meine Freunde")
        
        friends = get_user_friends(current_user_id)
        
        if not friends:
            st.info("Sie haben noch keine Freunde. Senden Sie Anfragen an andere Athleten!")
        else:
            for friend in friends:
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        if friend.get('picture'):
                            st.image(friend['picture'], width=80)
                        else:
                            st.image("https://via.placeholder.com/80", width=80)
                    
                    with col2:
                        st.markdown(f"### {friend.get('name', 'Unbekannt')}")
                        st.markdown(f"📧 {friend.get('email', 'N/A')}")
                    
                    st.divider()


# Hauptfunktion
if __name__ == "__main__" or not st.session_state.get('_is_main'):
    render_athletes_page()

