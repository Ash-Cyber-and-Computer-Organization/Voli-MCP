from __future__ import annotations

from typing import Sequence

from pydantic import BaseModel, Field, field_validator, ConfigDict


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

    @field_validator("pair", "session", "volatility_expectation", "agent_guidance", mode="before")
    @classmethod
    def _strip_and_validate_strings(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("value must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("drivers", mode="before")
    @classmethod
    def _validate_driver(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str):
                raise TypeError("drivers must be strings")
            stripped = item.strip()
            if not stripped:
                raise ValueError("driver entries must not be blank")
        return [item.strip() for item in value]
