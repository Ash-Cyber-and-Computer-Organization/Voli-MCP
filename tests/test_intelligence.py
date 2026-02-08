import unittest
from datetime import datetime, timezone

from src.session import detect_session
from src.volatility import volatility_for_session
from src.engine import build_intel


class SessionTests(unittest.TestCase):
    def test_asia_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)), "Asian session")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 6, 59, tzinfo=timezone.utc)), "Asian session")

    def test_london_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc)), "London Open")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 12, 59, tzinfo=timezone.utc)), "London Open")

    def test_newyork_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)), "New York Open")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 17, 59, tzinfo=timezone.utc)), "New York Open")

    def test_off_session(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc)), "Off-session")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 23, 59, tzinfo=timezone.utc)), "Off-session")


class VolatilityTests(unittest.TestCase):
    def test_london_volatility(self):
        vol = volatility_for_session("London Open")
        self.assertEqual(vol["volatility_expectation"], "High")
        self.assertAlmostEqual(vol["confidence"], 0.74)
        self.assertTrue(any("London" in d for d in vol["drivers"]))
        self.assertEqual(vol["expected_deviation_pips"], 38)
        self.assertIn("historical_context", vol)

    def test_newyork_volatility(self):
        vol = volatility_for_session("New York Open")
        self.assertEqual(vol["volatility_expectation"], "High")
        self.assertAlmostEqual(vol["confidence"], 0.7)
        self.assertTrue(any("New York" in d for d in vol["drivers"]))
        self.assertEqual(vol["expected_deviation_pips"], 45)
        self.assertIn("historical_context", vol)

    def test_off_session_volatility(self):
        vol = volatility_for_session("Off-session")
        self.assertEqual(vol["volatility_expectation"], "Normal")
        self.assertAlmostEqual(vol["confidence"], 0.5)
        self.assertEqual(vol["expected_deviation_pips"], 20)
        self.assertIn("historical_context", vol)


class EngineTests(unittest.TestCase):
    def test_engine_payload_shape(self):
        payload = build_intel("EURUSD")
        for key in ["pair", "session", "time_window_minutes", "volatility_expectation", "expected_deviation_pips", "confidence", "drivers", "historical_context", "agent_guidance", "last_24h_range_pips", "avg_7day_range_pips", "compression_ratio"]:
            self.assertIn(key, payload)
        self.assertEqual(payload["pair"], "EURUSD")
        self.assertEqual(payload["time_window_minutes"], 90)
        self.assertEqual(payload["last_24h_range_pips"], 45)
        self.assertEqual(payload["avg_7day_range_pips"], 52)
        self.assertEqual(payload["compression_ratio"], 0.87)
        self.assertEqual(payload["volatility_expectation"], "Normal")
        self.assertEqual(payload["expected_deviation_pips"], 35)
        self.assertEqual(payload["confidence"], 0.7)
        self.assertIn("Range compression detected (45 vs 52 pips baseline)", payload["drivers"])


if __name__ == "__main__":
    unittest.main()
