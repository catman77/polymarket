#!/usr/bin/env python3
"""
Test suite for US-BF-005: Implement "Skip" vote type

Verifies that:
1. Skip votes can be created without validation errors
2. Skip votes accept confidence=0.0 and quality=0.0
3. Direction validation accepts "Skip" as valid
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.base_agent import Vote


def test_skip_vote_creation():
    """Test that Skip vote can be created without errors."""
    print("Test 1: Skip vote creation...")

    vote = Vote(
        direction="Skip",
        confidence=0.0,
        quality=0.0,
        agent_name="TestAgent",
        reasoning="No signal detected → ABSTAINING"
    )

    assert vote.direction == "Skip", f"Expected direction 'Skip', got '{vote.direction}'"
    assert vote.confidence == 0.0, f"Expected confidence 0.0, got {vote.confidence}"
    assert vote.quality == 0.0, f"Expected quality 0.0, got {vote.quality}"

    print("✅ Skip vote created successfully")
    print(f"   Direction: {vote.direction}")
    print(f"   Confidence: {vote.confidence}")
    print(f"   Quality: {vote.quality}")
    print(f"   Reasoning: {vote.reasoning}")


def test_skip_vote_validation():
    """Test that Skip is accepted in direction validation."""
    print("\nTest 2: Skip vote validation...")

    # Should NOT raise AssertionError
    try:
        vote = Vote(
            direction="Skip",
            confidence=0.5,  # Can have non-zero confidence if needed
            quality=0.3,
            agent_name="TestAgent",
            reasoning="Weak skip signal"
        )
        print("✅ Skip accepted in validation (no AssertionError)")
        print(f"   Vote created: {vote.direction} @ {vote.confidence:.2f}")
    except AssertionError as e:
        print(f"❌ FAILED: Skip rejected by validation: {e}")
        sys.exit(1)


def test_invalid_direction_still_rejected():
    """Test that invalid directions are still rejected."""
    print("\nTest 3: Invalid direction rejection...")

    try:
        vote = Vote(
            direction="Maybe",  # Invalid
            confidence=0.5,
            quality=0.5,
            agent_name="TestAgent",
            reasoning="This should fail"
        )
        print("❌ FAILED: Invalid direction 'Maybe' was accepted")
        sys.exit(1)
    except AssertionError as e:
        print("✅ Invalid direction 'Maybe' correctly rejected")
        print(f"   Error: {e}")


def test_all_valid_directions():
    """Test that all four valid directions work."""
    print("\nTest 4: All valid directions...")

    valid_directions = ["Up", "Down", "Neutral", "Skip"]

    for direction in valid_directions:
        vote = Vote(
            direction=direction,
            confidence=0.5,
            quality=0.5,
            agent_name="TestAgent",
            reasoning=f"Testing {direction} direction"
        )
        assert vote.direction == direction
        print(f"✅ {direction} vote created successfully")


def test_skip_weighted_score():
    """Test that Skip vote with 0.0 confidence/quality returns 0 weighted score."""
    print("\nTest 5: Skip vote weighted score...")

    vote = Vote(
        direction="Skip",
        confidence=0.0,
        quality=0.0,
        agent_name="TestAgent",
        reasoning="Abstaining"
    )

    weighted = vote.weighted_score(weight=1.5)
    assert weighted == 0.0, f"Expected weighted score 0.0, got {weighted}"

    print("✅ Skip vote weighted score is 0.0")
    print(f"   Formula: {vote.confidence} × {vote.quality} × 1.5 = {weighted}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing US-BF-005: Skip Vote Type Implementation")
    print("=" * 70)

    test_skip_vote_creation()
    test_skip_vote_validation()
    test_invalid_direction_still_rejected()
    test_all_valid_directions()
    test_skip_weighted_score()

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
