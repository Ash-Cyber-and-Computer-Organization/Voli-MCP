"""
Economic calendar client for high-impact forex events.
Uses Forex Factory RSS with a deterministic fallback schedule.
"""

from __future__ import annotations

import os
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, time
import pytz
import httpx
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

from utils.formatters import normalize_pair_format

load_dotenv()


class CalendarClient:
    """Client for economic calendar data with fallback strategies."""

    FOREX_FACTORY_URL = os.getenv(
        "FOREX_FACTORY_RSS_URL",
        os.getenv("FOREX_FACTORY_URL", "https://www.forexfactory.com/ff_cal_thisweek.xml")
    )

    HIGH_IMPACT = {"high", "high impact", "high-impact"}

    EVENT_TYPE_KEYWORDS = {
        "NFP": ["NFP", "NON-FARM", "PAYROLL"],
        "CPI": ["CPI", "INFLATION", "CONSUMER PRICE"],
        "FOMC": ["FOMC", "FEDERAL RESERVE", "FED"],
        "ECB": ["ECB", "EUROPEAN CENTRAL BANK"],
        "BOE": ["BOE", "BANK OF ENGLAND"],
        "BOJ": ["BOJ", "BANK OF JAPAN"],
        "RBA": ["RBA", "RESERVE BANK"],
        "GDP": ["GDP", "GROSS DOMESTIC"],
        "RATE": ["RATE DECISION", "INTEREST RATE"]
    }

    def __init__(self):
        self.use_live = os.getenv("CALENDAR_DISABLE_LIVE", "false").lower() != "true"
        self.override_events = self._load_override_events()

    def _load_override_events(self) -> Optional[List[Dict[str, Any]]]:
        raw = os.getenv("CALENDAR_OVERRIDE_EVENTS")
        if not raw:
            return None
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
        except Exception:
            return None
        return None

    def now_utc(self) -> datetime:
        override = os.getenv("CALENDAR_NOW_UTC")
        if override:
            try:
                return datetime.fromisoformat(override.replace("Z", "+00:00"))
            except Exception:
                pass
        return datetime.now(pytz.UTC)

    def get_pair_events(
        self,
        pair: str,
        window_hours: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Get high-impact events within +/- window_hours of now for a currency pair.
        """
        normalized = normalize_pair_format(pair)
        currencies = {normalized[:3], normalized[3:]}
        now = self.now_utc()

        events = self.get_events_window(now, window_hours=window_hours)
        return [e for e in events if e.get("currency") in currencies]

    def get_events_within_window(
        self,
        center_time: Optional[datetime] = None,
        window_hours: int = 4,
        currencies: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Primary API used by the session analyzer. Returns events within a +/- window.
        """
        now = center_time or self.now_utc()
        events = self.get_events_window(now, window_hours=window_hours)
        if currencies:
            currencies = [c.upper() for c in currencies]
            events = [e for e in events if (e.get("currency") or "").upper() in currencies]
        return events

    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        country: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Backward-compatible helper for tests. Returns events in the next N hours.
        """
        now = self.now_utc()
        window = timedelta(hours=hours_ahead)
        events = self.get_events_window(now, window_hours=hours_ahead)
        upcoming = []
        for event in events:
            try:
                event_dt = datetime.fromisoformat(event["datetime"])
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=pytz.UTC)
                if now <= event_dt <= now + window:
                    if country and event.get("currency") != country.upper():
                        continue
                    upcoming.append(event)
            except Exception:
                continue
        return upcoming

    def get_events_window(
        self,
        now: datetime,
        window_hours: int = 4
    ) -> List[Dict[str, Any]]:
        """Fetch events in a +/- window around now (UTC)."""
        if self.override_events is not None:
            events = self.override_events
        else:
            try:
                if self.use_live:
                    events = self._fetch_forex_factory_events()
                else:
                    events = []
            except Exception:
                events = []

        if not events:
            events = self._get_fallback_events(now, window_hours=window_hours)

        window = timedelta(hours=window_hours)
        filtered = []
        for event in events:
            try:
                if not event.get("event_type") and event.get("event"):
                    event["event_type"] = self._infer_event_type(event["event"])
                event_dt = datetime.fromisoformat(event["datetime"])
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=pytz.UTC)
                if abs(event_dt - now) <= window:
                    filtered.append(event)
            except Exception:
                continue
        return filtered

    def check_event_proximity(
        self,
        target_time: datetime,
        window_minutes: int = 240
    ) -> Optional[Dict[str, Any]]:
        """Return the nearest event within a window around target_time."""
        events = self.get_events_window(target_time, window_hours=int(window_minutes / 60))
        if not events:
            return None

        closest = None
        closest_minutes = None
        for event in events:
            event_time = datetime.fromisoformat(event["datetime"])
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=pytz.UTC)
            minutes_until = int((event_time - target_time).total_seconds() / 60)
            if closest is None or abs(minutes_until) < abs(closest_minutes):
                closest = event.copy()
                closest["minutes_until"] = minutes_until
                closest_minutes = minutes_until
        return closest

    def _fetch_forex_factory_events(self) -> List[Dict[str, Any]]:
        headers = {"User-Agent": "Voli-MCP/1.0"}
        with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
            response = client.get(self.FOREX_FACTORY_URL)
            response.raise_for_status()
            xml_text = response.text

        root = ET.fromstring(xml_text)
        events = []

        for event in root.findall(".//event"):
            title = self._get_text(event, "title")
            country = self._get_text(event, "country") or self._get_text(event, "currency")
            currency = self._get_text(event, "currency") or country
            impact = self._get_text(event, "impact")
            date_text = self._get_text(event, "date")
            time_text = self._get_text(event, "time")

            if not title or not country or not impact:
                continue
            if impact.strip().lower() not in self.HIGH_IMPACT:
                continue

            event_dt = self._parse_event_datetime(date_text, time_text)
            if event_dt is None:
                continue

            event_type = self._infer_event_type(title)
            events.append({
                "event": title,
                "currency": currency.upper(),
                "country": country.upper(),
                "datetime": event_dt.isoformat(),
                "impact": "high",
                "event_type": event_type,
                "source": "forexfactory"
            })

        return events

    def _parse_event_datetime(self, date_text: str, time_text: str) -> Optional[datetime]:
        if not date_text or not time_text:
            return None
        time_text = time_text.strip()
        if time_text.lower() in {"all day", "tentative"}:
            return None

        try:
            date_obj = datetime.strptime(date_text.strip(), "%b %d, %Y").date()
        except ValueError:
            return None

        try:
            time_obj = datetime.strptime(time_text, "%H:%M").time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_text, "%I:%M%p").time()
            except ValueError:
                return None

        return datetime.combine(date_obj, time_obj, tzinfo=pytz.UTC)

    def _get_text(self, node: ET.Element, tag: str) -> str:
        child = node.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def _infer_event_type(self, name: str) -> Optional[str]:
        upper = name.upper()
        for event_type, keywords in self.EVENT_TYPE_KEYWORDS.items():
            if any(keyword in upper for keyword in keywords):
                return event_type
        return None

    def _get_fallback_events(self, now: datetime, window_hours: int = 4) -> List[Dict[str, Any]]:
        """Fallback schedule for recurring high-impact events."""
        window = timedelta(hours=window_hours)
        events: List[Dict[str, Any]] = []

        candidate_dates = [now.date() + timedelta(days=offset) for offset in range(-2, 3)]
        for day in candidate_dates:
            events.extend(self._recurring_events_for_date(day))

        filtered = []
        for event in events:
            event_dt = datetime.fromisoformat(event["datetime"])
            if abs(event_dt - now) <= window:
                filtered.append(event)
        return filtered

    def _recurring_events_for_date(self, day) -> List[Dict[str, Any]]:
        events = []

        # NFP: first Friday of month, 13:30 UTC
        if day.weekday() == 4 and 1 <= day.day <= 7:
            events.append(self._event("US Non-Farm Payrolls (NFP)", "USD", day, time(13, 30), "NFP"))

        # CPI: mid-month
        if 12 <= day.day <= 15:
            events.append(self._event("US Consumer Price Index (CPI)", "USD", day, time(13, 30), "CPI"))
            events.append(self._event("UK Consumer Price Index (CPI)", "GBP", day, time(7, 0), "CPI"))
            events.append(self._event("EU Consumer Price Index (CPI)", "EUR", day, time(10, 0), "CPI"))

        # FOMC: 8x/year, 3rd Wednesday
        if day.month in {1, 3, 5, 6, 7, 9, 11, 12} and day.weekday() == 2 and 14 <= day.day <= 21:
            events.append(self._event("FOMC Rate Decision", "USD", day, time(19, 0), "FOMC"))

        # ECB: 8x/year, 2nd Thursday
        if day.month in {1, 3, 4, 6, 7, 9, 10, 12} and day.weekday() == 3 and 7 <= day.day <= 14:
            events.append(self._event("ECB Rate Decision", "EUR", day, time(12, 45), "ECB"))

        # BOE: 8x/year, 2nd Thursday
        if day.month in {2, 3, 5, 6, 8, 9, 11, 12} and day.weekday() == 3 and 7 <= day.day <= 14:
            events.append(self._event("BOE Rate Decision", "GBP", day, time(12, 0), "BOE"))

        return events

    def _event(self, name: str, currency: str, day, t: time, event_type: Optional[str]) -> Dict[str, Any]:
        dt = datetime.combine(day, t, tzinfo=pytz.UTC)
        return {
            "event": name,
            "currency": currency,
            "country": currency,
            "datetime": dt.isoformat(),
            "impact": "high",
            "event_type": event_type,
            "source": "fallback"
        }

    def format_event_for_driver(self, event: Dict[str, Any]) -> str:
        """Format event for output drivers."""
        event_name = event.get("event", "Economic event")
        impact = event.get("impact", "high").capitalize()
        try:
            event_dt = datetime.fromisoformat(event["datetime"])
            time_str = event_dt.astimezone(pytz.UTC).strftime("%H:%M UTC")
            return f"{event_name} scheduled at {time_str} ({impact} impact)"
        except Exception:
            return f"{event_name} ({impact} impact)"


_calendar_instance: Optional[CalendarClient] = None


def get_calendar_client() -> CalendarClient:
    global _calendar_instance
    if _calendar_instance is None:
        _calendar_instance = CalendarClient()
    return _calendar_instance
