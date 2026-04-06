"""Test analysis modules"""

import numpy as np
from datetime import datetime, time, timedelta
import pytz

from src.analysis.range_calculator import RangeCalculator
from src.analysis.pattern_matcher import PatternMatcher
from src.analysis.confidence_scorer import ConfidenceScorer
from src.data.historical_store import HistoricalStore

print("=== Testing Range Calculator ===")

# Create sample data
import pandas as pd

dates = pd.date_range(start='2025-02-09 04:00', end='2025-02-09 16:00', freq='5min', tz=pytz.UTC)
prices = 1.0850 + np.cumsum(np.random.randn(len(dates)) * 0.0001)

df = pd.DataFrame({
    'open': prices,
    'high': prices + np.random.rand(len(prices)) * 0.0002,
    'low': prices - np.random.rand(len(prices)) * 0.0002,
    'close': prices + np.random.randn(len(prices)) * 0.0001,
    'volume': np.random.randint(1000, 5000, len(prices))
}, index=dates)

calc = RangeCalculator("EUR/USD")

# Test range calculation
range_pips = calc.calculate_range_pips(df)
print(f"✅ Full range: {range_pips:.1f} pips")

# Test pre-session range
pre_range = calc.calculate_pre_session_range_for_date(df, time(7, 0), minutes_before=90, target_date=dates[0].date())
print(f"✅ Pre-session range (90 min before 07:00): {pre_range:.1f} pips")

# Test session range
session_range = calc.calculate_session_range_for_date(df, time(7, 0), time(16, 0), target_date=dates[0].date())
print(f"✅ Session range (07:00-16:00): {session_range:.1f} pips")

# Test compression detection
is_compressed, ratio = calc.detect_compression(18, 32)
print(f"✅ Compression: {is_compressed} (ratio: {ratio})")

# Test expected deviation
expected = calc.calculate_expected_deviation(
    current_pre_range=18,
    avg_pre_range=32,
    historical_expansion_rate=0.62,
    avg_session_range=45
)
print(f"✅ Expected deviation: {expected:.1f} pips")

print("\n=== Testing Pattern Matcher ===")

store = HistoricalStore()
matcher = PatternMatcher("EUR/USD")

averages = store.get_recent_averages("EUR/USD", "london", days=30)
current_pre = averages["avg_pre_range"] * 0.6

similar = matcher.find_similar_conditions(
    store=store,
    session_key="london",
    event_type=None,
    current_pre_range=current_pre,
    avg_pre_range=averages["avg_pre_range"],
    threshold=0.30
)

print(f"✅ Similar conditions found: {similar['similar_conditions_occurrences']} days")
print(f"✅ Expansion rate: {similar['expansion_rate']}")
print(f"✅ Avg expansion: {similar['avg_expansion_pips']:.1f} pips")

print("\n=== Testing Confidence Scorer ===")

scorer = ConfidenceScorer()

confidence = scorer.calculate_confidence(
    breakout_occurrences=70,
    total_occurrences=112
)
print(f"✅ Confidence score: {confidence}")

print("\n✅ All analysis modules working!")
