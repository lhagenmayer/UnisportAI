"""Filtering utilities for offers and events.

This module provides functions to filter sports activities and events based on user criteria.

WHAT IS FILTERING?
------------------
Filtering means showing only items that match certain criteria. For example:
- "Show me only yoga classes" (sport filter)
- "Show me only Monday classes" (weekday filter)
- "Show me only morning classes" (time filter)
- "Show me only classes at Gym A" (location filter)

HOW FILTERING WORKS:
-------------------
1. User selects filter criteria (e.g., "Monday", "Morning", "Yoga")
2. Each event/offer is checked against these criteria
3. Only items that match ALL criteria are shown
4. Items that don't match are hidden

KEY CONCEPTS:
------------
- Hard Filters: Must match exactly (e.g., sport name, location)
- Date/Time Filters: Check if event is within a date or time range
- Boolean Filters: True/False checks (e.g., hide cancelled events)
- Multiple Filters: All filters must match (AND logic, not OR)

EXAMPLE:
--------
```python
# Filter events:
filtered = filter_events(
    events,
    sport_filter=['Yoga', 'Swimming'],
    weekday_filter=['Monday', 'Wednesday'],
    time_start=time(9, 0),  # 9 AM
    time_end=time(17, 0),    # 5 PM
    hide_cancelled=True
)
# Result: Only yoga/swimming events on Mon/Wed between 9 AM and 5 PM
```
"""

from datetime import datetime, time, date


def check_event_matches_filters(
    event,
    sport_filter,
    weekday_filter,
    date_start,
    date_end,
    time_start,
    time_end,
    location_filter,
    hide_cancelled,
    search_text="",
):
    """
    Check if a single event matches all the provided filters.
    
    Filters are checked one by one instead of using one complex condition.
    This makes it easier to debug and understand what's being filtered out.
    
    Args:
        event: Dictionary containing event data
        sport_filter: List of sport names to include (or None/empty for all)
        weekday_filter: List of weekdays to include (or None/empty for all)
        date_start: Start date for filtering (or None for no start limit)
        date_end: End date for filtering (or None for no end limit)
        time_start: Start time for filtering (or None for no start limit)
        time_end: End time for filtering (or None for no end limit)
        location_filter: List of locations to include (or None/empty for all)
        hide_cancelled: Boolean, if True exclude cancelled events
        search_text: Text to search in sport name, location name, or trainer names
    
    Returns:
        Boolean: True if event matches all filters, False otherwise
    """
    # STEP 1: Check sport filter
    # If user selected specific sports, only show those
    if sport_filter and len(sport_filter) > 0:
        event_sport = event.get('sport_name', '')
        if event_sport not in sport_filter:
            return False  # This event doesn't match, exclude it
    
    # STEP 2: Check if event is cancelled
    # If user wants to hide cancelled events, exclude them
    if hide_cancelled and event.get('canceled'):
        return False
    
    # STEP 3: Parse the event's start time
    # Convert ISO format string to datetime object for comparison
    start_time = event.get('start_time')
    if isinstance(start_time, str):
        # Replace 'Z' with '+00:00' for proper timezone handling
        start_time_str = start_time.replace('Z', '+00:00')
        start_dt = datetime.fromisoformat(start_time_str)
    else:
        start_dt = start_time
    
    # STEP 4: Check weekday filter
    # strftime('%A') gives us day name like 'Monday', 'Tuesday', etc.
    if weekday_filter and len(weekday_filter) > 0:
        event_weekday = start_dt.strftime('%A')
        if event_weekday not in weekday_filter:
            return False
    
    # STEP 5: Check date range filter
    event_date = start_dt.date()
    
    # Check if event is before start date
    if date_start and event_date < date_start:
        return False
    
    # Check if event is after end date
    if date_end and event_date > date_end:
        return False
    
    # STEP 6: Check time range filter
    if time_start or time_end:
        event_time = start_dt.time()
        
        # Check if event starts before allowed time
        if time_start and event_time < time_start:
            return False
        
        # Check if event starts after allowed time
        if time_end and event_time > time_end:
            return False
    
    # STEP 7: Check location filter
    if location_filter and len(location_filter) > 0:
        event_location = event.get('location_name', '')
        if event_location not in location_filter:
            return False
    
    # STEP 8: Check search text filter
    if search_text:
        search_text_lower = search_text.lower()
        # Search in sport name
        sport_name = event.get('sport_name', '').lower()
        # Search in location name
        location_name = event.get('location_name', '').lower()
        # Search in trainer names
        trainers = event.get('trainers', [])
        trainer_names = []
        for trainer in trainers:
            if isinstance(trainer, dict):
                trainer_names.append(trainer.get('name', '').lower())
            else:
                trainer_names.append(str(trainer).lower())
        trainer_names_str = ' '.join(trainer_names)
        
        # Check if search text matches any field
        if (search_text_lower not in sport_name and 
            search_text_lower not in location_name and 
            search_text_lower not in trainer_names_str):
            return False
    
    # If execution reaches here, event passed all filters
    return True


