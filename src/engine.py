"""FX Volatility Intelligence Engine - Core logic."""
from __future__ import annotations

import logging
from typing import Optional

from src.config import DATA_CONFIG
from src.data_fetcher import DataFetcher, RangeCalculator
from src.models import VolatilityIntelligence
from src.session import detect_session, SessionInfo
from src.volatility import volatility_for_session

logger = logging.getLogger(__name__)

# Global data fetcher instance
_data_fetcher = DataFetcher()
_range_calculator = RangeCalculator()


def build_intel(
    pair: str,
    macro_events: Optional[list[str]] = None,
    debug: bool = False
) -> dict:
    """Generate volatility intelligence for an FX pair.
    
    Args:
        pair: Currency pair code (e.g., 'EURUSD')
        macro_events: Optional list of scheduled macro events
        debug: If True, include debug fields in response
        
    Returns:
        Dictionary matching VolatilityIntelligence schema
    """
    pair = pair.upper().strip()
    
    # Validate pair
    if len(pair) != 6 or not pair.isalpha():
        raise ValueError(f"Invalid pair: {pair}. Must be 6-letter code like EURUSD")
    
    logger.info(f"Building volatility intelligence for {pair}")
    
    # Detect current session
    session_name = detect_session()
    logger.debug(f"Current session: {session_name}")
    
    # Fetch market data
    data = _data_fetcher.fetch_data(pair)
    
    if data is None or data.empty:
        logger.warning(f"No data available for {pair}, using fallback values")
        return _build_fallback_intel(pair, session_name, macro_events)
    
    # Calculate ranges
    pip_multiplier = _range_calculator.get_pip_multiplier(pair)
    
    last_24h_price_range, _ = _range_calculator.calculate_24h_range(data)
    last_24h_range_pips = last_24h_price_range * pip_multiplier
    
    avg_range_price = _range_calculator.calculate_avg_range(data)
    avg_range_pips = avg_range_price * pip_multiplier
    
    compression_ratio = _range_calculator.calculate_compression_ratio(
        last_24h_price_range, avg_range_price
    )
    
    logger.debug(
        f"{pair}: 24h range={last_24h_range_pips:.1f} pips, "
        f"avg={avg_range_pips:.1f} pips, ratio={compression_ratio:.2f}"
    )
    
    # Calculate volatility expectation
    vol_data = volatility_for_session(
        session_name,
        compression_ratio=compression_ratio,
        macro_events=macro_events,
        historical_occurrences=150
    )
    
    # Build response
    intel = {
        "pair": pair,
        "session": session_name,
        "time_window_minutes": 90,
        "volatility_expectation": vol_data["volatility_expectation"],
        "expected_deviation_pips": vol_data["expected_deviation_pips"],
        "confidence": vol_data["confidence"],
        "drivers": vol_data["drivers"],
        "historical_context": vol_data["historical_context"],
        "agent_guidance": _get_agent_guidance(vol_data["volatility_expectation"]),
    }
    
    # Add debug fields if requested
    if debug:
        intel.update({
            "last_24h_range_pips": round(last_24h_range_pips, 1),
            "avg_7day_range_pips": round(avg_range_pips, 1),
            "compression_ratio": round(compression_ratio, 2),
        })
    
    logger.info(f"Intelligence generated: {vol_data['volatility_expectation']} confidence={vol_data['confidence']}")
    
    return intel


def _build_fallback_intel(
    pair: str,
    session_name: str,
    macro_events: Optional[list[str]] = None
) -> dict:
    """Build fallback intelligence when data is unavailable.
    
    Args:
        pair: Currency pair
        session_name: Current session
        macro_events: Optional macro events
        
    Returns:
        Fallback intelligence dictionary
    """
    # Use conservative fallback values
    vol_data = volatility_for_session(
        session_name,
        compression_ratio=1.0,
        macro_events=macro_events,
        historical_occurrences=150
    )
    
    return {
        "pair": pair,
        "session": session_name,
        "time_window_minutes": 90,
        "volatility_expectation": vol_data["volatility_expectation"],
        "expected_deviation_pips": vol_data["expected_deviation_pips"],
        "confidence": min(vol_data["confidence"], 0.5),  # Reduce confidence for fallback
        "drivers": vol_data["drivers"] + ["No real-time data available; using session baseline"],
        "historical_context": vol_data["historical_context"],
        "agent_guidance": _get_agent_guidance(vol_data["volatility_expectation"]),
    }


def _get_agent_guidance(expectation: str) -> str:
    """Generate strategy guidance for trading agents.
    
    Args:
        expectation: Volatility expectation level
        
    Returns:
        Strategy guidance string
    """
    guidance_map = {
        "Low": "Range compression suggests calmer conditions; consider mean reversion strategies with tight stops and reduced position sizing.",
        "Normal": "Normal range conditions; apply standard risk management and position sizing relative to average volatility.",
        "High": "Range expansion indicates elevated volatility; favor breakout strategies with wider stops and careful position management.",
    }
    return guidance_map.get(expectation, "Monitor conditions; use adaptive risk management.")
