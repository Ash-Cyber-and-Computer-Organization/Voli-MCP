import httpx
import pytest
import pandas as pd
from datetime import datetime, time
from src.mcp.ingest import (
    read_csv,
    resample_session,
    _session_window,
    _session_mask,
    pipeline_from_csv,
)


class TestIngest:
    def test_read_csv_valid(self, tmp_path):
        csv_content = """timestamp,bid,ask
2023-01-01 10:00:00,1.1000,1.1010
2023-01-01 11:00:00,1.1005,1.1015"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        df = read_csv(str(csv_file))
        assert not df.empty
        assert 'timestamp' in df.columns
        assert 'bid' in df.columns
        assert 'ask' in df.columns
        assert 'mid' in df.columns
        assert df['mid'].iloc[0] == 1.1005

    def test_read_csv_missing_timestamp(self, tmp_path):
        csv_content = """bid,ask
1.1000,1.1010"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="CSV must include a 'timestamp' column"):
            read_csv(str(csv_file))

    def test_read_csv_missing_bid(self, tmp_path):
        csv_content = """timestamp,ask
2023-01-01 10:00:00,1.1010"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        with pytest.raises(ValueError, match="CSV must include a 'bid' column"):
            read_csv(str(csv_file))

    def test_read_csv_with_mid(self, tmp_path):
        csv_content = """timestamp,bid,ask,mid
2023-01-01 10:00:00,1.1000,1.1010,1.1005"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        df = read_csv(str(csv_file))
        assert df['mid'].iloc[0] == 1.1005

    '''def test_resample_session_valid(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01 08:00:00', periods=10, freq='D'),
            'bid': [1.1000 + i * 0.0001 for i in range(10)],
            'ask': [1.1010 + i * 0.0001 for i in range(10)],
            'mid': [1.1005 + i * 0.0001 for i in range(10)]
        })
        df.set_index('timestamp', inplace=True)
        result = resample_session(df, "asian", 60)
        assert not result.empty
        assert 'bid' in result.columns
        assert 'ask' in result.columns'''

    def test_resample_session_invalid_window(self):
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00'],
            'mid': [1.1005]
        })
        with pytest.raises(ValueError, match="window_minutes must be a positive integer"):
            resample_session(df, "asian", 0)

    def test_resample_session_missing_columns(self):
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00']
        })
        with pytest.raises(ValueError, match="DataFrame must contain 'timestamp' and 'mid' columns"):
            resample_session(df, "asian", 60)

    def test_resample_session_invalid_timestamp(self):
        df = pd.DataFrame({
            'timestamp': ['invalid'],
            'mid': [1.1005]
        })
        with pytest.raises(ValueError, match="Invalid timestamps present in DataFrame"):
            resample_session(df, "asian", 60)

    def test_session_window_default(self):
        start, end = _session_window(None)
        assert start == time(0, 0)
        assert end == time(9, 0)

    def test_session_window_london(self):
        start, end = _session_window("london")
        assert start == time(7, 0)
        assert end == time(16, 0)

    def test_session_mask_same_day(self):
        timestamps = pd.to_datetime(['2023-01-01 08:00:00', '2023-01-01 10:00:00'])
        mask = _session_mask(timestamps, time(7, 0), time(16, 0))
        assert mask.iloc[0] == True
        assert mask.iloc[1] == True

    def test_session_mask_overnight(self):
        timestamps = pd.to_datetime(['2023-01-01 22:00:00', '2023-01-01 02:00:00'])
        mask = _session_mask(timestamps, time(22, 0), time(6, 0))
        assert mask.iloc[0] == True
        assert mask.iloc[1] == True

    def test_pipeline_from_csv_calls_api(self, tmp_path, monkeypatch):
        csv_file = tmp_path / "pipeline.csv"
        csv_file.write_text("timestamp,bid,ask\n2023-01-01 09:00:00,1.1000,1.1010")

        class DummyResponse:
            def raise_for_status(self): pass

            def json(self):
                return {
                    "pair": "EURUSD",
                    "session": "London Open",
                    "time_window_minutes": 90,
                    "volatility_expectation": "High",
                    "expected_deviation_pips": 38.0,
                    "confidence": 0.74,
                    "drivers": [
                        "Asian session range compressed (18 pips vs 30-day avg of 32)",
                        "ECB speech scheduled during NY overlap",
                    ],
                    "historical_context": {"similar_conditions_occurrences": 112, "expansion_rate": 0.62},
                    "agent_guidance": "Avoid mean-reversion strategies; favor breakout or momentum confirmation setups.",
                }

        def fake_post(url, data=None, files=None, timeout=None):
            assert "generate" in url
            assert data["pair"] == "EURUSD" # type: ignore
            assert files is not None
            assert "csv_file" in files
            return DummyResponse()

        monkeypatch.setattr(httpx, "post", fake_post)
        result = pipeline_from_csv(
            csv_file,
            "EURUSD",
            "London Open",
            time_window_minutes=90,
            event="ECB",
            event_overlap="NY",
        )
        assert result.pair == "EURUSD"
        assert result.session == "London Open"
