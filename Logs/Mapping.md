 For demo and unit-test purposes, implement an engine path `engine.generate_from_hypothesis(hypothesis_dict)` which accepts a precomputed hypothesis object:
```py
hypothesis = {
  "pair":"EURUSD",
  "session":"London Open",
  "time_window_minutes":90,
  "asian_range_pips":18,
  "avg_30d_range_pips":32,
  "event":"ECB",
  "event_overlap":"NY",
  "historical": {"similar_conditions_occurrences":112, "expansion_rate":0.62}
}
```
- `generate_from_hypothesis` will deterministically produce the exact sample JSON. Use this for demos and for asserting billing justification.

