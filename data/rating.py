"""Rating widgets for sport offers and trainers.

This module provides Streamlit UI helpers to render rating widgets for
offers and trainers, read existing user ratings and submit updates via
the user management layer.
"""
import streamlit as st
from data.user_management import (
    submit_sportangebot_rating, 
    submit_trainer_rating
)
from data.auth import get_user_sub
from data.supabase_client import (
    get_user_sport_rating,
    get_user_trainer_rating,
    get_average_rating_for_offer,
    get_average_rating_for_trainer
)

def render_sportangebot_rating_widget(offer_href: str):
    """Render a Streamlit widget to view and submit an offer rating.

    The widget shows the current user's existing rating (if any) and
    allows submitting or updating the rating and an optional comment.

    Args:
        offer_href (str): Database identifier for the offer.
    """
    from data.auth import is_logged_in
    if not is_logged_in():
        return None
    
    user_sub = get_user_sub()
    if not user_sub:
        return None
    
    try:
        # Get existing rating
        existing_rating = get_user_sport_rating(user_sub, offer_href)
        
        with st.expander("⭐ Bewerten Sie dieses Sportangebot"):
            # Rating-Sterne
            if existing_rating:
                current_rating = existing_rating.get('rating', 3)
                current_comment = existing_rating.get('comment', '')
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
    """Render a Streamlit widget to view and submit a trainer rating.

    Args:
        trainer_name (str): Trainer display name used as the identifier.
    """
    from data.auth import is_logged_in
    if not is_logged_in():
        return None
    
    user_sub = get_user_sub()
    if not user_sub:
        return None
    
    try:
        # Get existing rating
        existing_rating = get_user_trainer_rating(user_sub, trainer_name)
        
        with st.expander(f"⭐ Bewerten Sie Trainer: {trainer_name}"):
            # Rating-Sterne
            if existing_rating:
                current_rating = existing_rating.get('rating', 3)
                current_comment = existing_rating.get('comment', '')
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