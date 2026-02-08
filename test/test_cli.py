import pytest
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner
from src.mcp.cli import app


class TestCli:
    runner = CliRunner()

    def test_generate_command(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("""timestamp,bid,ask
2023-01-01 10:00:00,1.1000,1.1010
2023-01-01 11:00:00,1.1005,1.1015""")
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        with patch('src.mcp.cli.save_output') as mock_save:
            mock_save.return_value = Path("mocked_path.json")
            result = self.runner.invoke(app, [
                "generate-command",
                "--csv", str(csv_file),
                "--pair", "EURUSD",
                "--session", "asian",
                "--event", "ECB",
                "--event-overlap", "NY",
                "--time-window-minutes", "60"
            ])
            assert result.exit_code == 0
            assert "Saved MCP output" in result.output
            mock_save.assert_called_once()

    def test_serve_command(self):
        with patch('uvicorn.run') as mock_run:
            result = self.runner.invoke(app, ["serve", "--port", "8080"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(
                "src.mcp.api:app",
                host="0.0.0.0",
                port=8080,
                log_level="info"
            )
