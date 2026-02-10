#!/usr/bin/env python
"""Simple test to check imports."""
print("Testing imports...")

print("1. Testing session module...")
from src.session import detect_session
print(f"   ✓ Current session: {detect_session()}")

print("2. Testing volatility module...")
from src.volatility import classify_volatility_expectation
result = classify_volatility_expectation(0.5)
print(f"   ✓ Volatility classification: {result}")

print("3. Testing data_fetcher module...")
from src.data_fetcher import RangeCalculator
mult = RangeCalculator.get_pip_multiplier("EURUSD")
print(f"   ✓ Pip multiplier for EURUSD: {mult}")

print("4. Testing config...")
from src.config import VOLATILITY_THRESHOLDS
print(f"   ✓ Low compression threshold: {VOLATILITY_THRESHOLDS.low_compression}")

print("\n✓ ALL IMPORTS SUCCESSFUL")
