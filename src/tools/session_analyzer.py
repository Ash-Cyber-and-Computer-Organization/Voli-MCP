"""
Main tool for forex session volatility analysis.
Orchestrates all components to produce final output.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

import pytz

from utils.sessions import (
    get_current_session,
    get_next_session,
    get_session_info,
    is_weekend,
    SESSIONS
)
from utils.formatters import (
    normalize_pair_format,
    display_pair_format,
    validate_pair,
    format_session_output,
    classify_volatility,
    generate_agent_guidance
)
from data.twelve_data_client import get_client
from data.calendar_client import get_calendar_client
from data.historical_store import HistoricalStore
from data.range_cache import get_cached_range, set_cached_range
from analysis.range_calculator import RangeCalculator
from analysis.pattern_matcher import PatternMatcher
from analysis.confidence_scorer import ConfidenceScorer


class SessionAnalyzer:
    """Main analyzer for forex session volatility predictions."""

    def __init__(self):
        """Initialize session analyzer with all required clients."""
        self.data_client = get_client()
        self.calendar_client = get_calendar_client()
        self.confidence_scorer = ConfidenceScorer()
        self.history_store = HistoricalStore()

    async def analyze_forex_session(
        self,
        pair: str,
        target_session: str = "auto"
    ) -> Dict[str, Any]:
        if not validate_pair(pair):
            raise ValueError(
                f"Unsupported pair: {pair}. "
                f"Use EUR/USD, GBP/USD, USD/JPY, etc."
            )

        normalized_pair = normalize_pair_format(pair)
        display_pair = display_pair_format(normalized_pair)

        if is_weekend():
            return self._weekend_response(display_pair)

        # Determine target session
        if target_session.lower() == "auto":
            current_session = get_current_session()
            if current_session != "closed":
                session_key = current_session
            else:
                session_key, _ = get_next_session()
        else:
            session_key = target_session.lower()
            if session_key not in SESSIONS:
                raise ValueError(
                    f"Invalid session: {target_session}. "
                    f"Must be 'asian', 'london', 'ny', or 'auto'"
                )

        session_info = get_session_info(session_key)
        session_name = session_info["name"]
        session_start = session_info["start"]

        range_calc = RangeCalculator(normalized_pair)
        pattern_matcher = PatternMatcher(normalized_pair)

        # Step 1: Fetch current intraday data (async, non-blocking)
        intraday_df = None
        try:
            intraday_df = await self.data_client.get_intraday_data(
                normalized_pair,
                interval="5min",
                outputsize=500
            )
        except Exception:
            intraday_df = None

        # Step 2: Calculate pre-session range from live feed
        current_pre_range = 0.0
        if intraday_df is not None and not intraday_df.empty:
            current_pre_range = range_calc.calculate_pre_session_range(
                intraday_df,
                session_start,
                minutes_before=90
            )

        # Step 3: Get 30-day averages from history store
        averages = self.history_store.get_recent_averages(
            normalized_pair,
            session_key,
            days=30
        )
        avg_pre_range = averages.get("avg_pre_range", 0.0)
        avg_session_range = averages.get("avg_session_range", 0.0)

        # Step 4: Fallback if history is missing
        if avg_pre_range <= 0:
            avg_pre_range = 25.0 if not normalized_pair.endswith("JPY") else 35.0
        if avg_session_range <= 0:
            avg_session_range = max(avg_pre_range * 2.0, 30.0)

        # Step 5: Fallback if live feed failed (never return 0)
        if current_pre_range <= 0:
            cached = get_cached_range(normalized_pair, session_key)
            if cached and cached > 0:
                current_pre_range = cached
            else:
                latest = self.history_store.get_latest_pre_range(normalized_pair, session_key)
                if latest and latest > 0:
                    current_pre_range = latest
                else:
                    current_pre_range = max(avg_pre_range * 0.8, 10.0)

        # Update cache with latest ranges
        if current_pre_range > 0:
            set_cached_range(
                normalized_pair,
                session_key,
                current_pre_range,
                avg_pre_range,
                avg_session_range
            )

        # Step 6: Detect compression
        is_compressed, compression_ratio = range_calc.detect_compression(
            current_pre_range,
            avg_pre_range,
            threshold=0.70
        )

        # Step 7: Check for economic events within +/- 4 hours of now
        try:
            events = self.calendar_client.get_pair_events(
                normalized_pair,
                window_hours=4
            )
        except Exception:
            events = []

        has_event = len(events) > 0
        event_type = events[0].get("event_type") if events else None
        macro_events = self._build_macro_events(events)
        primary_macro_event = macro_events[0] if macro_events else None

        # Step 8: Find similar historical patterns from store
        pattern_results = pattern_matcher.find_similar_conditions(
            store=self.history_store,
            session_key=session_key,
            event_type=event_type,
            current_pre_range=current_pre_range,
            avg_pre_range=avg_pre_range,
            threshold=0.30
        )

        # Step 9: Calculate expected deviation
        expected_deviation = range_calc.calculate_expected_deviation(
            current_pre_range,
            avg_pre_range,
            pattern_results["expansion_rate"],
            avg_session_range
        )

        # Step 10: Calculate confidence score
        confidence = self.confidence_scorer.calculate_confidence(
            breakout_occurrences=pattern_results.get("breakout_occurrences", 0),
            total_occurrences=pattern_results.get("similar_conditions_occurrences", 0)
        )

        # Step 11: Generate market drivers
        drivers = self._generate_drivers(
            current_pre_range,
            avg_pre_range,
            compression_ratio,
            is_compressed,
            events,
            pattern_results,
            event_type
        )

        # Step 12: Classify volatility
        volatility_level = classify_volatility(
            expected_deviation,
            normalized_pair,
            session_key
        )

        # Step 13: Generate agent guidance
        session_range_vs_avg = current_pre_range / avg_pre_range if avg_pre_range > 0 else 1.0
        agent_guidance = generate_agent_guidance(
            volatility_expectation=volatility_level,
            confidence=confidence,
            has_high_impact_event=has_event,
            session_range_vs_avg=session_range_vs_avg
        )

        # Step 14: Format and return output
        return format_session_output(
            pair=normalized_pair,
            session=session_name,
            time_window_minutes=90,
            expected_deviation_pips=expected_deviation,
            confidence=confidence,
            drivers=drivers,
            historical_context={
                "similar_conditions_occurrences": pattern_results["similar_conditions_occurrences"],
                "expansion_rate": pattern_results["expansion_rate"]
            },
            macro_events=macro_events,
            primary_macro_event=primary_macro_event,
            volatility_level=volatility_level,
            agent_guidance=agent_guidance
        )

    def _generate_drivers(
        self,
        current_pre_range: float,
        avg_pre_range: float,
        compression_ratio: float,
        is_compressed: bool,
        events: List[Dict[str, Any]],
        pattern_results: Dict,
        event_type: Optional[str]
    ) -> list[str]:
        drivers = []

        if is_compressed:
            drivers.append(
                f"Pre-session range compressed ({current_pre_range:.0f} pips vs "
                f"30-day avg of {avg_pre_range:.0f} pips)"
            )
        else:
            drivers.append(
                f"Pre-session range at {current_pre_range:.0f} pips "
                f"({compression_ratio:.0%} of 30-day avg)"
            )

        for event in events[:2]:
            drivers.append(self.calendar_client.format_event_for_driver(event))

        expansion_rate = pattern_results["expansion_rate"]
        occurrences = pattern_results["similar_conditions_occurrences"]

        if is_compressed and expansion_rate > 0.6:
            if event_type:
                drivers.append(
                    f"Pre-session compression on {event_type} days historically precedes "
                    f"{int(expansion_rate * 100)}% breakout rate ({occurrences} occurrences)"
                )
            else:
                drivers.append(
                    f"Pre-session compression historically precedes volatility expansion "
                    f"(observed in {int(expansion_rate * 100)}% of {occurrences} similar days)"
                )
        elif expansion_rate < 0.4:
            drivers.append(
                f"Similar conditions historically resulted in range-bound action "
                f"({occurrences} historical occurrences)"
            )
        else:
            drivers.append(
                f"Historical data shows mixed outcomes for similar conditions "
                f"({occurrences} comparable days)"
            )

        return drivers

    def _weekend_response(self, pair: str) -> Dict[str, Any]:
        return {
            "pair": pair,
            "session": "Market Closed",
            "time_window_minutes": 0,
            "volatility_expectation": "None",
            "expected_deviation_pips": 0,
            "confidence": 0,
            "drivers": [
                "Forex market closed for weekend",
                "Market reopens Sunday 22:00 UTC"
            ],
            "historical_context": {
                "similar_conditions_occurrences": 0,
                "expansion_rate": 0
            },
            "macro_events": [],
            "primary_macro_event": None,
            "agent_guidance": "Wait for market open. Review weekly levels and news during closure."
        }

    def _build_macro_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        structured_events: List[Dict[str, Any]] = []
        now = self.calendar_client.now_utc()

        for event in events:
            event_name = event.get("event")
            event_type = event.get("event_type")
            event_datetime = event.get("datetime")
            if not event_name or not event_datetime:
                continue

            try:
                event_dt = datetime.fromisoformat(event_datetime)
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=pytz.UTC)
                minutes_until = int((event_dt - now).total_seconds() / 60)
            except Exception:
                minutes_until = None

            structured_events.append(
                {
                    "name": event_name,
                    "event_type": event_type,
                    "currency": event.get("currency"),
                    "country": event.get("country"),
                    "impact": event.get("impact", "high"),
                    "datetime": event_datetime,
                    "minutes_until": minutes_until,
                    "source": event.get("source"),
                }
            )

        return structured_events


async def analyze_forex_session(pair: str, target_session: str = "auto") -> Dict[str, Any]:
    analyzer = SessionAnalyzer()
    return await analyzer.analyze_forex_session(pair, target_session)
