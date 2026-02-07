from __future__ import annotations

from src.session import detect_session
from src.volatility import volatility_for_session


def build_intel(pair: str) -> dict:
    session = detect_session()
    vol = volatility_for_session(session)

    if session == "London Open":
        guidance = "Avoid mean-reversion strategies; favor breakout or momentum confirmation setups."
    elif session == "New York Open":
        guidance = "High event sensitivity; favor smaller size and clear invalidation levels."
    elif session == "Asian session":
        guidance = "Range conditions are common; prioritize mean reversion setups."
    else:
        guidance = "Liquidity is thinner; avoid forcing trades and wait for session overlap."

    return {
        "pair": pair,
        "session": session,
        "time_window_minutes": 90,
        "volatility_expectation": vol["volatility_expectation"],
        "expected_deviation_pips": vol["expected_deviation_pips"],
        "confidence": vol["confidence"],
        "drivers": vol["drivers"],
        "historical_context": vol["historical_context"],
        "agent_guidance": guidance,
    }
