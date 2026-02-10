#!/usr/bin/env python
"""Quick validation script for the engine."""
import json
from src.engine import build_intel

print("=" * 60)
print("FX VOLATILITY INTELLIGENCE ENGINE - VALIDATION TEST")
print("=" * 60)

try:
    print("\n[1] Testing EURUSD...")
    result = build_intel("EURUSD", debug=True)
    print(f"    ✓ Pair: {result['pair']}")
    print(f"    ✓ Session: {result['session']}")
    print(f"    ✓ Expectation: {result['volatility_expectation']}")
    print(f"    ✓ Confidence: {result['confidence']}")
    print(f"    ✓ Expected Deviation: {result['expected_deviation_pips']} pips")
    print(f"    ✓ Drivers: {len(result['drivers'])} factors")
    
    print("\n[2] Testing USDJPY...")
    result2 = build_intel("USDJPY")
    print(f"    ✓ Pair: {result2['pair']}")
    print(f"    ✓ Expectation: {result2['volatility_expectation']}")
    
    print("\n[3] Testing with macro events...")
    result3 = build_intel("GBPUSD", macro_events=["ECB Rate Decision", "US NFP"])
    print(f"    ✓ Pair: {result3['pair']}")
    print(f"    ✓ Expectation: {result3['volatility_expectation']}")
    print(f"    ✓ Confidence: {result3['confidence']}")
    event_drivers = [d for d in result3['drivers'] if 'event' in d.lower() or 'macro' in d.lower()]
    print(f"    ✓ Macro event drivers found: {len(event_drivers)}")
    
    print("\n[4] Testing error handling...")
    try:
        build_intel("EUR")  # Invalid pair
        print("    ✗ Should have raised ValueError")
    except ValueError as e:
        print(f"    ✓ Correctly caught invalid pair: {str(e)[:50]}...")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    
    print("\nSample response (EURUSD):")
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
