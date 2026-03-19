"""
Local historical session range store backed by SQLite.
Seeds 2+ years of daily session range data per major pair.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random
from contextlib import contextmanager

import pytz
import pandas as pd

from utils.sessions import SESSIONS
from utils.formatters import ALL_PAIRS, normalize_pair_format


@dataclass
class SessionRangeRecord:
    date: str
    pair: str
    session: str
    pre_range_pips: float
    session_range_pips: float
    compression_ratio: float
    has_event: int
    event_type: Optional[str]


class HistoricalStore:
    """SQLite-backed store for historical session ranges."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            env_path = os.getenv("HISTORICAL_DB_PATH")
            default_path = Path(__file__).parent / "session_history.db"
            db_path = Path(env_path) if env_path else default_path
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()
        self._ensure_seeded()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_ranges (
                    date TEXT NOT NULL,
                    pair TEXT NOT NULL,
                    session TEXT NOT NULL,
                    pre_range_pips REAL NOT NULL,
                    session_range_pips REAL NOT NULL,
                    compression_ratio REAL NOT NULL,
                    has_event INTEGER NOT NULL,
                    event_type TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ranges_pair_session_date ON session_ranges(pair, session, date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ranges_event ON session_ranges(event_type)")

    def _ensure_seeded(self) -> None:
        with self._connection() as conn:
            cur = conn.execute("SELECT COUNT(1) FROM session_ranges")
            count = cur.fetchone()[0]
        if count == 0:
            self._seed_synthetic_history()
            return
        self._ensure_supported_pairs_seeded()

    def _seed_synthetic_history(self) -> None:
        """Generate synthetic 2-year session ranges for major pairs."""
        pairs = [normalize_pair_format(pair) for pair in ALL_PAIRS]
        end_date = datetime.now(pytz.UTC).date()
        start_date = end_date - timedelta(days=730)

        session_weights = {
            "asian": 0.28,
            "london": 0.45,
            "ny": 0.37
        }

        rng = random.Random(42)

        records: List[SessionRangeRecord] = []
        day = start_date
        while day <= end_date:
            if day.weekday() >= 5:
                day += timedelta(days=1)
                continue

            events = self._fallback_events_for_date(day)

            for pair in pairs:
                daily_base = self._estimate_daily_base(pair)
                day_multiplier = rng.uniform(0.7, 1.35)
                daily_range = daily_base * day_multiplier

                for session_key in SESSIONS.keys():
                    pre_range = daily_range * session_weights[session_key] * rng.uniform(0.35, 0.55)
                    # Control expansion probability to ~65%
                    if rng.random() < 0.65:
                        session_range = pre_range * rng.uniform(1.55, 2.0)
                    else:
                        session_range = pre_range * rng.uniform(1.1, 1.45)

                    event_type = None
                    has_event = 0
                    for ev in events:
                        if session_key == ev["session"] and ev["currency"] in {pair[:3], pair[3:]}:
                            event_type = ev["event_type"]
                            has_event = 1
                            # Recalibrate event-day expansion probability
                            if rng.random() < 0.55:
                                session_range = pre_range * rng.uniform(1.5, 1.9)
                            else:
                                session_range = pre_range * rng.uniform(1.1, 1.4)
                            break

                    records.append(
                        SessionRangeRecord(
                            date=day.isoformat(),
                            pair=pair,
                            session=session_key,
                            pre_range_pips=round(pre_range, 1),
                            session_range_pips=round(session_range, 1),
                            compression_ratio=0.0,
                            has_event=has_event,
                            event_type=event_type
                        )
                    )
            day += timedelta(days=1)

        keyed: Dict[Tuple[str, str], List[SessionRangeRecord]] = {}
        for rec in records:
            keyed.setdefault((rec.pair, rec.session), []).append(rec)

        for rows in keyed.values():
            rows.sort(key=lambda r: r.date)
            window: List[float] = []
            for rec in rows:
                window.append(rec.pre_range_pips)
                if len(window) > 30:
                    window.pop(0)
                avg_pre = sum(window) / len(window) if window else rec.pre_range_pips
                rec.compression_ratio = round(rec.pre_range_pips / avg_pre, 2) if avg_pre > 0 else 1.0

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO session_ranges
                (date, pair, session, pre_range_pips, session_range_pips, compression_ratio, has_event, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.date,
                        r.pair,
                        r.session,
                        r.pre_range_pips,
                        r.session_range_pips,
                        r.compression_ratio,
                        r.has_event,
                        r.event_type
                    )
                    for r in records
                ]
            )

    def _ensure_supported_pairs_seeded(self) -> None:
        """Backfill synthetic history for supported pairs missing from an existing DB."""
        pairs = [normalize_pair_format(pair) for pair in ALL_PAIRS]
        with self._connection() as conn:
            cur = conn.execute("SELECT DISTINCT pair FROM session_ranges")
            existing_pairs = {row[0] for row in cur.fetchall()}

        missing_pairs = [pair for pair in pairs if pair not in existing_pairs]
        if not missing_pairs:
            return

        self._seed_synthetic_history_for_pairs(missing_pairs)

    def _seed_synthetic_history_for_pairs(self, pairs: List[str]) -> None:
        end_date = datetime.now(pytz.UTC).date()
        start_date = end_date - timedelta(days=730)
        session_weights = {
            "asian": 0.28,
            "london": 0.45,
            "ny": 0.37
        }
        rng = random.Random(42)
        records: List[SessionRangeRecord] = []
        day = start_date

        while day <= end_date:
            if day.weekday() >= 5:
                day += timedelta(days=1)
                continue

            events = self._fallback_events_for_date(day)

            for pair in pairs:
                daily_base = self._estimate_daily_base(pair)
                day_multiplier = rng.uniform(0.7, 1.35)
                daily_range = daily_base * day_multiplier

                for session_key in SESSIONS.keys():
                    pre_range = daily_range * session_weights[session_key] * rng.uniform(0.35, 0.55)
                    if rng.random() < 0.65:
                        session_range = pre_range * rng.uniform(1.55, 2.0)
                    else:
                        session_range = pre_range * rng.uniform(1.1, 1.45)

                    event_type = None
                    has_event = 0
                    for ev in events:
                        if session_key == ev["session"] and ev["currency"] in {pair[:3], pair[3:]}:
                            event_type = ev["event_type"]
                            has_event = 1
                            if rng.random() < 0.55:
                                session_range = pre_range * rng.uniform(1.5, 1.9)
                            else:
                                session_range = pre_range * rng.uniform(1.1, 1.4)
                            break

                    records.append(
                        SessionRangeRecord(
                            date=day.isoformat(),
                            pair=pair,
                            session=session_key,
                            pre_range_pips=round(pre_range, 1),
                            session_range_pips=round(session_range, 1),
                            compression_ratio=0.0,
                            has_event=has_event,
                            event_type=event_type
                        )
                    )
            day += timedelta(days=1)

        self._insert_seed_records(records)

    def _insert_seed_records(self, records: List[SessionRangeRecord]) -> None:
        keyed: Dict[Tuple[str, str], List[SessionRangeRecord]] = {}
        for rec in records:
            keyed.setdefault((rec.pair, rec.session), []).append(rec)

        for rows in keyed.values():
            rows.sort(key=lambda r: r.date)
            window: List[float] = []
            for rec in rows:
                window.append(rec.pre_range_pips)
                if len(window) > 30:
                    window.pop(0)
                avg_pre = sum(window) / len(window) if window else rec.pre_range_pips
                rec.compression_ratio = round(rec.pre_range_pips / avg_pre, 2) if avg_pre > 0 else 1.0

        with self._connection() as conn:
            conn.executemany(
                """
                INSERT INTO session_ranges
                (date, pair, session, pre_range_pips, session_range_pips, compression_ratio, has_event, event_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        r.date,
                        r.pair,
                        r.session,
                        r.pre_range_pips,
                        r.session_range_pips,
                        r.compression_ratio,
                        r.has_event,
                        r.event_type
                    )
                    for r in records
                ]
            )

    def _estimate_daily_base(self, pair: str) -> float:
        """Estimate a plausible baseline daily pip range for supported pairs."""
        pair = normalize_pair_format(pair)
        direct_map = {
            "EURUSD": 70,
            "GBPUSD": 85,
            "USDJPY": 90,
            "AUDUSD": 65,
            "USDCAD": 60,
            "NZDUSD": 62,
            "USDCHF": 68,
        }
        if pair in direct_map:
            return direct_map[pair]

        currency_weights = {
            "EUR": 34,
            "GBP": 42,
            "USD": 30,
            "JPY": 48,
            "AUD": 28,
            "CAD": 24,
            "NZD": 26,
            "CHF": 24,
            "SGD": 20,
            "HKD": 14,
            "ZAR": 58,
            "MXN": 62,
            "TRY": 72,
        }
        base = currency_weights.get(pair[:3], 30) + currency_weights.get(pair[3:], 30)
        return float(max(45, min(base, 140)))

    def _fallback_events_for_date(self, day) -> List[Dict[str, str]]:
        """Simple recurring event schedule for synthetic data."""
        events = []

        # NFP: first Friday of month, 13:30 UTC (NY session)
        if day.weekday() == 4 and 1 <= day.day <= 7:
            events.append({"event_type": "NFP", "currency": "USD", "session": "ny"})

        # CPI: mid-month
        if 12 <= day.day <= 15:
            events.append({"event_type": "CPI", "currency": "USD", "session": "ny"})
            events.append({"event_type": "CPI", "currency": "EUR", "session": "london"})
            events.append({"event_type": "CPI", "currency": "GBP", "session": "london"})

        # FOMC: 8x/year, 3rd Wednesday
        if day.month in {1, 3, 5, 6, 7, 9, 11, 12} and day.weekday() == 2 and 14 <= day.day <= 21:
            events.append({"event_type": "FOMC", "currency": "USD", "session": "ny"})

        # ECB: 8x/year, 2nd Thursday
        if day.month in {1, 3, 4, 6, 7, 9, 10, 12} and day.weekday() == 3 and 7 <= day.day <= 14:
            events.append({"event_type": "ECB", "currency": "EUR", "session": "london"})

        # BOE: 8x/year, 2nd Thursday
        if day.month in {2, 3, 5, 6, 8, 9, 11, 12} and day.weekday() == 3 and 7 <= day.day <= 14:
            events.append({"event_type": "BOE", "currency": "GBP", "session": "london"})

        return events

    def get_recent_averages(self, pair: str, session: str, days: int = 30) -> Dict[str, float]:
        normalized = normalize_pair_format(pair)
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT pre_range_pips, session_range_pips
                FROM session_ranges
                WHERE pair = ? AND session = ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (normalized, session.lower(), days)
            )
            rows = cur.fetchall()

        if not rows:
            return {"avg_pre_range": 0.0, "avg_session_range": 0.0}

        pre_ranges = [r[0] for r in rows]
        session_ranges = [r[1] for r in rows]
        return {
            "avg_pre_range": round(sum(pre_ranges) / len(pre_ranges), 1),
            "avg_session_range": round(sum(session_ranges) / len(session_ranges), 1)
        }

    def get_rolling_averages(self, pair: str, session: str, window_days: int = 30) -> Tuple[float, float]:
        averages = self.get_recent_averages(pair, session, days=window_days)
        return averages.get("avg_pre_range", 0.0), averages.get("avg_session_range", 0.0)

    def get_history_df(self, pair: str, session: str) -> pd.DataFrame:
        normalized = normalize_pair_format(pair)
        with self._connection() as conn:
            df = pd.read_sql_query(
                """
                SELECT date, pre_range_pips, session_range_pips,
                       compression_ratio, has_event, event_type
                FROM session_ranges
                WHERE pair = ? AND session = ?
                ORDER BY date ASC
                """,
                conn,
                params=(normalized, session.lower())
            )

        if df.empty:
            return df

        df["date"] = pd.to_datetime(df["date"]).dt.date
        # Add rolling averages for compression comparison if needed downstream
        df["avg_pre_range_30d"] = df["pre_range_pips"].rolling(30, min_periods=10).mean()
        df["avg_session_range_30d"] = df["session_range_pips"].rolling(30, min_periods=10).mean()
        return df

    def get_comparable_conditions(
        self,
        pair: str,
        session: str,
        event_type: Optional[str],
        compression_ratio: float,
        tolerance: float = 0.30
    ) -> List[SessionRangeRecord]:
        normalized = normalize_pair_format(pair)
        session_key = session.lower()
        min_ratio = compression_ratio * (1 - tolerance)
        max_ratio = compression_ratio * (1 + tolerance)

        with self._connection() as conn:
            if event_type == "ANY":
                cur = conn.execute(
                    """
                    SELECT date, pair, session, pre_range_pips, session_range_pips,
                           compression_ratio, has_event, event_type
                    FROM session_ranges
                    WHERE pair = ? AND session = ? AND event_type IS NOT NULL AND event_type != ''
                      AND compression_ratio BETWEEN ? AND ?
                    """,
                    (normalized, session_key, min_ratio, max_ratio)
                )
            elif event_type:
                cur = conn.execute(
                    """
                    SELECT date, pair, session, pre_range_pips, session_range_pips,
                           compression_ratio, has_event, event_type
                    FROM session_ranges
                    WHERE pair = ? AND session = ? AND event_type = ?
                      AND compression_ratio BETWEEN ? AND ?
                    """,
                    (normalized, session_key, event_type, min_ratio, max_ratio)
                )
            else:
                cur = conn.execute(
                    """
                    SELECT date, pair, session, pre_range_pips, session_range_pips,
                           compression_ratio, has_event, event_type
                    FROM session_ranges
                    WHERE pair = ? AND session = ? AND (event_type IS NULL OR event_type = '')
                      AND compression_ratio BETWEEN ? AND ?
                    """,
                    (normalized, session_key, min_ratio, max_ratio)
                )
            rows = cur.fetchall()

        return [
            SessionRangeRecord(
                date=r[0],
                pair=r[1],
                session=r[2],
                pre_range_pips=r[3],
                session_range_pips=r[4],
                compression_ratio=r[5],
                has_event=r[6],
                event_type=r[7]
            )
            for r in rows
        ]

    def get_latest_pre_range(self, pair: str, session: str) -> Optional[float]:
        normalized = normalize_pair_format(pair)
        with self._connection() as conn:
            cur = conn.execute(
                """
                SELECT pre_range_pips
                FROM session_ranges
                WHERE pair = ? AND session = ?
                ORDER BY date DESC
                LIMIT 1
                """,
                (normalized, session.lower())
            )
            row = cur.fetchone()
        return float(row[0]) if row else None
