"""
Full system integration test.
Tests the complete analysis pipeline end-to-end.
"""

import json
from src.tools.session_analyzer import analyze_forex_session

print("=" * 60)
print("VOLI MCP FULL SYSTEM TEST")
print("=" * 60)

# Test 1: EUR/USD with auto session
print("\n[Test 1] EUR/USD - Auto Session Detection")
print("-" * 60)

try:
    result = analyze_forex_session("AUD/USD", "auto")
    print(json.dumps(result, indent=2))
    print(" Test 1 PASSED")
except Exception as e:
    print(f" Test 1 FAILED: {e}")

# Test 2: GBP/USD - London session
print("\n[Test 2] GBP/USD - London Session")
print("-" * 60)

try:
    result = analyze_forex_session("GBP/USD", "london")
    print(json.dumps(result, indent=2))
    print(" Test 2 PASSED")
except Exception as e:
    print(f" Test 2 FAILED: {e}")

# Test 3: USD/JPY - NY session
print("\n[Test 3] USD/JPY - NY Session")
print("-" * 60)

try:
    result = analyze_forex_session("USD/JPY", "ny")
    
    # Verify output structure
    assert "pair" in result
    assert "session" in result
    assert "volatility_expectation" in result
    assert "expected_deviation_pips" in result
    assert "confidence" in result
    assert "drivers" in result
    assert "historical_context" in result
    assert "agent_guidance" in result
    
    assert isinstance(result["drivers"], list)
    assert len(result["drivers"]) > 0
    assert 0 <= result["confidence"] <= 1
    
    print(json.dumps(result, indent=2))
    print("Test 3 PASSED - Output structure validated")
    
except Exception as e:
    print(f"Test 3 FAILED: {e}")

# Test 4: Invalid pair handling
print("\n[Test 4] Invalid Pair Handling")
print("-" * 60)

try:
    result = analyze_forex_session("INVALID/PAIR", "auto")
    print(" Test 4 FAILED: Should have raised ValueError")
except ValueError as e:
    print(f" Test 4 PASSED: Correctly rejected invalid pair - {e}")
except Exception as e:
    print(f" Test 4 FAILED: Wrong exception type - {e}")

# Test 5: Different pair formats
print("\n[Test 5] Pair Format Normalization")
print("-" * 60)

formats = ["EUR/USD", "EURUSD", "eur/usd", "eur-usd"]
try:
    for fmt in formats:
        result = analyze_forex_session(fmt, "auto")
        assert result["pair"] == "EUR/USD"
    print(" Test 5 PASSED: All formats normalized correctly")
except Exception as e:
    print(f" Test 5 FAILED: {e}")

print("\n" + "=" * 60)
print("SYSTEM TEST COMPLETE")
print("=" * 60)