from __future__ import annotations

from datetime import datetime, timezone


def detect_session(now_utc: datetime | None = None) -> str:
    now_utc = now_utc or datetime.now(timezone.utc)
    hour = now_utc.hour
    if 0 <= hour <= 6:
        return "Asia"
    if 7 <= hour <= 12:
        return "London"
    if 13 <= hour <= 17:
        return "NewYork"
    return "Off-session"
