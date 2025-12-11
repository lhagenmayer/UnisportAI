"""
================================================================================
HTML AND FORMATTING UTILITIES
================================================================================

Purpose: Functions for generating HTML and formatted strings that can be displayed
in Streamlit using st.markdown() with unsafe_allow_html=True. Also includes
date/time formatting utilities for consistent display across the app.

WHY: Streamlit has built-in components (st.write, st.title, etc.), but sometimes
you need custom styling. This module helps create custom HTML/CSS that can be
rendered in Streamlit. Always use unsafe_allow_html=True carefully - only with
trusted content.
================================================================================
"""

from datetime import datetime
import pandas as pd
import streamlit as st


def format_intensity_display(intensity_value):
    """Format intensity value with emoji indicator.
    
    Args:
        intensity_value (str or None): Intensity level (e.g., 'low', 'medium', 'high').
    
    Returns:
        str: Formatted string with emoji and capitalized intensity (e.g., "🟢 Low") or "N/A".
        
    Example:
        >>> format_intensity_display('high')
        '🔴 High'
        >>> format_intensity_display(None)
        'N/A'
    """
    if not intensity_value:
        return "N/A"
    
    intensity = intensity_value.capitalize()
    color_map = {'Low': '🟢', 'Medium': '🟡', 'High': '🔴'}
    color_emoji = color_map.get(intensity, '⚪')
    return f"{color_emoji} {intensity}"


def _format_list_display(items, max_items=2, show_count=True, extract_name=None):
    """Generic helper function to format lists for display.
    
    Args:
        items (list): List of items to format.
        max_items (int, optional): Maximum number of items to show. Defaults to 2.
        show_count (bool, optional): If True, show "+X" count when more items exist.
            Defaults to True.
        extract_name (callable, optional): Function to extract name from item (for dicts).
            Defaults to None.
    
    Returns:
        str: Formatted string with comma-separated items, or "N/A" if empty.
    """
    if not items:
        return "N/A"
    
    formatted_items = []
    display_items = items[:max_items]
    
    for item in display_items:
        if extract_name:
            name = extract_name(item)
        else:
            name = str(item) if item else None
        
        if name:
            # Capitalize strings, but preserve already-formatted names
            if isinstance(name, str):
                formatted_items.append(name.capitalize())
            else:
                formatted_items.append(str(name))
    
    if show_count and len(items) > max_items:
        formatted_items.append(f"+{len(items) - max_items}")
    
    return ', '.join(formatted_items)


def format_focus_display(focus_list):
    """Format focus list for display (shows max 2 items + count if more).
    
    Args:
        focus_list (list): List of focus area strings (e.g., ['strength', 'endurance']).
    
    Returns:
        str: Formatted string (e.g., "Strength, Endurance" or "Strength, Endurance +2").
        
    Example:
        >>> format_focus_display(['strength', 'endurance', 'flexibility'])
        'Strength, Endurance +1'
    """
    return _format_list_display(focus_list, max_items=2, show_count=True)


def format_setting_display(setting_list):
    """Format setting list for display (shows max 2 items).
    
    Args:
        setting_list (list): List of setting strings (e.g., ['solo', 'team']).
    
    Returns:
        str: Formatted string (e.g., "Solo, Team").
        
    Example:
        >>> format_setting_display(['solo', 'team'])
        'Solo, Team'
    """
    return _format_list_display(setting_list, max_items=2, show_count=False)


def format_trainers_display(trainers_list):
    """Format trainers list for display (shows max 2 names + count if more).
    
    Args:
        trainers_list (list): List of trainer dictionaries with 'name' key or strings.
    
    Returns:
        str: Formatted string (e.g., "John Doe, Jane Smith" or "John Doe, Jane Smith +3").
        
    Example:
        >>> format_trainers_display([{'name': 'John Doe'}, {'name': 'Jane Smith'}, {'name': 'Bob'}])
        'John Doe, Jane Smith +1'
    """
    def extract_trainer_name(item):
        if isinstance(item, dict):
            return item.get('name', '')
        return str(item) if item else None
    
    return _format_list_display(trainers_list, max_items=2, show_count=True, extract_name=extract_trainer_name)


