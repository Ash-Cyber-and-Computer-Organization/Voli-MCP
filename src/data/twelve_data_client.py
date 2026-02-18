"""
Twelve Data API client for forex market data.
Handles rate limiting, error handling, and data formatting.
"""

import os
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import pytz

# Load environment variables
load_dotenv()


class TwelveDataClient:
    """Client for Twelve Data API with rate limiting and caching."""
    
    BASE_URL = "https://api.twelvedata.com"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Twelve Data client.
        
        Args:
            api_key: API key (defaults to env var TWELVE_DATA_API_KEY)
        """
        self.api_key = api_key or os.getenv("TWELVE_DATA_API_KEY")
        if not self.api_key:
            raise ValueError("TWELVE_DATA_API_KEY not found in environment")
        
        # Rate limiting
        self.max_requests_per_day = int(os.getenv("MAX_REQUESTS_PER_DAY", "800"))
        self.request_delay = float(os.getenv("REQUEST_DELAY_SECONDS", "1.0"))
        self.last_request_time = 0
        self.daily_request_count = 0
        self.daily_reset_time = datetime.now(pytz.UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    
    def _check_rate_limit(self):
        """Enforce rate limiting between requests."""
        # Reset daily counter if needed
        now = datetime.now(pytz.UTC)
        if now >= self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        
        # Check daily limit
        if self.daily_request_count >= self.max_requests_per_day:
            raise Exception(
                f"Daily API limit reached ({self.max_requests_per_day} requests). "
                f"Resets at {self.daily_reset_time.strftime('%H:%M UTC')}"
            )
        
        # Enforce delay between requests
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict:
        """
        Make API request with error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            Exception: If API returns error or request fails
        """
        self._check_rate_limit()
        
        # Add API key to params
        params["apikey"] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=30)
            self.last_request_time = time.time()
            self.daily_request_count += 1
            
            response.raise_for_status()
            data = response.json()
            
            # Check for API error messages
            if "status" in data and data["status"] == "error":
                raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            
            if "code" in data and data["code"] >= 400:
                raise Exception(f"API Error {data['code']}: {data.get('message', 'Unknown error')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def get_quote(self, pair: str) -> Dict[str, Any]:
        """
        Get real-time quote for a currency pair.

        Args:
            pair: Currency pair (e.g., "EUR/USD" or "EURUSD")

        Returns:
            Dict with current price, timestamp, etc.

        Example:
            {
                "symbol": "EUR/USD",
                "price": "1.08523",
                "timestamp": 1707494400,
                ...
            }
        """
        from utils.formatters import display_pair_format

        normalized = display_pair_format(pair)
        
        params = {
            "symbol": normalized,
            "format": "JSON"
        }
        
        data = self._make_request("quote", params)
        return data
    
    def get_time_series(
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

        Example output:
                                 open     high      low    close  volume
            datetime
            2025-02-09 08:00:00  1.0850  1.0855  1.0848  1.0852   12500
            2025-02-09 08:05:00  1.0852  1.0858  1.0851  1.0857   15230
        """
        from utils.formatters import display_pair_format

        normalized = display_pair_format(pair)

        params = {
            "symbol": normalized,
            "interval": interval,
            "outputsize": min(outputsize, 5000),  # API max
            "format": "JSON",
            "timezone": "UTC"
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        data = self._make_request("time_series", params)
        
        if "values" not in data:
            raise Exception(f"No data returned for {pair}")
        
        # Convert to DataFrame
        df = pd.DataFrame(data["values"])
        
        # Convert datetime column
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        
        # Convert price columns to float
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        
        # Volume might not be available for forex
        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        else:
            df["volume"] = 0
        
        # Sort by datetime (oldest first)
        df.sort_index(inplace=True)
        
        return df
    
    def get_intraday_data(
        self,
        pair: str,
        interval: str = "5min",
        outputsize: int = 300
    ) -> pd.DataFrame:
        """
        Get recent intraday data (convenience wrapper for get_time_series).
        
        Args:
            pair: Currency pair
            interval: Time interval
            outputsize: Number of recent candles
            
        Returns:
            DataFrame with OHLC data
        """
        return self.get_time_series(pair, interval, outputsize)
    
    def get_daily_data(
        self,
        pair: str,
        outputsize: int = 60
    ) -> pd.DataFrame:
        """
        Get daily historical data.
        
        Args:
            pair: Currency pair
            outputsize: Number of days
            
        Returns:
            DataFrame with daily OHLC data
        """
        return self.get_time_series(pair, interval="1day", outputsize=outputsize)
    
    def get_range_data_for_session(
        self,
        pair: str,
        session_start: datetime,
        session_end: datetime,
        interval: str = "5min"
    ) -> pd.DataFrame:
        """
        Get data for a specific session time window.
        
        Args:
            pair: Currency pair
            session_start: Session start datetime (UTC)
            session_end: Session end datetime (UTC)
            interval: Data interval
            
        Returns:
            DataFrame filtered to session window
        """
        # Calculate how many candles we need
        duration_minutes = (session_end - session_start).total_seconds() / 60
        interval_minutes = self._parse_interval_minutes(interval)
        candles_needed = int(duration_minutes / interval_minutes) + 10  # Buffer
        
        # Get data
        df = self.get_time_series(pair, interval, outputsize=candles_needed)
        
        # Filter to time window
        mask = (df.index >= session_start) & (df.index <= session_end)
        return df[mask]
    
    def get_historical_sessions(
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
            
        Note:
            For 60 days of 5-min data, this is ~17,280 candles (60 * 24 * 12)
        """
        interval_minutes = self._parse_interval_minutes(interval)
        candles_per_day = (24 * 60) / interval_minutes
        total_candles = int(days_back * candles_per_day)
        
        # API limit is 5000, so cap it
        outputsize = min(total_candles, 5000)
        
        return self.get_time_series(pair, interval, outputsize)
    
    @staticmethod
    def _parse_interval_minutes(interval: str) -> int:
        """
        Parse interval string to minutes.
        
        Args:
            interval: Interval string (1min, 5min, 1h, etc.)
            
        Returns:
            Minutes as integer
        """
        if interval.endswith("min"):
            return int(interval.replace("min", ""))
        elif interval.endswith("h"):
            return int(interval.replace("h", "")) * 60
        elif interval == "1day":
            return 24 * 60
        else:
            raise ValueError(f"Unsupported interval: {interval}")
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Dict with request count, limit, and reset time
        """
        return {
            "requests_today": self.daily_request_count,
            "daily_limit": self.max_requests_per_day,
            "remaining": self.max_requests_per_day - self.daily_request_count,
            "resets_at": self.daily_reset_time.isoformat(),
            "percentage_used": round(
                (self.daily_request_count / self.max_requests_per_day) * 100, 1
            )
        }


# Singleton instance
_client_instance = None

def get_client() -> TwelveDataClient:
    """
    Get singleton Twelve Data client instance.
    
    Returns:
        TwelveDataClient instance
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = TwelveDataClient()
    return _client_instance