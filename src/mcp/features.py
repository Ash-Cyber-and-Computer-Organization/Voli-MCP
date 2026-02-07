from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import time
from typing import Any

import pandas as pd

ASIAN_SESSION_START = time(0, 0)
ASIAN_SESSION_END = time(9, 0)
SESSION_WINDOWS = {
    "asian": (ASIAN_SESSION_START, ASIAN_SESSION_END, "Asian session"),
    "tokyo": (ASIAN_SESSION_START, ASIAN_SESSION_END, "Asian session"),
    "london": (time(7, 0), time(16, 0), "London session"),
    "london open": (time(7, 0), time(16, 0), "London session"),
    "ny": (time(12, 30), time(21, 0), "New York session"),
    "new york": (time(12, 30), time(21, 0), "New York session"),
}
DEFAULT_PIP_SIZE = 0.0001
AVG_RANGE_LOOKBACK_DAYS = 30


@dataclass
class FeatureSet:
    session_range_pips: float | None
    avg_30d_range_pips: float | None
    compression_ratio: float | None
    drivers: list[str]
    event: str | None
    event_overlap: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_range_pips": self.session_range_pips,
            "avg_30d_range_pips": self.avg_30d_range_pips,
            "compression_ratio": self.compression_ratio,
            "drivers": list(self.drivers),
            "event": self.event,
            "event_overlap": self.event_overlap,
        }


def compute_features(df: pd.DataFrame, metadata: Mapping[str, Any]) -> FeatureSet:
    """Derive range-based signals and assemble drivers from the market data and metadata."""

    df = _prepare_df(df)
    pip_size = _normalize_pip_size(metadata)

    session_name = _metadata_value(metadata, "session")
    session_range_pips, session_label = _calc_session_range_pips(df, pip_size, session_name)
    avg_30d_range_pips = _calc_avg_30d_range_pips(df, pip_size)
    compression_ratio = _calc_compression_ratio(session_range_pips, avg_30d_range_pips)

    event = _metadata_value(metadata, "event")
    event_overlap = _metadata_value(metadata, "event_overlap")
    drivers = _assemble_drivers(
        session_range_pips,
        avg_30d_range_pips,
        compression_ratio,
        event,
        event_overlap,
        session_name,
        session_label,
    )

    return FeatureSet(
        session_range_pips=session_range_pips,
        avg_30d_range_pips=avg_30d_range_pips,
        compression_ratio=compression_ratio,
        drivers=drivers,
        event=event,
        event_overlap=event_overlap,
    )


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "timestamp" in df:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    if "mid" not in df and {"bid", "ask"}.issubset(df.columns):
        df["mid"] = (
            pd.to_numeric(df["bid"], errors="coerce") + pd.to_numeric(df["ask"], errors="coerce")
        )
        df["mid"] = df["mid"] / 2

    if "mid" in df:
        df["mid"] = pd.to_numeric(df["mid"], errors="coerce")

    return df.dropna(subset=["timestamp", "mid"]) if "timestamp" in df and "mid" in df else df


def _normalize_pip_size(metadata: Mapping[str, Any]) -> float:
    pip = _metadata_value(metadata, "pip_size")
    try:
        pip = float(pip)
    except (TypeError, ValueError):
        pip = DEFAULT_PIP_SIZE
    if pip <= 0:
        pip = DEFAULT_PIP_SIZE
    return pip


def _session_window(session: str | None) -> tuple[time, time, str]:
    if not session:
        return ASIAN_SESSION_START, ASIAN_SESSION_END, "Asian session"
    normalized = session.strip().lower()
    for key, window in SESSION_WINDOWS.items():
        if key in normalized:
            return window
    return ASIAN_SESSION_START, ASIAN_SESSION_END, f"{session.strip()} session"


def _calc_session_range_pips(
    df: pd.DataFrame, pip_size: float, session: str | None
) -> tuple[float | None, str]:
    if df.empty or "timestamp" not in df or "mid" not in df:
        return None, "session"

    start, end, label = _session_window(session)
    times = pd.to_datetime(df["timestamp"]).dt.strftime("%H:%M:%S").map(lambda x: time(hour=int(x.split(":")[0]), minute=int(x.split(":")[1]), second=int(x.split(":")[2])))
    if start <= end:
        mask = (times >= start) & (times < end)
    else:
        mask = (times >= start) | (times < end)

    session_slice: pd.Series = pd.Series(df.loc[mask, "mid"]).dropna()
    if session_slice.empty:
        return None, label
    session_range = session_slice.max() - session_slice.min()
    return session_range / pip_size, label


def _calc_avg_30d_range_pips(df: pd.DataFrame, pip_size: float) -> float | None:
    if df.empty or "timestamp" not in df or "mid" not in df:
        return None

    daily = (
        df.set_index("timestamp")["mid"].resample("1D").agg(["max", "min"]).dropna()
    )
    if daily.empty:
        return None
    daily["range"] = daily["max"] - daily["min"]
    last_ranges = daily["range"].tail(AVG_RANGE_LOOKBACK_DAYS)
    if last_ranges.empty:
        return None
    avg_range = last_ranges.mean()
    return avg_range / pip_size


def _calc_compression_ratio(
    session_range_pips: float | None, avg_30d_range_pips: float | None
) -> float | None:
    if session_range_pips is None or avg_30d_range_pips in (None, 0):
        return None
    return session_range_pips / avg_30d_range_pips


def _assemble_drivers(
    session_range_pips: float | None,
    avg_30d_range_pips: float | None,
    compression_ratio: float | None,
    event: str | None,
    event_overlap: str | None,
    session: str | None,
    session_label: str | None,
) -> list[str]:
    drivers: list[str] = []

    compression_text = _compression_message(
        session_range_pips, avg_30d_range_pips, compression_ratio, session_label
    )
    if compression_text:
        drivers.append(compression_text)

    event_driver = _event_message(event, event_overlap)
    if event_driver:
        drivers.append(event_driver)

    if session and event and session.lower() == "london open" and event.strip().upper() == "ECB":
        drivers.append(
            "Pre-London positioning historically precedes volatility expansion on ECB days"
        )

    if not drivers:
        drivers.append("Data insufficient to characterize drivers for the current context")

    return drivers


def _compression_message(
    session_range_pips: float | None,
    avg_30d_range_pips: float | None,
    compression_ratio: float | None,
    session_label: str | None,
) -> str | None:
    if session_range_pips is None or avg_30d_range_pips is None:
        label = session_label or "Session"
        return f"{label} range data unavailable to characterize compression"

    adjective = ""
    if compression_ratio is None:
        adjective = "relative"
    elif compression_ratio <= 0.6:
        adjective = "compressed"
    elif compression_ratio >= 1.4:
        adjective = "expanded"
    else:
        adjective = "in line with" if compression_ratio <= 1 else "slightly above"

    label = session_label or "Session"
    return (
        f"{label} range {adjective} ({_format_pips(session_range_pips)} pips vs 30-day avg of "
        f"{_format_pips(avg_30d_range_pips)})"
    )


def _event_message(event: str | None, event_overlap: str | None) -> str | None:
    if not event:
        return None
    event_label = event.strip().upper()
    overlap_label = (event_overlap or "").strip().upper()

    message = f"{event_label} speech scheduled"
    if overlap_label == "NY":
        message += " during NY overlap"
    elif overlap_label:
        message += f" with overlap into {overlap_label}"
    return message


def _format_pips(value: float) -> str:
    if value is None:
        return "0"
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"


def _metadata_value(metadata: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if metadata is None:
        return default
    return metadata.get(key, default) if isinstance(metadata, Mapping) else getattr(metadata, key, default)
