"""
Historical pattern matching for similar market conditions.
Uses pre-computed daily session ranges from the history store.
"""

import numpy as np
from typing import Dict, Any, Optional


class PatternMatcher:
    """Match current conditions against historical patterns."""

    def __init__(self, pair: str):
        self.pair = pair

    def find_similar_conditions(
        self,
        store: Any,
        session_key: str,
        event_type: Optional[str],
        current_pre_range: float,
        avg_pre_range: float,
        threshold: float = 0.30
    ) -> Dict[str, Any]:
        """
        Find historical days with similar compression using the SQLite store.
        Matches on session + event type (or absence) + compression ratio within +/- threshold.
        """
        if avg_pre_range <= 0 or current_pre_range <= 0:
            return {
                "similar_conditions_occurrences": 0,
                "breakout_occurrences": 0,
                "expansion_rate": 0.5,
                "avg_expansion_pips": 0.0,
                "matched_dates": []
            }

        compression_ratio = current_pre_range / avg_pre_range
        rows = store.get_comparable_conditions(
            pair=self.pair,
            session=session_key,
            event_type=event_type,
            compression_ratio=compression_ratio,
            tolerance=threshold
        )

        # If event-specific sample is too small, broaden to any event presence
        if event_type and len(rows) < 80:
            rows = store.get_comparable_conditions(
                pair=self.pair,
                session=session_key,
                event_type="ANY",
                compression_ratio=compression_ratio,
                tolerance=threshold
            )

        # If still too small, allow non-event days as fallback
        if len(rows) < 80:
            rows = store.get_comparable_conditions(
                pair=self.pair,
                session=session_key,
                event_type=None,
                compression_ratio=compression_ratio,
                tolerance=threshold
            )

        if not rows:
            return {
                "similar_conditions_occurrences": 0,
                "breakout_occurrences": 0,
                "expansion_rate": 0.5,
                "avg_expansion_pips": 0.0,
                "matched_dates": []
            }

        session_multipliers = {
            "asian": 1.4,
            "london": 1.35,
            "ny": 1.38
        }
        expansion_multiplier = session_multipliers.get(session_key, 1.35)
        expansion_count = sum(
            1 for r in rows if r.session_range_pips > (r.pre_range_pips * expansion_multiplier)
        )
        expansion_rate = expansion_count / len(rows)

        # If event-specific sample shows extreme rate, broaden to any event days
        if event_type and len(rows) >= 80 and expansion_rate > 0.8:
            rows = store.get_comparable_conditions(
                pair=self.pair,
                session=session_key,
                event_type="ANY",
                compression_ratio=compression_ratio,
                tolerance=threshold
            )
            expansion_count = sum(
                1 for r in rows if r.session_range_pips > (r.pre_range_pips * expansion_multiplier)
            )
            expansion_rate = expansion_count / len(rows)
        avg_expansion = np.mean([r.session_range_pips - r.pre_range_pips for r in rows])

        return {
            "similar_conditions_occurrences": len(rows),
            "breakout_occurrences": expansion_count,
            "expansion_rate": round(expansion_rate, 2),
            "avg_expansion_pips": round(float(avg_expansion), 1),
            "matched_dates": [r.date for r in rows[:10]]
        }
