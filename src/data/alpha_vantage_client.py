"""
Alpha Vantage API client for FX daily data.
"""

from __future__ import annotations

import os
from typing import Dict, Any, Optional
import httpx
import pandas as pd

from dotenv import load_dotenv

load_dotenv()


class AlphaVantageClient:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY not found in environment")

    async def get_intraday_data(
        self,
        pair: str,
        interval: str = "5min",
        outputsize: str = "compact"
    ) -> pd.DataFrame:
        """Fetch intraday FX data from Alpha Vantage."""
        from_symbol = pair[:3]
        to_symbol = pair[3:]
        params = {
            "function": "FX_INTRADAY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self.api_key
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        key = f"Time Series FX ({interval})"
        ts = data.get(key)
        if not ts:
            raise Exception(f"No intraday data returned for {pair}")

        df = pd.DataFrame.from_dict(ts, orient="index")
        df.index = pd.to_datetime(df.index)
        df.rename(
            columns={
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close"
            },
            inplace=True
        )
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df["volume"] = 0
        df.sort_index(inplace=True)
        return df

    def get_fx_daily(self, from_symbol: str, to_symbol: str, outputsize: str = "full") -> Dict[str, Any]:
        params = {
            "function": "FX_DAILY",
            "from_symbol": from_symbol,
            "to_symbol": to_symbol,
            "outputsize": outputsize,
            "apikey": self.api_key
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()
