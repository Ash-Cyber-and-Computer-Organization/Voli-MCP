"""
Main tool for forex session volatility analysis.
Orchestrates all components to produce final output.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pytz

from src.utils.sessions import (
    get_current_session,
    get_next_session,
    get_session_info,
    is_weekend,
    SESSIONS
)
from src.utils.formatters import (
    normalize_pair_format,
    display_pair_format,
    validate_pair,
    format_session_output,
    classify_volatility,
    generate_agent_guidance
)
from src.data.twelve_data_client import get_client
from src.data.calendar_client import get_calendar_client
from src.analysis.range_calculator import RangeCalculator
from src.analysis.pattern_matcher import PatternMatcher
from src.analysis.confidence_scorer import ConfidenceScorer


class SessionAnalyzer:
    """Main analyzer for forex session volatility predictions."""
    
    def __init__(self):
        """Initialize session analyzer with all required clients."""
        self.data_client = get_client()
        self.calendar_client = get_calendar_client()
        self.confidence_scorer = ConfidenceScorer()
    
    def analyze_forex_session(
        self,
        pair: str,
        target_session: str = "auto"
    ) -> Dict[str, Any]:
        """
        Analyze forex session volatility and generate trading guidance.
        
        Args:
            pair: Currency pair (e.g., "EUR/USD", "EURUSD")
            target_session: "asian", "london", "ny", or "auto" for next session
            
        Returns:
            Complete analysis output matching the required JSON schema
            
        Raises:
            ValueError: If pair is invalid or session not recognized
        """
        # Validate inputs
        if not validate_pair(pair):
            raise ValueError(
                f"Unsupported pair: {pair}. "
                f"Use EUR/USD, GBP/USD, USD/JPY, etc."
            )
        
        normalized_pair = normalize_pair_format(pair)
        display_pair = display_pair_format(normalized_pair)
        
        # Check if market is open
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
        
        # Initialize analyzers
        range_calc = RangeCalculator(normalized_pair)
        pattern_matcher = PatternMatcher(normalized_pair)
        
        # Step 1: Fetch current intraday data (last 2-3 hours for pre-session analysis)
        print(f"Fetching intraday data for {display_pair}...")
        try:
            intraday_df = self.data_client.get_intraday_data(
                normalized_pair,
                interval="5min",
                outputsize=100  # ~8 hours of 5-min candles
            )
        except Exception as e:
            raise Exception(f"Failed to fetch intraday data: {str(e)}")
        
        # Step 2: Fetch historical data for pattern matching
        print(f"Fetching historical data for pattern matching...")
        try:
            historical_df = self.data_client.get_historical_sessions(
                normalized_pair,
                days_back=60,
                interval="5min"
            )
        except Exception as e:
            raise Exception(f"Failed to fetch historical data: {str(e)}")
        
        # Step 3: Calculate pre-session range
        session_start = session_info["start"]
        session_end = session_info["end"]
        
        current_pre_range = range_calc.calculate_pre_session_range(
            intraday_df,
            session_start,
            minutes_before=90
        )
        
        # Step 4: Calculate 30-day average pre-session range
        avg_pre_range = range_calc.calculate_30day_avg_range(
            historical_df,
            session_start,
            minutes_window=90,
            is_pre_session=True
        )
        
        # Step 5: Calculate average session range
        session_duration_minutes = self._get_session_duration(session_start, session_end)
        avg_session_range = range_calc.calculate_30day_avg_range(
            historical_df,
            session_start,
            minutes_window=session_duration_minutes,
            is_pre_session=False
        )
        
        # Step 6: Detect compression
        is_compressed, compression_ratio = range_calc.detect_compression(
            current_pre_range,
            avg_pre_range,
            threshold=0.70
        )
        
        # Step 7: Find similar historical patterns
        print(f"Matching historical patterns...")
        pattern_results = pattern_matcher.find_similar_conditions(
            current_pre_range,
            avg_pre_range,
            historical_df,
            session_start,
            session_end,
            threshold=0.15
        )
        
        # Step 8: Check for economic events
        print(f"Checking economic calendar...")
        now = datetime.now(pytz.UTC)
        session_start_dt = self._get_next_session_datetime(session_key)
        session_end_dt = session_start_dt + timedelta(minutes=session_duration_minutes)
        
        nearby_event = self.calendar_client.check_event_proximity(
            session_start_dt,
            window_minutes=120
        )
        
        has_event = nearby_event is not None
        
        # Step 9: Calculate expected deviation
        expected_deviation = range_calc.calculate_expected_deviation(
            current_pre_range,
            avg_pre_range,
            pattern_results["expansion_rate"],
            avg_session_range
        )
        
        # Step 10: Calculate confidence score
        confidence = self.confidence_scorer.calculate_confidence(
            occurrences=pattern_results["similar_conditions_occurrences"],
            expansion_rate=pattern_results["expansion_rate"],
            has_event=has_event,
            data_age_days=30  # We're using 30-60 day data
        )
        
        # Step 11: Generate market drivers
        drivers = self._generate_drivers(
            current_pre_range,
            avg_pre_range,
            compression_ratio,
            is_compressed,
            nearby_event,
            pattern_results
        )
        
        # Step 12: Classify volatility
        volatility_level = classify_volatility(
            expected_deviation,
            normalized_pair,
            session_key
        )
        
        # Step 13: Generate agent guidance
        agent_guidance = generate_agent_guidance(
            volatility_level,
            pattern_results["expansion_rate"],
            is_compressed,
            has_event
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
            volatility_level=volatility_level,
            agent_guidance=agent_guidance
        )
    
    def _generate_drivers(
        self,
        current_pre_range: float,
        avg_pre_range: float,
        compression_ratio: float,
        is_compressed: bool,
        event: Optional[Dict],
        pattern_results: Dict
    ) -> list[str]:
        """
        Generate list of market drivers explaining the analysis.
        
        Args:
            current_pre_range: Current pre-session range
            avg_pre_range: Average pre-session range
            compression_ratio: Compression ratio
            is_compressed: Whether range is compressed
            event: Economic event if present
            pattern_results: Pattern matching results
            
        Returns:
            List of driver strings
        """
        drivers = []
        
        # Driver 1: Pre-session range status
        if is_compressed:
            drivers.append(
                f"Asian session range compressed ({current_pre_range:.0f} pips vs "
                f"30-day avg of {avg_pre_range:.0f} pips)"
            )
        else:
            drivers.append(
                f"Pre-session range at {current_pre_range:.0f} pips "
                f"({compression_ratio:.0%} of 30-day avg)"
            )
        
        # Driver 2: Economic event if present
        if event:
            event_desc = self.calendar_client.format_event_for_driver(event)
            drivers.append(event_desc)
        
        # Driver 3: Historical pattern context
        expansion_rate = pattern_results["expansion_rate"]
        occurrences = pattern_results["similar_conditions_occurrences"]
        
        if is_compressed and expansion_rate > 0.6:
            drivers.append(
                f"Pre-session positioning historically precedes volatility expansion "
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
    
    def _get_session_duration(self, start: Any, end: Any) -> int:
        """
        Calculate session duration in minutes.
        
        Args:
            start: Session start time
            end: Session end time
            
        Returns:
            Duration in minutes
        """
        from datetime import datetime, time
        
        # Convert to datetime for arithmetic
        dummy_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(dummy_date, start)
        end_dt = datetime.combine(dummy_date, end)
        
        # Handle overnight sessions
        if end_dt < start_dt:
            end_dt += timedelta(days=1)
        
        duration = (end_dt - start_dt).total_seconds() / 60
        return int(duration)
    
    def _get_next_session_datetime(self, session_key: str) -> datetime:
        """
        Get datetime for next occurrence of session.
        
        Args:
            session_key: Session identifier
            
        Returns:
            Datetime of next session start
        """
        now = datetime.now(pytz.UTC)
        today = now.date()
        
        session_info = get_session_info(session_key)
        session_start = session_info["start"]
        
        # Try today
        session_dt = datetime.combine(today, session_start, tzinfo=pytz.UTC)
        
        # If already passed, use tomorrow
        if session_dt < now:
            session_dt = datetime.combine(
                today + timedelta(days=1),
                session_start,
                tzinfo=pytz.UTC
            )
        
        return session_dt
    
    def _weekend_response(self, pair: str) -> Dict[str, Any]:
        """
        Generate response for weekend closure.
        
        Args:
            pair: Currency pair
            
        Returns:
            Weekend closure message
        """
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
            "agent_guidance": "Wait for market open. Review weekly levels and news during closure."
        }


# Main analysis function for MCP tool
def analyze_forex_session(pair: str, target_session: str = "auto") -> Dict[str, Any]:
    """
    MCP tool entry point for forex session analysis.
    
    Args:
        pair: Currency pair (e.g., "EUR/USD")
        target_session: Target session ("asian", "london", "ny", or "auto")
        
    Returns:
        Analysis output in required JSON format
        
    Example:
        result = analyze_forex_session("EUR/USD", "london")
    """
    analyzer = SessionAnalyzer()
    return analyzer.analyze_forex_session(pair, target_session)