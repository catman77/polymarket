"""
Test TechAgent Skip vote behavior
Validates US-BF-001: Remove TechAgent default-to-Up bias
"""

import sys
from unittest.mock import MagicMock, patch

# Mock the imports
sys.modules['py_clob_client'] = MagicMock()
sys.modules['web3'] = MagicMock()

from agents.tech_agent import TechAgent

def test_tie_scenario_returns_skip():
    """Test: 2 Up, 2 Down (tie) should return Skip vote"""
    agent = TechAgent()

    # Mock price feed to return None direction (no confluence)
    with patch.object(agent.price_feed, 'get_confluence_signal') as mock_signal:
        # Simulate tie: 2 exchanges Up, 2 exchanges Down
        mock_signal.return_value = (
            None,  # direction = None (no confluence)
            0,     # agreeing_count = 0
            0.0,   # avg_change = 0.0 (flat)
            {
                'binance': 'Up',
                'kraken': 'Down',
                'coinbase': 'Up',
                'gemini': 'Down'
            }
        )

        vote = agent.analyze("BTC", 1234567890, {})

        assert vote.direction == "Skip", f"Expected Skip, got {vote.direction}"
        assert vote.confidence == 0.0, f"Expected confidence=0.0, got {vote.confidence}"
        assert vote.quality == 0.0, f"Expected quality=0.0, got {vote.quality}"
        assert "ABSTAINING" in vote.reasoning, f"Expected 'ABSTAINING' in reasoning, got: {vote.reasoning}"
        print("✓ Tie scenario (2 Up, 2 Down) returns Skip vote")

def test_flat_market_returns_skip():
    """Test: avg_change=0 (flat market) should return Skip vote"""
    agent = TechAgent()

    with patch.object(agent.price_feed, 'get_confluence_signal') as mock_signal:
        # Simulate flat market: no change, equal signals
        mock_signal.return_value = (
            None,  # direction = None
            0,     # agreeing_count = 0
            0.0,   # avg_change = 0.0 (perfectly flat)
            {
                'binance': 'Up',
                'kraken': 'Down'
            }
        )

        vote = agent.analyze("ETH", 1234567890, {})

        assert vote.direction == "Skip", f"Expected Skip, got {vote.direction}"
        assert vote.confidence == 0.0
        assert vote.quality == 0.0
        assert "No confluence detected" in vote.reasoning
        print("✓ Flat market (avg_change=0) returns Skip vote")

def test_majority_up_still_returns_up():
    """Test: 3 Up, 1 Down (clear majority) should still return Up"""
    agent = TechAgent()

    with patch.object(agent.price_feed, 'get_confluence_signal') as mock_signal:
        mock_signal.return_value = (
            None,  # direction = None (no confluence threshold met)
            0,
            0.25,  # avg_change = +0.25% (slight up)
            {
                'binance': 'Up',
                'kraken': 'Up',
                'coinbase': 'Up',
                'gemini': 'Down'
            }
        )

        vote = agent.analyze("BTC", 1234567890, {})

        assert vote.direction == "Up", f"Expected Up, got {vote.direction}"
        assert vote.confidence == 0.35  # Weak signal floor
        assert "Weak signal: 3Up/1Down" in vote.reasoning
        print("✓ Majority Up (3 Up, 1 Down) returns Up vote")

def test_majority_down_still_returns_down():
    """Test: 1 Up, 3 Down (clear majority) should return Down"""
    agent = TechAgent()

    with patch.object(agent.price_feed, 'get_confluence_signal') as mock_signal:
        mock_signal.return_value = (
            None,  # direction = None
            0,
            -0.18,  # avg_change = -0.18% (slight down)
            {
                'binance': 'Down',
                'kraken': 'Down',
                'coinbase': 'Up',
                'gemini': 'Down'
            }
        )

        vote = agent.analyze("SOL", 1234567890, {})

        assert vote.direction == "Down", f"Expected Down, got {vote.direction}"
        assert vote.confidence == 0.35
        assert "Weak signal: 1Up/3Down" in vote.reasoning
        print("✓ Majority Down (1 Up, 3 Down) returns Down vote")

def test_confluence_detected_still_works():
    """Test: Confluence detected (strong signal) should return normal vote"""
    agent = TechAgent()

    with patch.object(agent.price_feed, 'get_confluence_signal') as mock_signal:
        # Simulate strong confluence
        mock_signal.return_value = (
            "Up",  # direction = Up (confluence threshold met)
            3,     # agreeing_count = 3
            0.45,  # avg_change = +0.45% (above 0.30% threshold)
            {
                'binance': 'Up',
                'kraken': 'Up',
                'coinbase': 'Up'
            }
        )

        vote = agent.analyze("BTC", 1234567890, {})

        assert vote.direction == "Up", f"Expected Up, got {vote.direction}"
        assert vote.confidence > 0.5, f"Expected high confidence, got {vote.confidence}"
        print("✓ Confluence detected returns normal high-confidence vote")

if __name__ == "__main__":
    print("Testing TechAgent Skip vote behavior (US-BF-001)...")
    print()

    test_tie_scenario_returns_skip()
    test_flat_market_returns_skip()
    test_majority_up_still_returns_up()
    test_majority_down_still_returns_down()
    test_confluence_detected_still_works()

    print()
    print("✅ All tests passed! TechAgent now abstains on ties/flat markets.")
    print("   No more default-to-Up bias.")
