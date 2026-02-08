from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Union

import orjson

from .schema import MCPOutput

OUT_DIR = Path("out")


def validate_and_format(payload: MCPOutput | dict) -> MCPOutput:
    """Ensure the payload conforms to the MCP output schema."""

    if isinstance(payload, MCPOutput):
        return payload
    return MCPOutput(**payload)


def format_output(output: MCPOutput) -> bytes:
    """Serialize the validated output using orjson."""

    return orjson.dumps(output.dict())


def save_output(output: MCPOutput, path: Path | str | None = None) -> Path:
    """Persist the serialized payload to out/{pair}-{timestamp}.json."""

    OUT_DIR.mkdir(exist_ok=True)
    if path is None:
        safe_pair = output.pair.lower().replace(" ", "_")
        filename = f"{safe_pair}-{datetime.utcnow():%Y%m%dT%H%M%SZ}.json"
        path_obj = OUT_DIR / filename
    else:
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)

    path_obj.write_bytes(format_output(output))
    return path_obj
