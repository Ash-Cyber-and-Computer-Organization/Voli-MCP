import unittest
from datetime import datetime, timezone

from src.session import detect_session
from src.volatility import volatility_for_session
from src.engine import build_intel


class SessionTests(unittest.TestCase):
    def test_asia_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)), "Asia")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 6, 59, tzinfo=timezone.utc)), "Asia")

    def test_london_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 7, 0, tzinfo=timezone.utc)), "London")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 12, 59, tzinfo=timezone.utc)), "London")

    def test_newyork_boundaries(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)), "NewYork")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 17, 59, tzinfo=timezone.utc)), "NewYork")

    def test_off_session(self):
        self.assertEqual(detect_session(datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc)), "Off-session")
        self.assertEqual(detect_session(datetime(2024, 1, 1, 23, 59, tzinfo=timezone.utc)), "Off-session")


class VolatilityTests(unittest.TestCase):
    def test_london_volatility(self):
        vol = volatility_for_session("London")
        self.assertEqual(vol["volatility_expectation"], "Elevated")
        self.assertAlmostEqual(vol["confidence"], 0.65)
        self.assertTrue(any("London" in d for d in vol["drivers"]))

    def test_newyork_volatility(self):
        vol = volatility_for_session("NewYork")
        self.assertEqual(vol["volatility_expectation"], "High")
        self.assertAlmostEqual(vol["confidence"], 0.7)
        self.assertTrue(any("New York" in d for d in vol["drivers"]))

    def test_off_session_volatility(self):
        vol = volatility_for_session("Off-session")
        self.assertEqual(vol["volatility_expectation"], "Normal")
        self.assertAlmostEqual(vol["confidence"], 0.5)


class EngineTests(unittest.TestCase):
    def test_engine_payload_shape(self):
        payload = build_intel("EURUSD")
        for key in ["pair", "session", "volatility_expectation", "confidence", "drivers", "agent_guidance"]:
            self.assertIn(key, payload)
        self.assertEqual(payload["pair"], "EURUSD")


if __name__ == "__main__":
    unittest.main()
