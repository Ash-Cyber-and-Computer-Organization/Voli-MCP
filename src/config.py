"""Configuration and settings for the FX volatility engine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PipConfig:
    """Pip multiplier configuration for different pair types."""
    
    default: int = 10000  # EURUSD, GBPUSD, etc.
    jpy: int = 100  # Yen pairs (USDJPY, EURJPY, etc.)
    gbp_jpy: int = 100  # GBP/JPY
    crypto: int = 1  # BTC, ETH, etc.


@dataclass
class VolatilityThresholds:
    """Volatility classification thresholds based on compression ratio."""
    
    low_compression: float = 0.75  # Below this = Low volatility
    high_expansion: float = 1.25  # Above this = High volatility
    # Between = Normal volatility


@dataclass
class SessionConfig:
    """Market session hours (UTC)."""
    
    asian_start: int = 0
    asian_end: int = 6
    london_start: int = 7
    london_end: int = 12
    newyork_start: int = 13
    newyork_end: int = 17
    # Off-session: 18-23


@dataclass
class DataConfig:
    """Data fetching configuration."""
    
    yfinance_period: str = "7d"  # Historical period for calculations
    yfinance_interval: str = "1h"  # Hourly candles
    lookback_hours: int = 24  # For 24-hour range calculation
    user_agent: str = "Mozilla/5.0"  # yfinance user agent


# Global configuration instances
PIP_CONFIG = PipConfig()
VOLATILITY_THRESHOLDS = VolatilityThresholds()
SESSION_CONFIG = SessionConfig()
DATA_CONFIG = DataConfig()
