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
    drivers = [
        f"Range compression detected ({last_24h_range_pips} vs {avg_7day_range_pips} pips baseline)"
    ]

    # Add session-specific drivers if any
    if session == "London Open":
        drivers.append("ECB speech scheduled during NY overlap")
        drivers.append("Pre-London positioning historically precedes volatility expansion on ECB days")
    elif session == "New York Open":
        drivers.append("New York session liquidity and macro overlap")
    # Asian and Off-session use default

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
