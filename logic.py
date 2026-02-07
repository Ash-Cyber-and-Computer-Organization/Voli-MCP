def session_volatility_intel(pair):
    session = detect_session()
    compression = check_range_compression(pair)

    if session == "London" and compression:
        expectation = "High"
        confidence = 0.68
        drivers = ["Asian range compression", "London volatility expansion tendency"]
    else:
        expectation = "Normal"
        confidence = 0.52
        drivers = ["No abnormal volatility signals detected"]

    return {
        "pair": pair,
        "session": session,
        "volatility_expectation": expectation,
        "confidence": confidence,
        "drivers": drivers,
        "agent_guidance": "Favor confirmation-based entries."
    }
#potential logic 