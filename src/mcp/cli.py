from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from .engine import generate
from .ingest import read_csv
from .output import save_output, validate_and_format

app = typer.Typer(help="Command-line entrypoints into the MCP toolset.")


@app.command()
def generate_command(
    csv: Path = typer.Option(..., exists=True, file_okay=True, dir_okay=False),
    pair: str = typer.Option(..., help="Forex pair for the forecast"),
    session: str = typer.Option(..., help="Session label (e.g., London Open)"),
    event: Optional[str] = typer.Option(None, help="Calendar event flag"),
    event_overlap: Optional[str] = typer.Option(None, help="Event overlap label such as NY"),
    time_window_minutes: int = typer.Option(90, help="Minutes covered by the time window"),
    historical_stats_path: Optional[Path] = typer.Option(
        None, help="Optional path to historical stats JSON"
    ),
    out: Optional[Path] = typer.Option(None, help="Optional custom output path"),
) -> None:
    """Generate MCP output from a CSV file."""

    df = read_csv(str(csv))
    metadata = {
        "session": session,
        "event": event,
        "event_overlap": event_overlap,
        "time_window_minutes": time_window_minutes,
        "historical_stats_path": str(historical_stats_path) if historical_stats_path else None,
    }
    result = generate(pair, df, metadata)
    validated = validate_and_format(result)
    path = save_output(validated, out)
    typer.secho(f"Saved MCP output to {path}", fg=typer.colors.GREEN)


@app.command()
def serve(port: int = typer.Option(8000, help="Port for the FastAPI service")) -> None:
    """Serve the MCP FastAPI app over HTTP."""

    import uvicorn

    uvicorn.run("src.mcp.api:app", host="0.0.0.0", port=port, log_level="info")
