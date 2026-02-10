"""Unit tests for volatility intelligence engine."""
import unittest
from datetime import datetime, timezone

from src.config import VOLATILITY_THRESHOLDS
from src.data_fetcher import RangeCalculator
from src.engine import build_intel
from src.session import detect_session, detect_session_detailed, is_high_impact_session
from src.volatility import (
    classify_volatility_expectation,
    get_confidence_for_expectation,
    get_session_volatility_multiplier,
    volatility_for_session,
)


class SessionDetectionTests(unittest.TestCase):
    """Tests for session detection."""

    def test_asia_boundaries(self):
        """Test Asian session boundaries."""
        self.assertEqual(detect_session(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)), "Asian")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 6, 59, tzinfo=timezone.utc)), "Asian")

    def test_london_boundaries(self):
        """Test London session boundaries."""
        self.assertEqual(detect_session(datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc)), "London")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 12, 59, tzinfo=timezone.utc)), "London")

    def test_newyork_boundaries(self):
        """Test New York session boundaries."""
        self.assertEqual(detect_session(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)), "New York")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 17, 59, tzinfo=timezone.utc)), "New York")

    def test_off_session(self):
        """Test off-session detection."""
        self.assertEqual(detect_session(datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc)), "Off-session")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 23, 59, tzinfo=timezone.utc)), "Off-session")

    def test_session_detailed(self):
        """Test detailed session information."""
        info = detect_session_detailed(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc))
        self.assertEqual(info.name, "London")
        self.assertTrue(0 <= info.session_progress <= 1)

    def test_high_impact_session(self):
        """Test high impact session detection."""
        self.assertTrue(is_high_impact_session("London"))
        self.assertTrue(is_high_impact_session("New York"))
        self.assertFalse(is_high_impact_session("Asian"))
        self.assertFalse(is_high_impact_session("Off-session"))


class VolatilityClassificationTests(unittest.TestCase):
    """Tests for volatility classification."""

    def test_low_compression(self):
        """Test low volatility classification."""
        result = classify_volatility_expectation(0.5)
        self.assertEqual(result, "Low")

    def test_normal_volatility(self):
        """Test normal volatility classification."""
        result = classify_volatility_expectation(0.9)
        self.assertEqual(result, "Normal")

    def test_high_expansion(self):
        """Test high volatility classification."""
        result = classify_volatility_expectation(1.5)
        self.assertEqual(result, "High")

    def test_confidence_scores(self):
        """Test confidence score calculations."""
        conf_low = get_confidence_for_expectation("Low", 0.5, 150)
        conf_high = get_confidence_for_expectation("High", 1.5, 150)
        
        # Extreme compression should have high confidence
        self.assertGreater(conf_high, conf_low)
        self.assertTrue(0 <= conf_low <= 1)
        self.assertTrue(0 <= conf_high <= 1)

    def test_session_multiplier(self):
        """Test session volatility multipliers."""
        from src.session import SessionInfo
        
        london = SessionInfo(name="London")
        mult, reason = get_session_volatility_multiplier(london)
        self.assertGreater(mult, 1.0)  # London should amplify volatility
        self.assertIn("London", reason)


class VolatilityCalculationTests(unittest.TestCase):
    """Tests for volatility expectation calculation."""

    def test_volatility_for_session_low(self):
        """Test volatility calculation with low compression."""
        vol = volatility_for_session("Asian", compression_ratio=0.5)
        self.assertEqual(vol["volatility_expectation"], "Low")
        self.assertIn("historical_context", vol)
        self.assertIn("drivers", vol)

    def test_volatility_for_session_normal(self):
        """Test volatility calculation with normal compression."""
        vol = volatility_for_session("London", compression_ratio=1.0)
        self.assertEqual(vol["volatility_expectation"], "Normal")
        self.assertGreater(vol["confidence"], 0)

    def test_volatility_for_session_high(self):
        """Test volatility calculation with high expansion."""
        vol = volatility_for_session("New York", compression_ratio=1.5)
        self.assertEqual(vol["volatility_expectation"], "High")
        self.assertGreater(vol["expected_deviation_pips"], 30)

    def test_macro_event_impact(self):
        """Test macro event impact on volatility."""
        vol_no_events = volatility_for_session("London", compression_ratio=1.0, macro_events=None)
        vol_with_events = volatility_for_session(
            "London", compression_ratio=1.0, macro_events=["US NFP"]
        )
        
        # High impact events should increase deviation
        self.assertGreater(
            vol_with_events["expected_deviation_pips"],
            vol_no_events["expected_deviation_pips"]
        )


class RangeCalculatorTests(unittest.TestCase):
    """Tests for range calculations."""

    def test_pip_multiplier_default(self):
        """Test default pip multiplier."""
        mult = RangeCalculator.get_pip_multiplier("EURUSD")
        self.assertEqual(mult, 10000)

    def test_pip_multiplier_jpy(self):
        """Test JPY pair pip multiplier."""
        mult = RangeCalculator.get_pip_multiplier("USDJPY")
        self.assertEqual(mult, 100)

    def test_pip_multiplier_crypto(self):
        """Test crypto pip multiplier."""
        mult = RangeCalculator.get_pip_multiplier("BTCUSD")
        self.assertEqual(mult, 1)

    def test_compression_ratio_low(self):
        """Test compression ratio calculation."""
        ratio = RangeCalculator.calculate_compression_ratio(0.5, 1.0)
        self.assertEqual(ratio, 0.5)  # Half the average = compression

    def test_compression_ratio_expansion(self):
        """Test expansion ratio calculation."""
        ratio = RangeCalculator.calculate_compression_ratio(1.5, 1.0)
        self.assertEqual(ratio, 1.5)  # 1.5x the average = expansion

    def test_compression_ratio_safety(self):
        """Test compression ratio handles zero average."""
        ratio = RangeCalculator.calculate_compression_ratio(1.0, 0.0)
        self.assertEqual(ratio, 1.0)  # Should return 1.0 as neutral


class EngineTests(unittest.TestCase):
    """Tests for the volatility intelligence engine."""

    def test_engine_response_schema(self):
        """Test that engine returns correct schema."""
        intel = build_intel("EURUSD", debug=True)
        
        required_keys = {
            "pair",
            "session",
            "time_window_minutes",
            "volatility_expectation",
            "expected_deviation_pips",
            "confidence",
            "drivers",
            "historical_context",
            "agent_guidance",
        }
        
        self.assertTrue(required_keys.issubset(intel.keys()))
        self.assertEqual(intel["pair"], "EURUSD")
        self.assertEqual(intel["time_window_minutes"], 90)

    def test_engine_pair_validation(self):
        """Test that engine validates pair format."""
        with self.assertRaises(ValueError):
            build_intel("EUR")  # Too short
        
        with self.assertRaises(ValueError):
            build_intel("EURUSD123")  # Not alphabetic

    def test_engine_with_macro_events(self):
        """Test engine with macro events."""
        intel = build_intel("EURUSD", macro_events=["ECB Rate Decision"])
        self.assertIn("ECB", " ".join(intel["drivers"]))

    def test_engine_debug_mode(self):
        """Test engine debug mode includes extra fields."""
        intel_no_debug = build_intel("EURUSD", debug=False)
        intel_debug = build_intel("EURUSD", debug=True)
        
        self.assertNotIn("last_24h_range_pips", intel_no_debug)
        self.assertIn("last_24h_range_pips", intel_debug)


if __name__ == "__main__":
    unittest.main()
