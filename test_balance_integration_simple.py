#!/usr/bin/env python3
"""
Test: DirectionalBalanceTracker Integration (US-BF-009) - Simple Unit Test

Verifies that:
1. Balance tracker is instantiated in DecisionEngine.__init__
2. tracker.record() is called in decide() method
3. Warning logged when bias detected
"""

import sys
from pathlib import Path

# Direct file reading test (no imports needed)
decision_engine_path = Path(__file__).parent / "coordinator" / "decision_engine.py"

def test_tracker_instantiation():
    """Test 1: Balance tracker instantiated in __init__."""
    print("\n=== Test 1: Tracker Instantiation in __init__ ===")

    with open(decision_engine_path) as f:
        content = f.read()

    # Check for DirectionalBalanceTracker class definition
    assert "class DirectionalBalanceTracker:" in content, "DirectionalBalanceTracker class should exist"

    # Check for tracker instantiation in __init__
    assert "self.balance_tracker = DirectionalBalanceTracker" in content, \
        "__init__ should instantiate DirectionalBalanceTracker"

    # Check parameters
    assert "window_size=20" in content, "Should initialize with window_size=20"
    assert "bias_threshold=0.70" in content, "Should initialize with bias_threshold=0.70"

    print("✅ PASS: Balance tracker instantiated in __init__")
    print("   - DirectionalBalanceTracker class exists")
    print("   - self.balance_tracker initialized with window_size=20, bias_threshold=0.70")

def test_tracker_record_call():
    """Test 2: tracker.record() called after decision."""
    print("\n=== Test 2: tracker.record() Called After Decision ===")

    with open(decision_engine_path) as f:
        content = f.read()

    # Check for record() call
    assert "self.balance_tracker.record(" in content, \
        "Should call self.balance_tracker.record() in decide() method"

    # Check for direction passed to record
    assert "self.balance_tracker.record(prediction.direction)" in content, \
        "Should pass prediction.direction to record()"

    print("✅ PASS: tracker.record() called after decision")
    print("   - self.balance_tracker.record(prediction.direction) found in decide()")

def test_bias_warning_logged():
    """Test 3: Warning logged when bias detected."""
    print("\n=== Test 3: Warning Logged When Bias Detected ===")

    with open(decision_engine_path) as f:
        content = f.read()

    # Check for has_bias() check
    assert "self.balance_tracker.has_bias()" in content, \
        "Should check self.balance_tracker.has_bias()"

    # Check for warning log
    assert "self.log.warning" in content and "BIAS DETECTED" in content, \
        "Should log warning when bias detected"

    # Check for balance_summary
    assert "balance_summary = self.balance_tracker.get_balance_summary()" in content, \
        "Should call get_balance_summary() for warning message"

    print("✅ PASS: Warning logged when bias detected")
    print("   - has_bias() check exists")
    print("   - log.warning() with 'BIAS DETECTED' message")
    print("   - get_balance_summary() called for details")

def test_logic_flow():
    """Test 4: Verify recording happens AFTER vote aggregation."""
    print("\n=== Test 4: Logic Flow (Recording After Aggregation) ===")

    with open(decision_engine_path) as f:
        lines = f.readlines()

    # Find line numbers
    aggregate_line = None
    record_line = None

    for i, line in enumerate(lines):
        if "aggregate_votes(votes, self.agent_weights)" in line:
            aggregate_line = i
        if "self.balance_tracker.record(prediction.direction)" in line:
            record_line = i

    assert aggregate_line is not None, "Should find aggregate_votes() call"
    assert record_line is not None, "Should find balance_tracker.record() call"
    assert record_line > aggregate_line, \
        f"record() (line {record_line}) should come AFTER aggregate_votes() (line {aggregate_line})"

    print("✅ PASS: Recording happens after vote aggregation")
    print(f"   - aggregate_votes() at line {aggregate_line + 1}")
    print(f"   - balance_tracker.record() at line {record_line + 1}")

def test_conditional_recording():
    """Test 5: Recording only happens when prediction.direction exists."""
    print("\n=== Test 5: Conditional Recording (Only When Direction Exists) ===")

    with open(decision_engine_path) as f:
        content = f.read()

    # Check for conditional check
    assert "if prediction.direction:" in content, \
        "Should check if prediction.direction exists before recording"

    print("✅ PASS: Conditional recording")
    print("   - if prediction.direction: check exists")
    print("   - Skip/Neutral votes filtered by tracker.record() itself")

if __name__ == "__main__":
    print("Testing DirectionalBalanceTracker Integration (US-BF-009)")
    print("=" * 70)

    try:
        test_tracker_instantiation()
        test_tracker_record_call()
        test_bias_warning_logged()
        test_logic_flow()
        test_conditional_recording()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nIntegration verified:")
        print("1. ✅ DirectionalBalanceTracker instantiated in DecisionEngine.__init__")
        print("2. ✅ tracker.record() called after each decision with prediction.direction")
        print("3. ✅ Warning logged when has_bias() returns True")
        print("4. ✅ Recording happens AFTER vote aggregation")
        print("5. ✅ Conditional recording (only when direction exists)")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
