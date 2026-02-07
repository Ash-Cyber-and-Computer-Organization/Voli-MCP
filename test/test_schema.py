import pytest
from pydantic import ValidationError
from src.mcp.schema import HistoricalContext, MCPOutput


class TestSchema:
    def test_historical_context_valid(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        assert hc.similar_conditions_occurrences == 5
        assert hc.expansion_rate == 0.8

    def test_historical_context_invalid_occurrences(self):
        with pytest.raises(ValidationError):
            HistoricalContext(similar_conditions_occurrences=-1, expansion_rate=0.8)

    def test_historical_context_invalid_expansion_rate(self):
        with pytest.raises(ValidationError):
            HistoricalContext(similar_conditions_occurrences=5, expansion_rate=1.5)

    def test_historical_context_extra_field(self):
        with pytest.raises(ValidationError):
            HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8, **{"extra_field": "invalid"})

    def test_mcp_output_valid(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair="EURUSD",
            session="london",
            time_window_minutes=60,
            volatility_expectation="high",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=["driver1", "driver2"],
            historical_context=hc,
            agent_guidance="guidance text"
        )
        assert mcp.pair == "EURUSD"
        assert mcp.session == "london"
        assert mcp.time_window_minutes == 60
        assert mcp.volatility_expectation == "high"
        assert mcp.expected_deviation_pips == 50.0
        assert mcp.confidence == 0.9
        assert mcp.drivers == ["driver1", "driver2"]
        assert mcp.historical_context == hc
        assert mcp.agent_guidance == "guidance text"

    def test_mcp_output_invalid_pair_empty(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_session_empty(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_time_window(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=0,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_volatility_expectation_empty(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_expected_deviation_negative(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=-1.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_confidence(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=1.5,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_drivers_empty_list(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=[],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_driver_blank(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["", "driver2"],
                historical_context=hc,
                agent_guidance="guidance"
            )

    def test_mcp_output_invalid_agent_guidance_empty(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance=""
            )

    def test_mcp_output_strip_strings(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        mcp = MCPOutput(
            pair=" EURUSD ",
            session=" london ",
            time_window_minutes=60,
            volatility_expectation=" high ",
            expected_deviation_pips=50.0,
            confidence=0.9,
            drivers=[" driver1 ", " driver2 "],
            historical_context=hc,
            agent_guidance=" guidance "
        )
        assert mcp.pair == "EURUSD"
        assert mcp.session == "london"
        assert mcp.volatility_expectation == "high"
        assert mcp.drivers == ["driver1", "driver2"]
        assert mcp.agent_guidance == "guidance"

    def test_mcp_output_extra_field(self):
        hc = HistoricalContext(similar_conditions_occurrences=5, expansion_rate=0.8)
        with pytest.raises(ValidationError):
            MCPOutput(
                pair="EURUSD",
                session="london",
                time_window_minutes=60,
                volatility_expectation="high",
                expected_deviation_pips=50.0,
                confidence=0.9,
                drivers=["driver1"],
                historical_context=hc,
                agent_guidance="guidance",
                **{"extra_field": "invalid"}
            )
