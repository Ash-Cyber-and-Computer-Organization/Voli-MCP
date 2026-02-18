"""
Range and volatility calculation utilities.
Analyzes pre-session compression and expected session ranges.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from datetime import datetime, time, timedelta
import pytz

from utils.formatters import get_pip_value, price_to_pips


class RangeCalculator:
    """Calculate and analyze forex price ranges."""
    
    def __init__(self, pair: str):
        """
        Initialize range calculator for a currency pair.
        
        Args:
            pair: Currency pair (e.g., "EUR/USD")
        """
        self.pair = pair
        self.pip_value = get_pip_value(pair)
    
    def calculate_range_pips(self, df: pd.DataFrame) -> float:
        """
        Calculate price range in pips for a DataFrame of candles.
        
        Args:
            df: DataFrame with 'high' and 'low' columns
            
        Returns:
            Range in pips
        """
        if df.empty:
            return 0.0
        
        high = df["high"].max()
        low = df["low"].min()
        price_range = high - low
        
        return price_to_pips(price_range, self.pair)
    
    def calculate_pre_session_range(
        self,
        df: pd.DataFrame,
        session_start_time: time,
        minutes_before: int = 90
    ) -> float:
        """
        Calculate range for the pre-session window.
        
        Args:
            df: Intraday DataFrame (should include pre-session period)
            session_start_time: When session starts (time object)
            minutes_before: Pre-session window length
            
        Returns:
            Pre-session range in pips
        """
        # Filter to pre-session window
        pre_session_df = self._filter_pre_session(df, session_start_time, minutes_before)
        
        return self.calculate_range_pips(pre_session_df)
    
    def calculate_session_range(
        self,
        df: pd.DataFrame,
        session_start_time: time,
        session_end_time: time
    ) -> float:
        """
        Calculate range during the actual session.
        
        Args:
            df: Intraday DataFrame
            session_start_time: Session start
            session_end_time: Session end
            
        Returns:
            Session range in pips
        """
        session_df = self._filter_session(df, session_start_time, session_end_time)
        return self.calculate_range_pips(session_df)
    
    def calculate_30day_avg_range(
        self,
        historical_df: pd.DataFrame,
        session_start_time: time,
        minutes_window: int = 90,
        is_pre_session: bool = True
    ) -> float:
        """
        Calculate 30-day average range for a specific time window.
        
        Args:
            historical_df: 30+ days of intraday data
            session_start_time: Reference time for window
            minutes_window: Window length (90 for pre-session, or session duration)
            is_pre_session: If True, calculate for pre-session; else for session
            
        Returns:
            Average range in pips
        """
        daily_ranges = []
        
        # Group by date
        historical_df['date'] = historical_df.index.date
        
        for date, day_df in historical_df.groupby('date'):
            if is_pre_session:
                range_pips = self.calculate_pre_session_range(
                    day_df,
                    session_start_time,
                    minutes_window
                )
            else:
                # For session range, need session_end_time
                # Calculate from window duration
                dummy_dt = datetime.combine(datetime.today(), session_start_time)
                session_end = (dummy_dt + timedelta(minutes=minutes_window)).time()
                range_pips = self.calculate_session_range(
                    day_df,
                    session_start_time,
                    session_end
                )
            
            if range_pips > 0:  # Only include valid ranges
                daily_ranges.append(range_pips)
        
        if not daily_ranges:
            return 0.0
        
        return np.mean(daily_ranges)
    
    def detect_compression(
        self,
        current_range: float,
        avg_range: float,
        threshold: float = 0.7
    ) -> Tuple[bool, float]:
        """
        Detect if current range is compressed vs average.
        
        Args:
            current_range: Current pre-session range in pips
            avg_range: 30-day average range in pips
            threshold: Compression threshold (0.7 = 70% of average)
            
        Returns:
            Tuple of (is_compressed: bool, compression_ratio: float)
            
        Example:
            (True, 0.56) means range is 56% of average (compressed)
        """
        if avg_range == 0:
            return False, 1.0
        
        ratio = current_range / avg_range
        is_compressed = ratio <= threshold
        
        return is_compressed, round(ratio, 2)
    
    def calculate_expected_deviation(
        self,
        current_pre_range: float,
        avg_pre_range: float,
        historical_expansion_rate: float,
        avg_session_range: float
    ) -> float:
        """
        Calculate expected session deviation based on compression and history.
        
        Args:
            current_pre_range: Current pre-session range (pips)
            avg_pre_range: Average pre-session range (pips)
            historical_expansion_rate: Rate at which compressed ranges expanded (0-1)
            avg_session_range: Average session range from history (pips)
            
        Returns:
            Expected deviation in pips
            
        Logic:
            - If compressed, expect expansion proportional to expansion_rate
            - If not compressed, expect normal session range
            - Blend the two based on compression severity
        """
        is_compressed, ratio = self.detect_compression(current_pre_range, avg_pre_range)
        
        if is_compressed:
            # Calculate compression delta
            compression_amount = avg_pre_range - current_pre_range
            
            # Expected expansion is proportional to historical rate
            expected_expansion = compression_amount * historical_expansion_rate * 1.5
            
            # Base expectation on average session range + expansion
            expected = avg_session_range + expected_expansion
        else:
            # Not compressed, expect normal volatility
            expected = avg_session_range
        
        # Ensure minimum expected deviation
        return max(expected, 10.0)  # At least 10 pips
    
    def _filter_pre_session(
        self,
        df: pd.DataFrame,
        session_start: time,
        minutes_before: int
    ) -> pd.DataFrame:
        """
        Filter DataFrame to pre-session window.
        
        Args:
            df: Intraday DataFrame with datetime index
            session_start: Session start time
            minutes_before: Window length before session
            
        Returns:
            Filtered DataFrame
        """
        # Get all unique dates in the data
        df_copy = df.copy()
        df_copy['date'] = df_copy.index.date
        dates = df_copy['date'].unique()
        
        # For the most recent date, calculate window
        if len(dates) == 0:
            return pd.DataFrame()
        
        recent_date = dates[-1]
        
        # Create datetime for session start on that date
        session_start_dt = datetime.combine(
            recent_date,
            session_start
        )
        
        # Ensure timezone awareness
        if df.index.tz is not None:
            session_start_dt = session_start_dt.replace(tzinfo=df.index.tz)
        
        window_start_dt = session_start_dt - timedelta(minutes=minutes_before)
        
        # Filter
        mask = (df.index >= window_start_dt) & (df.index < session_start_dt)
        return df[mask]
    
    def _filter_session(
        self,
        df: pd.DataFrame,
        session_start: time,
        session_end: time
    ) -> pd.DataFrame:
        """
        Filter DataFrame to session window.
        
        Args:
            df: Intraday DataFrame
            session_start: Session start time
            session_end: Session end time
            
        Returns:
            Filtered DataFrame
        """
        # Extract time component from index
        df_copy = df.copy()
        df_copy['time'] = df_copy.index.time
        
        # Handle sessions that cross midnight
        if session_start < session_end:
            mask = (df_copy['time'] >= session_start) & (df_copy['time'] < session_end)
        else:
            mask = (df_copy['time'] >= session_start) | (df_copy['time'] < session_end)
        
        return df[mask]
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range (ATR) in pips.
        
        Args:
            df: DataFrame with high, low, close columns
            period: ATR period (default 14)
            
        Returns:
            ATR in pips
        """
        if len(df) < period:
            return 0.0
        
        # Calculate True Range
        df = df.copy()
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        # Calculate ATR
        atr = df['tr'].rolling(window=period).mean().iloc[-1]
        
        return price_to_pips(atr, self.pair)
    
    def get_range_statistics(
        self,
        df: pd.DataFrame,
        session_start: time,
        session_end: time
    ) -> Dict[str, float]:
        """
        Get comprehensive range statistics for analysis.
        
        Args:
            df: Intraday DataFrame
            session_start: Session start time
            session_end: Session end time
            
        Returns:
            Dict with range stats in pips
        """
        session_df = self._filter_session(df, session_start, session_end)
        
        return {
            "range_pips": self.calculate_range_pips(session_df),
            "atr_14": self.calculate_atr(session_df, period=14),
            "avg_candle_range": self._avg_candle_range(session_df),
            "max_candle_range": self._max_candle_range(session_df),
            "candle_count": len(session_df)
        }
    
    def _avg_candle_range(self, df: pd.DataFrame) -> float:
        """Calculate average candle range in pips."""
        if df.empty:
            return 0.0
        candle_ranges = df['high'] - df['low']
        avg = candle_ranges.mean()
        return price_to_pips(avg, self.pair)
    
    def _max_candle_range(self, df: pd.DataFrame) -> float:
        """Calculate maximum candle range in pips."""
        if df.empty:
            return 0.0
        candle_ranges = df['high'] - df['low']
        max_range = candle_ranges.max()
        return price_to_pips(max_range, self.pair)