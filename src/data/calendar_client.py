"""
Economic calendar client for high-impact forex events.
Uses Twelve Data economic calendar API.
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

from src.data.twelve_data_client import TwelveDataClient

load_dotenv()


class CalendarClient:
    """Client for economic calendar data."""
    
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
    
    def __init__(self, twelve_data_client: Optional[TwelveDataClient] = None):
        """
        Initialize calendar client.
        
        Args:
            twelve_data_client: Optional Twelve Data client instance
        """
        from src.data.twelve_data_client import get_client
        self.client = twelve_data_client or get_client()
    
    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming high-impact economic events.
        
        Args:
            hours_ahead: Look ahead window in hours
            country: Optional country filter (US, GB, EU, JP, etc.)
            
        Returns:
            List of event dictionaries
            
        Example output:
            [
                {
                    "event": "FOMC Interest Rate Decision",
                    "country": "US",
                    "datetime": "2025-02-10 19:00:00",
                    "impact": "high",
                    "currency": "USD"
                }
            ]
        """
        try:
            # Twelve Data economic calendar endpoint
            params = {
                "apikey": self.client.api_key,
                "format": "JSON"
            }
            
            if country:
                params["country"] = country
            
            response = self.client._make_request("economic_calendar", params)
            
            # Filter and format events
            now = datetime.now(pytz.UTC)
            cutoff = now + timedelta(hours=hours_ahead)
            
            events = []
            for event_data in response.get("data", []):
                event_time_str = event_data.get("datetime", "")
                
                # Parse event time
                try:
                    event_time = datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))
                except:
                    continue
                
                # Filter by time window
                if now <= event_time <= cutoff:
                    # Check if high impact
                    event_name = event_data.get("event", "")
                    if self._is_high_impact(event_name):
                        events.append({
                            "event": event_name,
                            "country": event_data.get("country", ""),
                            "datetime": event_time.isoformat(),
                            "impact": "high",
                            "currency": event_data.get("currency", "")
                        })
            
            return events
            
        except Exception as e:
            # Fallback: return empty list if calendar API fails
            # This ensures the main analysis can continue
            print(f"Warning: Calendar API failed: {str(e)}")
            return []
    
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
        hours_ahead = (window_minutes * 2) / 60  # Convert to hours, search both directions
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
            List of events during session
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
    
    def format_event_for_driver(self, event: Dict[str, Any]) -> str:
        """
        Format event as a driver string for output.
        
        Args:
            event: Event dictionary
            
        Returns:
            Formatted driver string
            
        Example:
            "FOMC Interest Rate Decision scheduled during NY session"
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
        
        return f"{event_name} scheduled during {session}"


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