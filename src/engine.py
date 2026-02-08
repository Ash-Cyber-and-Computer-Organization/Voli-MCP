from __future__ import annotations

from src.session import detect_session
from src.volatility import volatility_for_session


def build_intel(pair: str) -> dict:
    session = detect_session()

    # Dynamic metrics (in real system, fetch from data)
    last_24h_range_pips = 45
    avg_7day_range_pips = 52
    compression_ratio = last_24h_range_pips / avg_7day_range_pips

    # Determine volatility expectation based on compression ratio
    if compression_ratio < 0.75:
        volatility_expectation = "Low"
        expected_deviation_pips = 20
        confidence = 0.6
        guidance = "Range compression suggests calmer conditions; consider mean reversion or tight stops."
    elif compression_ratio > 1.25:
        volatility_expectation = "High"
        expected_deviation_pips = 50
        confidence = 0.8
        guidance = "Range expansion indicates higher volatility; favor breakout strategies and wider stops."
    else:
        volatility_expectation = "Normal"
        expected_deviation_pips = 35
        confidence = 0.7
        guidance = "Normal range conditions; standard risk management applies."

    # Generate drivers from conditions
    if compression_ratio < 0.75:
        range_driver = f"Range compression detected ({last_24h_range_pips} vs {avg_7day_range_pips} pips baseline)"
    elif compression_ratio > 1.25:
        range_driver = f"Range expansion detected ({last_24h_range_pips} vs {avg_7day_range_pips} pips baseline)"
    else:
        range_driver = f"Range behavior within normal volatility bounds ({last_24h_range_pips} vs {avg_7day_range_pips} pips baseline)"

    drivers = [range_driver]

    # Add session-specific drivers (generic, not event-based)
    if session == "London Open":
        drivers.append("London session historically increases participation and volatility")
    elif session == "New York Open":
        drivers.append("New York session brings high liquidity and macro event sensitivity")
    elif session == "Asian session":
        drivers.append("Asian session typically shows range-bound conditions")
    elif session == "Off-session":
        drivers.append("Off-session hours have thinner liquidity")

    # Historical context (placeholder)
    historical_context = {
        "similar_conditions_occurrences": 150,
        "expansion_rate": 0.5
    }

    return {
        "pair": pair,
        "session": session,
        "time_window_minutes": 90,
        "volatility_expectation": volatility_expectation,
        "expected_deviation_pips": expected_deviation_pips,
        "confidence": confidence,
        "drivers": drivers,
        "historical_context": historical_context,
        "agent_guidance": guidance,
        "last_24h_range_pips": last_24h_range_pips,
        "avg_7day_range_pips": avg_7day_range_pips,
        "compression_ratio": round(compression_ratio, 2),
    }
