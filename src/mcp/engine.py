from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from .features import FeatureSet, compute_features
from .schema import HistoricalContext, MCPOutput

DEFAULT_HISTORICAL_STATS = (
    Path(__file__).resolve().parent.parent / "examples" / "historical_stats.json"
)


def load_historical_stats(path: str | Path | None = None) -> Mapping[str, Any]:
    """Load historical occurrence counts and expansion rates from disk or return a fallback."""

    target = Path(path) if path else DEFAULT_HISTORICAL_STATS
    if target.exists():
        with target.open() as fh:
            return json.load(fh)
    return {"similar_conditions_occurrences": 112, "expansion_rate": 0.62}


def _normalize_time_window(metadata: Mapping[str, Any]) -> int:
    window = metadata.get("time_window_minutes")
    if window is None:
        return 90
    try:
        window = int(window)
    except (TypeError, ValueError):
        return 90
    return max(1, window)


def generate(
    pair: str, df: pd.DataFrame, metadata: Mapping[str, Any]
) -> MCPOutput:
    """Primary deterministic MCP entry point that projects the JSON output shape."""

    features = compute_features(df, metadata)
    stats = load_historical_stats(metadata.get("historical_stats_path"))
    historical_context = HistoricalContext(**stats)
    drivers = list(features.drivers)
    expectation, deviation, confidence = _derive_volatility(
        features, historical_context, metadata
    )
    return MCPOutput(
        pair=pair,
        session=str(metadata.get("session") or "Unknown"),
        time_window_minutes=_normalize_time_window(metadata),
        volatility_expectation=expectation,
        expected_deviation_pips=deviation,
        confidence=confidence,
        drivers=drivers,
        historical_context=historical_context,
        agent_guidance=_agent_guidance(expectation),
    )


def _derive_volatility(
    features: FeatureSet, context: HistoricalContext, metadata: Mapping[str, Any]
) -> tuple[str, float, float]:
    avg_range = features.avg_30d_range_pips or 20.0
    ratio = features.compression_ratio or 1.0
    event = (metadata.get("event") or "").strip().upper()
    session = (metadata.get("session") or "").strip().lower()
    base_dev = avg_range * (1 + context.expansion_rate / 2)
    expectation = "Moderate"
    confidence = 0.55
    deviation = round(base_dev, 1)

    if event == "ECB" and "london open" in session and ratio <= 0.6:
        expectation = "High"
        deviation = max(deviation, 38.0)
        confidence = min(0.95, 0.7 + (0.6 - ratio) * 0.2 + context.expansion_rate * 0.1)
    elif ratio < 0.9:
        expectation = "Moderate"
        confidence = min(0.8, 0.6 + (0.9 - ratio) * 0.1)
    else:
        expectation = "Low"
        confidence = max(0.35, 0.5 - (ratio - 1) * 0.1)

    return expectation, deviation, round(confidence, 2)


def _agent_guidance(expectation: str) -> str:
    if expectation == "High":
        return "Avoid mean-reversion strategies; favor breakout or momentum confirmation setups."
    if expectation == "Low":
        return "Sweep for consolidation and liquidity before extending directional bets."
    return "Monitor range dynamics and let expansion mechanics confirm before adding risk."


def generate_from_hypothesis(hypothesis: Mapping[str, Any]) -> MCPOutput:
    """Deterministic helper that mirrors the recorded sample output for demos."""

    historical = HistoricalContext(**hypothesis["historical"])
    event = hypothesis.get("event", "ECB")
    overlap = hypothesis.get("event_overlap", "NY")
    drivers: Sequence[str] = [
        f"Asian session range compressed ({hypothesis['asian_range_pips']} pips vs 30-day avg of {hypothesis['avg_30d_range_pips']})",
        f"{event} speech scheduled during {overlap} overlap",
        "Pre-London positioning historically precedes volatility expansion on ECB days",
    ]
    return MCPOutput(
        pair=hypothesis["pair"],
        session=hypothesis["session"],
        time_window_minutes=hypothesis["time_window_minutes"],
        volatility_expectation="High",
        expected_deviation_pips=38.0,
        confidence=0.74,
        drivers=list(drivers),
        historical_context=historical,
        agent_guidance="Avoid mean-reversion strategies; favor breakout or momentum confirmation setups.",
    )
