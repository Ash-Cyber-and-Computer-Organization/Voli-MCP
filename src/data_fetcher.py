"""Data fetching and market data utilities."""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from src.config import DATA_CONFIG, PIP_CONFIG

logger = logging.getLogger(__name__)


class DataFetcher:
    """Handles market data fetching and caching."""
    
    def __init__(self):
        """Initialize data fetcher with reusable session."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DATA_CONFIG.user_agent})
        self._cache: dict[str, pd.DataFrame] = {}
    
    def get_symbol(self, pair: str) -> str:
        """Convert FX pair to yfinance symbol format.
        
        Args:
            pair: Currency pair code (e.g., EURUSD)
            
        Returns:
            Symbol for yfinance (e.g., EURUSD=X)
        """
        pair = pair.upper()
        symbol_map = {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
            "BTCUSD": "BTC-USD",
            "ETHUSD": "ETH-USD",
        }
        return symbol_map.get(pair, f"{pair}=X")
    
    def fetch_data(self, pair: str, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """Fetch market data for a pair.
        
        Args:
            pair: Currency pair code
            use_cache: Whether to use cached data if available
            
        Returns:
            DataFrame with OHLC data or None if fetch fails
        """
        symbol = self.get_symbol(pair)
        
        # Check cache first
        if use_cache and pair in self._cache:
            logger.debug(f"Using cached data for {pair}")
            return self._cache[pair]
        
        try:
            logger.info(f"Fetching data for {pair} ({symbol})")
            data = yf.download(
                symbol,
                period=DATA_CONFIG.yfinance_period,
                interval=DATA_CONFIG.yfinance_interval,
                session=self.session,
                progress=False,  # Suppress progress bar
                quiet=True  # Suppress yfinance output
            )
            
            if data.empty:
                logger.warning(f"No data returned for {pair}")
                return None
            
            # Cache the data
            self._cache[pair] = data
            logger.debug(f"Successfully fetched {len(data)} candles for {pair}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {pair}: {e}")
            return None
    
    def clear_cache(self, pair: Optional[str] = None):
        """Clear data cache.
        
        Args:
            pair: Specific pair to clear, or None to clear all
        """
        if pair:
            self._cache.pop(pair, None)
            logger.debug(f"Cleared cache for {pair}")
        else:
            self._cache.clear()
            logger.debug("Cleared all cache")


class RangeCalculator:
    """Calculates price ranges and compression metrics."""
    
    @staticmethod
    def get_pip_multiplier(pair: str) -> int:
        """Get pip multiplier for a pair type.
        
        Args:
            pair: Currency pair code
            
        Returns:
            Pip multiplier (10000 for EUR/USD, 100 for JPY pairs, etc.)
        """
        pair = pair.upper()
        if pair.endswith("JPY"):
            return PIP_CONFIG.jpy
        elif pair in ["BTCUSD", "ETHUSD", "BTC-USD", "ETH-USD"]:
            return PIP_CONFIG.crypto
        return PIP_CONFIG.default
    
    @staticmethod
    def calculate_24h_range(data: pd.DataFrame) -> tuple[float, float]:
        """Calculate last 24-hour high-low range.
        
        Args:
            data: OHLC DataFrame
            
        Returns:
            (range_in_price_units, range_in_pips)
        """
        last_24h = data.tail(24)
        if last_24h.empty:
            return 0.0, 0.0
        
        high = last_24h["High"].max()
        low = last_24h["Low"].min()
        range_price = high - low
        return range_price, range_price
    
    @staticmethod
    def calculate_avg_range(data: pd.DataFrame) -> float:
        """Calculate average daily range from OHLC data.
        
        Args:
            data: OHLC DataFrame with daily data
            
        Returns:
            Average daily range in price units
        """
        daily_ranges = []
        
        for date in data.index.date:
            day_data = data[data.index.date == date]
            if not day_data.empty:
                daily_range = day_data["High"].max() - day_data["Low"].min()
                daily_ranges.append(daily_range)
        
        if not daily_ranges:
            return 0.0
        
        return sum(daily_ranges) / len(daily_ranges)
    
    @staticmethod
    def calculate_compression_ratio(last_24h_range: float, avg_range: float) -> float:
        """Calculate range compression ratio.
        
        Args:
            last_24h_range: Last 24-hour range
            avg_range: Average historical range
            
        Returns:
            Compression ratio (< 1.0 = compression, > 1.0 = expansion)
        """
        if avg_range <= 0:
            return 1.0
        return last_24h_range / avg_range
