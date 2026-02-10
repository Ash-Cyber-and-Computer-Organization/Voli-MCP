"""Pydantic models for request/response validation."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VolatilityIntelligence(BaseModel):
    """Response schema for volatility intelligence output."""
    
    pair: str = Field(..., description="FX pair (e.g., EURUSD)")
    session: str = Field(..., description="Active trading session")
    time_window_minutes: int = Field(..., description="Time window for volatility expectation")
    volatility_expectation: Literal["Low", "Normal", "High"] = Field(
        ..., description="Volatility classification"
    )
    expected_deviation_pips: float = Field(..., description="Expected price movement in pips")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    drivers: list[str] = Field(..., description="Causal factors driving volatility expectation")
    historical_context: dict = Field(..., description="Historical condition statistics")
    agent_guidance: str = Field(..., description="Strategy guidance for trading agents")
    
    # Debug fields (optional)
    last_24h_range_pips: float | None = Field(None, description="Last 24-hour range")
    avg_7day_range_pips: float | None = Field(None, description="7-day average range")
    compression_ratio: float | None = Field(None, description="Compression ratio vs. baseline")

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, v: str) -> str:
        """Validate pair format."""
        if len(v) != 6 or not v.isalpha():
            raise ValueError("Pair must be a 6-letter code like EURUSD")
        return v.upper()

    @field_validator("time_window_minutes")
    @classmethod
    def validate_window(cls, v: int) -> int:
        """Validate time window is positive."""
        if v <= 0:
            raise ValueError("Time window must be positive")
        return v

    @field_validator("expected_deviation_pips")
    @classmethod
    def validate_pips(cls, v: float) -> float:
        """Validate deviation is positive."""
        if v < 0:
            raise ValueError("Expected deviation must be non-negative")
        return v


class HistoricalContext(BaseModel):
    """Historical context for similar market conditions."""
    
    similar_conditions_occurrences: int = Field(..., description="How many times similar conditions occurred")
    expansion_rate: float = Field(..., ge=0, le=1, description="Historical volatility expansion rate (0-1)")
