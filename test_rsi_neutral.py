"""
Test RSI neutral zone scoring (US-BF-004)

Verifies that RSI 40-60 (neutral zone) returns 0.5 confidence instead of 1.0,
preventing false high confidence signals in sideways markets.
"""

import sys
sys.path.insert(0, '/Volumes/TerraTitan/Development/polymarket-autotrader')

from agents.tech_agent import RSICalculator

def test_rsi_neutral_zone():
    """Test: RSI 40-60 should return 0.5 confidence (neutral → low confidence)"""
    rsi_calc = RSICalculator()

    # Set RSI to 50 (middle of neutral zone)
    rsi_calc.rsi_values["BTC"] = 50.0

    # Test RSI=50 (middle of neutral zone)
    score_up, desc_up = rsi_calc.get_rsi_signal("BTC", "Up")
    assert score_up == 0.5, f"Expected 0.5 for RSI 50 Up, got {score_up}"
    assert "neutral → low confidence" in desc_up, f"Expected neutral message, got: {desc_up}"

    score_down, desc_down = rsi_calc.get_rsi_signal("BTC", "Down")
    assert score_down == 0.5, f"Expected 0.5 for RSI 50 Down, got {score_down}"
    assert "neutral → low confidence" in desc_down, f"Expected neutral message, got: {desc_down}"

    print("✓ Test passed: RSI=50 returns 0.5 confidence for both Up and Down")

def test_rsi_bearish_zone():
    """Test: RSI 65 should return 0.8 confidence for Down (bearish signal)"""
    rsi_calc = RSICalculator()
    rsi_calc.rsi_values["BTC"] = 65.0

    score, desc = rsi_calc.get_rsi_signal("BTC", "Down")
    assert score == 0.8, f"Expected 0.8 for RSI 65 Down (bearish), got {score}"
    assert "overbought" in desc.lower(), f"Expected overbought mention, got: {desc}"

    print("✓ Test passed: RSI=65 returns 0.8 confidence for Down (bearish, unchanged)")

def test_rsi_bullish_zone():
    """Test: RSI 35 should return 0.8 confidence for Up (bullish signal)"""
    rsi_calc = RSICalculator()
    rsi_calc.rsi_values["BTC"] = 35.0

    score, desc = rsi_calc.get_rsi_signal("BTC", "Up")
    assert score == 0.8, f"Expected 0.8 for RSI 35 Up (bullish), got {score}"
    assert "oversold" in desc.lower(), f"Expected oversold mention, got: {desc}"

    print("✓ Test passed: RSI=35 returns 0.8 confidence for Up (bullish, unchanged)")

def test_rsi_boundary_cases():
    """Test: RSI at 40 and 60 boundaries"""
    rsi_calc = RSICalculator()

    # RSI=40 (boundary of neutral zone)
    rsi_calc.rsi_values["BTC"] = 40.0
    score_up_40, desc_up_40 = rsi_calc.get_rsi_signal("BTC", "Up")
    assert score_up_40 == 0.5, f"Expected 0.5 for RSI 40 Up, got {score_up_40}"

    score_down_40, desc_down_40 = rsi_calc.get_rsi_signal("BTC", "Down")
    assert score_down_40 == 0.5, f"Expected 0.5 for RSI 40 Down, got {score_down_40}"

    # RSI=60 (boundary of neutral zone)
    rsi_calc.rsi_values["BTC"] = 60.0
    score_up_60, desc_up_60 = rsi_calc.get_rsi_signal("BTC", "Up")
    assert score_up_60 == 0.5, f"Expected 0.5 for RSI 60 Up, got {score_up_60}"

    score_down_60, desc_down_60 = rsi_calc.get_rsi_signal("BTC", "Down")
    assert score_down_60 == 0.5, f"Expected 0.5 for RSI 60 Down, got {score_down_60}"

    print("✓ Test passed: RSI boundaries (40, 60) return 0.5 confidence")

def test_rsi_extreme_zones():
    """Test: RSI <30 (oversold) and >70 (overbought) should return 0.0 for opposing direction"""
    rsi_calc = RSICalculator()

    # RSI=75 overbought → 0.0 for Up
    rsi_calc.rsi_values["BTC"] = 75.0
    score_up, desc_up = rsi_calc.get_rsi_signal("BTC", "Up")
    assert score_up == 0.0, f"Expected 0.0 for RSI 75 Up (overbought), got {score_up}"
    assert "OVERBOUGHT" in desc_up, f"Expected OVERBOUGHT, got: {desc_up}"

    # RSI=25 oversold → 0.0 for Down
    rsi_calc.rsi_values["BTC"] = 25.0
    score_down, desc_down = rsi_calc.get_rsi_signal("BTC", "Down")
    assert score_down == 0.0, f"Expected 0.0 for RSI 25 Down (oversold), got {score_down}"
    assert "OVERSOLD" in desc_down, f"Expected OVERSOLD, got: {desc_down}"

    print("✓ Test passed: RSI extremes (<30, >70) return 0.0 for opposing direction")

if __name__ == "__main__":
    print("\n=== Testing RSI Neutral Zone Scoring (US-BF-004) ===\n")

    test_rsi_neutral_zone()
    test_rsi_bearish_zone()
    test_rsi_bullish_zone()
    test_rsi_boundary_cases()
    test_rsi_extreme_zones()

    print("\n✅ All RSI neutral zone tests passed!\n")
