from __future__ import annotations

from typing import Sequence

from pydantic import BaseModel, Field, validator


class HistoricalContext(BaseModel):
    """Historical analog statistics referenced by the engine."""

    similar_conditions_occurrences: int = Field(
        ...,
        ge=0,
        description="Number of historical times the triggering conditions materialized",
    )
    expansion_rate: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Historic range expansion factor observed in the analogous conditions",
    )

    class Config:
        extra = "forbid"


class MCPOutput(BaseModel):
    """Strict schema for the MCP response documented in Logs/Proposed Outcome.md."""

    pair: str = Field(..., min_length=1)
    session: str = Field(..., min_length=1)
    time_window_minutes: int = Field(..., gt=0)
    volatility_expectation: str = Field(..., min_length=1)
    expected_deviation_pips: float = Field(..., ge=0.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    drivers: Sequence[str] = Field(..., min_length=1)
    historical_context: HistoricalContext
    agent_guidance: str = Field(..., min_length=1)

    class Config:
        extra = "forbid"

    @validator("pair", "session", "volatility_expectation", "agent_guidance", pre=True)
    def _strip_and_validate_strings(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @validator("drivers", each_item=True)
    def _validate_driver(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("drivers must be strings")
        stripped = value.strip()
        if not stripped:
            raise ValueError("driver entries must not be blank")
        return stripped
