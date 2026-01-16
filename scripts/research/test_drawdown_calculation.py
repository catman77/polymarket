#!/usr/bin/env python3
"""
US-RC-022: Unit tests for drawdown calculation formula
Persona: Colonel Rita "The Guardian" Stevens (Risk Management)

Tests edge cases in drawdown calculation to ensure it catches issues
before they cause trading halts or allow unsafe trading.
"""

import sys
from typing import Tuple


# Simulated constants (from bot code)
MAX_DRAWDOWN_PCT = 0.30  # 30% max drawdown


class MockState:
    """Mock TradingState for testing."""
    def __init__(self, peak_balance: float, current_balance: float):
        self.peak_balance = peak_balance
        self.current_balance = current_balance


def calculate_drawdown_safe(peak_balance: float, effective_balance: float) -> Tuple[bool, str, float]:
    """
    Safe drawdown calculation with proper edge case handling.

    Returns:
        (halt, message, drawdown_pct)
    """
    # Edge case 1: Uninitialized peak
    if peak_balance <= 0:
        return False, "Peak balance not initialized", 0.0

    # Edge case 2: Negative effective balance (should never happen but guard anyway)
    if effective_balance < 0:
        return True, f"CRITICAL: Negative balance ${effective_balance:.2f}", 1.0

    # Edge case 3: Effective balance exceeds peak (profit scenario)
    if effective_balance >= peak_balance:
        return False, f"No drawdown - balance at or above peak", 0.0

    # Normal case: Calculate drawdown
    drawdown = (peak_balance - effective_balance) / peak_balance

    if drawdown > MAX_DRAWDOWN_PCT:
        return True, f"Drawdown {drawdown*100:.1f}% exceeds {MAX_DRAWDOWN_PCT*100:.0f}% (peak ${peak_balance:.2f} -> ${effective_balance:.2f})", drawdown

    return False, f"Drawdown {drawdown*100:.1f}% within limits", drawdown


def run_test_suite():
    """Execute comprehensive test suite for drawdown calculation."""

    print("=" * 80)
    print("DRAWDOWN CALCULATION TEST SUITE")
    print("=" * 80)
    print()

    tests_passed = 0
    tests_failed = 0

    # Test 1: Normal case - small drawdown (10%)
    print("Test 1: Normal case - 10% drawdown")
    peak = 300.0
    effective = 270.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    expected_dd = 0.10
    assert not halt, "Should NOT halt at 10% drawdown"
    assert abs(dd - expected_dd) < 0.001, f"Expected {expected_dd}, got {dd}"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 2: Boundary case - exactly 30% drawdown
    print("Test 2: Boundary case - exactly 30% drawdown (should NOT halt - boundary exclusive)")
    peak = 300.0
    effective = 210.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    expected_dd = 0.30
    assert not halt, "Should NOT halt at exactly 30% drawdown (> is exclusive)"
    assert abs(dd - expected_dd) < 0.001, f"Expected {expected_dd}, got {dd}"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 3: Danger zone - 35% drawdown
    print("Test 3: Danger zone - 35% drawdown (should halt)")
    peak = 300.0
    effective = 195.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    expected_dd = 0.35
    assert halt, "SHOULD halt at 35% drawdown (exceeds 30% limit)"
    assert abs(dd - expected_dd) < 0.001, f"Expected {expected_dd}, got {dd}"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 4: Edge case - uninitialized peak (peak=0)
    print("Test 4: Edge case - uninitialized peak (peak=0)")
    peak = 0.0
    effective = 100.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    assert not halt, "Should NOT halt when peak uninitialized"
    assert dd == 0.0, "Drawdown should be 0 when peak=0"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 5: Edge case - negative balance (critical error)
    print("Test 5: Edge case - negative balance (critical error)")
    peak = 300.0
    effective = -10.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    assert halt, "SHOULD halt on negative balance"
    assert dd == 1.0, "Drawdown should be 100% on negative balance"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 6: Profit case - balance exceeds peak
    print("Test 6: Profit case - balance exceeds peak")
    peak = 300.0
    effective = 350.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    assert not halt, "Should NOT halt when making profit"
    assert dd == 0.0, "Drawdown should be 0 when balance > peak"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 7: Jan 16 incident - incorrect peak tracking
    print("Test 7: Jan 16 incident simulation - peak includes unredeemed positions")
    # Scenario: Peak was $386.97 (cash $200.97 + $186 in positions)
    # Positions redeemed → cash now $200.97
    # Incorrect: drawdown = ($386.97 - $200.97) / $386.97 = 48% → HALT
    # Correct: Peak should have been cash-only ($200.97)
    peak_incorrect = 386.97  # BUG: Includes unredeemed position values
    cash_only = 200.97
    halt, msg, dd = calculate_drawdown_safe(peak_incorrect, cash_only)
    assert halt, "Incorrect peak causes false halt"
    assert dd > 0.40, f"Drawdown should be >40%, got {dd*100:.1f}%"
    print(f"  ✅ PASS: Reproduced Jan 16 bug - {msg}")
    print(f"     Root cause: Peak included unredeemed positions, not just cash")
    tests_passed += 1
    print()

    # Test 8: Correct peak tracking - cash only
    print("Test 8: Correct peak tracking - cash only")
    peak_correct = 200.97  # FIX: Peak tracks cash only
    cash_only = 200.97
    halt, msg, dd = calculate_drawdown_safe(peak_correct, cash_only)
    assert not halt, "Correct peak should NOT halt"
    assert dd == 0.0, "No drawdown when balance equals peak"
    print(f"  ✅ PASS: {msg}")
    tests_passed += 1
    print()

    # Test 9: Redeemable value handling - should include winning positions
    print("Test 9: Effective balance includes redeemable positions")
    peak = 300.0
    cash = 200.0
    redeemable = 50.0  # Winning positions at 99%+
    effective = cash + redeemable  # 250.0
    halt, msg, dd = calculate_drawdown_safe(peak, effective)
    expected_dd = (300.0 - 250.0) / 300.0  # 16.7%
    assert not halt, "Should NOT halt with redeemable positions"
    assert abs(dd - expected_dd) < 0.001, f"Expected {expected_dd:.3f}, got {dd:.3f}"
    print(f"  ✅ PASS: {msg}")
    print(f"     Effective balance: ${cash:.2f} cash + ${redeemable:.2f} redeemable = ${effective:.2f}")
    tests_passed += 1
    print()

    # Test 10: Division by zero protection
    print("Test 10: Zero peak (should not divide by zero)")
    peak = 0.0
    effective = 0.0
    try:
        halt, msg, dd = calculate_drawdown_safe(peak, effective)
        assert not halt, "Should handle zero peak gracefully"
        print(f"  ✅ PASS: {msg}")
        tests_passed += 1
    except ZeroDivisionError:
        print(f"  ❌ FAIL: ZeroDivisionError not handled!")
        tests_failed += 1
    print()

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Passed: {tests_passed}/10")
    print(f"Tests Failed: {tests_failed}/10")

    if tests_failed == 0:
        print("\n✅ ALL TESTS PASSED - Drawdown calculation is robust")
        return 0
    else:
        print(f"\n❌ {tests_failed} TEST(S) FAILED - Review implementation")
        return 1


if __name__ == "__main__":
    sys.exit(run_test_suite())
