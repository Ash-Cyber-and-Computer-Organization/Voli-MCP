"""
Output formatting utilities for forex analysis results.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


# Major forex pairs organized by category
FOREX_PAIRS = {
    "majors": [
        "EUR/USD",  # Euro / US Dollar
        "USD/JPY",  # US Dollar / Japanese Yen
        "GBP/USD",  # British Pound / US Dollar
        "USD/CHF",  # US Dollar / Swiss Franc
        "AUD/USD",  # Australian Dollar / US Dollar
        "USD/CAD",  # US Dollar / Canadian Dollar
        "NZD/USD",  # New Zealand Dollar / US Dollar
    ],
    "minors": [
        "EUR/GBP",  # Euro / British Pound
        "EUR/AUD",  # Euro / Australian Dollar
        "EUR/CAD",  # Euro / Canadian Dollar
        "EUR/CHF",  # Euro / Swiss Franc
        "GBP/JPY",  # British Pound / Japanese Yen
        "EUR/JPY",  # Euro / Japanese Yen
        "GBP/CHF",  # British Pound / Swiss Franc
        "AUD/JPY",  # Australian Dollar / Japanese Yen
        "NZD/JPY",  # New Zealand Dollar / Japanese Yen
        "CHF/JPY",  # Swiss Franc / Japanese Yen
    ],
    "exotics": [
        "USD/SGD",  # US Dollar / Singapore Dollar
        "USD/HKD",  # US Dollar / Hong Kong Dollar
        "USD/ZAR",  # US Dollar / South African Rand
        "USD/MXN",  # US Dollar / Mexican Peso
        "USD/TRY",  # US Dollar / Turkish Lira
        "EUR/TRY",  # Euro / Turkish Lira
        "GBP/ZAR",  # British Pound / South African Rand
    ]
}

# All pairs flattened
ALL_PAIRS = [pair for pairs in FOREX_PAIRS.values() for pair in pairs]

# Pip value definitions (standard = 0.0001, JPY pairs = 0.01)
PIP_VALUES = {
    "standard": 0.0001,  # Most pairs
    "jpy": 0.01,         # JPY pairs
}


def normalize_pair_format(pair: str) -> str:
    """
    Normalize forex pair format to API-compatible string.
    
    Args:
        pair: Pair in any format (EUR/USD, EURUSD, eur/usd)
        
    Returns:
        Normalized format (EURUSD)
        
    Examples:
        EUR/USD -> EURUSD
        eur-usd -> EURUSD
        gbp_jpy -> GBPJPY
    """
    # Remove common separators and convert to uppercase
    normalized = pair.upper().replace("/", "").replace("-", "").replace("_", "").replace(" ", "")
    
    # Validate length (should be 6 characters)
    if len(normalized) != 6:
        raise ValueError(f"Invalid pair format: {pair}. Expected 6-character currency pair.")
    
    return normalized


def display_pair_format(pair: str) -> str:
    """
    Convert API format to human-readable format.
    
    Args:
        pair: Pair in API format (EURUSD)
        
    Returns:
        Display format (EUR/USD)
    """
    normalized = normalize_pair_format(pair)
    return f"{normalized[:3]}/{normalized[3:]}"


def get_pip_value(pair: str) -> float:
    """
    Get pip value for a given currency pair.
    
    Args:
        pair: Currency pair (any format)
        
    Returns:
        Pip value (0.0001 for most, 0.01 for JPY pairs)
    """
    normalized = normalize_pair_format(pair)
    
    # Check if JPY is quote currency (last 3 chars)
    if normalized.endswith("JPY"):
        return PIP_VALUES["jpy"]
    
    return PIP_VALUES["standard"]


def price_to_pips(price_difference: float, pair: str) -> float:
    """
    Convert price difference to pips.
    
    Args:
        price_difference: Absolute price difference
        pair: Currency pair
        
    Returns:
        Difference in pips
    """
    pip_value = get_pip_value(pair)
    return round(price_difference / pip_value, 1)


def pips_to_price(pips: float, pair: str) -> float:
    """
    Convert pips to price difference.
    
    Args:
        pips: Number of pips
        pair: Currency pair
        
    Returns:
        Price difference
    """
    pip_value = get_pip_value(pair)
    return pips * pip_value


def classify_volatility(expected_pips: float, pair: str, session: str) -> str:
    """
    Classify volatility level based on expected pip movement.
    
    Args:
        expected_pips: Expected deviation in pips
        pair: Currency pair
        session: Trading session
        
    Returns:
        "Low", "Medium", or "High"
    """
    # Baseline thresholds (adjust for JPY pairs)
    normalized = normalize_pair_format(pair)
    
    if normalized.endswith("JPY"):
        # JPY pairs are more volatile in pip terms
        low_threshold = 25
        high_threshold = 60
    else:
        low_threshold = 15
        high_threshold = 35
    
    # Session adjustments
    session_multipliers = {
        "asian": 0.7,      # Lower volatility
        "london": 1.2,     # Higher volatility
        "ny": 1.1,         # Slightly higher
    }
    
    multiplier = session_multipliers.get(session.lower(), 1.0)
    adjusted_low = low_threshold * multiplier
    adjusted_high = high_threshold * multiplier
    
    if expected_pips < adjusted_low:
        return "Low"
    elif expected_pips < adjusted_high:
        return "Medium"
    else:
        return "High"


def generate_agent_guidance(
    volatility_expectation: str,
    confidence: float,
    has_high_impact_event: bool,
    session_range_vs_avg: float
) -> str:
    """
    Generate trading strategy guidance based on conditions.
    
    Args:
        volatility_expectation: "Low", "Medium", "High", or "None"
        confidence: Confidence score (0-1)
        has_high_impact_event: Whether high-impact event is scheduled
        session_range_vs_avg: Current pre-session vs 30-day avg ratio
        
    Returns:
        Strategy guidance string
    """
    # Treat "Medium" as "Normal" for guidance logic
    volatility_key = "Normal" if volatility_expectation == "Medium" else volatility_expectation
    
    if volatility_key == "High" and confidence > 0.60:
        if has_high_impact_event:
            return (
                "High-impact event imminent. Avoid pre-positioning; "
                "wait for post-release momentum confirmation before entry."
            )
        return (
            "Session expansion likely based on compression + historical pattern. "
            "Favor breakout setups with wider stops."
        )
    elif volatility_key == "Low" and confidence > 0.60:
        return (
            "Compression regime expected. Mean-reversion and range-bound strategies "
            "favored; keep targets tight."
        )
    elif volatility_key == "Normal":
        return (
            "Standard session volatility expected. No directional bias from volatility "
            "structure; apply your base strategy."
        )
    else:
        if confidence < 0.35:
            return "Insufficient signal confluence. Reduce position size and wait for session open confirmation."
        # If confidence is higher but volatility is unclear, avoid the generic fallback
        if session_range_vs_avg < 0.8:
            return (
                "Pre-session compression present but signal strength is mixed. "
                "Favor smaller size and wait for early-session confirmation."
            )
        return (
            "Signal alignment is moderate without a clear volatility bias. "
            "Wait for early-session structure before committing size."
        )


def format_session_output(
    pair: str,
    session: str,
    time_window_minutes: int,
    expected_deviation_pips: float,
    confidence: float,
    drivers: List[str],
    historical_context: Dict[str, Any],
    macro_events: Optional[List[Dict[str, Any]]] = None,
    primary_macro_event: Optional[Dict[str, Any]] = None,
    volatility_level: Optional[str] = None,
    agent_guidance: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format complete analysis output in the required JSON structure.
    
    Args:
        pair: Currency pair
        session: Session name
        time_window_minutes: Analysis window length
        expected_deviation_pips: Expected movement in pips
        confidence: Confidence score (0-1)
        drivers: List of market driver strings
        historical_context: Dict with occurrences and expansion_rate
        volatility_level: Optional pre-calculated volatility classification
        agent_guidance: Optional pre-generated guidance
        
    Returns:
        Formatted output dictionary
    """
    # Auto-generate missing fields
    if volatility_level is None:
        volatility_level = classify_volatility(expected_deviation_pips, pair, session)
    
    if agent_guidance is None:
        # Infer event/compression from drivers if not explicitly passed
        has_event = "event" in " ".join(drivers).lower() or "speech" in " ".join(drivers).lower()
        is_compressed = "compressed" in " ".join(drivers).lower()
        session_range_vs_avg = 0.7 if is_compressed else 1.0
        agent_guidance = generate_agent_guidance(
            volatility_expectation=volatility_level,
            confidence=confidence,
            has_high_impact_event=has_event,
            session_range_vs_avg=session_range_vs_avg
        )
    
    return {
        "pair": display_pair_format(pair),
        "session": session,
        "time_window_minutes": time_window_minutes,
        "volatility_expectation": volatility_level,
        "expected_deviation_pips": round(expected_deviation_pips, 1),
        "confidence": round(confidence, 2),
        "drivers": drivers,
        "historical_context": {
            "similar_conditions_occurrences": historical_context.get("similar_conditions_occurrences", 0),
            "expansion_rate": round(historical_context.get("expansion_rate", 0.0), 2)
        },
        "macro_events": macro_events or [],
        "primary_macro_event": primary_macro_event,
        "agent_guidance": agent_guidance
    }


def validate_pair(pair: str) -> bool:
    """
    Check if pair is in supported list.
    
    Args:
        pair: Currency pair in any format
        
    Returns:
        True if supported
    """
    try:
        normalized = normalize_pair_format(pair)
        display = display_pair_format(normalized)
        return display in ALL_PAIRS
    except ValueError:
        return False


def get_supported_pairs() -> Dict[str, List[str]]:
    """
    Get all supported forex pairs organized by category.
    
    Returns:
        Dict with majors, minors, and exotics lists
    """
    return FOREX_PAIRS.copy()
