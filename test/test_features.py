import pytest
import pandas as pd
from datetime import datetime, time
from src.mcp.features import (
    compute_features,
    _prepare_df,
    _normalize_pip_size,
    _session_window,
    _calc_session_range_pips,
    _calc_avg_30d_range_pips,
    _calc_compression_ratio,
    _assemble_drivers,
    _compression_message,
    _event_message,
    _format_pips,
    _metadata_value,
    FeatureSet,
)


class TestFeatures:
    def test_prepare_df_with_timestamp_and_mid(self):
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00', '2023-01-01 11:00:00'],
            'mid': [1.1000, 1.1010]
        })
        result = _prepare_df(df)
        assert not result.empty
        assert 'timestamp' in result.columns
        assert 'mid' in result.columns

    def test_prepare_df_with_bid_ask(self):
        df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00'],
            'bid': [1.1000],
            'ask': [1.1010]
        })
        result = _prepare_df(df)
        assert 'mid' in result.columns
        assert result['mid'].iloc[0] == 1.1005

    def test_normalize_pip_size_valid(self):
        metadata = {'pip_size': 0.0001}
        assert _normalize_pip_size(metadata) == 0.0001

    def test_normalize_pip_size_invalid(self):
        metadata = {'pip_size': 'invalid'}
        assert _normalize_pip_size(metadata) == 0.0001  # default

    def test_session_window_default(self):
        start, end, label = _session_window(None)
        assert start == time(0, 0)
        assert end == time(9, 0)
        assert label == "Asian session"

    def test_session_window_london(self):
        start, end, label = _session_window("london")
        assert start == time(7, 0)
        assert end == time(16, 0)
        assert label == "London session"

    def test_calc_session_range_pips(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01 08:00:00', periods=10, freq='h'),
            'mid': [1.1000 + i * 0.0001 for i in range(10)]
        })
        pip_size = 0.0001
        session = "asian"
        range_pips, label = _calc_session_range_pips(df, pip_size, session)
        assert range_pips is not None
        assert label == "Asian session"

    def test_calc_avg_30d_range_pips(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01', periods=30, freq='D'),
            'mid': [1.1000 + i * 0.001 for i in range(30)]
        })
        pip_size = 0.0001
        avg_range = _calc_avg_30d_range_pips(df, pip_size)
        assert avg_range is not None

    def test_calc_compression_ratio(self):
        ratio = _calc_compression_ratio(10.0, 20.0)
        assert ratio == 0.5

    def test_assemble_drivers(self):
        drivers = _assemble_drivers(10.0, 20.0, 0.5, "ECB", "NY", "london", "London session")
        assert len(drivers) > 0

    def test_compression_message(self):
        msg = _compression_message(10.0, 20.0, 0.5, "Session")
        assert msg is not None
        assert "compressed" in msg

    def test_event_message(self):
        msg = _event_message("ECB", "NY")
        assert "ECB speech scheduled during NY overlap" == msg

    def test_format_pips(self):
        assert _format_pips(10.5) == "10.5"
        assert _format_pips(10.0) == "10"

    def test_metadata_value(self):
        metadata = {'key': 'value'}
        assert _metadata_value(metadata, 'key') == 'value'
        assert _metadata_value(metadata, 'missing', 'default') == 'default'

    def test_compute_features(self):
        df = pd.DataFrame({
            'timestamp': pd.date_range('2023-01-01 08:00:00', periods=10, freq='D'),
            'mid': [1.1000 + i * 0.0001 for i in range(10)]
        })
        metadata = {'session': 'asian', 'pip_size': 0.0001, 'event': 'ECB', 'event_overlap': 'NY'}
        feature_set = compute_features(df, metadata)
        assert isinstance(feature_set, FeatureSet)
        assert feature_set.session_range_pips is not None
