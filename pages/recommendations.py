"""pages.recommendations

Streamlit page that collects a user's fitness preferences via a form and
requests sport recommendations from the ML integration. The page displays
ranked recommendations and additional information (ratings, upcoming
events) when the corresponding offer exists in the database.
"""

import streamlit as st
from data.auth import is_logged_in
from data.ml_integration import get_sport_recommendations, validate_user_preferences
from data.supabase_client import get_offers_with_stats, get_events_for_offer
from data.shared_sidebar import render_sidebar_user_info

# Check authentication
if not is_logged_in():
    st.error("❌ Bitte melden Sie sich an.")
    st.stop()

# Render user info in sidebar
with st.sidebar:
    render_sidebar_user_info()

# Page config
st.title('🤖 AI Sport Recommendations')
st.caption('Get personalized sport recommendations based on your preferences')

# Introduction
st.markdown("""
Fülle die Präferenzen aus und lass dir von unserem KI-Modell die perfekten Sportarten empfehlen!
""")

# Create input form
with st.form("preferences_form"):
    st.subheader("Deine Fitness-Ziele")
    
    col1, col2 = st.columns(2)
    
    with col1:
        balance = st.slider("🤸 Balance", 0.0, 1.0, 0.5, 
                           help="Wie wichtig ist dir Balance und Stabilität?")
        flexibility = st.slider("🧘 Flexibilität", 0.0, 1.0, 0.5,
                               help="Wie wichtig ist dir Beweglichkeit?")
        coordination = st.slider("🎯 Koordination", 0.0, 1.0, 0.5,
                                help="Wie wichtig ist dir Hand-Auge-Koordination?")
        relaxation = st.slider("😌 Entspannung", 0.0, 1.0, 0.5,
                              help="Wie entspannend soll der Sport sein?")
    
    with col2:
        strength = st.slider("💪 Kraft", 0.0, 1.0, 0.5,
                           help="Wie wichtig ist dir Kraftaufbau?")
        endurance = st.slider("🏃 Ausdauer", 0.0, 1.0, 0.5,
                            help="Wie wichtig ist dir Ausdauertraining?")
        longevity = st.slider("⏳ Langlebigkeit", 0.0, 1.0, 0.5,
                            help="Wie wichtig ist dir langfristige Gesundheit?")
        intensity = st.slider("🔥 Intensität", 0.0, 1.0, 0.5,
                            help="Wie intensiv soll das Training sein?")
    
    st.subheader("Dein bevorzugtes Setting")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        setting_team = st.checkbox("👥 Teamsport", value=False)
        setting_duo = st.checkbox("👫 Zu zweit", value=False)
    
    with col4:
        setting_solo = st.checkbox("🧍 Alleine", value=False)
        setting_fun = st.checkbox("🎉 Spaß & Fun", value=False)
    
    with col5:
        setting_competitive = st.checkbox("🏆 Wettkampf", value=False)
    
    # Submit button
    submitted = st.form_submit_button("🚀 Empfehlungen erhalten", use_container_width=True)

if submitted:
    # Build the preference vector as expected by the ML model. Numeric
    # sliders are passed directly; boolean checkboxes are converted to
    # floats in [0.0, 1.0] to match the training input schema.
    user_preferences = {
        'balance': balance,
        'flexibility': flexibility,
        'coordination': coordination,
        'relaxation': relaxation,
        'strength': strength,
        'endurance': endurance,
        'longevity': longevity,
        'intensity': intensity,
        'setting_team': 1.0 if setting_team else 0.0,
        'setting_fun': 1.0 if setting_fun else 0.0,
        'setting_duo': 1.0 if setting_duo else 0.0,
        'setting_solo': 1.0 if setting_solo else 0.0,
        'setting_competitive': 1.0 if setting_competitive else 0.0
    }

    # Validate the prepared preference dictionary before sending to ML
    if not validate_user_preferences(user_preferences):
        st.error("❌ Ungültige Präferenzen. Bitte überprüfe deine Eingaben.")
        st.stop()

    # Request recommendations from the ML layer
    with st.spinner('🤖 KI analysiert deine Präferenzen...'):
        recommendations = get_sport_recommendations(user_preferences, top_n=10)

    if not recommendations:
        st.error("❌ Keine Empfehlungen gefunden. Bitte versuche es erneut.")
        st.stop()

    # Inform user and render results. We load all offers once and match by
    # human-readable name returned by the model to the DB offer records.
    st.success(f"✅ Hier sind deine Top {len(recommendations)} Empfehlungen!")

    all_offers = get_offers_with_stats()
    offers_dict = {offer['name']: offer for offer in all_offers}

    for i, (sport_name, confidence) in enumerate(recommendations, 1):
        offer = offers_dict.get(sport_name)

        if offer:
            with st.container():
                st.markdown(f"### {i}. {sport_name}")

                col_a, col_b, col_c = st.columns([2, 2, 1])

                with col_a:
                    st.metric("Match-Score", f"{confidence:.1f}%")

                with col_b:
                    if offer.get('avg_rating'):
                        stars = "⭐" * int(offer['avg_rating'])
                        st.metric("Bewertung", f"{stars} ({offer['avg_rating']:.1f})")
                    else:
                        st.metric("Bewertung", "Noch keine Bewertungen")

                with col_c:
                    if offer.get('future_events_count', 0) > 0:
                        st.metric("Kurse", f"{offer['future_events_count']}")
                    else:
                        st.metric("Kurse", "Keine")

                # Offer description and a short list of upcoming events
                if offer.get('beschreibung'):
                    with st.expander("📝 Beschreibung"):
                        st.write(offer['beschreibung'])

                if offer.get('future_events_count', 0) > 0:
                    with st.expander(f"📅 Nächste Termine ({offer['future_events_count']})"):
                        events = get_events_for_offer(offer['href'])

                        if events:
                            for event in events[:5]:  # Show first 5 events
                                col_x, col_y = st.columns([3, 1])
                                with col_x:
                                    st.write(f"**{event.get('start_time', 'N/A')}**")
                                    st.caption(f"{event.get('ort_name', 'N/A')}")
                                with col_y:
                                    if event.get('canceled'):
                                        st.error("Abgesagt")
                        else:
                            st.info("Keine Termine verfügbar")

                st.divider()
        else:
            # The ML model suggested a sport that is not present in the DB.
            with st.container():
                st.markdown(f"### {i}. {sport_name}")
                st.metric("Match-Score", f"{confidence:.1f}%")
                st.info("ℹ️ Dieser Sport ist derzeit nicht im Angebot verfügbar.")
                st.divider()

# Info section
with st.expander("ℹ️ Wie funktioniert das?"):
    st.markdown("""
    ### KI-gestützte Empfehlungen
    
    Unser Machine Learning Modell wurde mit Daten von Unisport-Angeboten trainiert und kann:
    - Deine persönlichen Fitness-Ziele analysieren
    - Sportarten empfehlen, die am besten zu dir passen
    - Match-Scores basierend auf deinen Präferenzen berechnen
    
    **Features:**
    - 13 verschiedene Parameter für präzise Empfehlungen
    - Berücksichtigung von Fitness-Zielen und Social-Settings
    - Integration mit echten Kursangeboten
    
    Je genauer du deine Präferenzen angibst, desto besser werden die Empfehlungen!
    """)
