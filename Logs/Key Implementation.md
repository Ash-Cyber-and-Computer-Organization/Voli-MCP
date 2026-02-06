- **Schema** (`src/mcp/schema.py`)
  - Use `pydantic.BaseModel` to define `HistoricalContext` and `MCPOutput`.
  - Example model (fields + validators; defaults are not required but tests will assert values match the sample output).

- **Ingestion** (`src/mcp/ingest.py`)
  - Provide `read_csv(path)` → returns `pandas.DataFrame` with columns `timestamp`, `bid`, `ask`, `mid`.
  - Provide `resample_session(df, session_name, window_minutes)` helper.

- **Features** (`src/mcp/features.py`)
  - Compute:
    - `asian_range_pips` (e.g., 18),
    - `avg_30d_range_pips` (e.g., 32),
    - `compression_ratio = asian_range / avg_30d`.
  - Detect known calendar events: input metadata flag `event='ECB'` and `event_overlap='NY'`.
  - Return `drivers` list assembled from computed facts and metadata.

- **Engine rules (deterministic mapping)** (`src/mcp/engine.py`)
  - Input: `pair`, `df`, `metadata` (session, window, events).
  - Rule example to reproduce sample output:
    - If `asian_range_pips <= 0.6 * avg_30d_range_pips` AND `metadata.event == 'ECB'` AND `session == 'London Open'`:
      - `volatility_expectation = "High"`
      - `expected_deviation_pips = 38` (map from historical expansion rate * avg_range or fixed bucket)
      - `confidence = 0.74` (derived from expansion_rate and occurrence frequency; e.g., 0.62 expansion_rate → base_conf=0.7, scaled by occurrence factor → 0.74)
      - `drivers` = [
        f"Asian session range compressed ({asian_range_pips} pips vs 30-day avg of {avg_30d_range_pips})",
        "ECB speech scheduled during NY overlap",
        "Pre-London positioning historically precedes volatility expansion on ECB days"
      ]
      - `historical_context` = { similar_conditions_occurrences: 112, expansion_rate: 0.62 }
      - `agent_guidance` = fixed string shown in sample

  - Provide hook `load_historical_stats()` to compute `similar_conditions_occurrences` and `expansion_rate` (for reproducible demos this can be loaded from `examples/historical_stats.json`).

- **Output & validation** (`src/mcp/output.py`)
  - Build `MCPOutput` via `schema.MCPOutput(...)` and `model.dict()` for JSON.
  - Serialize with `orjson.dumps()` for speed.
  - Save to `./out/{pair}-{timestamp}.json`.
  - Expose `validate_and_format(result)` that raises clear errors on mismatch.

- **API** (`src/mcp/api.py`)
  - FastAPI app with:
    - POST `/generate` accepts:
      - multipart CSV upload OR `data_url` OR `metadata` (pair, session, event flags).
    - Returns validated JSON matching `MCPOutput`.
    - GET `/schema` returns the JSON Schema exported from `pydantic`.

- **CLI** (`src/mcp/cli.py`)
  - Commands:
    - `mcp generate --csv examples/data/sample_eurusd.csv --pair EURUSD --session "London Open" --event ECB --out out/sample.json`
    - `mcp serve --port 8000`