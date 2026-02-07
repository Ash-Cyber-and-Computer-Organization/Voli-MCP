from __future__ import annotations

from intelligence.session import detect_session
from intelligence.volatility import volatility_for_session


def build_intel(pair: str) -> dict:
    session = detect_session()
    vol = volatility_for_session(session)

    if session == "London":
        guidance = "Expect faster intraday swings; focus on tight risk controls and liquid windows."
    elif session == "NewYork":
        guidance = "High event sensitivity; favor smaller size and clear invalidation levels."
    elif session == "Asia":
        guidance = "Range conditions are common; prioritize mean reversion setups."
    else:
        guidance = "Liquidity is thinner; avoid forcing trades and wait for session overlap."

    return {
        "pair": pair,
        "session": session,
        "volatility_expectation": vol["volatility_expectation"],
        "confidence": vol["confidence"],
        "drivers": vol["drivers"],
        "agent_guidance": guidance,
    }
