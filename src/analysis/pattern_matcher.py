"""
Historical pattern matching for similar market conditions.
Pure in-memory analysis without database.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import time, datetime, timedelta

from analysis.range_calculator import RangeCalculator


class PatternMatcher:
    """Match current conditions against historical patterns."""
    
    def __init__(self, pair: str):
        """
        Initialize pattern matcher.
        
        Args:
            pair: Currency pair
        """
        self.pair = pair
        self.range_calc = RangeCalculator(pair)
    
    def find_similar_conditions(
        self,
        current_pre_range: float,
        avg_pre_range: float,
        historical_df: pd.DataFrame,
        session_start: time,
        session_end: time,
        threshold: float = 0.15
    ) -> Dict[str, Any]:
        """
        Find historical days with similar pre-session compression.
        
        Args:
            current_pre_range: Today's pre-session range (pips)
            avg_pre_range: 30-day average pre-session range (pips)
            historical_df: 30-60 days of intraday data
            session_start: Session start time
            session_end: Session end time
            threshold: Similarity threshold (0.15 = ±15%)
            
        Returns:
            Dict with:
                - similar_conditions_occurrences: int
                - expansion_rate: float (0-1)
                - avg_expansion_pips: float
                - matched_dates: list of date strings
        """
        if avg_pre_range == 0:
            return {
                "similar_conditions_occurrences": 0,
                "expansion_rate": 0.5,
                "avg_expansion_pips": 0.0,
                "matched_dates": []
            }
        
        current_ratio = current_pre_range / avg_pre_range
        lower_bound = current_ratio - threshold
        upper_bound = current_ratio + threshold
        
        # FIX: always copy before adding columns (pandas 2.x ChainedAssignmentError)
        df = historical_df.copy()
        df["date"] = df.index.date  # safe — working on our own copy
        
        matches = []
        
        for date, day_df in df.groupby("date"):
            pre_range = self.range_calc.calculate_pre_session_range(
                day_df,
                session_start,
                minutes_before=90
            )
            
            if pre_range == 0:
                continue
            
            day_ratio = pre_range / avg_pre_range
            
            if lower_bound <= day_ratio <= upper_bound:
                session_range = self.range_calc.calculate_session_range(
                    day_df,
                    session_start,
                    session_end
                )
                
                expansion_multiplier = 1.5
                expanded = session_range > (pre_range * expansion_multiplier)
                
                matches.append({
                    "date": str(date),
                    "pre_range": pre_range,
                    "session_range": session_range,
                    "expanded": expanded,
                    "expansion_pips": session_range - pre_range
                })
        
        if not matches:
            return {
                "similar_conditions_occurrences": 0,
                "expansion_rate": 0.5,
                "avg_expansion_pips": 0.0,
                "matched_dates": []
            }
        
        expansion_count = sum(1 for m in matches if m["expanded"])
        expansion_rate = expansion_count / len(matches)
        avg_expansion = np.mean([m["expansion_pips"] for m in matches])
        
        return {
            "similar_conditions_occurrences": len(matches),
            "expansion_rate": round(expansion_rate, 2),
            "avg_expansion_pips": round(avg_expansion, 1),
            "matched_dates": [m["date"] for m in matches[-10:]]
        }
    
    def find_event_day_patterns(
        self,
        historical_df: pd.DataFrame,
        event_dates: List[str],
        session_start: time,
        session_end: time
    ) -> Dict[str, Any]:
        """
        Analyze volatility patterns on days with high-impact events.
        
        Args:
            historical_df: Historical intraday data
            event_dates: List of dates with events (YYYY-MM-DD format)
            session_start: Session start time
            session_end: Session end time
            
        Returns:
            Dict with event-day statistics
        """
        # FIX: copy before column assignment
        df = historical_df.copy()
        df["date"] = df.index.date
        
        event_date_objs = [datetime.strptime(d, "%Y-%m-%d").date() for d in event_dates]
        
        event_ranges = []
        non_event_ranges = []
        
        for date, day_df in df.groupby("date"):
            session_range = self.range_calc.calculate_session_range(
                day_df,
                session_start,
                session_end
            )
            if date in event_date_objs:
                event_ranges.append(session_range)
            elif session_range > 0:
                non_event_ranges.append(session_range)
        
        if not event_ranges:
            return {
                "event_day_count": 0,
                "avg_event_day_range": 0.0,
                "event_volatility_multiplier": 1.0
            }
        
        avg_event = np.mean(event_ranges)
        avg_non_event = np.mean(non_event_ranges) if non_event_ranges else avg_event
        multiplier = avg_event / avg_non_event if avg_non_event > 0 else 1.0
        
        return {
            "event_day_count": len(event_ranges),
            "avg_event_day_range": round(avg_event, 1),
            "event_volatility_multiplier": round(multiplier, 2)
        }
    
    def calculate_directional_bias(
        self,
        historical_df: pd.DataFrame,
        session_start: time,
        session_end: time
    ) -> Dict[str, Any]:
        """
        Calculate directional bias for the session (bullish/bearish tendency).
        
        Args:
            historical_df: Historical data
            session_start: Session start
            session_end: Session end
            
        Returns:
            Dict with directional statistics
        """
        # FIX: copy before column assignment
        df = historical_df.copy()
        df["date"] = df.index.date
        
        bullish_days = 0
        bearish_days = 0
        
        for date, day_df in df.groupby("date"):
            session_df = self.range_calc._filter_session(
                day_df,
                session_start,
                session_end
            )
            
            if session_df.empty:
                continue
            
            open_price = session_df["open"].iloc[0]
            close_price = session_df["close"].iloc[-1]
            
            if close_price > open_price:
                bullish_days += 1
            else:
                bearish_days += 1
        
        total_days = bullish_days + bearish_days
        
        if total_days == 0:
            return {
                "bias": "neutral",
                "bullish_percentage": 50.0,
                "bearish_percentage": 50.0
            }
        
        bullish_pct = (bullish_days / total_days) * 100
        bearish_pct = (bearish_days / total_days) * 100
        
        if bullish_pct > 60:
            bias = "bullish"
        elif bearish_pct > 60:
            bias = "bearish"
        else:
            bias = "neutral"
        
        return {
            "bias": bias,
            "bullish_percentage": round(bullish_pct, 1),
            "bearish_percentage": round(bearish_pct, 1),
            "sample_size": total_days
        }