from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

import pandas as pd

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import ORJSONResponse

from .engine import generate
from .ingest import read_csv
from .schema import MCPOutput

app = FastAPI(title="Forex MCP", default_response_class=ORJSONResponse)


@app.post("/generate", response_model=MCPOutput)
async def generate_endpoint(
    pair: str = Form(...),
    session: str = Form(...),
    time_window_minutes: int = Form(...),
    event: Optional[str] = Form(None),
    event_overlap: Optional[str] = Form(None),
    historical_stats_path: Optional[str] = Form(None),
    csv_file: Optional[UploadFile] = File(None),
    data_url: Optional[str] = Form(None),
) -> MCPOutput:
    """Generate MCP output from uploaded CSV or a previously stored CSV path."""

    df = await _load_dataframe(csv_file, data_url)
    metadata = {
        "session": session,
        "time_window_minutes": time_window_minutes,
        "event": event,
        "event_overlap": event_overlap,
        "historical_stats_path": historical_stats_path,
    }
    return generate(pair, df, metadata)


@app.get("/schema")
def schema() -> dict:
    """Return the JSON schema for the MCP output contract."""

    return MCPOutput.schema()


async def _load_dataframe(
    csv_file: Optional[UploadFile], data_url: Optional[str]
) -> "pd.DataFrame":
    if csv_file:
        return await _dataframe_from_upload(csv_file)
    if data_url:
        path = Path(data_url.replace("file://", "")) if data_url.startswith("file://") else Path(data_url)
        if not path.exists():
            raise HTTPException(422, detail="data_url must point to an existing CSV")
        return read_csv(str(path))
    raise HTTPException(400, detail="Please provide a CSV file upload or data_url")


async def _dataframe_from_upload(upload: UploadFile) -> "pd.DataFrame":
    with NamedTemporaryFile("wb", suffix=".csv", delete=False) as tmp:
        tmp.write(await upload.read())
        temp_path = Path(tmp.name)
    try:
        return read_csv(str(temp_path))
    finally:
        temp_path.unlink(missing_ok=True)
