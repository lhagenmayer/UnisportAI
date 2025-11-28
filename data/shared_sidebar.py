"""
Sidebar Components for UnisportAI
- Filter sidebar for Overview and Details pages
- User info section that appears on all pages
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from data.state_manager import (
    get_filter_state, set_filter_state, init_multiple_offers_state,
    get_sports_data, get_selected_offer, has_multiple_offers, get_nav_date
)

def _create_user_info_card_html(user_name: str, user_email: str) -> str:
    """
    Creates HTML markup for the user info card.
    
    Args:
        user_name: User's display name
        user_email: User's email address
        
    Returns:
        HTML string for the user info card
    """
    return f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <div style="color: white; font-size: 14px; font-weight: 600; margin-bottom: 8px;">
            👤 Signed in as
        </div>
        <div style="color: white; font-size: 16px; font-weight: 700; margin-bottom: 4px;">
            {user_name}
        </div>
        <div style="color: rgba(255,255,255,0.8); font-size: 13px;">
            {user_email}
        </div>
    </div>
    """

def render_sidebar_user_info() -> None:
    """
    Renders the user info section at the top of the sidebar.
    This should be called on ALL pages to ensure consistent user info display.
    Always renders in the sidebar, whether called standalone or within render_filters_sidebar().
    """
    from data.auth import is_logged_in
    
    if not is_logged_in():
        return
    
    with st.sidebar:
        # User info card - safely access user info
        try:
            user_name = st.user.name if hasattr(st, 'user') and st.user else "User"
            user_email = st.user.email if hasattr(st, 'user') and st.user else ""
        except Exception:
            user_name = "User"
            user_email = ""
        
        user_card_html = _create_user_info_card_html(user_name, user_email)
        st.markdown(user_card_html, unsafe_allow_html=True)
        
        # Logout button
        if st.button("🚪 Logout", key="sidebar_logout", use_container_width=True, type="secondary"):
            from data.auth import handle_logout
            handle_logout()
        
        # Add spacing after user info
        st.markdown("<br>", unsafe_allow_html=True)

