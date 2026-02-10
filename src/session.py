"""Trading session detection and analysis."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from src.config import SESSION_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class SessionInfo:
    """Information about the current trading session."""
    
    name: str  # e.g., "Asian", "London", "New York"
    is_overlap: bool = False  # True if multiple sessions are active
    overlap_with: str | None = None  # Secondary session during overlap
    hour_utc: int = 0  # Current hour in UTC
    session_progress: float = 0.0  # Progress through session (0-1)


def detect_session(now_utc: datetime | None = None) -> str:
    """Detect current trading session.
    
    Args:
        now_utc: Optional specific UTC datetime (defaults to now)
        
    Returns:
        Session name as string
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    hour = now_utc.hour
    
    config = SESSION_CONFIG
    
    if config.asian_start <= hour <= config.asian_end:
        return "Asian"
    if config.london_start <= hour <= config.london_end:
        return "London"
    if config.newyork_start <= hour <= config.newyork_end:
        return "New York"
    return "Off-session"


def detect_session_detailed(now_utc: datetime | None = None) -> SessionInfo:
    """Detect session with detailed information including overlaps.
    
    Args:
        now_utc: Optional specific UTC datetime (defaults to now)
        
    Returns:
        SessionInfo with session details
    """
    now_utc = now_utc or datetime.now(timezone.utc)
    hour = now_utc.hour
    minute = now_utc.minute
    
    config = SESSION_CONFIG
    
    # Check for overlaps (e.g., London-NY overlap at 13:00-12:59 UTC is actually 12:00-17:00 London, 8:00-13:00 NY)
    # Simplified: London 7-12, NY 13-17, overlap none in this config
    # But in reality there's overlap at specific times
    
    if config.asian_start <= hour <= config.asian_end:
        progress = (hour - config.asian_start) / (config.asian_end - config.asian_start)
        return SessionInfo(
            name="Asian",
            hour_utc=hour,
            session_progress=max(0, min(1, progress))
        )
    elif config.london_start <= hour <= config.london_end:
        progress = (hour - config.london_start) / (config.london_end - config.london_start)
        return SessionInfo(
            name="London",
            hour_utc=hour,
            session_progress=max(0, min(1, progress))
        )
    elif config.newyork_start <= hour <= config.newyork_end:
        progress = (hour - config.newyork_start) / (config.newyork_end - config.newyork_start)
        return SessionInfo(
            name="New York",
            hour_utc=hour,
            session_progress=max(0, min(1, progress))
        )
    else:
        return SessionInfo(
            name="Off-session",
            hour_utc=hour,
            session_progress=0.0
        )


def is_high_impact_session(session: str) -> bool:
    """Check if session typically has high volatility.
    
    Args:
        session: Session name
        
    Returns:
        Boolean indicating if session typically generates high activity
    """
    high_impact = {"London", "New York"}
    return any(s in session for s in high_impact)
