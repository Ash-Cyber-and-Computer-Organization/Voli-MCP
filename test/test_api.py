import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.mcp.api import app


class TestApi:
    client = TestClient(app)

    def test_schema_endpoint(self):
        response = self.client.get("/schema")
        assert response.status_code == 200
        data = response.json()
        assert "properties" in data
        assert "pair" in data["properties"]

    @patch('src.mcp.api._load_dataframe')
    @patch('src.mcp.api.generate')
    def test_generate_endpoint_with_csv_file(self, mock_generate, mock_load_df):
        import pandas as pd
        mock_df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00'],
            'bid': [1.1000],
            'ask': [1.1010],
            'mid': [1.1005]
        })
        mock_load_df.return_value = mock_df
        mock_generate.return_value = {
            "pair": "EURUSD",
            "session": "asian",
            "time_window_minutes": 60,
            "volatility_expectation": "Moderate",
            "expected_deviation_pips": 20.0,
            "confidence": 0.5,
            "drivers": ["test driver"],
            "historical_context": {"similar_conditions_occurrences": 10, "expansion_rate": 0.6},
            "agent_guidance": "Test guidance"
        }

        response = self.client.post("/generate", data={
            "pair": "EURUSD",
            "session": "asian",
            "time_window_minutes": 60
        })
        assert response.status_code == 200
        data = response.json()
        assert data["pair"] == "EURUSD"

    def test_generate_endpoint_missing_csv_and_url(self):
        response = self.client.post("/generate", data={
            "pair": "EURUSD",
            "session": "asian",
            "time_window_minutes": 60
        })
        assert response.status_code == 400
        assert "Please provide a CSV file upload or data_url" in response.json()["detail"]

    @patch('src.mcp.api.read_csv')
    def test_load_dataframe_with_data_url(self, mock_read_csv):
        import pandas as pd
        mock_df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00'],
            'bid': [1.1000],
            'ask': [1.1010],
            'mid': [1.1005]
        })
        mock_read_csv.return_value = mock_df

        from src.mcp.api import _load_dataframe
        result = _load_dataframe(None, "file:///tmp/test.csv")
        assert not result.empty

    def test_load_dataframe_invalid_data_url(self):
        from src.mcp.api import _load_dataframe
        with pytest.raises(Exception):  # HTTPException
            _load_dataframe(None, "file:///nonexistent.csv")

    '''@patch('src.mcp.api.NamedTemporaryFile')
    @patch('src.mcp.api.read_csv')
    async def test_dataframe_from_upload(self, mock_read_csv, mock_temp_file):
        import pandas as pd
        mock_df = pd.DataFrame({
            'timestamp': ['2023-01-01 10:00:00'],
            'bid': [1.1000],
            'ask': [1.1010],
            'mid': [1.1005]
        })
        mock_read_csv.return_value = mock_df'''

        mock_temp = mock_temp_file.return_value.__enter__.return_value
        mock_temp.name = "/tmp/test.csv"

        from src.mcp.api import _dataframe_from_upload
        from fastapi import UploadFile
        import io

        upload = UploadFile(filename="test.csv", file=io.BytesIO(b"data"))
        result = await _dataframe_from_upload(upload)
        assert not result.empty
