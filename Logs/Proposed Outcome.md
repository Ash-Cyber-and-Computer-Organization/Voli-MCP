```json
{
  "pair": "EURUSD", #python code to return the pair (is it a single or multiple pair system)
  "session": "London Open",
  "time_window_minutes": 90,
  "volatility_expectation": "High",(find algo for forex volaitity)
  "expected_deviation_pips": 38, (is this predictablity/slipage)
  "confidence": 0.74, (possibiltiy of indicators in a line)
  "drivers": [   #make more research
    "Asian session range compressed (18 pips vs 30-day avg of 32)",
    "ECB speech scheduled during NY overlap",
    "Pre-London positioning historically precedes volatility expansion on ECB days"
  ],
  "historical_context": {
    "similar_conditions_occurrences": 112,
    "expansion_rate": 0.62
  },
  "agent_guidance": "Avoid mean-reversion strategies; favor breakout or momentum confirmation setups.
  # Important
}