def filter_offers(
    offers,
    show_upcoming_only=True,
    search_text="",
    intensity=None,
    focus=None,
    setting=None,
    min_match_score=0,
    max_results=20,
):
    """
    Filter sports offers (activities) based on various criteria.
    
    Shows users activities that match their preferences.
    Uses hard filters (must match) and ML scoring (when no hard filters).
    
    Logic:
        - If intensity/focus/setting filters are selected: strict 100% match filtering
        - If no filters selected: show all with ML scoring for ranking
    
    Args:
        offers: List of offer dictionaries
        show_upcoming_only: If True, only show offers with future events
        search_text: Text to search in activity names
        intensity: List of intensity levels (strict filter)
        focus: List of focus areas (strict filter)
        setting: List of settings (strict filter)
        min_match_score: Minimum match percentage (0-100) - only used when no hard filters
        max_results: Maximum number of results to return
    
    Returns:
        List of filtered offers with added 'match_score'
    """
    # STEP 1: Start with only offers that have meaningful tags/features
    filtered = []
    for offer in offers:
        # Check if offer has meaningful tags (valid data check)
        # Check focus using any() with generator expression
        focus_list = offer.get('focus')
        has_focus = any(f and f.strip() for f in focus_list) if focus_list else False
        
        # Check setting using any() with generator expression
        setting_list = offer.get('setting')
        has_setting = any(s and s.strip() for s in setting_list) if setting_list else False
        
        # Check intensity
        intensity_value = offer.get('intensity')
        has_intensity = bool(intensity_value and intensity_value.strip())
        
        if not (has_focus or has_setting or has_intensity):
            continue
            
        # Upcoming filter (hard filter)
        if show_upcoming_only and offer.get('future_events_count', 0) == 0:
            continue
            
        # Search filter (hard filter)
        if search_text:
            offer_name = offer.get('name', '')
            offer_name_lower = offer_name.lower()
            search_text_lower = search_text.lower()
            if search_text_lower not in offer_name_lower:
                continue
            
        filtered.append(offer)
    
    # STEP 2: Apply strict filters for intensity/focus/setting
    # If ANY of these are selected, 100% match filtering is used
    has_hard_filters = bool(intensity or focus or setting)
    
    if has_hard_filters:
        # Strict filtering mode must match ALL selected criteria
        strict_filtered = []
        
        for offer in filtered:
            matches = True
            
            # Intensity filter (must match if selected)
            if intensity:
                offer_intensity = offer.get('intensity')
                if offer_intensity not in intensity:
                    matches = False
            
            # Focus filter (must have ANY of the selected focus areas)
            if focus and matches:
                offer_focus = offer.get('focus')
                if offer_focus:
                    matches = any(f in offer_focus for f in focus)
                else:
                    matches = False
            
            # Setting filter (must have ANY of the selected settings)
            if setting and matches:
                offer_setting = offer.get('setting')
                if offer_setting:
                    matches = any(s in offer_setting for s in setting)
                else:
                    matches = False
            
            if matches:
                offer['match_score'] = 100.0  # Perfect match
                strict_filtered.append(offer)
        
        return strict_filtered[:max_results]
    
    else:
        # No hard filters use ML scoring for ranking
        # Assign default score and return
        # Use list comprehension to set match_score efficiently
        for offer in filtered:
            offer['match_score'] = 100.0
        return filtered[:max_results]


def filter_events(
    events,
    sport_filter=None,
    weekday_filter=None,
    date_start=None,
    date_end=None,
    time_start=None,
    time_end=None,
    location_filter=None,
    hide_cancelled=True,
    search_text="",
):
    """
    Filter a list of events using the check_event_matches_filters function.
    
    Applies all filters to a list of events by looping through each event
    and checking if it passes the filters.
    
    Args:
        events: List of event dictionaries
        sport_filter: List of sport names to include (or None/empty for all)
        weekday_filter: List of weekdays to include (or None/empty for all)
        date_start: Start date for filtering (or None for no start limit)
        date_end: End date for filtering (or None for no end limit)
        time_start: Start time for filtering (or None for no start limit)
        time_end: End time for filtering (or None for no end limit)
        location_filter: List of locations to include (or None/empty for all)
        hide_cancelled: Boolean, if True exclude cancelled events
        search_text: Text to search in sport name, location name, or trainer names
    
    Returns:
        List of filtered events
    """
    filtered = []
    
    # Check each event one by one
    for event in events:
        # Use helper function to check if event matches
        matches = check_event_matches_filters(
            event, sport_filter, weekday_filter,
            date_start, date_end, time_start, time_end,
            location_filter, hide_cancelled, search_text
        )
        if matches:
            filtered.append(event)
    
    return filtered

# Parts of this codebase were developed with the assistance of AI-based tools (Cursor and Github Copilot)
# All outputs generated by such systems were reviewed, validated, and modified by the author.
