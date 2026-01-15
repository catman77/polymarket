#!/usr/bin/env python3
"""
Test script to verify the conflict check logic works correctly.
This simulates the Guardian's check_live_position_conflicts method.
"""

def test_conflict_detection():
    """Test various conflict scenarios."""

    # Simulated API response scenarios
    test_cases = [
        {
            "name": "No conflict - no existing positions",
            "positions": [],
            "target_crypto": "BTC",
            "target_direction": "Up",
            "expected_conflict": False
        },
        {
            "name": "Conflict - same crypto, same direction",
            "positions": [
                {"title": "BTC will go up in the next 15 minutes", "outcome": "Up", "size": 25.0}
            ],
            "target_crypto": "BTC",
            "target_direction": "Up",
            "expected_conflict": True
        },
        {
            "name": "CRITICAL - same crypto, opposite direction",
            "positions": [
                {"title": "BTC will go down in the next 15 minutes", "outcome": "Down", "size": 31.0}
            ],
            "target_crypto": "BTC",
            "target_direction": "Up",
            "expected_conflict": True
        },
        {
            "name": "No conflict - different crypto",
            "positions": [
                {"title": "ETH will go up in the next 15 minutes", "outcome": "Up", "size": 20.0}
            ],
            "target_crypto": "BTC",
            "target_direction": "Up",
            "expected_conflict": False
        },
        {
            "name": "No conflict - negligible size",
            "positions": [
                {"title": "BTC will go up in the next 15 minutes", "outcome": "Up", "size": 0.001}
            ],
            "target_crypto": "BTC",
            "target_direction": "Up",
            "expected_conflict": False
        }
    ]

    def check_conflict(positions, crypto, direction):
        """Simulate the conflict check logic."""
        crypto_upper = crypto.upper()

        for pos in positions:
            size = float(pos.get('size', 0))
            if size < 0.01:
                continue

            title = pos.get('title', '')
            outcome = pos.get('outcome', '')

            if crypto_upper not in title.upper():
                continue

            pos_direction = None
            if 'Up' in outcome or 'up' in title.lower():
                pos_direction = 'Up'
            elif 'Down' in outcome or 'down' in title.lower():
                pos_direction = 'Down'

            if not pos_direction:
                continue

            # Conflict if same OR opposite direction
            if pos_direction == direction:
                return True, f"Already have {crypto} {direction} position"
            else:
                return True, f"Already have {crypto} {pos_direction} position - cannot bet both sides!"

        return False, ""

    # Run tests
    print("=" * 70)
    print("TESTING CONFLICT DETECTION LOGIC")
    print("=" * 70)
    print()

    passed = 0
    failed = 0

    for test in test_cases:
        has_conflict, msg = check_conflict(
            test["positions"],
            test["target_crypto"],
            test["target_direction"]
        )

        expected = test["expected_conflict"]
        result = "✅ PASS" if has_conflict == expected else "❌ FAIL"

        if has_conflict == expected:
            passed += 1
        else:
            failed += 1

        print(f"{result}: {test['name']}")
        print(f"  Expected conflict: {expected}, Got: {has_conflict}")
        if msg:
            print(f"  Message: {msg}")
        print()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70)

    return failed == 0

if __name__ == "__main__":
    success = test_conflict_detection()
    exit(0 if success else 1)