def render_filters_sidebar(sports_data=None, events=None):
    """
    Renders the filter sidebar for Overview and Details pages.
    Includes user info at the top, followed by filters for activities and course dates.
    
    Args:
        sports_data: Data for activity filters (intensity, focus, setting)
        events: Event data for course filters (date, time, location, weekday)
    """
    
    with st.sidebar:
        # Render user info at the top
        render_sidebar_user_info()
        
        # Quick search (always visible)
        search_text = st.text_input(
            "🔎 Quick Search",
            value=get_filter_state('search_text', ''),
            placeholder="Search activities...",
            key="global_search_text",
            help="Search by activity name, location, or trainer"
        )
        set_filter_state('search_text', search_text)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Load sports data if needed
        if not sports_data:
            sports_data = get_sports_data()
        
        # Load events if not provided (optional, will show filters if available)
        if not events:
            try:
                from data.supabase_client import get_all_events
                events = get_all_events()
            except Exception:
                events = None
        
        # === ACTIVITY FILTERS ===
        # Show activity filters whenever sports_data is available
        if sports_data and len(sports_data) > 0:
            with st.expander("🎯 Activity Type", expanded=True):
                # Extract unique values
                intensities = sorted(set([item.get('intensity') for item in sports_data if item.get('intensity')]))
                all_focuses = set()
                all_settings = set()
                for item in sports_data:
                    if item.get('focus'):
                        all_focuses.update(item.get('focus'))
                    if item.get('setting'):
                        all_settings.update(item.get('setting'))
                
                focuses = sorted(list(all_focuses))
                settings = sorted(list(all_settings))
                
                # Intensity
                if intensities:
                    current_intensity = get_filter_state('intensity', [])
                    selected_intensity = st.multiselect(
                        "💪 Intensity",
                        options=intensities,
                        default=current_intensity,
                        key="global_intensity",
                        help="Filter by exercise intensity level"
                    )
                    # Always sync state with widget value for immediate updates
                    set_filter_state('intensity', selected_intensity)
                
                # Focus
                if focuses:
                    current_focus = get_filter_state('focus', [])
                    selected_focus = st.multiselect(
                        "🎯 Focus",
                        options=focuses,
                        default=current_focus,
                        key="global_focus",
                        help="Filter by training focus area"
                    )
                    # Always sync state with widget value for immediate updates
                    set_filter_state('focus', selected_focus)
                
                # Setting
                if settings:
                    current_setting = get_filter_state('setting', [])
                    selected_setting = st.multiselect(
                        "🏠 Setting",
                        options=settings,
                        default=current_setting,
                        key="global_setting",
                        help="Indoor or outdoor activities"
                    )
                    # Always sync state with widget value for immediate updates
                    set_filter_state('setting', selected_setting)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Show upcoming only checkbox
                show_upcoming_only = st.checkbox(
                    "📅 Show upcoming only",
                    value=get_filter_state('show_upcoming_only', True),
                    key="global_show_upcoming_only"
                )
                set_filter_state('show_upcoming_only', show_upcoming_only)
        
        # === COURSE FILTERS (shown when events are available) ===
        if events and len(events) > 0:
            # Multiple Activities Selection (if applicable)
            if has_multiple_offers():
                with st.expander("🎯 Selected Activities", expanded=True):
                    from data.supabase_client import get_offers_with_stats
                    from data.state_manager import get_multiple_offers
                    
                    all_offers_for_select = get_offers_with_stats()
                    all_offer_hrefs = get_multiple_offers()
                    
                    # Build mapping
                    href_to_offer = {}
                    offer_options = []
                    for offer_href in all_offer_hrefs:
                        for offer in all_offers_for_select:
                            if offer.get('href') == offer_href:
                                href_to_offer[offer_href] = offer
                                offer_options.append(offer_href)
                                break
                    
                    multiselect_key = "state_selected_offers_multiselect"
                    init_multiple_offers_state(all_offer_hrefs, multiselect_key)
                    current_selected = st.session_state.get(multiselect_key, all_offer_hrefs.copy())
                    
                    selected_offers = st.multiselect(
                        "Activities",
                        options=offer_options,
                        default=current_selected,
                        format_func=lambda href: href_to_offer[href].get('name', 'Unknown'),
                        key=multiselect_key,
                        label_visibility="collapsed"
                    )
                    
                    # Always sync state with widget value for immediate updates
                    st.session_state[multiselect_key] = selected_offers
                    
                    if selected_offers:
                        st.success(f"✓ {len(selected_offers)} selected")
            
            # Sport filter (if not using multiple offers)
            if not has_multiple_offers():
                with st.expander("🏃 Sport & Status", expanded=True):
                    sport_names = sorted(set([e.get('sport_name', '') for e in events if e.get('sport_name')]))
                    
                    # Check for pre-selected sports - ensure they exist in available options
                    default_sports = []
                    selected_offer = get_selected_offer()
                    if selected_offer:
                        selected_name = selected_offer.get('name', '')
                        if selected_name and selected_name in sport_names:
                            default_sports = [selected_name]
                    
                    # Get stored filter state and validate against available options
                    stored_offers = get_filter_state('offers', default_sports)
                    # Only use stored offers that exist in current sport_names
                    valid_default = [sport for sport in stored_offers if sport in sport_names]
                    
                    current_sports = get_filter_state('offers', valid_default)
                    selected_sports = st.multiselect(
                        "Sport",
                        options=sport_names,
                        default=current_sports if current_sports else valid_default,
                        key="global_sport_input"
                    )
                    # Always sync state with widget value for immediate updates
                    set_filter_state('offers', selected_sports)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # Hide cancelled
                    hide_cancelled = st.checkbox(
                        "🚫 Hide cancelled courses",
                        value=get_filter_state('hide_cancelled', True),
                        key="global_hide_cancelled"
                    )
                    set_filter_state('hide_cancelled', hide_cancelled)
            
            # Date & Time filters (shown on both detail and main pages when events are available)
            with st.expander("📅 Date & Time", expanded=False):
                st.markdown("**Date Range**")
                
                # Date range
                nav_date = get_nav_date()
                preset_date = None
                if nav_date:
                    preset_date = datetime.strptime(nav_date, '%Y-%m-%d').date()
                
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input(
                        "From",
                        value=get_filter_state('date_start', preset_date),
                        key="global_start_date"
                    )
                    set_filter_state('date_start', start_date)
                
                with col2:
                    end_date = st.date_input(
                        "To",
                        value=get_filter_state('date_end', preset_date),
                        key="global_end_date"
                    )
                    set_filter_state('date_end', end_date)
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("**Time Range**")
                
                # Time range
                col1, col2 = st.columns(2)
                with col1:
                    start_time_filter = st.time_input(
                        "From",
                        value=get_filter_state('start_time', None),
                        key="global_start_time"
                    )
                    if start_time_filter != time(0, 0):
                        set_filter_state('start_time', start_time_filter)
                    else:
                        set_filter_state('start_time', None)
                
                with col2:
                    end_time_filter = st.time_input(
                        "To",
                        value=get_filter_state('end_time', None),
                        key="global_end_time"
                    )
                    if end_time_filter != time(0, 0):
                        set_filter_state('end_time', end_time_filter)
                    else:
                        set_filter_state('end_time', None)
            
            # Location & Weekday filters
            with st.expander("📍 Location & Day", expanded=False):
                # Location
                locations = sorted(set([e.get('location_name', '') for e in events if e.get('location_name')]))
                current_locations = get_filter_state('location', [])
                selected_locations = st.multiselect(
                    "📍 Location",
                    options=locations,
                    default=current_locations,
                    key="global_location",
                    help="Filter by location/venue"
                )
                # Always sync state with widget value for immediate updates
                set_filter_state('location', selected_locations)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Weekdays
                weekdays_de = {
                    'Monday': 'Montag', 'Tuesday': 'Dienstag', 'Wednesday': 'Mittwoch',
                    'Thursday': 'Donnerstag', 'Friday': 'Freitag', 'Saturday': 'Samstag', 'Sunday': 'Sonntag'
                }
                weekdays_options = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                current_weekdays = get_filter_state('weekday', [])
                selected_weekdays = st.multiselect(
                    "📆 Weekday",
                    options=weekdays_options,
                    default=current_weekdays,
                    format_func=lambda x: weekdays_de.get(x, x),
                    key="global_weekday",
                    help="Filter by day of the week"
                )
                # Always sync state with widget value for immediate updates
                set_filter_state('weekday', selected_weekdays)

