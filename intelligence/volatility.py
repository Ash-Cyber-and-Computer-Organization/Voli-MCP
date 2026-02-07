from __future__ import annotations


def volatility_for_session(session: str) -> dict:
    if session == "London":
        return {
            "volatility_expectation": "Elevated",
            "confidence": 0.65,
            "drivers": ["London session volatility expansion tendency"],
        }
    if session == "NewYork":
        return {
            "volatility_expectation": "High",
            "confidence": 0.7,
            "drivers": ["New York session liquidity and macro overlap"],
        }
    return {
        "volatility_expectation": "Normal",
        "confidence": 0.5,
        "drivers": ["No major session catalysts"],
    }
