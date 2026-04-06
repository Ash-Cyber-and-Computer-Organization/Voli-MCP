"""
Simple JSON-backed cache for live range estimates.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import os
import pytz


@dataclass
class RangeCacheEntry:
    pair: str
    session: str
    pre_range_pips: float
    avg_pre_range_pips: float
    avg_session_range_pips: float
    timestamp: str


class RangeCache:
    """Persisted cache to avoid zero ranges on data outages."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = Path(__file__).parent / "range_cache.json"
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, Dict] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._data = {}
            return
        try:
            self._data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self._data = {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _key(self, pair: str, session: str) -> str:
        return f"{pair.upper()}::{session.lower()}"

    def get(self, pair: str, session: str, max_age_hours: int = 72) -> Optional[RangeCacheEntry]:
        key = self._key(pair, session)
        entry = self._data.get(key)
        if not entry:
            return None
        try:
            timestamp = datetime.fromisoformat(entry["timestamp"])
            now = datetime.now(pytz.UTC)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            if now - timestamp > timedelta(hours=max_age_hours):
                return None
            return RangeCacheEntry(**entry)
        except Exception:
            return None

    def set(
        self,
        pair: str,
        session: str,
        pre_range_pips: float,
        avg_pre_range_pips: float,
        avg_session_range_pips: float
    ) -> None:
        key = self._key(pair, session)
        self._data[key] = {
            "pair": pair.upper(),
            "session": session.lower(),
            "pre_range_pips": float(pre_range_pips),
            "avg_pre_range_pips": float(avg_pre_range_pips),
            "avg_session_range_pips": float(avg_session_range_pips),
            "timestamp": datetime.now(pytz.UTC).isoformat()
        }
        self._save()


_cache_instance: Optional[RangeCache] = None


def _get_cache() -> RangeCache:
    global _cache_instance
    if _cache_instance is None:
        path = os.getenv("RANGE_CACHE_PATH")
        cache_path = Path(path) if path else (Path(__file__).parent / "range_cache.json")
        _cache_instance = RangeCache(cache_path)
    return _cache_instance


def get_cached_range(pair: str, session: str) -> Optional[float]:
    entry = _get_cache().get(pair, session)
    return entry.pre_range_pips if entry else None


def get_cached_ranges(pair: str, session: str) -> Optional[Dict[str, float]]:
    entry = _get_cache().get(pair, session)
    if not entry:
        return None
    return {
        "pre_range_pips": entry.pre_range_pips,
        "avg_pre_range_pips": entry.avg_pre_range_pips,
        "avg_session_range_pips": entry.avg_session_range_pips
    }


def set_cached_range(
    pair: str,
    session: str,
    pre_range_pips: float,
    avg_pre_range_pips: float = 0.0,
    avg_session_range_pips: float = 0.0
) -> None:
    _get_cache().set(
        pair=pair,
        session=session,
        pre_range_pips=pre_range_pips,
        avg_pre_range_pips=avg_pre_range_pips,
        avg_session_range_pips=avg_session_range_pips
    )


def update_cached_ranges(
    pair: str,
    session: str,
    pre_range_pips: float,
    avg_pre_range_pips: float,
    avg_session_range_pips: float
) -> None:
    set_cached_range(
        pair=pair,
        session=session,
        pre_range_pips=pre_range_pips,
        avg_pre_range_pips=avg_pre_range_pips,
        avg_session_range_pips=avg_session_range_pips
    )
