"""
Twelve Data API client for forex market data.
Handles rate limiting, error handling, and data formatting.
Uses async httpx for non-blocking HTTP calls.
"""

import os
import asyncio
import httpx
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import pytz

# Load environment variables
load_dotenv()


class TwelveDataClient:
    """Async client for Twelve Data API with rate limiting and caching."""
    
    BASE_URL = "https://api.twelvedata.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Twelve Data client.
        
        Args:
            api_key: API key (defaults to env var TWELVE_DATA_API_KEY)
        """
        self.api_key = api_key or os.getenv("TWELVE_DATA_API_KEY")
        self.enabled = bool(self.api_key)
        
        # Rate limiting
        self.max_requests_per_day = int(os.getenv("MAX_REQUESTS_PER_DAY", "800"))
        self.request_delay = float(os.getenv("REQUEST_DELAY_SECONDS", "1.0"))
        self.last_request_time: float = 0.0
        self.daily_request_count: int = 0
        self.daily_reset_time = datetime.now(pytz.UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    
    async def _check_rate_limit(self) -> None:
        """Enforce rate limiting between requests (async-safe)."""
        now = datetime.now(pytz.UTC)
        if now >= self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        
        if self.daily_request_count >= self.max_requests_per_day:
            raise Exception(
                f"Daily API limit reached ({self.max_requests_per_day} requests). "
                f"Resets at {self.daily_reset_time.strftime('%H:%M UTC')}"
            )
        
        # Async-safe delay — does NOT block the event loop
        loop = asyncio.get_event_loop()
        time_since_last = loop.time() - self.last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """
        Make async API request with error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
        """
        if not self.enabled:
            raise Exception("Twelve Data client disabled (missing API key)")
        await self._check_rate_limit()
        
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                loop = asyncio.get_event_loop()
                self.last_request_time = loop.time()
                self.daily_request_count += 1
                
                response.raise_for_status()
                data = response.json()
            
            # Check for API-level error messages
            if "status" in data and data["status"] == "error":
                raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            
            if "code" in data and data["code"] >= 400:
                raise Exception(f"API Error {data['code']}: {data.get('message', 'Unknown error')}")
            
            return data
            
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP error {e.response.status_code}: {e.response.text}")
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")
    
    async def get_quote(self, pair: str) -> Dict[str, Any]:
        """
        Get real-time quote for a currency pair.
        
        Args:
            pair: Currency pair (e.g., "EUR/USD" or "EURUSD")
            
        Returns:
            Dict with current price, timestamp, etc.
        """
        from utils.formatters import display_pair_format
        normalized = display_pair_format(pair)
        params = {"symbol": normalized, "format": "JSON"}
        return await self._make_request("quote", params)
    
    async def get_time_series(
        self,
        pair: str,
        interval: str = "5min",
        outputsize: int = 300,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get historical time series data.
        
        Args:
            pair: Currency pair
            interval: Time interval (1min, 5min, 15min, 30min, 1h, 1day)
            outputsize: Number of data points (max 5000)
            start_date: Start date (YYYY-MM-DD format)
            end_date: End date (YYYY-MM-DD format)
            
        Returns:
            DataFrame with columns: datetime, open, high, low, close, volume
        """
        from utils.formatters import display_pair_format
        normalized = display_pair_format(pair)
        
        params: Dict[str, Any] = {
            "symbol": normalized,
            "interval": interval,
            "outputsize": min(outputsize, 5000),
            "format": "JSON",
            "timezone": "UTC"
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = await self._make_request("time_series", params)
        
        if "values" not in data:
            raise Exception(f"No data returned for {pair}")
        
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        else:
            df["volume"] = 0
        
        df.sort_index(inplace=True)
        return df
    
    async def get_intraday_data(
        self,
        pair: str,
        interval: str = "5min",
        outputsize: int = 300
    ) -> pd.DataFrame:
        """Get recent intraday data."""
        return await self.get_time_series(pair, interval, outputsize)
    
    async def get_daily_data(
        self,
        pair: str,
        outputsize: int = 60
    ) -> pd.DataFrame:
        """Get daily historical data."""
        return await self.get_time_series(pair, interval="1day", outputsize=outputsize)
    
    async def get_historical_sessions(
        self,
        pair: str,
        days_back: int = 60,
        interval: str = "5min"
    ) -> pd.DataFrame:
        """
        Get multiple days of historical intraday data for pattern matching.
        
        Args:
            pair: Currency pair
            days_back: Number of days to retrieve
            interval: Data interval
            
        Returns:
            DataFrame with historical intraday data
        """
        interval_minutes = self._parse_interval_minutes(interval)
        candles_per_day = (24 * 60) / interval_minutes
        total_candles = int(days_back * candles_per_day)
        outputsize = min(total_candles, 5000)
        return await self.get_time_series(pair, interval, outputsize)
    
    @staticmethod
    def _parse_interval_minutes(interval: str) -> int:
        """Parse interval string to minutes."""
        if interval.endswith("min"):
            return int(interval.replace("min", ""))
        elif interval.endswith("h"):
            return int(interval.replace("h", "")) * 60
        elif interval == "1day":
            return 24 * 60
        else:
            raise ValueError(f"Unsupported interval: {interval}")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return {
            "requests_today": self.daily_request_count,
            "daily_limit": self.max_requests_per_day,
            "remaining": self.max_requests_per_day - self.daily_request_count,
            "resets_at": self.daily_reset_time.isoformat(),
            "percentage_used": round(
                (self.daily_request_count / self.max_requests_per_day) * 100, 1
            ),
            "enabled": self.enabled
        }


class NullDataClient:
    """Fallback client when no API key is available."""

    enabled = False

    async def get_intraday_data(self, *args, **kwargs) -> pd.DataFrame:
        return pd.DataFrame()

    async def get_time_series(self, *args, **kwargs) -> pd.DataFrame:
        return pd.DataFrame()

    async def get_daily_data(self, *args, **kwargs) -> pd.DataFrame:
        return pd.DataFrame()

    async def get_historical_sessions(self, *args, **kwargs) -> pd.DataFrame:
        return pd.DataFrame()

    def get_rate_limit_status(self) -> Dict[str, Any]:
        return {
            "requests_today": 0,
            "daily_limit": 0,
            "remaining": 0,
            "resets_at": None,
            "percentage_used": 0,
            "enabled": False
        }


# Singleton instance
_client_instance: Optional[TwelveDataClient] = None

def get_client() -> TwelveDataClient:
    """Get singleton Twelve Data client instance."""
    global _client_instance
    if _client_instance is None:
        try:
            _client_instance = TwelveDataClient()
            if not _client_instance.enabled:
                _client_instance = NullDataClient()
        except Exception:
            _client_instance = NullDataClient()
    return _client_instance
