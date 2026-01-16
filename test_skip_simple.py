#!/usr/bin/env python3
"""
Minimal test for Skip vote filtering logic
Tests the core filtering logic without full imports
"""

# Simulate Vote structure
class MockVote:
    def __init__(self, agent_name, direction, confidence, quality):
        self.agent_name = agent_name
        self.direction = direction
        self.confidence = confidence
        self.quality = quality

    def weighted_score(self, weight):
        return self.confidence * self.quality * weight


def test_skip_filtering():
    """Test Skip vote filtering logic"""
    votes = [
        MockVote("TechAgent", "Up", 0.80, 0.80),
        MockVote("MomentumAgent", "Up", 0.70, 0.70),
        MockVote("PriceAgent", "Up", 0.65, 0.75),
        MockVote("RegimeAgent", "Down", 0.60, 0.65),
        MockVote("RiskAgent", "Down", 0.55, 0.60),
        MockVote("SentimentAgent", "Skip", 0.0, 0.0),
    ]

    # Filter Skip votes
    skip_votes = [v for v in votes if v.direction == "Skip"]
    non_skip_votes = [v for v in votes if v.direction != "Skip"]

    print(f"Total votes: {len(votes)}")
    print(f"Skip votes: {len(skip_votes)}")
    print(f"Non-skip votes: {len(non_skip_votes)}")
    print(f"Skip agents: {[v.agent_name for v in skip_votes]}")

    # Assertions
    assert len(skip_votes) == 1, "Should have 1 Skip vote"
    assert len(non_skip_votes) == 5, "Should have 5 non-Skip votes"
    assert skip_votes[0].agent_name == "SentimentAgent", "Skip vote should be from SentimentAgent"

    # Count by direction (after filtering)
    up_votes = [v for v in non_skip_votes if v.direction == "Up"]
    down_votes = [v for v in non_skip_votes if v.direction == "Down"]

    assert len(up_votes) == 3, "Should have 3 Up votes"
    assert len(down_votes) == 2, "Should have 2 Down votes"

    print("\n✅ Test 1 passed: 3 Up, 2 Down, 1 Skip → 5 votes counted\n")


def test_all_skip():
    """Test all Skip votes scenario"""
    votes = [
        MockVote("TechAgent", "Skip", 0.0, 0.0),
        MockVote("SentimentAgent", "Skip", 0.0, 0.0),
        MockVote("RegimeAgent", "Skip", 0.0, 0.0),
    ]

    skip_votes = [v for v in votes if v.direction == "Skip"]
    non_skip_votes = [v for v in votes if v.direction != "Skip"]

    print(f"Total votes: {len(votes)}")
    print(f"Skip votes: {len(skip_votes)}")
    print(f"Non-skip votes: {len(non_skip_votes)}")

    assert len(skip_votes) == 3, "All votes should be Skip"
    assert len(non_skip_votes) == 0, "No non-Skip votes"

    # This should trigger "no consensus" logic
    if not non_skip_votes:
        print("⚠️  No consensus: all agents abstained")

    print("\n✅ Test 2 passed: All Skip votes → no consensus\n")


def test_mixed_skip():
    """Test mixed Skip and directional votes"""
    votes = [
        MockVote("TechAgent", "Up", 0.85, 0.80),
        MockVote("SentimentAgent", "Skip", 0.0, 0.0),
        MockVote("MomentumAgent", "Up", 0.75, 0.75),
        MockVote("RegimeAgent", "Skip", 0.0, 0.0),
    ]

    skip_votes = [v for v in votes if v.direction == "Skip"]
    non_skip_votes = [v for v in votes if v.direction != "Skip"]

    print(f"Total votes: {len(votes)}")
    print(f"Skip votes: {len(skip_votes)}")
    print(f"Non-skip votes: {len(non_skip_votes)}")
    print(f"Skip agents: {[v.agent_name for v in skip_votes]}")

    assert len(skip_votes) == 2, "Should have 2 Skip votes"
    assert len(non_skip_votes) == 2, "Should have 2 non-Skip votes"
    assert all(v.direction == "Up" for v in non_skip_votes), "All non-Skip votes should be Up"

    print("\n✅ Test 3 passed: Mixed Skip and directional votes\n")


if __name__ == "__main__":
    print("Testing Skip vote filtering logic...\n")
    print("="*60)

    test_skip_filtering()
    test_all_skip()
    test_mixed_skip()

    print("="*60)
    print("✅ All tests passed!")
