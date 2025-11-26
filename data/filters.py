"""Utilities for filtering offers and events.

This module provides helper functions used by the Streamlit UI to filter
offers and event lists according to sidebar-controlled criteria such as
date ranges, weekdays, time windows, locations and cancellation status.
"""


def _check_event_matches_filters(event, sport_filter, weekday_filter, 
                                   date_start, date_end, time_start, time_end,
                                   location_filter, hide_cancelled):
    """Return whether a single event matches the provided filters.

    Args:
        event (dict): Event record with keys like ``start_time``,
            ``sport_name``, ``location_name`` and ``canceled``.
        sport_filter (list|None): List of sport names to include.
        weekday_filter (list|None): List of weekday names (e.g. "Monday").
        date_start (date|None): Inclusive start date filter.
        date_end (date|None): Inclusive end date filter.
        time_start (time|None): Earliest allowed event time.
        time_end (time|None): Latest allowed event time.
        location_filter (list|None): List of allowed location names.
        hide_cancelled (bool): Whether to exclude canceled events.

    Returns:
        bool: True when the event satisfies all filters, False otherwise.
    """
    from datetime import datetime
    
    # Check sport filter
    if sport_filter and len(sport_filter) > 0:
        if event.get('sport_name', '') not in sport_filter:
            return False
    
    # Check cancelled events
    if hide_cancelled and event.get('canceled'):
        return False
    
    # Parse start time
    start_time = event.get('start_time')
    if isinstance(start_time, str):
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    else:
        start_dt = start_time
    
    # Check weekday
    if weekday_filter and len(weekday_filter) > 0:
        if start_dt.strftime('%A') not in weekday_filter:
            return False
    
    # Check date
    event_date = start_dt.date()
    if date_start and event_date < date_start:
        return False
    if date_end and event_date > date_end:
        return False
    
    # Check time
    if time_start or time_end:
        event_time = start_dt.time()
        if time_start and event_time < time_start:
            return False
        if time_end and event_time > time_end:
            return False
    
    # Check location
    if location_filter and len(location_filter) > 0:
        if event.get('location_name', '') not in location_filter:
            return False
    
    return True


def filter_offers(offers, show_upcoming_only=True, search_text="", intensity=None, focus=None, setting=None):
    """Filter a list of offers according to UI criteria.

    Args:
        offers (list): List of offer dictionaries as returned from the DB.
        show_upcoming_only (bool): When True, exclude offers with no upcoming events.
        search_text (str): Case-insensitive substring match against offer name.
        intensity (list|None): Allowed intensity values.
        focus (list|None): Allowed focus values.
        setting (list|None): Allowed setting values.

    Returns:
        list: Filtered list of offers.
    """
    filtered = offers
    
    if show_upcoming_only:
        # Filter offers that have upcoming events
        filtered = [offer for offer in filtered if offer.get('future_events_count', 0) > 0]
    
    if search_text:
        filtered = [offer for offer in filtered if search_text.lower() in offer.get('name', '').lower()]
    
    if intensity:
        filtered = [offer for offer in filtered if offer.get('intensity') in intensity]
    
    if focus:
        filtered = [offer for offer in filtered if offer.get('focus') and any(f in offer.get('focus', []) for f in focus)]
    
    if setting:
        filtered = [offer for offer in filtered if offer.get('setting') and any(s in offer.get('setting', []) for s in setting)]
    
    return filtered


def filter_events(events, sport_filter=None, weekday_filter=None, 
                   date_start=None, date_end=None, time_start=None, time_end=None,
                   location_filter=None, hide_cancelled=True):
    """Filter a list of events using the shared event predicate.

    Returns a list containing only events that match the provided filters.
    """
    filtered = []
    for event in events:
        if _check_event_matches_filters(event, sport_filter, weekday_filter, 
                                          date_start, date_end, time_start, 
                                          time_end, location_filter, hide_cancelled):
            filtered.append(event)
    return filtered


def filter_offers_by_events(offers, events_mapping, sport_filter=None, weekday_filter=None, 
                                date_start=None, date_end=None, time_start=None, time_end=None,
                                location_filter=None, hide_cancelled=True):
    """Return offers that have at least one event matching the filters.

    Args:
        offers (list): Offer dictionaries.
        events_mapping (dict): Mapping from ``offer['href']`` to list of events.

    Returns:
        list: Offers that have at least one matching event.
    """
    filtered = []
    for offer in offers:
        offer_href = offer.get('href')
        events = events_mapping.get(offer_href, [])
        for event in events:
            if _check_event_matches_filters(event, sport_filter, weekday_filter, 
                                              date_start, date_end, time_start, 
                                              time_end, location_filter, hide_cancelled):
                filtered.append(offer)
                break
    return filtered