def create_offer_metadata_df(offer, match_score=None, include_trainers=None, upcoming_count=None):
    """Create a pandas DataFrame with offer metadata for display.
    
    Formats all offer metadata (intensity, focus, setting, trainers)
    and creates a single-row DataFrame suitable for display in Streamlit.
    
    Args:
        offer (dict): Dictionary containing offer data with keys:
            - 'intensity': Intensity level string
            - 'focus': List of focus areas
            - 'setting': List of settings
            - 'trainers': List of trainer dictionaries or strings
        match_score (float, optional): Match score (0-100) to include in the DataFrame.
        include_trainers (bool, optional): Explicitly control trainer inclusion.
            If None, trainers are included when match_score is provided.
        upcoming_count (int, optional): Count of upcoming events to include.
    
    Returns:
        pd.DataFrame: DataFrame with single row containing formatted metadata columns:
            - Match (if match_score provided)
            - Intensity
            - Focus
            - Setting
            - Upcoming (if upcoming_count provided)
            - Trainers (if include_trainers is True or match_score is provided)
    """
    # Format intensity
    intensity_value = offer.get('intensity') or ''
    intensity_display = format_intensity_display(intensity_value)
    
    # Format focus
    focus_display = format_focus_display(offer.get('focus'))
    
    # Format setting
    setting_display = format_setting_display(offer.get('setting'))
    
    # Format trainers
    trainers_display = format_trainers_display(offer.get('trainers', []))
    
    # Build DataFrame columns
    columns = {}
    
    if match_score is not None:
        columns['Match'] = [f"{match_score:.0f}%"]
    
    columns['Intensity'] = [intensity_display]
    columns['Focus'] = [focus_display]
    columns['Setting'] = [setting_display]
    
    # Include upcoming count if provided
    if upcoming_count is not None:
        columns['Upcoming'] = [upcoming_count if upcoming_count > 0 else 0]
    
    # Include trainers based on include_trainers flag or match_score presence
    if include_trainers is None:
        include_trainers = match_score is not None
    
    if include_trainers:
        columns['Trainers'] = [trainers_display]
    
    return pd.DataFrame(columns)


def parse_event_datetime(datetime_string):
    """Parse an ISO format datetime string from event data.
    
    Handles timezone conversion by replacing 'Z' with '+00:00' for proper
    datetime parsing. This is needed because some databases return 'Z' format
    which Python's fromisoformat() doesn't handle directly.
    
    Args:
        datetime_string (str or datetime): ISO format datetime string (may include 'Z' timezone)
            or already-parsed datetime object.
    
    Returns:
        datetime: Parsed datetime object.
        
    Example:
        >>> parse_event_datetime("2025-01-15T10:30:00Z")
        datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
    """
    if isinstance(datetime_string, str):
        # Replace 'Z' with '+00:00' for proper timezone handling
        datetime_clean = datetime_string.replace('Z', '+00:00')
        return datetime.fromisoformat(datetime_clean)
    return datetime_string


def format_weekday(datetime_obj, abbreviated=False):
    """Format weekday from a datetime object.
    
    Args:
        datetime_obj (datetime): Datetime object to extract weekday from.
        abbreviated (bool, optional): If True, returns abbreviated form (Mon, Tue, etc.).
            If False, returns full name (Monday, Tuesday, etc.). Defaults to False.
    
    Returns:
        str: Weekday name (full or abbreviated).
        
    Example:
        >>> format_weekday(datetime(2025, 1, 15), abbreviated=True)
        'Wed'
        >>> format_weekday(datetime(2025, 1, 15), abbreviated=False)
        'Wednesday'
    """
    weekday_name = datetime_obj.strftime('%A')
    
    if abbreviated:
        weekday_abbreviations = {
            'Monday': 'Mon',
            'Tuesday': 'Tue',
            'Wednesday': 'Wed',
            'Thursday': 'Thu',
            'Friday': 'Fri',
            'Saturday': 'Sat',
            'Sunday': 'Sun'
        }
        return weekday_abbreviations.get(weekday_name, weekday_name)
    
    return weekday_name


def format_time_range(start_dt, end_dt=None):
    """Format time or time range from datetime objects.
    
    Args:
        start_dt (datetime): Datetime object for start time.
        end_dt (datetime, optional): Datetime object for end time. Defaults to None.
    
    Returns:
        str: Formatted time string (e.g., "10:30" or "10:30 - 12:00").
        
    Example:
        >>> format_time_range(datetime(2025, 1, 15, 10, 30))
        '10:30'
        >>> format_time_range(datetime(2025, 1, 15, 10, 30), datetime(2025, 1, 15, 12, 0))
        '10:30 - 12:00'
    """
    start_time_str = start_dt.strftime('%H:%M')
    
    if end_dt:
        end_time_str = end_dt.strftime('%H:%M')
        return f"{start_time_str} - {end_time_str}"
    
    return start_time_str


