"""
Economic calendar client for high-impact forex events.
Uses multiple fallback strategies when API is unavailable.
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()


class CalendarClient:
    """Client for economic calendar data with fallback strategies."""
    
    # High-impact event keywords
    HIGH_IMPACT_KEYWORDS = [
        "NFP", "Non-Farm", "Payroll",
        "FOMC", "Federal Reserve", "Fed", "Interest Rate",
        "ECB", "European Central Bank",
        "GDP", "Gross Domestic",
        "CPI", "Inflation", "Consumer Price",
        "Unemployment",
        "Central Bank", "Policy Decision",
        "BOE", "Bank of England",
        "BOJ", "Bank of Japan",
        "RBA", "Reserve Bank"
    ]
    
    # Known recurring high-impact events (days of month when they typically occur)
    RECURRING_EVENTS = {
        "US": {
            "NFP": {"day": "first_friday", "time": "13:30"},
            "FOMC": {"days": [1, 15], "time": "19:00"},  # Approximate
            "CPI": {"day": "mid_month", "time": "13:30"},
        },
        "EU": {
            "ECB": {"days": [1, 15], "time": "12:45"},  # ECB meetings
            "GDP": {"day": "end_month", "time": "10:00"},
        },
        "UK": {
            "BOE": {"days": [1, 15], "time": "12:00"},
            "CPI": {"day": "mid_month", "time": "07:00"},
        }
    }
    
    def __init__(self, twelve_data_client: Optional[Any] = None):
        """
        Initialize calendar client.
        
        Args:
            twelve_data_client: Optional Twelve Data client (not used in fallback)
        """
        # We'll use fallback mode by default since API endpoint is unavailable
        self.use_fallback = True
    
    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming high-impact economic events.
        Uses heuristic-based fallback when API is unavailable.
        
        Args:
            hours_ahead: Look ahead window in hours
            country: Optional country filter (US, GB, EU, JP, etc.)
            
        Returns:
            List of event dictionaries (may be empty if no events detected)
        """
        # Always use fallback mode since API endpoint doesn't work
        return self._get_fallback_events(hours_ahead, country)
    
    def _get_fallback_events(
        self,
        hours_ahead: int,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fallback event detection using heuristics.
        Detects likely high-impact events based on day/time patterns.
        
        Args:
            hours_ahead: Hours to look ahead
            country: Country filter
            
        Returns:
            List of potential events
        """
        events = []
        now = datetime.now(pytz.UTC)
        cutoff = now + timedelta(hours=hours_ahead)
        
        # Check for common event patterns
        current_day = now.day
        current_hour = now.hour
        
        # Check if it's first Friday (NFP day)
        if self._is_first_friday(now) and current_hour < 14:
            # NFP typically at 13:30 UTC
            nfp_time = now.replace(hour=13, minute=30, second=0, microsecond=0)
            if now < nfp_time < cutoff:
                events.append({
                    "event": "US Non-Farm Payrolls (NFP)",
                    "country": "US",
                    "datetime": nfp_time.isoformat(),
                    "impact": "high",
                    "currency": "USD",
                    "source": "heuristic"
                })
        
        # Check for mid-month CPI releases (typically around 12th-15th)
        if 12 <= current_day <= 15:
            # US CPI typically at 13:30 UTC
            cpi_time = now.replace(hour=13, minute=30, second=0, microsecond=0)
            if now < cpi_time < cutoff and now.day == cpi_time.day:
                events.append({
                    "event": "US Consumer Price Index (CPI)",
                    "country": "US",
                    "datetime": cpi_time.isoformat(),
                    "impact": "high",
                    "currency": "USD",
                    "source": "heuristic"
                })
        
        # Check for FOMC/ECB meeting days (typically occur on specific weeks)
        # This is a simplified heuristic - real dates vary
        
        return events
    
    def check_event_proximity(
        self,
        target_time: datetime,
        window_minutes: int = 120
    ) -> Optional[Dict[str, Any]]:
        """
        Check if high-impact event is near target time.
        
        Args:
            target_time: Time to check around
            window_minutes: Window before/after to search
            
        Returns:
            Event dict if found, None otherwise
        """
        hours_ahead = (window_minutes * 2) / 60
        events = self.get_upcoming_events(hours_ahead=int(hours_ahead))
        
        for event in events:
            event_time = datetime.fromisoformat(event["datetime"])
            time_diff = abs((event_time - target_time).total_seconds() / 60)
            
            if time_diff <= window_minutes:
                event["minutes_until"] = int((event_time - target_time).total_seconds() / 60)
                return event
        
        return None
    
    def get_events_for_session(
        self,
        session_start: datetime,
        session_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get all high-impact events during a session.
        
        Args:
            session_start: Session start time
            session_end: Session end time
            
        Returns:
            List of events during session (may be empty)
        """
        duration_hours = (session_end - session_start).total_seconds() / 3600
        events = self.get_upcoming_events(hours_ahead=int(duration_hours + 2))
        
        session_events = []
        for event in events:
            event_time = datetime.fromisoformat(event["datetime"])
            if session_start <= event_time <= session_end:
                session_events.append(event)
        
        return session_events
    
    def _is_high_impact(self, event_name: str) -> bool:
        """
        Check if event is high-impact based on keywords.
        
        Args:
            event_name: Event description
            
        Returns:
            True if high-impact
        """
        event_upper = event_name.upper()
        return any(keyword.upper() in event_upper for keyword in self.HIGH_IMPACT_KEYWORDS)
    
    def _is_first_friday(self, dt: datetime) -> bool:
        """
        Check if date is the first Friday of the month.
        
        Args:
            dt: Datetime to check
            
        Returns:
            True if first Friday
        """
        # Check if it's Friday (weekday 4)
        if dt.weekday() != 4:
            return False
        
        # Check if it's in the first week (day 1-7)
        return 1 <= dt.day <= 7
    
    def format_event_for_driver(self, event: Dict[str, Any]) -> str:
        """
        Format event as a driver string for output.
        
        Args:
            event: Event dictionary
            
        Returns:
            Formatted driver string
        """
        event_name = event.get("event", "Economic event")
        
        # Determine session timing
        event_time = datetime.fromisoformat(event["datetime"])
        hour = event_time.hour
        
        if 0 <= hour < 9:
            session = "Asian session"
        elif 8 <= hour < 16:
            session = "London session"
        elif 13 <= hour < 21:
            if 13 <= hour < 16:
                session = "London-NY overlap"
            else:
                session = "NY session"
        else:
            session = "off-hours"
        
        # Add context about source
        source_note = ""
        if event.get("source") == "heuristic":
            source_note = " (check economic calendar for confirmation)"
        
        return f"{event_name} may be scheduled during {session}{source_note}"


# Singleton instance
_calendar_instance = None

def get_calendar_client() -> CalendarClient:
    """
    Get singleton calendar client instance.
    
    Returns:
        CalendarClient instance
    """
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = CalendarClient()
    return _calendar_instance