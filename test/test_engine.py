import pytest
import json
from pathlib import Path
import pandas as pd
from src.mcp.engine import (
    load_historical_stats,
    _normalize_time_window,
    generate,
    _derive_volatility,
    _agent_guidance,
    generate_from_hypothesis
)
from src.mcp.schema import HistoricalContext


class TestEngine:
    def test_load_historical_stats_existing_file(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        stats_data = {"similar_conditions_occurrences": 10, "expansion_rate": 0.5}
        stats_file.write_text(json.dumps(stats_data))

        result = load_historical_stats(stats_file)
        assert result == stats_data

    def test_load_historical_stats_missing_file(self):
        result = load_historical_stats("nonexistent.json")
        assert result == {"similar_conditions_occurrences": 112, "expansion_rate": 0.62}

    def test_normalize_time_window_valid(self):
        metadata = {"time_window_minutes": 60}
        assert _normalize_time_window(metadata) == 60

    def test_normalize_time_window_invalid(self):
        metadata = {"time_window_minutes": "invalid"}
        assert _normalize_time_window(metadata) == 90

    def test_normalize_time_window_none(self):
        metadata = {}
        assert _normalize_time_window(metadata) == 90

    def test_normalize_time_window_negative(self):
        metadata = {"time_window_minutes": -10}
        assert _normalize_time_window(metadata) == 1

    '''def test_generate(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01 08:00:00', periods=10, freq='H'),
            'bid': [1.1000 + i * 0.0001 for i in range(10)],
            'ask': [1.1010 + i * 0.0001 for i in range(10)],
            'mid': [1.1005 + i * 0.0001 for i in range(10)]
        })
        metadata = {
            "session": "asian",
            "event": "ECB",
            "event_overlap": "NY",
            "time_window_minutes": 60
        }
        result = generate("EURUSD", df, metadata)
        assert result.pair == "EURUSD"
        assert result.session == "asian"
        assert result.time_window_minutes == 60
        assert isinstance(result.drivers, list)'''

    def test_derive_volatility_high(self):
        from src.mcp.features import FeatureSet
        features = FeatureSet(
            session_range_pips=10.0,
            avg_30d_range_pips=20.0,
            compression_ratio=0.5,
            drivers=[],
            event="ECB",
            event_overlap="NY"
        )
        context = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        metadata = {"event": "ECB", "session": "london open"}
        expectation, deviation, confidence = _derive_volatility(features, context, metadata)
        assert expectation == "High"
        assert deviation >= 38.0

    def test_derive_volatility_moderate(self):
        from src.mcp.features import FeatureSet
        features = FeatureSet(
            session_range_pips=15.0,
            avg_30d_range_pips=20.0,
            compression_ratio=0.75,
            drivers=[],
            event=None,
            event_overlap=None
        )
        context = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        metadata = {}
        expectation, deviation, confidence = _derive_volatility(features, context, metadata)
        assert expectation == "Moderate"

    def test_derive_volatility_low(self):
        from src.mcp.features import FeatureSet
        features = FeatureSet(
            session_range_pips=25.0,
            avg_30d_range_pips=20.0,
            compression_ratio=1.25,
            drivers=[],
            event=None,
            event_overlap=None
        )
        context = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        metadata = {}
        expectation, deviation, confidence = _derive_volatility(features, context, metadata)
        assert expectation == "Low"

    def test_agent_guidance_high(self):
        guidance = _agent_guidance("High")
        assert "Avoid mean-reversion" in guidance

    def test_agent_guidance_low(self):
        guidance = _agent_guidance("Low")
        assert "Sweep for consolidation" in guidance

    def test_agent_guidance_moderate(self):
        guidance = _agent_guidance("Moderate")
        assert "Monitor range dynamics" in guidance

    def test_generate_from_hypothesis(self):
        hypothesis = {
            "pair": "EURUSD",
            "session": "london open",
            "time_window_minutes": 60,
            "asian_range_pips": 10.0,
            "avg_30d_range_pips": 20.0,
            "historical": {"similar_conditions_occurrences": 5, "expansion_rate": 0.8}
        }
        result = generate_from_hypothesis(hypothesis)
        assert result.pair == "EURUSD"
        assert result.volatility_expectation == "High"
        assert result.expected_deviation_pips == 38.0
        assert result.confidence == 0.74