def render_ml_recommendations(sports_data=None):
    """
    Renders ML recommendations section when the ML button is clicked.
    Should be called on pages that use the filter sidebar (Overview, Details).
    
    Args:
        sports_data: Sports data to match recommendations with available courses
    """
    from data.ml_integration import get_recommendations_from_sidebar
    
    # Check if ML button was clicked
    if get_filter_state('trigger_ml', False):
        with st.expander("🤖 AI Recommendations", expanded=True):
            with st.spinner("Analyzing your preferences..."):
                recommendations = get_recommendations_from_sidebar()
                
                if recommendations:
                    st.success(f"✨ Found {len(recommendations)} personalized recommendations based on your filters!")
                    
                    # Show top 5 recommendations
                    for i, rec in enumerate(recommendations[:5], 1):
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"**{i}. {rec['sport']}**")
                        
                        with col2:
                            st.metric("Match", f"{rec['confidence']:.0f}%")
                        
                        # Find matching offer
                        if sports_data:
                            matching_offer = next((o for o in sports_data if o.get('name') == rec['sport']), None)
                            if matching_offer:
                                st.caption(f"⭐ {matching_offer.get('rating', 'N/A')} • {matching_offer.get('future_events_count', 0)} upcoming courses")
                        
                        st.divider()
                else:
                    st.info("Set some filters above to get personalized recommendations!")

