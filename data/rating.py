"""
Rating-Funktionalität für Sportangebote und Trainer
"""

import streamlit as st
from data.user_management import (
    submit_sportangebot_rating, 
    submit_trainer_rating
)
from data.auth import get_user_sub
from data.supabase_client import get_supabase_client


def render_sportangebot_rating_widget(offer_href: str):
    """Rendert ein Rating-Widget für ein Sportangebot"""
    from data.auth import is_logged_in
    if not is_logged_in():
        return None
    
    user_sub = get_user_sub()
    if not user_sub:
        return None
    
    try:
        # Hole user_id
        client = get_supabase_client()
        user = client.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            return None
        
        user_id = user.data[0]['id']
        
        # Prüfe ob User bereits eine Bewertung hat
        existing_rating = client.table("sportangebote_user_ratings").select("*").eq("user_id", user_id).eq("sportangebot_href", offer_href).execute()
        
        with st.expander("⭐ Bewerten Sie dieses Sportangebot"):
            # Rating-Sterne
            if existing_rating.data:
                current_rating = existing_rating.data[0].get('rating', 3)
                current_comment = existing_rating.data[0].get('comment', '')
                st.info(f"Ihre aktuelle Bewertung: {'⭐' * current_rating} ({current_rating}/5)")
            else:
                current_rating = 3
                current_comment = ''
            
            rating = st.slider("Bewertung", 1, 5, current_rating, help="1 = Schlecht, 5 = Ausgezeichnet", key=f"rating_slider_{offer_href}")
            comment = st.text_area("Kommentar (optional)", value=current_comment, placeholder="Teilen Sie Ihre Erfahrungen mit...", key=f"rating_comment_{offer_href}")
            
            if st.button("Bewertung speichern", key=f"save_rating_{offer_href}"):
                if submit_sportangebot_rating(offer_href, rating, comment):
                    st.success("✅ Bewertung wurde gespeichert!")
                    st.rerun()
                else:
                    st.error("Fehler beim Speichern der Bewertung")
    except Exception as e:
        st.error(f"Fehler: {e}")
    
    return None


def render_trainer_rating_widget(trainer_name: str):
    """Rendert ein Rating-Widget für einen Trainer"""
    from data.auth import is_logged_in
    if not is_logged_in():
        return None
    
    user_sub = get_user_sub()
    if not user_sub:
        return None
    
    try:
        # Hole user_id
        client = get_supabase_client()
        user = client.table("users").select("id").eq("sub", user_sub).execute()
        if not user.data:
            return None
        
        user_id = user.data[0]['id']
        
        # Prüfe ob User bereits eine Bewertung hat
        existing_rating = client.table("trainer_user_ratings").select("*").eq("user_id", user_id).eq("trainer_name", trainer_name).execute()
        
        with st.expander(f"⭐ Bewerten Sie Trainer: {trainer_name}"):
            # Rating-Sterne
            if existing_rating.data:
                current_rating = existing_rating.data[0].get('rating', 3)
                current_comment = existing_rating.data[0].get('comment', '')
                st.info(f"Ihre aktuelle Bewertung: {'⭐' * current_rating} ({current_rating}/5)")
            else:
                current_rating = 3
                current_comment = ''
            
            rating = st.slider("Bewertung", 1, 5, current_rating, help="1 = Schlecht, 5 = Ausgezeichnet", key=f"trainer_rating_{trainer_name}")
            comment = st.text_area("Kommentar (optional)", value=current_comment, placeholder="Teilen Sie Ihre Erfahrungen mit...", key=f"trainer_comment_{trainer_name}")
            
            if st.button("Bewertung speichern", key=f"save_trainer_rating_{trainer_name}"):
                if submit_trainer_rating(trainer_name, rating, comment):
                    st.success("✅ Bewertung wurde gespeichert!")
                    st.rerun()
                else:
                    st.error("Fehler beim Speichern der Bewertung")
    except Exception as e:
        st.error(f"Fehler: {e}")
    
    return None


def get_average_rating_for_offer(offer_href: str) -> dict:
    """Gibt die durchschnittliche Bewertung für ein Sportangebot zurück"""
    try:
        client = get_supabase_client()
        ratings = client.table("sportangebote_user_ratings").select("rating").eq("sportangebot_href", offer_href).execute()
        
        if not ratings.data:
            return {"avg": 0, "count": 0}
        
        avg_rating = sum(r['rating'] for r in ratings.data) / len(ratings.data)
        return {"avg": round(avg_rating, 1), "count": len(ratings.data)}
    except Exception:
        return {"avg": 0, "count": 0}


def get_average_rating_for_trainer(trainer_name: str) -> dict:
    """Gibt die durchschnittliche Bewertung für einen Trainer zurück"""
    try:
        client = get_supabase_client()
        ratings = client.table("trainer_user_ratings").select("rating").eq("trainer_name", trainer_name).execute()
        
        if not ratings.data:
            return {"avg": 3, "count": 0}  # Default rating
        
        avg_rating = sum(r['rating'] for r in ratings.data) / len(ratings.data)
        return {"avg": round(avg_rating, 1), "count": len(ratings.data)}
    except Exception:
        return {"avg": 3, "count": 0}