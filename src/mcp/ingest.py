from __future__ import annotations

from datetime import time
from typing import Iterable

import pandas as pd

SESSION_WINDOWS = {
    "asian": (time(0, 0), time(9, 0)),
    "tokyo": (time(0, 0), time(9, 0)),
    "london": (time(7, 0), time(16, 0)),
    "london open": (time(7, 0), time(16, 0)),
    "ny": (time(12, 30), time(21, 0)),
    "new york": (time(12, 30), time(21, 0)),
}


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
    times = pd.Series(list(timestamps)).dt.time
    if start <= end:
        return (times >= start) & (times < end)
    return (times >= start) | (times < end)
