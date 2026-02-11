"""
Forex trading session definitions and utilities.
All times in UTC.
"""

from datetime import datetime, time, timedelta
from typing import Dict, Tuple, Optional
import pytz


# Session definitions (all times in UTC)
SESSIONS = {
    "asian": {
        "name": "Asian Session",
        "start": time(0, 0),      # 00:00 UTC
        "end": time(9, 0),        # 09:00 UTC
        "major_centers": ["Tokyo", "Singapore", "Hong Kong"],
        "peak_hours": (time(1, 0), time(6, 0)),  # Tokyo open to mid-session
    },
    "london": {
        "name": "London Session",
        "start": time(8, 0),      # 08:00 UTC
        "end": time(16, 0),       # 16:00 UTC
        "major_centers": ["London", "Frankfurt", "Paris"],
        "peak_hours": (time(8, 0), time(12, 0)),  # London open to NY overlap
    },
    "ny": {
        "name": "New York Session",
        "start": time(13, 0),     # 13:00 UTC
        "end": time(21, 0),       # 21:00 UTC
        "major_centers": ["New York", "Chicago", "Toronto"],
        "peak_hours": (time(13, 0), time(17, 0)),  # NY open to London close
    }
}

# Session overlaps (high volatility periods)
OVERLAPS = {
    "london_ny": {
        "name": "London-NY Overlap",
        "start": time(13, 0),     # 13:00 UTC
        "end": time(16, 0),       # 16:00 UTC
        "sessions": ["london", "ny"],
        "volatility_multiplier": 1.8
    },
    "asian_london": {
        "name": "Asian-London Overlap",
        "start": time(8, 0),      # 08:00 UTC
        "end": time(9, 0),        # 09:00 UTC
        "sessions": ["asian", "london"],
        "volatility_multiplier": 1.3
    }
}


def get_current_session(dt: Optional[datetime] = None) -> str:
    """
    Determine which session is currently active.
    
    Args:
        dt: Datetime to check (defaults to current UTC time)
        
    Returns:
        Session key: "asian", "london", "ny", or "closed"
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    current_time = dt.time()
    
    for session_key, session_data in SESSIONS.items():
        start = session_data["start"]
        end = session_data["end"]
        
        # Handle sessions that cross midnight
        if start < end:
            if start <= current_time < end:
                return session_key
        else:  # Crosses midnight
            if current_time >= start or current_time < end:
                return session_key
    
    return "closed"


def get_next_session(dt: Optional[datetime] = None) -> Tuple[str, datetime]:
    """
    Get the next upcoming session and its start time.
    
    Args:
        dt: Reference datetime (defaults to current UTC time)
        
    Returns:
        Tuple of (session_key, start_datetime)
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    current_time = dt.time()
    today = dt.date()
    
    # Check sessions in chronological order
    session_order = [
        ("asian", SESSIONS["asian"]["start"]),
        ("london", SESSIONS["london"]["start"]),
        ("ny", SESSIONS["ny"]["start"])
    ]
    
    for session_key, start_time in session_order:
        session_start = datetime.combine(today, start_time, tzinfo=pytz.UTC)
        
        if current_time < start_time:
            return session_key, session_start
    
    # If no session today, return first session tomorrow
    tomorrow = today + timedelta(days=1)
    next_session_start = datetime.combine(
        tomorrow, 
        SESSIONS["asian"]["start"], 
        tzinfo=pytz.UTC
    )
    return "asian", next_session_start


def is_session_overlap(dt: Optional[datetime] = None) -> Optional[Dict]:
    """
    Check if current time is during a session overlap.
    
    Args:
        dt: Datetime to check (defaults to current UTC time)
        
    Returns:
        Overlap info dict if in overlap, None otherwise
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    current_time = dt.time()
    
    for overlap_key, overlap_data in OVERLAPS.items():
        start = overlap_data["start"]
        end = overlap_data["end"]
        
        if start <= current_time < end:
            return {
                "key": overlap_key,
                **overlap_data
            }
    
    return None


def get_session_info(session_key: str) -> Dict:
    """
    Get detailed information about a specific session.
    
    Args:
        session_key: "asian", "london", or "ny"
        
    Returns:
        Session configuration dict
        
    Raises:
        ValueError: If session_key is invalid
    """
    if session_key not in SESSIONS:
        raise ValueError(f"Invalid session key: {session_key}. Must be one of {list(SESSIONS.keys())}")
    
    return SESSIONS[session_key]


def get_pre_session_window(session_key: str, minutes: int = 90) -> Tuple[time, time]:
    """
    Calculate the time window before a session starts.
    
    Args:
        session_key: Session to analyze
        minutes: Length of pre-session window (default 90)
        
    Returns:
        Tuple of (start_time, end_time) for the pre-session window
    """
    session = get_session_info(session_key)
    session_start = session["start"]
    
    # Convert to datetime for arithmetic
    dummy_date = datetime(2000, 1, 1)
    session_start_dt = datetime.combine(dummy_date, session_start)
    window_start_dt = session_start_dt - timedelta(minutes=minutes)
    
    return window_start_dt.time(), session_start


def get_session_duration_minutes(session_key: str) -> int:
    """
    Get the duration of a session in minutes.
    
    Args:
        session_key: Session to check
        
    Returns:
        Duration in minutes
    """
    session = get_session_info(session_key)
    start = session["start"]
    end = session["end"]
    
    # Convert to minutes from midnight
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    
    # Handle overnight sessions
    if end_minutes < start_minutes:
        end_minutes += 24 * 60
    
    return end_minutes - start_minutes


def is_weekend(dt: Optional[datetime] = None) -> bool:
    """
    Check if given time is during forex market weekend closure.
    Forex closes Friday 21:00 UTC, reopens Sunday 22:00 UTC.
    
    Args:
        dt: Datetime to check (defaults to current UTC time)
        
    Returns:
        True if market is closed for weekend
    """
    if dt is None:
        dt = datetime.now(pytz.UTC)
    
    weekday = dt.weekday()  # 0=Monday, 6=Sunday
    current_time = dt.time()
    
    # Friday after 21:00 UTC
    if weekday == 4 and current_time >= time(21, 0):
        return True
    
    # All day Saturday
    if weekday == 5:
        return True
    
    # Sunday before 22:00 UTC
    if weekday == 6 and current_time < time(22, 0):
        return True
    
    return False