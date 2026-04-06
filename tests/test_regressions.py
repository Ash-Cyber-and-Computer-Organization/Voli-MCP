import json
import os
import tempfile
import unittest
from pathlib import Path

from src.analysis.pattern_matcher import PatternMatcher
import src.data.calendar_client as calendar_client_module
from src.data.historical_store import HistoricalStore
from src.tools.session_analyzer import analyze_forex_session


class RegressionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._old_db = os.environ.get("HISTORICAL_DB_PATH")
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        self.db_path = tmp.name
        os.environ["HISTORICAL_DB_PATH"] = self.db_path

        self._old_override = os.environ.get("CALENDAR_OVERRIDE_EVENTS")
        self._old_disable_live = os.environ.get("CALENDAR_DISABLE_LIVE")
        self._old_now = os.environ.get("CALENDAR_NOW_UTC")
        os.environ["CALENDAR_DISABLE_LIVE"] = "true"
        calendar_client_module._calendar_instance = None

    def tearDown(self):
        if self._old_db is None:
            os.environ.pop("HISTORICAL_DB_PATH", None)
        else:
            os.environ["HISTORICAL_DB_PATH"] = self._old_db

        if self._old_override is None:
            os.environ.pop("CALENDAR_OVERRIDE_EVENTS", None)
        else:
            os.environ["CALENDAR_OVERRIDE_EVENTS"] = self._old_override

        if self._old_disable_live is None:
            os.environ.pop("CALENDAR_DISABLE_LIVE", None)
        else:
            os.environ["CALENDAR_DISABLE_LIVE"] = self._old_disable_live

        if self._old_now is None:
            os.environ.pop("CALENDAR_NOW_UTC", None)
        else:
            os.environ["CALENDAR_NOW_UTC"] = self._old_now

        calendar_client_module._calendar_instance = None
        try:
            Path(self.db_path).unlink(missing_ok=True)
        except PermissionError:
            pass

    async def test_gbpjpy_has_historical_depth(self):
        store = HistoricalStore()
        averages = store.get_recent_averages("GBP/JPY", "ny", days=30)
        self.assertGreater(averages["avg_pre_range"], 0)

        matcher = PatternMatcher("GBP/JPY")
        results = matcher.find_similar_conditions(
            store=store,
            session_key="ny",
            event_type=None,
            current_pre_range=averages["avg_pre_range"] * 0.9,
            avg_pre_range=averages["avg_pre_range"],
            threshold=0.30,
        )

        self.assertGreater(results["similar_conditions_occurrences"], 0)
        self.assertGreater(results["breakout_occurrences"], 0)

    async def test_named_macro_events_are_exposed(self):
        os.environ["CALENDAR_NOW_UTC"] = "2026-03-18T12:00:00+00:00"
        os.environ["CALENDAR_OVERRIDE_EVENTS"] = json.dumps(
            [
                {
                    "event": "ECB Rate Decision",
                    "currency": "EUR",
                    "country": "EUR",
                    "datetime": "2026-03-18T12:45:00+00:00",
                    "impact": "high",
                    "event_type": "ECB",
                    "source": "test",
                },
                {
                    "event": "UK Consumer Price Index (CPI)",
                    "currency": "GBP",
                    "country": "GBP",
                    "datetime": "2026-03-18T10:00:00+00:00",
                    "impact": "high",
                    "event_type": "CPI",
                    "source": "test",
                },
            ]
        )

        result = await analyze_forex_session("EUR/GBP", "london")

        self.assertIn("macro_events", result)
        self.assertTrue(result["macro_events"])
        self.assertEqual(result["primary_macro_event"]["event_type"], "ECB")
        self.assertEqual(result["macro_events"][0]["name"], "ECB Rate Decision")
        self.assertIn(result["macro_events"][1]["event_type"], {"CPI", "ECB"})


if __name__ == "__main__":
    unittest.main()