def render_ml_recommendations_section(sports_data=None, current_filter_results=None):
    """
    Render ML-based recommendations section with user-configurable threshold
    
    Args:
        sports_data: All available sports
        current_filter_results: Sports already shown by logic-based filters (to exclude)
    """
    from data.ml_integration import get_ml_recommendations
    
    # Get current filter state
    selected_focus = get_filter_state('focus', [])
    selected_intensity = get_filter_state('intensity', [])
    selected_setting = get_filter_state('setting', [])
    
    # Check if user has selected any filters
    has_filters = bool(selected_focus or selected_intensity or selected_setting)
    
    if not has_filters:
        st.info("💡 Select some filters above to get AI-powered recommendations!")
        return
    
    # User controls for ML recommendations
    with st.expander("🤖 AI Recommendations Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            min_match = st.slider(
                "Minimum Match %",
                min_value=50,
                max_value=100,
                value=75,
                step=5,
                help="Only show sports with at least this match percentage"
            )
        
        with col2:
            max_results = st.slider(
                "Max Results",
                min_value=3,
                max_value=20,
                value=10,
                step=1,
                help="Maximum number of AI recommendations"
            )
    
    # Get sports to exclude (already shown in main results)
    exclude_names = []
    if current_filter_results:
        exclude_names = [sport.get('name', '') for sport in current_filter_results]
    
    # Get ML recommendations
    with st.spinner("🤖 AI is analyzing sports..."):
        ml_recommendations = get_ml_recommendations(
            selected_focus=selected_focus,
            selected_intensity=selected_intensity,
            selected_setting=selected_setting,
            min_match_score=min_match,
            max_results=max_results,
            exclude_sports=exclude_names
        )
    
    # Display results
    if ml_recommendations:
        st.success(f"✨ Found {len(ml_recommendations)} AI recommendations for you!")
        
        # Simple model performance indicator
        avg_score = sum(rec['match_score'] for rec in ml_recommendations) / len(ml_recommendations)
        max_score = max(rec['match_score'] for rec in ml_recommendations)
        
        # Model quality indicators
        st.metric("🎯 Best Match", f"{max_score:.1f}%")
        
        # Simple bar chart showing match scores
        sports_names = [rec['sport'] for rec in ml_recommendations]
        match_scores = [rec['match_score'] for rec in ml_recommendations]
        
        # Create simple bar chart
        fig_simple = go.Figure(data=[
            go.Bar(
                x=match_scores,
                y=[f"{i+1}. {name[:25]}{'...' if len(name) > 25 else ''}" for i, name in enumerate(sports_names)],
                orientation='h',
                marker=dict(
                    color=match_scores,
                    colorscale='RdYlGn',  # Red-Yellow-Green scale
                    cmin=50,
                    cmax=100
                ),
                text=[f"{score}%" for score in match_scores],
                textposition='inside',
                textfont=dict(color='white', size=11)
            )
        ])
        
        fig_simple.update_layout(
            title="🤖 AI Recommendation Confidence",
            xaxis_title="Match Score (%)",
            yaxis_title="Recommended Sports",
            height=max(300, len(ml_recommendations) * 35),
            margin=dict(l=20, r=20, t=50, b=20),
            showlegend=False
        )
        
        # Create a fancy, interactive polar bar chart
        fig_fancy = go.Figure()
        
        # Add polar bar chart with gradient colors
        colors = ['#FF6B6B', '#FFA726', '#FFEE58', '#66BB6A', '#42A5F5', '#AB47BC', '#FF7043', '#8D6E63']
        
        # Create a more sophisticated chart with multiple visual elements
        fig_fancy = go.Figure()
        
        # Create hover text with sport tags (only show NON-selected tags)
        hover_texts = []
        for rec in ml_recommendations:
            item = rec.get('item', {})
            additional_tags = []
            
            # Show NON-selected focus tags that this sport has
            focus_tags = ['balance', 'flexibility', 'coordination', 'relaxation', 'strength', 'endurance', 'longevity']
            for tag in focus_tags:
                if item.get(tag, 0) == 1 and tag not in selected_focus:
                    additional_tags.append(f"🎯 {tag.capitalize()}")
            
            # Show intensity if different from selected (handle both numeric and string values)
            intensity = item.get('intensity')
            if intensity is not None:
                # Convert numeric intensity to string
                if isinstance(intensity, (int, float)):
                    if intensity <= 0.4:
                        intensity_str = "low"
                    elif intensity <= 0.7:
                        intensity_str = "moderate"
                    else:
                        intensity_str = "high"
                else:
                    intensity_str = str(intensity).lower()
                
                # Check if this intensity is different from selected
                if not selected_intensity or intensity_str not in [i.lower() for i in selected_intensity]:
                    additional_tags.append(f"⚡ {intensity_str.capitalize()} Intensity")
            
            # Show NON-selected setting tags that this sport has
            setting_tags = ['setting_team', 'setting_fun', 'setting_duo', 'setting_solo', 'setting_competitive']
            for tag in setting_tags:
                if item.get(tag, 0) == 1:
                    setting_name = tag.replace('setting_', '')
                    if setting_name not in selected_setting:
                        additional_tags.append(f"🏃 {setting_name.capitalize()}")
            
            if additional_tags:
                tags_text = "<br>".join(additional_tags[:6])  # Limit to 6 tags for readability
                hover_texts.append(f"<b>{rec['sport']}</b><br>" +
                                  f"Match Score: <b>{rec['match_score']}%</b><br>" +
                                  f"<br><i>Additional Features:</i><br>{tags_text}")
            else:
                hover_texts.append(f"<b>{rec['sport']}</b><br>" +
                                  f"Match Score: <b>{rec['match_score']}%</b><br>" +
                                  f"<br><i>No additional features beyond your selection</i>")
        
        # Add bars with custom colors and effects
        fig_fancy.add_trace(go.Bar(
            y=[f"{name[:20]}{'...' if len(name) > 20 else ''}" for name in sports_names],
            x=match_scores,
            orientation='h',
            marker=dict(
                color=match_scores,
                colorscale='Turbo',  # Beautiful color scale
                cmin=50,
                cmax=100,
                line=dict(color='rgba(255,255,255,0.8)', width=2),
                opacity=0.8
            ),
            text=[f"<b>{score}%</b>" for score in match_scores],
            textposition='inside',
            textfont=dict(color='white', size=13, family='Arial Black'),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_texts,
            name="AI Recommendations"
        ))
        
        # Add sparkle effect with scatter points
        for i, (score, name) in enumerate(zip(match_scores, sports_names)):
            if score >= 75:  # Only add sparkles for good matches
                fig_fancy.add_trace(go.Scatter(
                    x=[score + 2],
                    y=[f"{name[:20]}{'...' if len(name) > 20 else ''}"],
                    mode='markers',
                    marker=dict(
                        symbol='star',
                        size=15 if score >= 90 else 12,
                        color='gold' if score >= 90 else 'silver',
                        line=dict(color='white', width=1)
                    ),
                    showlegend=False,
                    hoverinfo='skip'
                ))
        
        # Beautiful styling
        fig_fancy.update_layout(
            title=dict(
                text="✨ AI Recommendation Confidence ✨",
                x=0.5,
                font=dict(size=18, family='Arial', color='#2E86AB')
            ),
            xaxis=dict(
                title="Match Score (%)",
                range=[0, 105],
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True,
                tickfont=dict(size=12, color='#666')
            ),
            yaxis=dict(
                title="🏃 Recommended Sports",
                tickfont=dict(size=11, color='#666')
            ),
            height=max(350, len(ml_recommendations) * 45),
            margin=dict(l=30, r=30, t=70, b=30),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(248,249,250,0.7)',
            showlegend=False,
            font=dict(family='Arial'),
            # Add subtle animation
            transition=dict(duration=500, easing="cubic-in-out")
        )
        
        # Add range annotations for visual guidance
        fig_fancy.add_vrect(
            x0=90, x1=100,
            fillcolor="rgba(76, 175, 80, 0.1)",
            layer="below",
            line_width=0,
        )
        fig_fancy.add_vrect(
            x0=75, x1=90,
            fillcolor="rgba(255, 193, 7, 0.1)",
            layer="below",
            line_width=0,
        )
        
        # Add red line for average quality
        fig_fancy.add_vline(
            x=avg_score,
            line=dict(color="red", width=3, dash="solid"),
            annotation_text=f"📊 Avg: {avg_score:.1f}%",
            annotation_position="top",
            annotation=dict(
                font=dict(size=12, color="red"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="red",
                borderwidth=1
            )
        )
        
        # Add text annotations for score ranges
        fig_fancy.add_annotation(
            x=95, y=len(sports_names) * 0.95,
            text="🎯 Perfect Match",
            showarrow=False,
            font=dict(size=10, color='green'),
            bgcolor="rgba(76, 175, 80, 0.2)",
            bordercolor="green",
            borderwidth=1
        )
        
        st.plotly_chart(fig_fancy, use_container_width=True)
        
        # Show Top 3 Recommendations below the chart
        st.subheader("🏆 Top 3 AI Recommendations")
        
        top_3 = ml_recommendations[:3]
        for i, rec in enumerate(top_3, 1):
            item = rec.get('item', {})
            
            with st.container():
                # Create columns for layout
                col_rank, col_content, col_score = st.columns([0.5, 3, 1])
                
                with col_rank:
                    # Medal emojis for top 3
                    medals = ["🥇", "🥈", "🥉"]
                    st.markdown(f"<div style='font-size: 2em; text-align: center;'>{medals[i-1]}</div>", 
                               unsafe_allow_html=True)
                
                with col_content:
                    st.markdown(f"**{rec['sport']}**")
                    
                    # Show ONLY non-selected tags as additional features
                    additional_tags_display = []
                    
                    # Show NON-selected focus tags that this sport has
                    focus_tags = ['balance', 'flexibility', 'coordination', 'relaxation', 'strength', 'endurance', 'longevity']
                    for tag in focus_tags:
                        if item.get(tag, 0) == 1 and tag not in selected_focus:
                            additional_tags_display.append(f"`➕ {tag.capitalize()}`")
                    
                    # Show intensity if different from selected (handle both numeric and string values)
                    intensity = item.get('intensity')
                    if intensity is not None:
                        # Convert numeric intensity to string
                        if isinstance(intensity, (int, float)):
                            if intensity <= 0.4:
                                intensity_str = "low"
                            elif intensity <= 0.7:
                                intensity_str = "moderate"
                            else:
                                intensity_str = "high"
                        else:
                            intensity_str = str(intensity).lower()
                        
                        # Check if this intensity is different from selected
                        if not selected_intensity or intensity_str not in [i.lower() for i in selected_intensity]:
                            additional_tags_display.append(f"`➕ {intensity_str.capitalize()}`")
                    
                    # Show NON-selected setting tags that this sport has
                    setting_tags = ['setting_team', 'setting_fun', 'setting_duo', 'setting_solo', 'setting_competitive']
                    for tag in setting_tags:
                        if item.get(tag, 0) == 1:
                            setting_name = tag.replace('setting_', '')
                            if setting_name not in selected_setting:
                                additional_tags_display.append(f"`➕ {setting_name.capitalize()}`")
                    
                    if additional_tags_display:
                        st.markdown(" ".join(additional_tags_display))
                        st.caption("✨ Additional features beyond your selection")
                    else:
                        st.caption("🎯 Perfect match - no additional features")
                
                with col_score:
                    score = rec['match_score']
                    if score >= 90:
                        st.markdown(f"<div style='text-align: center; font-size: 1.2em;'>🟢<br><b>{score}%</b></div>", 
                                   unsafe_allow_html=True)
                    elif score >= 75:
                        st.markdown(f"<div style='text-align: center; font-size: 1.2em;'>🟡<br><b>{score}%</b></div>", 
                                   unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align: center; font-size: 1.2em;'>🟠<br><b>{score}%</b></div>", 
                                   unsafe_allow_html=True)
                
                if i < len(top_3):  # Don't add divider after last item
                    st.divider()
    else:
        st.info(f"No sports found with ≥{min_match}% match. Try lowering the threshold.")