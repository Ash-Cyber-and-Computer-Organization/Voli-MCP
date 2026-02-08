import pytest
import orjson
from pathlib import Path
from src.mcp.output import validate_and_format, format_output, save_output
from src.mcp.schema import MCPOutput, HistoricalContext


class TestOutput:
    def test_validate_and_format_dict(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        payload = {
            "pair": "EURUSD",
            "session": "london",
            "time_window_minutes": 60,
            "volatility_expectation": "high",
            "expected_deviation_pips": 50.0,
            "confidence": 0.9,
            "drivers": ["driver1"],
            "historical_context": hc.dict(),
            "agent_guidance": "guidance"
        }
        result = validate_and_format(payload)
        assert isinstance(result, MCPOutput)
        assert result.pair == "EURUSD"

    def test_validate_and_format_mcp_output(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair="EURUSD",
            session="london",
            time_window_minutes=60,
            volatility_expectation="high",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=["driver1"],
            historical_context=hc,
            agent_guidance="guidance"
        )
        result = validate_and_format(mcp)
        assert result == mcp

    def test_format_output(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair="EURUSD",
            session="london",
            time_window_minutes=60,
            volatility_expectation="high",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=["driver1"],
            historical_context=hc,
            agent_guidance="guidance"
        )
        result = format_output(mcp)
        assert isinstance(result, bytes)
        parsed = orjson.loads(result)
        assert parsed["pair"] == "EURUSD"

    def test_save_output_default_path(self, tmp_path):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair="EURUSD",
            session="london",
            time_window_minutes=60,
            volatility_expectation="high",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=["driver1"],
            historical_context=hc,
            agent_guidance="guidance"
        )
        # Change to tmp_path for testing
        import src.mcp.output
        original_out_dir = src.mcp.output.OUT_DIR
        src.mcp.output.OUT_DIR = tmp_path
        try:
            path = save_output(mcp)
            assert path.exists()
            assert path.name.startswith("eurusd-")
            assert path.suffix == ".json"
        finally:
            src.mcp.output.OUT_DIR = original_out_dir

    def test_save_output_custom_path(self, tmp_path):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair="EURUSD",
            session="london",
            time_window_minutes=60,
            volatility_expectation="high",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=["driver1"],
            historical_context=hc,
            agent_guidance="guidance"
        )
        custom_path = tmp_path / "custom.json"
        path = save_output(mcp, custom_path)
        assert path == custom_path
        assert path.exists()
