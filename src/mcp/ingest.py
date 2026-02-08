from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Iterable

import httpx
import pandas as pd

from .schema import MCPOutput

SESSION_WINDOWS = {
    "asian": (time(0, 0), time(9, 0)),
    "tokyo": (time(0, 0), time(9, 0)),
    "london": (time(7, 0), time(16, 0)),
    "london open": (time(7, 0), time(16, 0)),
    "ny": (time(12, 30), time(21, 0)),
    "new york": (time(12, 30), time(21, 0)),
}

DEFAULT_API_BASE_URL = "http://localhost:8000"
DEFAULT_API_TIMEOUT = 30.0


def read_csv(path: str) -> pd.DataFrame:
    """Load the FX time series and ensure timestamp/bid/ask/mid columns exist."""

    df = pd.read_csv(path)
    if "timestamp" not in df:
        raise ValueError("CSV must include a 'timestamp' column")
    for col in ("bid", "ask"):
        if col not in df:
            raise ValueError(f"CSV must include a '{col}' column")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="raise")
    df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
    df["ask"] = pd.to_numeric(df["ask"], errors="coerce")

    if "mid" not in df:
        df["mid"] = (df["bid"] + df["ask"]) / 2
    else:
        df["mid"] = pd.to_numeric(df["mid"], errors="coerce")

    required = ["timestamp", "bid", "ask", "mid"]
    df = df.loc[:, required].dropna(subset=required).sort_values("timestamp")
    return df.reset_index(drop=True)


def resample_session(
    df: pd.DataFrame, session_name: str | None, window_minutes: int
) -> pd.DataFrame:
    """Filter a trading session and resample to uniform time buckets."""

    if window_minutes <= 0:
        raise ValueError("window_minutes must be a positive integer")
    if "timestamp" not in df or "mid" not in df:
        raise ValueError("DataFrame must contain 'timestamp' and 'mid' columns")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    if df["timestamp"].isna().any():
        raise ValueError("Invalid timestamps present in DataFrame")

    window = _session_window(session_name)
    start, end = window
    mask = _session_mask(df["timestamp"], start, end)
    session_slice = df.loc[mask].copy()
    if session_slice.empty:
        return session_slice.iloc[0:0]

    resampled = (
        session_slice.set_index("timestamp")[["bid", "ask", "mid"]]
        .resample(f"{window_minutes}T")
        .last()
        .dropna(subset=["mid"])
        .reset_index()
    )
    return resampled


def _session_window(session_name: str | None) -> tuple[time, time]:
    if not session_name:
        return SESSION_WINDOWS["asian"]
    normalized = session_name.strip().lower()
    for key, window in SESSION_WINDOWS.items():
        if key in normalized:
            return window
    return SESSION_WINDOWS["asian"]


def _session_mask(
    timestamps: Iterable[pd.Timestamp], start: time, end: time
) -> pd.Series:
    times = pd.Series(pd.DatetimeIndex(list(timestamps)).time)
    if start <= end:
        return (times >= start) & (times < end)
    return (times >= start) | (times < end)


def pipeline_from_dataframe(
    df: pd.DataFrame,
    pair: str,
    session: str,
    time_window_minutes: int,
    event: str | None = None,
    event_overlap: str | None = None,
    historical_stats_path: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout: float = DEFAULT_API_TIMEOUT,
) -> "MCPOutput":
    """Use the MCP API to execute the full pipeline on a prepared DataFrame."""

    csv_payload = df.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S").encode("utf-8")
    return _post_to_api(
        csv_bytes=csv_payload,
        pair=pair,
        session=session,
        time_window_minutes=time_window_minutes,
        event=event,
        event_overlap=event_overlap,
        historical_stats_path=historical_stats_path,
        api_base_url=api_base_url,
        timeout=timeout,
    )


def pipeline_from_csv(
    csv_path: Path | str,
    pair: str,
    session: str,
    time_window_minutes: int,
    event: str | None = None,
    event_overlap: str | None = None,
    historical_stats_path: str | None = None,
    api_base_url: str = DEFAULT_API_BASE_URL,
    timeout: float = DEFAULT_API_TIMEOUT,
) -> "MCPOutput":
    """Pipe a CSV through MCP preprocessing and POST the data to the API."""

    df = read_csv(str(csv_path))
    return pipeline_from_dataframe(
        df,
        pair=pair,
        session=session,
        time_window_minutes=time_window_minutes,
        event=event,
        event_overlap=event_overlap,
        historical_stats_path=historical_stats_path,
        api_base_url=api_base_url,
        timeout=timeout,
    )


def _post_to_api(
    *,
    csv_bytes: bytes | None,
    pair: str,
    session: str,
    time_window_minutes: int,
    event: str | None,
    event_overlap: str | None,
    historical_stats_path: str | None,
    api_base_url: str,
    timeout: float,
) -> "MCPOutput":
    from .schema import MCPOutput

    url = f"{api_base_url.rstrip('/')}/generate"
    data = {
        "pair": pair,
        "session": session,
        "time_window_minutes": time_window_minutes,
        "event": event or "",
        "event_overlap": event_overlap or "",
        "historical_stats_path": historical_stats_path or "",
    }
    files = {"csv_file": ("data.csv", csv_bytes, "text/csv")} if csv_bytes else None
    response = httpx.post(url, data=data, files=files, timeout=timeout)
    response.raise_for_status()
    return MCPOutput(**response.json())
