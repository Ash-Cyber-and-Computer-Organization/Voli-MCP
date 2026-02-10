"""Volatility intelligence and expectation calculation."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from src.config import VOLATILITY_THRESHOLDS
from src.session import SessionInfo, is_high_impact_session

logger = logging.getLogger(__name__)


@dataclass
class VolatilityFactors:
    """Factors influencing volatility expectation."""
    
    compression_ratio: float  # < 0.75 = Low, > 1.25 = High
    session_impact: float  # Session multiplier (0.8-1.3)
    macro_event_impact: float  # Event multiplier (1.0-1.5)
    liquidity_score: float  # 0-1, higher = better liquidity


def classify_volatility_expectation(compression_ratio: float) -> str:
    """Classify volatility based on range compression.
    
    Args:
        compression_ratio: Ratio of current range to historical average
        
    Returns:
        Volatility classification ("Low", "Normal", or "High")
    """
    thresholds = VOLATILITY_THRESHOLDS
    
    if compression_ratio < thresholds.low_compression:
        return "Low"
    elif compression_ratio > thresholds.high_expansion:
        return "High"
    return "Normal"


def get_confidence_for_expectation(
    expectation: str,
    compression_ratio: float,
    sample_size: int = 150
) -> float:
    """Calculate confidence score for volatility expectation.
    
    Args:
        expectation: Volatility classification
        compression_ratio: Current range compression ratio
        sample_size: Number of historical occurrences
        
    Returns:
        Confidence score (0.0-1.0)
    """
    # More extreme compression = higher confidence
    extremeness = abs(compression_ratio - 1.0)
    extremeness_score = min(extremeness / 0.5, 1.0)  # Cap at 1.0
    
    # More samples = higher confidence (diminishing returns)
    sample_confidence = min(sample_size / 200, 0.3)
    
    base_confidence = {
        "Low": 0.65,
        "Normal": 0.70,
        "High": 0.75
    }[expectation]
    
    confidence = base_confidence + (extremeness_score * 0.15) + sample_confidence
    return min(confidence, 0.99)  # Cap at 0.99


def get_session_volatility_multiplier(session_info: SessionInfo) -> tuple[float, str]:
    """Get volatility multiplier based on session.
    
    Args:
        session_info: SessionInfo object with current session details
        
    Returns:
        Tuple of (multiplier, driver_reason)
    """
    session_name = session_info.name
    
    multipliers = {
        "Asian": (0.85, "Asian session typically has lower volatility"),
        "London": (1.20, "London session historically increases participation and volatility"),
        "New York": (1.25, "New York session brings high liquidity and macro event sensitivity"),
        "Off-session": (0.70, "Off-session hours have thinner liquidity"),
    }
    
    multiplier, reason = multipliers.get(session_name, (1.0, "Normal session conditions"))
    return multiplier, reason


def get_macro_event_impact(events: list[str] | None) -> tuple[float, list[str]]:
    """Calculate impact of macro events on volatility.
    
    Args:
        events: List of macro events (e.g., ['ECB Rate Decision', 'US NFP'])
        
    Returns:
        Tuple of (impact_multiplier, driver_reasons)
    """
    if not events:
        return 1.0, []
    
    # Impact scores for common events
    event_impacts = {
        "ECB Rate Decision": 1.35,
        "Fed Decision": 1.40,
        "US NFP": 1.50,
        "US CPI": 1.35,
        "Eurozone GDP": 1.25,
        "UK Inflation": 1.30,
        "BoE Rate Decision": 1.35,
        "RBA Decision": 1.30,
    }
    
    drivers = []
    max_impact = 1.0
    
    for event in events:
        impact = event_impacts.get(event, 1.20)  # Default impact for unlisted events
        if impact > max_impact:
            max_impact = impact
            drivers.append(f"Macro event: {event} scheduled during window")
    
    return max_impact, drivers


def volatility_for_session(
    session_name: str,
    compression_ratio: float = 1.0,
    macro_events: list[str] | None = None,
    historical_occurrences: int = 150
) -> dict:
    """Calculate volatility expectation for a session.
    
    Args:
        session_name: Name of trading session
        compression_ratio: Range compression ratio vs historical
        macro_events: List of scheduled macro events
        historical_occurrences: Number of similar historical occurrences
        
    Returns:
        Dictionary with volatility intelligence
    """
    # Classify base expectation
    expectation = classify_volatility_expectation(compression_ratio)
    
    # Session impact
    session_info = SessionInfo(name=session_name)
    session_mult, session_reason = get_session_volatility_multiplier(session_info)
    
    # Macro event impact
    macro_mult, macro_reasons = get_macro_event_impact(macro_events)
    
    # Calculate final deviation
    base_deviation = {
        "Low": 20,
        "Normal": 35,
        "High": 50
    }[expectation]
    
    final_deviation = int(base_deviation * session_mult * macro_mult)
    
    # Confidence calculation
    confidence = get_confidence_for_expectation(expectation, compression_ratio, historical_occurrences)
    
    # Build drivers
    drivers = []
    
    # Range compression driver
    if compression_ratio < 0.75:
        drivers.append(f"Range compression detected (compression ratio: {compression_ratio:.2f})")
    elif compression_ratio > 1.25:
        drivers.append(f"Range expansion detected (expansion ratio: {compression_ratio:.2f})")
    else:
        drivers.append(f"Range behavior within normal bounds (ratio: {compression_ratio:.2f})")
    
    # Session driver
    drivers.append(session_reason)
    
    # Macro drivers
    drivers.extend(macro_reasons)
    
    return {
        "volatility_expectation": expectation,
        "confidence": round(confidence, 2),
        "expected_deviation_pips": final_deviation,
        "drivers": drivers,
        "historical_context": {
            "similar_conditions_occurrences": historical_occurrences,
            "expansion_rate": min(compression_ratio * 0.5 + 0.25, 1.0)  # Estimates expansion likelihood
        }
    }
