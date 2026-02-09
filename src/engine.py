from __future__ import annotations

import yfinance as yf
import pandas as pd

from src.session import detect_session
from src.volatility import volatility_for_session


def get_symbol(pair: str) -> str:
    """Convert FX pair to yfinance symbol format."""
    pair = pair.upper()
    symbol_map = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "BTCUSD": "BTC-USD"
    }
    return symbol_map.get(pair, pair)


def build_intel(pair: str) -> dict:
    session = detect_session()

    # Fetch fresh market data for the pair
    symbol = get_symbol(pair)
    print(f"Fetching data for {symbol}")
    data = yf.download(symbol, period="7d", interval="1h")

    if data.empty:
        # Fallback to default values if data unavailable
        last_24h_range_pips = 50
        avg_7day_range_pips = 60
        compression_ratio = 0.83
    else:
        # Calculate last 24h range (last 24 candles)
        last_24h = data.tail(24)
        last_24h_high = last_24h['High'].max()
        last_24h_low = last_24h['Low'].min()
        last_24h_range = last_24h_high - last_24h_low

        # Calculate average 7-day range (mean of daily ranges)
        daily_ranges = []
        for date in data.index.date:
            day_data = data[data.index.date == date]
            if not day_data.empty:
                daily_range = day_data['High'].max() - day_data['Low'].min()
                daily_ranges.append(daily_range)

        avg_7day_range = sum(daily_ranges) / len(daily_ranges) if daily_ranges else last_24h_range

        # Convert to pips based on pair type
        pip_multiplier = 10000  # Default for EURUSD, GBPUSD
        if pair.upper().endswith('JPY'):
            pip_multiplier = 100  # JPY pairs
        elif pair.upper() == 'BTCUSD':
            pip_multiplier = 1  # BTC is already in dollar terms

        last_24h_range_pips = last_24h_range * pip_multiplier
        avg_7day_range_pips = avg_7day_range * pip_multiplier

        compression_ratio = last_24h_range_pips / avg_7day_range_pips if avg_7day_range_pips > 0 else 1.0

    # Determine volatility expectation based on compression ratio
    if compression_ratio < 0.75:
        volatility_expectation = "Low"
        expected_deviation_pips = int(last_24h_range_pips * 0.8)
        confidence = 0.6
        guidance = "Range compression suggests calmer conditions; consider mean reversion or tight stops."
    elif compression_ratio > 1.25:
        volatility_expectation = "High"
        expected_deviation_pips = int(last_24h_range_pips * 1.2)
        confidence = 0.8
        guidance = "Range expansion indicates higher volatility; favor breakout strategies and wider stops."
    else:
        volatility_expectation = "Normal"
        expected_deviation_pips = int(last_24h_range_pips)
        confidence = 0.7
        guidance = "Normal range conditions; standard risk management applies."

    # Generate drivers from conditions
    if compression_ratio < 0.75:
        range_driver = f"Range compression detected ({last_24h_range_pips:.1f} vs {avg_7day_range_pips:.1f} pips baseline)"
    elif compression_ratio > 1.25:
        range_driver = f"Range expansion detected ({last_24h_range_pips:.1f} vs {avg_7day_range_pips:.1f} pips baseline)"
    else:
        range_driver = f"Range behavior within normal volatility bounds ({last_24h_range_pips:.1f} vs {avg_7day_range_pips:.1f} pips baseline)"

    drivers = [range_driver]

    # Add session-specific drivers (generic, not event-based)
    if session == "London Open":
        drivers.append("London session historically increases participation and volatility")
    elif session == "New York Open":
        drivers.append("New York session brings high liquidity and macro event sensitivity")
    elif session == "Asian session":
        drivers.append("Asian session typically shows range-bound conditions")
    elif session == "Off-session":
        drivers.append("Off-session hours have thinner liquidity")

    # Historical context (placeholder)
    historical_context = {
        "similar_conditions_occurrences": 150,
        "expansion_rate": 0.5
    }

    return {
        "pair": pair,
        "session": session,
        "time_window_minutes": 90,
        "volatility_expectation": volatility_expectation,
        "expected_deviation_pips": expected_deviation_pips,
        "confidence": confidence,
        "drivers": drivers,
        "historical_context": historical_context,
        "agent_guidance": guidance,
        "last_24h_range_pips": round(last_24h_range_pips, 1),
        "avg_7day_range_pips": round(avg_7day_range_pips, 1),
        "compression_ratio": round(compression_ratio, 2),
    }
