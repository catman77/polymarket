#!/usr/bin/env python3
"""
Test Vote Aggregator Skip Vote Handling

Verifies that Skip votes are properly filtered from consensus calculation.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from coordinator.vote_aggregator import VoteAggregator, AggregatePrediction
from agents.base_agent import Vote


def test_skip_votes_filtered_from_consensus():
    """Test: 3 Up, 2 Down, 1 Skip → consensus calculated from 5 votes (not 6)"""
    aggregator = VoteAggregator(consensus_threshold=0.70, min_agents=2)

    votes = [
        Vote(agent_name="TechAgent", direction="Up", confidence=0.80, quality=0.80, reasoning="Strong up trend"),
        Vote(agent_name="MomentumAgent", direction="Up", confidence=0.70, quality=0.70, reasoning="Positive momentum"),
        Vote(agent_name="PriceAgent", direction="Up", confidence=0.65, quality=0.75, reasoning="Price support"),
        Vote(agent_name="RegimeAgent", direction="Down", confidence=0.60, quality=0.65, reasoning="Bear regime"),
        Vote(agent_name="RiskAgent", direction="Down", confidence=0.55, quality=0.60, reasoning="High risk"),
        Vote(agent_name="SentimentAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="No orderbook data"),
    ]

    weights = {name: 1.0 for name in ["TechAgent", "MomentumAgent", "PriceAgent", "RegimeAgent", "RiskAgent", "SentimentAgent"]}

    result = aggregator.aggregate_votes(votes, weights)

    # Should have 5 participating agents (Skip filtered out)
    assert result.total_agents == 5, f"Expected 5 agents, got {result.total_agents}"

    # Should have 3 Up, 2 Down, 0 Neutral
    assert result.up_votes == 3, f"Expected 3 Up votes, got {result.up_votes}"
    assert result.down_votes == 2, f"Expected 2 Down votes, got {result.down_votes}"
    assert result.neutral_votes == 0, f"Expected 0 Neutral votes, got {result.neutral_votes}"

    # SentimentAgent should not be in participating list
    assert "SentimentAgent" not in result.participating_agents, "Skip voter should not be in participating list"
    assert len(result.participating_agents) == 5, f"Expected 5 participating agents, got {len(result.participating_agents)}"

    print("✅ Test passed: Skip votes correctly filtered from consensus (3 Up, 2 Down, 1 Skip → 5 votes counted)")


def test_all_skip_votes_returns_no_consensus():
    """Test: All Skip votes → return no consensus (skip trade)"""
    aggregator = VoteAggregator(consensus_threshold=0.70, min_agents=2)

    votes = [
        Vote(agent_name="TechAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="No confluence"),
        Vote(agent_name="SentimentAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="No orderbook"),
        Vote(agent_name="RegimeAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="Sideways regime"),
    ]

    weights = {name: 1.0 for name in ["TechAgent", "SentimentAgent", "RegimeAgent"]}

    result = aggregator.aggregate_votes(votes, weights)

    # Should return empty prediction
    assert result.direction == "Neutral", f"Expected Neutral direction, got {result.direction}"
    assert result.weighted_score == 0.0, f"Expected 0.0 weighted score, got {result.weighted_score}"
    assert result.total_agents == 0, f"Expected 0 agents, got {result.total_agents}"
    assert result.participating_agents == [], f"Expected empty list, got {result.participating_agents}"

    print("✅ Test passed: All Skip votes returns no consensus (empty prediction)")


def test_mixed_skip_and_directional_votes():
    """Test: Mix of Skip and directional votes, only directional votes counted"""
    aggregator = VoteAggregator(consensus_threshold=0.70, min_agents=2)

    votes = [
        Vote(agent_name="TechAgent", direction="Up", confidence=0.85, quality=0.80, reasoning="Strong confluence"),
        Vote(agent_name="SentimentAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="No contrarian signal"),
        Vote(agent_name="MomentumAgent", direction="Up", confidence=0.75, quality=0.75, reasoning="Momentum up"),
        Vote(agent_name="RegimeAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="Sideways regime"),
    ]

    weights = {name: 1.0 for name in ["TechAgent", "SentimentAgent", "MomentumAgent", "RegimeAgent"]}

    result = aggregator.aggregate_votes(votes, weights)

    # Should only count 2 Up votes (2 Skip votes filtered)
    assert result.total_agents == 2, f"Expected 2 agents, got {result.total_agents}"
    assert result.up_votes == 2, f"Expected 2 Up votes, got {result.up_votes}"
    assert result.down_votes == 0, f"Expected 0 Down votes, got {result.down_votes}"
    assert result.direction == "Up", f"Expected Up direction, got {result.direction}"

    # Skip voters should not be in participating list
    assert "SentimentAgent" not in result.participating_agents
    assert "RegimeAgent" not in result.participating_agents
    assert "TechAgent" in result.participating_agents
    assert "MomentumAgent" in result.participating_agents

    print("✅ Test passed: Mixed Skip and directional votes - only directional votes counted")


def test_skip_vote_validation():
    """Test: Skip votes pass validation"""
    aggregator = VoteAggregator(consensus_threshold=0.70, min_agents=2)

    votes = [
        Vote(agent_name="TechAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="Uncertain"),
        Vote(agent_name="SentimentAgent", direction="Up", confidence=0.70, quality=0.70, reasoning="Contrarian fade"),
    ]

    is_valid, error_msg = aggregator.validate_votes(votes)

    assert is_valid, f"Expected valid votes, got error: {error_msg}"

    print("✅ Test passed: Skip votes pass validation")


def test_one_skip_one_directional_below_min_agents():
    """Test: 1 Skip + 1 Up (below min_agents=2) → warning but still processes"""
    aggregator = VoteAggregator(consensus_threshold=0.70, min_agents=2)

    votes = [
        Vote(agent_name="TechAgent", direction="Skip", confidence=0.0, quality=0.0, reasoning="No confluence"),
        Vote(agent_name="SentimentAgent", direction="Up", confidence=0.75, quality=0.75, reasoning="Contrarian"),
    ]

    weights = {name: 1.0 for name in ["TechAgent", "SentimentAgent"]}

    result = aggregator.aggregate_votes(votes, weights)

    # After filtering Skip, only 1 agent remains → below min_agents threshold
    # Should return empty prediction (not enough high-quality votes)
    assert result.total_agents == 0, f"Expected 0 agents (below threshold), got {result.total_agents}"
    assert result.direction == "Neutral", f"Expected Neutral, got {result.direction}"

    print("✅ Test passed: 1 Skip + 1 directional (below min_agents) → returns empty prediction")


if __name__ == "__main__":
    print("Testing Vote Aggregator Skip Vote Handling...\n")

    test_skip_votes_filtered_from_consensus()
    test_all_skip_votes_returns_no_consensus()
    test_mixed_skip_and_directional_votes()
    test_skip_vote_validation()
    test_one_skip_one_directional_below_min_agents()

    print("\n✅ All tests passed!")