def get_match_score_style(match_score):
    """Get CSS style string for match score badge based on score value.
    
    Args:
        match_score (float): Numeric score (0-100).
    
    Returns:
        str: CSS style string for the badge with background-color and color properties.
        
    Example:
        >>> get_match_score_style(95)  # Returns green style
        'background-color: #dcfce7; color: #166534;'
        >>> get_match_score_style(75)  # Returns yellow style
        'background-color: #fef9c3; color: #854d0e;'
        >>> get_match_score_style(50)  # Returns gray style
        'background-color: #f3f4f6; color: #374151;'
    """
    if match_score >= 90:
        return 'background-color: #dcfce7; color: #166534;'
    elif match_score >= 70:
        return 'background-color: #fef9c3; color: #854d0e;'
    else:
        return 'background-color: #f3f4f6; color: #374151;'


def render_user_avatar(user_name, user_picture=None, size='large'):
    """Render user avatar (image or initials) in Streamlit.
    
    Args:
        user_name (str): User's name (for generating initials).
        user_picture (str, optional): URL or path to user picture. Defaults to None.
        size (str, optional): 'large' (default) or 'small' - affects heading size.
            Defaults to 'large'.
        
    Example:
        >>> render_user_avatar("John Doe", "https://example.com/pic.jpg")
        # Renders image
        >>> render_user_avatar("Jane Smith")  # Shows initials
        # Renders "JS" as heading
    """
    if user_picture and str(user_picture).startswith('http'):
        if size == 'small':
            st.image(user_picture, width=120)
        else:
            st.image(user_picture)
    else:
        name_words = user_name.split()[:2] if user_name else []
        initials = ''.join([word[0].upper() for word in name_words if word]) if name_words else "U"
        
        if size == 'small':
            st.markdown(f"## {initials}")
        else:
            st.markdown(f"# {initials}")


def convert_events_to_table_data(events, abbreviated_weekday=True, include_status=False, include_sport=False, include_trainers=False):
    """Convert list of event dictionaries to table-ready data format.
    
    Handles parsing datetime strings, formatting times and weekdays,
    and creating a consistent structure for displaying events in Streamlit dataframes.
    
    Args:
        events (list): List of event dictionaries with 'start_time', 'end_time', etc.
        abbreviated_weekday (bool, optional): If True, use abbreviated weekday (e.g., "Mon"),
            else full name. Defaults to True.
        include_status (bool, optional): If True, include 'status' field (Active/Cancelled).
            Defaults to False.
        include_sport (bool, optional): If True, include 'sport' field. Defaults to False.
        include_trainers (bool, optional): If True, include 'trainers' field. Defaults to False.
    
    Returns:
        list: List of dictionaries ready for st.dataframe(), each containing:
            - date: date object
            - time: time string (e.g., "10:00" or "10:00 - 12:00")
            - weekday: weekday string
            - location: location name
            - status: "Active" or "Cancelled" (if include_status=True)
            - sport: sport name (if include_sport=True)
            - trainers: comma-separated trainer names (if include_trainers=True)
        
    Example:
        >>> events = [{'start_time': '2025-01-15T10:00:00Z', 'end_time': '2025-01-15T12:00:00Z', ...}]
        >>> table_data = convert_events_to_table_data(events, abbreviated_weekday=True)
        >>> st.dataframe(table_data)
    """
    table_data = []
    for event in events:
        start_dt = parse_event_datetime(str(event.get('start_time')))
        end_time = event.get('end_time')
        
        if end_time:
            end_dt = parse_event_datetime(str(end_time))
            time_val = format_time_range(start_dt, end_dt)
        else:
            time_val = format_time_range(start_dt)
        
        weekday = format_weekday(start_dt, abbreviated=abbreviated_weekday)
        
        row = {
            'date': start_dt.date(),
            'time': time_val,
            'weekday': weekday,
            'location': event.get('location_name', 'N/A')
        }
        
        if include_status:
            if event.get('canceled'):
                row['status'] = "Cancelled"
            else:
                row['status'] = "Active"
        
        if include_sport:
            row['sport'] = event.get('sport_name', 'Course')
        
        if include_trainers:
            trainers = event.get('trainers', [])
            row['trainers'] = ", ".join(str(t) for t in trainers) if trainers else "N/A"
        
        table_data.append(row)
    
    return table_data

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
