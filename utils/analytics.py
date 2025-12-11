"""
================================================================================
ANALYTICS AND VISUALIZATION UTILITIES
================================================================================

Purpose: Functions to render analytics visualizations including statistics charts
and AI-powered recommendations. Centralizes all analytics visualization logic,
making it easier to maintain and reuse chart configurations across the application.
================================================================================
"""

import streamlit as st
import plotly.graph_objects as go
from utils.db import (
    get_events_by_weekday,
    get_events_by_hour,
    load_and_filter_offers
)
from utils.filters import get_filter_values_from_session, get_merged_recommendations, has_offer_filters
from utils.ml_utils import load_knn_model
from pathlib import Path

# =============================================================================
# ANALYTICS VISUALIZATIONS
# =============================================================================
# PURPOSE: Functions for rendering analytics charts and recommendations

def render_analytics_section():
    """Render analytics visualizations with AI recommendations and charts.
    
    Displays:
    - AI-powered sport recommendations (if filters are selected)
    - Course availability by weekday (Bar chart)
    - Course availability by time of day (Histogram)
    
    Note:
        This function reads filter values from session state and displays
        recommendations only if offer filters (focus/intensity/setting) are set.
        Chart configurations use Plotly with custom styling for consistent appearance.
    """
    # Get filter state from session_state for AI recommendations
    filters = get_filter_values_from_session()
    selected_focus = filters['focus']
    selected_intensity = filters['intensity']
    selected_setting = filters['setting']
    
    # Check if any ML-relevant filters are selected
    has_filters = has_offer_filters(filters=filters)
    
    # =========================================================================
    # STATISTICS CHARTS SECTION
    # =========================================================================
    
    # Get all analytics data
    try:
        weekday_data = get_events_by_weekday()
        hour_data = get_events_by_hour()
    except Exception as e:
        st.warning(f"⚠️ Fehler beim Laden der Analytics-Daten: {e}")
        return
    
    # Create 2 columns for the charts
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Kursverfügbarkeit nach Wochentag
        if weekday_data:
            weekdays = list(weekday_data.keys())
            counts = list(weekday_data.values())
            
            fig = go.Figure(data=[
                go.Bar(
                    x=weekdays,
                    y=counts,
                    marker_color='#2E86AB',
                )
            ])
            fig.update_layout(
                title=dict(text="Course Availability by Weekday", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Weekday",
                yaxis_title="Number of Courses",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    with col2:
        # 2. Kursverfügbarkeit nach Tageszeit
        if hour_data:
            # Filter: Nur Stunden zwischen 6 und 22 Uhr
            filtered_hours = {h: hour_data.get(h, 0) for h in range(6, 23)}
            
            # Formatierung: Stunden als "06:00", "07:00", etc.
            hours_formatted = [f"{h:02d}:00" for h in range(6, 23)]
            counts = [filtered_hours[h] for h in range(6, 23)]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=hours_formatted,
                    y=counts,
                    marker_color='#F77F00',
                )
            ])
            fig.update_layout(
                title=dict(text="Course Availability by Time of Day", x=0.5, xanchor='center', font=dict(size=18, family='Arial', color='#000000')),
                xaxis_title="Time",
                yaxis_title="Number of Courses",
                height=300,
                margin=dict(l=20, r=20, t=50, b=20),
                paper_bgcolor='#FFFFFF',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter, system-ui, sans-serif', size=12),
                xaxis=dict(
                    tickmode='linear',
                    tick0=0,
                    dtick=2,
                    gridcolor='rgba(108, 117, 125, 0.1)',
                    showgrid=True,
                    tickangle=-45
                ),
                yaxis=dict(gridcolor='rgba(108, 117, 125, 0.1)', showgrid=True)
            )
            st.plotly_chart(fig, width="stretch")
    
    # =========================================================================
    # AI RECOMMENDATIONS SECTION (appears naturally after statistics if filters are selected)
    # =========================================================================
    if has_filters:
        # Get sports data using unified load function
        try:
            sports_data = load_and_filter_offers(filters=None, update_session_state=True)
        except Exception:
            sports_data = st.session_state.get('sports_data', [])
            if not sports_data:
                st.warning("⚠️ Could not load sports data for recommendations")
        
        if sports_data:
            # Extract min_match for error message
            min_match = filters['ml_min_match']
            
            # Get merged recommendations using the unified function
            with st.spinner("🤖 AI is analyzing sports..."):
                # Try with user's ml_min_match, fallback to 0 if no results
                all_recommendations = get_merged_recommendations(
                    sports_data,
                    filters=filters,
                    min_match_score=min_match
                )
                # Fallback to lower threshold if no results
                if not all_recommendations:
                    all_recommendations = get_merged_recommendations(
                        sports_data,
                        filters=filters,
                        min_match_score=0
                    )
            
            # Show AI recommendations if available
            if all_recommendations:
                # Apply sport filter if set (same logic as Sports Overview tab)
                # If sport filter is active, only show recommendations that have events for selected sports
                selected_sports = filters.get('selected_sports', [])
                if selected_sports and len(selected_sports) > 0:
                    from utils.db import load_and_filter_events
                    filtered_recommendations = []
                    for rec in all_recommendations:
                        offer = rec.get('offer', {})
                        offer_href = offer.get('href')
                        if offer_href:
                            # Check if this offer has events for the selected sports
                            events = load_and_filter_events(
                                filters={'selected_sports': selected_sports}, 
                                offer_href=offer_href, 
                                show_spinner=False
                            )
                            if events:
                                filtered_recommendations.append(rec)
                        else:
                            # If no href, include it (shouldn't happen, but be safe)
                            filtered_recommendations.append(rec)
                    all_recommendations = filtered_recommendations
                
                # Get top 3 for podest
                top3_combined = all_recommendations[:3]
                
                # Get next 10 for graph (excluding top 3)
                top3_names = {item['name'] for item in top3_combined}
                chart_data_filtered = [item for item in all_recommendations if item['name'] not in top3_names]
                chart_data_top10 = chart_data_filtered[:10]
                
                # Calculate average score for chart (using top 10)
                if chart_data_top10:
                    avg_score = sum(d['match_score'] for d in chart_data_top10) / len(chart_data_top10)
                else:
                    avg_score = 0
                
                # Create two columns: left for podest, right for graph
                col_podest, col_graph = st.columns([1, 1])
                
                # Left column: Podest (Top 3 vertically) - compact version
                with col_podest:
                    # Add title above podest (consistent with graph titles)
                    st.markdown("### Top Recommendations")
                    
                    if top3_combined:
                        medals = ['🥇', '🥈', '🥉']
                        
                        # Create compact podest using Streamlit components
                        for idx, top_item in enumerate(top3_combined):
                            medal = medals[idx]
                            offer = top_item['offer']
                            sport_name = top_item['name']
                            match_score = top_item['match_score']
                            
                            # Quality indicator with new color palette
                            if match_score >= 90:
                                quality_emoji = "🟢"
                                quality_text = "Excellent"
                                quality_color = "#06A77D"  # Teal
                            elif match_score >= 65:
                                quality_emoji = "🟠"
                                quality_text = "Good"
                                quality_color = "#FCBF49"  # Light orange
                            else:
                                quality_emoji = "🔴"
                                quality_text = "Fair"
                                quality_color = "#D62828"  # Warm red
                            
                            # Get additional features not in user's selection (simplified)
                            additional_focus = []
                            # Check if balance is not in selected focus
                            balance_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'balance':
                                        balance_in_selected = True
                                        break
                            if offer.get('balance') and not balance_in_selected:
                                additional_focus.append('Balance')
                            
                            # Check if flexibility is not in selected focus
                            flexibility_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'flexibility':
                                        flexibility_in_selected = True
                                        break
                            if offer.get('flexibility') and not flexibility_in_selected:
                                additional_focus.append('Flexibility')
                            
                            # Check if strength is not in selected focus
                            strength_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'strength':
                                        strength_in_selected = True
                                        break
                            if offer.get('strength') and not strength_in_selected:
                                additional_focus.append('Strength')
                            
                            # Check if endurance is not in selected focus
                            endurance_in_selected = False
                            if selected_focus:
                                for f in selected_focus:
                                    if f.lower() == 'endurance':
                                        endurance_in_selected = True
                                        break
                            if offer.get('endurance') and not endurance_in_selected:
                                additional_focus.append('Endurance')
                            
                            additional_setting = []
                            # Check if team is not in selected setting
                            team_in_selected = False
                            if selected_setting:
                                for s in selected_setting:
                                    if s.lower() == 'team':
                                        team_in_selected = True
                                        break
                            if offer.get('setting_team') and not team_in_selected:
                                additional_setting.append('Team')
                            
                            # Check if solo is not in selected setting
                            solo_in_selected = False
                            if selected_setting:
                                for s in selected_setting:
                                    if s.lower() == 'solo':
                                        solo_in_selected = True
                                        break
                            if offer.get('setting_solo') and not solo_in_selected:
                                additional_setting.append('Solo')
                            
                            # Build compact features text
                            features_parts = []
                            if additional_focus:
                                features_parts.append(', '.join(additional_focus[:2]))
                            if additional_setting:
                                features_parts.append(', '.join(additional_setting[:2]))
                            if features_parts:
                                features_text = " | ".join(features_parts)
                            else:
                                features_text = "Matches preferences"
                            
                            # Compact container using Streamlit-native components
                            with st.container(border=True):
                                st.markdown(f"**{medal} {sport_name}**")
                                st.markdown(f"**{match_score:.1f}%** {quality_emoji} {quality_text}")
                                st.caption(features_text)
                
                # Right column: Graph (Top 10)
                with col_graph:
                    # Only show chart if data is available
                    if not chart_data_top10:
                        st.info("Die Top 3 Empfehlungen werden links angezeigt. Es gibt keine weiteren Empfehlungen für das Diagramm.")
                    else:
                        # Prepare data for chart (top 10)
                        sport_names = []
                        match_scores = []
                        for d in chart_data_top10:
                            sport_names.append(d['name'])
                            match_scores.append(d['match_score'])
                        
                        # Ensure valid data is available
                        has_sport_names = bool(sport_names)
                        has_match_scores = bool(match_scores)
                        lengths_match = len(sport_names) == len(match_scores)
                        if not has_sport_names or not has_match_scores or not lengths_match:
                            st.warning("Data mismatch in chart data.")
                        else:
                            # Build hover tooltips with additional features
                            hover_texts = []
                            for chart_item in chart_data_top10:
                                offer = chart_item['offer']
                                sport_name = chart_item['name']
                                match_score = chart_item['match_score']
                                
                                # Get additional focus tags not in user's selection
                                additional_focus = []
                                focus_map = {
                                    'balance': 'Balance',
                                    'flexibility': 'Flexibility',
                                    'coordination': 'Coordination',
                                    'relaxation': 'Relaxation',
                                    'strength': 'Strength',
                                    'endurance': 'Endurance',
                                    'longevity': 'Longevity'
                                }
                                
                                for key, label in focus_map.items():
                                    label_in_selected = False
                                    if selected_focus:
                                        for f in selected_focus:
                                            if f.lower() == label.lower():
                                                label_in_selected = True
                                                break
                                    if offer.get(key) and not label_in_selected:
                                        additional_focus.append(label)
                                
                                # Get additional intensity if different
                                additional_intensity = None
                                offer_intensity_raw = offer.get('intensity')
                                if offer_intensity_raw:
                                    if isinstance(offer_intensity_raw, str):
                                        offer_intensity = offer_intensity_raw.lower()
                                    else:
                                        offer_intensity = str(offer_intensity_raw).lower()
                                    
                                    intensity_in_selected = False
                                    if selected_intensity:
                                        for i in selected_intensity:
                                            if i.lower() == offer_intensity:
                                                intensity_in_selected = True
                                                break
                                    if offer_intensity and not intensity_in_selected:
                                        additional_intensity = offer_intensity.capitalize()
                                
                                # Get additional setting tags not in user's selection
                                additional_setting = []
                                setting_map = {
                                    'setting_team': 'Team',
                                    'setting_fun': 'Fun',
                                    'setting_duo': 'Duo',
                                    'setting_solo': 'Solo',
                                    'setting_competitive': 'Competitive'
                                }
                                
                                for key, label in setting_map.items():
                                    label_in_selected = False
                                    if selected_setting:
                                        for s in selected_setting:
                                            if s.lower() == label.lower():
                                                label_in_selected = True
                                                break
                                    if offer.get(key) and not label_in_selected:
                                        additional_setting.append(label)
                                
                                # Build hover text
                                hover_parts = [f"<b>{sport_name}</b>", f"Match: {match_score:.1f}%"]
                                
                                if additional_focus:
                                    hover_parts.append(f"<br>Additional Focus: {', '.join(additional_focus[:3])}")
                                if additional_intensity:
                                    hover_parts.append(f"<br>Intensity: {additional_intensity}")
                                if additional_setting:
                                    hover_parts.append(f"<br>Additional Setting: {', '.join(additional_setting[:3])}")
                                
                                hover_texts.append("<br>".join(hover_parts))
                            
                            # Create beautiful horizontal bar chart
                            fig = go.Figure()
                            
                            # Prepare data for horizontal bars
                            display_names = []
                            for name in sport_names:
                                if len(name) > 30:
                                    display_name = f"{name[:30]}..."
                                else:
                                    display_name = name
                                display_names.append(display_name)
                            
                            # Create hover tooltips with additional sport features (only show NON-selected tags)
                            recommendation_hover_tooltips = []
                            for chart_item in chart_data_top10:
                                offer = chart_item['offer']
                                sport_name = chart_item['name']
                                match_score = chart_item['match_score']
                                
                                additional_feature_tags = []
                                
                                # Show NON-selected focus tags that this sport has
                                focus_tag_names = ['balance', 'flexibility', 'coordination', 'relaxation', 'strength', 'endurance', 'longevity']
                                for focus_tag in focus_tag_names:
                                    focus_tag_in_selected = False
                                    if selected_focus:
                                        for f in selected_focus:
                                            if f.lower() == focus_tag:
                                                focus_tag_in_selected = True
                                                break
                                    if offer.get(focus_tag, 0) == 1 and not focus_tag_in_selected:
                                        additional_feature_tags.append(f"🎯 {focus_tag.capitalize()}")
                                
                                # Show intensity if different from selected (handle both numeric and string values)
                                sport_intensity = offer.get('intensity')
                                if sport_intensity is not None:
                                    # Convert numeric intensity to string
                                    if isinstance(sport_intensity, (int, float)):
                                        if sport_intensity <= 0.4:
                                            intensity_level = "low"
                                        elif sport_intensity <= 0.7:
                                            intensity_level = "moderate"
                                        else:
                                            intensity_level = "high"
                                    else:
                                        intensity_level = str(sport_intensity).lower()
                                    
                                    # Check if this intensity is different from selected
                                    intensity_in_selected = False
                                    if selected_intensity:
                                        for i in selected_intensity:
                                            if i.lower() == intensity_level:
                                                intensity_in_selected = True
                                                break
                                    if not selected_intensity or not intensity_in_selected:
                                        additional_feature_tags.append(f"⚡ {intensity_level.capitalize()} Intensity")
                                
                                # Show NON-selected setting tags that this sport has
                                setting_tag_names = ['setting_team', 'setting_fun', 'setting_duo', 'setting_solo', 'setting_competitive']
                                for setting_tag in setting_tag_names:
                                    if offer.get(setting_tag, 0) == 1:
                                        setting_display_name = setting_tag.replace('setting_', '')
                                        setting_in_selected = False
                                        if selected_setting:
                                            for s in selected_setting:
                                                if s.lower() == setting_display_name:
                                                    setting_in_selected = True
                                                    break
                                        if not setting_in_selected:
                                            additional_feature_tags.append(f"🏃 {setting_display_name.capitalize()}")
                                
                                # Build hover text
                                if additional_feature_tags:
                                    tooltip_tags_text = "<br>".join(additional_feature_tags[:6])  # Limit to 6 tags for readability
                                    recommendation_hover_tooltips.append(f"<b>{sport_name}</b><br>" +
                                                      f"Match Score: <b>{match_score:.1f}%</b><br>" +
                                                      f"<br><i>Additional Features:</i><br>{tooltip_tags_text}")
                                else:
                                    recommendation_hover_tooltips.append(f"<b>{sport_name}</b><br>" +
                                                      f"Match Score: <b>{match_score:.1f}%</b><br>")
                            
                            # Add horizontal bars with gradient colors based on match scores
                            bar_colors = []
                            for item in chart_data_top10:
                                bar_colors.append(item['match_score'])
                            
                            # Build text labels for bars
                            text_labels = []
                            for score in match_scores:
                                text_labels.append(f"<b>{score:.1f}%</b>")
                            
                            fig.add_trace(go.Bar(
                                y=display_names,
                                x=match_scores,
                                orientation='h',
                                marker=dict(
                                    color=bar_colors,
                                    colorscale=[[0, '#D62828'], [0.5, '#FCBF49'], [1, '#06A77D']],  # Warm gradient: red -> orange -> teal
                                    cmin=min(match_scores) if match_scores else 0,
                                    cmax=max(match_scores) if match_scores else 100,
                                    line=dict(color='rgba(255,255,255,0.8)', width=2),
                                    opacity=0.85
                                ),
                                text=text_labels,
                                textposition='inside',
                                textfont=dict(color='white', size=12, family='Arial Black'),
                                hovertemplate="%{customdata}<extra></extra>",
                                customdata=recommendation_hover_tooltips,
                                name="AI Recommendations"
                            ))
                            
                            # Calculate dynamic range for x-axis
                            if match_scores:
                                min_score = min(match_scores)
                                max_score = max(match_scores)
                            else:
                                min_score = 0
                                max_score = 100
                            range_min = max(0, (int(min_score) // 10) * 10 - 5)
                            range_max = min(105, ((int(max_score) // 10) + 1) * 10 + 5)
                            
                            # Configure chart layout and styling
                            fig.update_layout(
                                title=dict(
                                    text="Sports you might also like",
                                    x=0.5,
                                    xanchor='center',
                                    font=dict(size=18, family='Arial', color='#000000')
                                ),
                                xaxis=dict(
                                    title="Match Score (%)",
                                    range=[range_min, range_max],
                                    gridcolor='rgba(108, 117, 125, 0.1)',
                                    showgrid=True,
                                    tickfont=dict(size=12, color='#666')
                                ),
                                yaxis=dict(
                                    title="Recommended Sports",
                                    tickfont=dict(size=11, color='#666'),
                                    autorange='reversed',  # Show highest scores at top
                                    gridcolor='rgba(108, 117, 125, 0.1)',
                                    showgrid=True
                                ),
                                height=max(400, len(chart_data_top10) * 35),
                                margin=dict(l=30, r=30, t=70, b=30),
                                paper_bgcolor='#FFFFFF',
                                plot_bgcolor='rgba(0,0,0,0)',
                                showlegend=False,
                                font=dict(family='Inter, system-ui, sans-serif')
                            )
                            
                            # Add average line
                            fig.add_vline(
                                x=avg_score,
                                line_dash="dash",
                                line_color="#F77F00",
                                line_width=2,
                                annotation_text=f"Avg. {avg_score:.1f}%",
                                annotation_position="top",
                                annotation_font_color="#F77F00",
                                annotation_font_size=11
                            )
                            
                            # Display chart with key based on filter values to ensure updates on filter changes
                            filter_key = f"ai_recommendations_{hash(tuple(sorted(selected_focus or [])))}_{hash(tuple(sorted(selected_intensity or [])))}_{hash(tuple(sorted(selected_setting or [])))}"
                            st.plotly_chart(fig, width="stretch", key=filter_key)
            else:
                # Show helpful message when no recommendations found
                # First check if model was loaded successfully
                model_data = load_knn_model()
                if model_data is None:
                    st.warning("⚠️ **KI-Empfehlungen**: Das ML-Modell konnte nicht geladen werden. Bitte stellen Sie sicher, dass das Modell trainiert wurde (führen Sie `ml/train.py` aus).")
                else:
                    st.info(f"🤖 **KI-Empfehlungen**: Keine Empfehlungen gefunden mit einem Match-Score ≥ {min_match}%. Versuchen Sie, den Mindest-Match-Score zu senken oder andere Filter auszuwählen.")


def render_team_contribution_matrix(team_members, assets_path):
    """Render a team contribution matrix heatmap showing each team member's contribution to different tasks.
    
    Creates a Plotly heatmap visualization that displays the contribution level
    of each team member across different project tasks.
    
    Args:
        team_members (list): List of dictionaries, each containing:
            - 'name' (str): Full name of team member
            - 'url' (str): LinkedIn profile URL
            - 'avatar' (str): Path to avatar image
        assets_path (Path): Path object pointing to the assets/images directory.
            Currently unused but kept for API compatibility.
        
    Note:
        Contribution levels are:
        - 3 = Main Contribution (Blue)
        - 2 = Contribution (Green)
        - 1 = Supporting Role (Orange)
        
        The heatmap displays tasks on the y-axis and team members on the x-axis.
        Hover tooltips show the contribution level for each cell.
    """
    # Define tasks (reversed order so first task appears at top)
    tasks = [
        "Video & Cut",
        "Testing & Bug-Fixing",
        "Code Documentation",
        "Backend incl. DB",
        "Machine Learning",
        "Frontend",
        "Requirements mapping & prototyping",
        "Project organization & planning"
    ]
    
    # Contribution matrix: each row = task, each column = team member
    # Values: 3 = Main Contribution, 2 = Contribution, 1 = Supporting Role
    # Order: Tamara, Till, Sarah, Antonia, Luca
    # Note: Matrix is reversed to match reversed tasks list
    contribution_matrix = [
        [1, 1, 3, 3, 1],  # Video & Cut
        [2, 3, 2, 2, 3],  # Testing & Bug-Fixing
        [2, 2, 1, 1, 2],  # Code Documentation
        [1, 2, 1, 1, 3],  # Backend incl. DB
        [2, 3, 1, 1, 2],  # Machine Learning
        [1, 2, 1, 1, 3],  # Frontend
        [3, 1, 2, 2, 1],  # Requirements mapping & prototyping
        [3, 3, 3, 3, 3],  # Project organization & planning
    ]
    
    # Text labels for hover tooltips
    label_map = {3: "Main Contribution", 2: "Contribution", 1: "Supporting Role"}
    matrix_text = [[label_map[val] for val in row] for row in contribution_matrix]
    
    member_names = [member["name"].split()[0] for member in team_members]  # First names only
    
    # Create Plotly heatmap
    # Simple approach: directly use numeric values (3, 2, 1) for colors
    fig = go.Figure(data=go.Heatmap(
        z=contribution_matrix,
        x=member_names,
        y=tasks,
        text=matrix_text,
        colorscale=[
            [0.0, '#F77F00'],   # 1 = Supporting Role (Orange)
            [0.5, '#06A77D'],   # 2 = Contribution (Green)
            [1.0, '#2E86AB']    # 3 = Main Contribution (Blue)
        ],
        hovertemplate='<b>%{y}</b><br>%{x}: <b>%{text}</b><extra></extra>',
        showscale=True,  # Hide color scale
        xgap=2,
        ygap=2
    ))
    
    fig.update_layout(
        title=dict(text='Team Contribution Matrix', x=0.5, xanchor='center', font=dict(size=20, family='Arial, sans-serif')),
        xaxis_title="Team Members",
        yaxis_title="",
        margin=dict(l=220, r=120, t=100, b=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        xaxis=dict(tickfont=dict(size=12)),
        yaxis=dict(tickfont=dict(size=11))
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
