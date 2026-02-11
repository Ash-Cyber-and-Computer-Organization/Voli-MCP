"""Test analysis modules"""

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
import pytz

from src.analysis.range_calculator import RangeCalculator
from src.analysis.pattern_matcher import PatternMatcher
from src.analysis.confidence_scorer import ConfidenceScorer

print("=== Testing Range Calculator ===")

# Create sample data
dates = pd.date_range(start='2025-02-09 06:00', end='2025-02-09 16:00', freq='5min', tz=pytz.UTC)
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
pre_range = calc.calculate_pre_session_range(df, time(8, 0), minutes_before=90)
print(f"✅ Pre-session range (90 min before 08:00): {pre_range:.1f} pips")

# Test session range
session_range = calc.calculate_session_range(df, time(8, 0), time(16, 0))
print(f"✅ Session range (08:00-16:00): {session_range:.1f} pips")

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

# Create 30 days of sample data
start = datetime.now(pytz.UTC) - timedelta(days=30)
dates_hist = pd.date_range(start=start, end=datetime.now(pytz.UTC), freq='5min', tz=pytz.UTC)
prices_hist = 1.0850 + np.cumsum(np.random.randn(len(dates_hist)) * 0.00005)

df_hist = pd.DataFrame({
    'open': prices_hist,
    'high': prices_hist + np.random.rand(len(prices_hist)) * 0.0002,
    'low': prices_hist - np.random.rand(len(prices_hist)) * 0.0002,
    'close': prices_hist + np.random.randn(len(prices_hist)) * 0.0001,
    'volume': np.random.randint(1000, 5000, len(prices_hist))
}, index=dates_hist)

matcher = PatternMatcher("EUR/USD")

# Test pattern matching
similar = matcher.find_similar_conditions(
    current_pre_range=18,
    avg_pre_range=32,
    historical_df=df_hist,
    session_start=time(8, 0),
    session_end=time(16, 0),
    threshold=0.15
)

print(f"✅ Similar conditions found: {similar['similar_conditions_occurrences']} days")
print(f"✅ Expansion rate: {similar['expansion_rate']}")
print(f"✅ Avg expansion: {similar['avg_expansion_pips']:.1f} pips")

# Test directional bias
bias = matcher.calculate_directional_bias(df_hist, time(8, 0), time(16, 0))
print(f"✅ Directional bias: {bias['bias']} ({bias['bullish_percentage']:.1f}% bullish)")

print("\n=== Testing Confidence Scorer ===")

scorer = ConfidenceScorer()

# Test confidence calculation
confidence = scorer.calculate_confidence(
    occurrences=112,
    expansion_rate=0.62,
    has_event=True,
    data_age_days=25
)
print(f"✅ Confidence score: {confidence}")

# Test breakdown
breakdown = scorer.get_confidence_breakdown(112, 0.62, True, 25)
print(f"✅ Breakdown: {breakdown}")

# Test explanation
explanation = scorer.get_confidence_explanation(confidence, 112, 0.62, True)
print(f"✅ Explanation: {explanation}")

# Test volatility adjustment
adjusted = scorer.adjust_for_volatility_regime(confidence, current_atr=25, avg_atr=22)
print(f"✅ Volatility-adjusted confidence: {adjusted}")

print("\n✅ All analysis modules working!")