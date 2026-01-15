#!/usr/bin/env python3
"""
Unit tests for OrderBookAgent
"""

import unittest
import sys
import os

# Add agents directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agents'))

from voting.orderbook_agent import OrderBookAgent


class TestOrderBookAgent(unittest.TestCase):
    """Test cases for OrderBookAgent."""

    def setUp(self):
        """Initialize agent for testing."""
        self.agent = OrderBookAgent()

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        self.assertEqual(self.agent.name, "OrderBookAgent")
        self.assertEqual(self.agent.weight, 1.0)

    def test_simplified_orderbook_bullish_imbalance(self):
        """Test simplified orderbook with bullish imbalance (Down cheaper)."""
        data = {
            'orderbook': {
                'Up': {'price': 0.60, 'ask': 0.60},
                'Down': {'price': 0.40, 'ask': 0.40}  # Down is cheap = bullish for Up
            }
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Should vote Up (bullish) because Down is cheaper (more supply of Down)
        self.assertEqual(vote.direction, "Up")
        self.assertGreaterEqual(vote.confidence, 0.34)  # Allow for floating point rounding
        # Quality is low (0.2) because spread is wide (40%)
        self.assertEqual(vote.quality, 0.2)  # Wide spread = low quality
        self.assertEqual(vote.agent_name, "OrderBookAgent")
        self.assertIn('imbalance', vote.details)

    def test_simplified_orderbook_bearish_imbalance(self):
        """Test simplified orderbook with bearish imbalance (Up cheaper)."""
        data = {
            'orderbook': {
                'Up': {'price': 0.30, 'ask': 0.30},    # Up is cheap = bearish
                'Down': {'price': 0.70, 'ask': 0.70}
            }
        }

        vote = self.agent.analyze('eth', 1234567890, data)

        # Should vote Down (bearish) because Up is cheaper (more supply of Up)
        self.assertEqual(vote.direction, "Down")
        self.assertGreater(vote.confidence, 0.35)

    def test_detailed_orderbook_strong_bid_imbalance(self):
        """Test detailed orderbook with strong bid imbalance."""
        data = {
            'orderbook': {
                'bids': [
                    {'price': '0.48', 'size': '1000'},
                    {'price': '0.47', 'size': '500'},
                    {'price': '0.46', 'size': '300'}
                ],
                'asks': [
                    {'price': '0.52', 'size': '200'},
                    {'price': '0.53', 'size': '100'}
                ]
            }
        }

        vote = self.agent.analyze('sol', 1234567890, data)

        # Should vote Up (more bid volume)
        self.assertEqual(vote.direction, "Up")
        self.assertGreater(vote.confidence, 0.5)
        self.assertIn('imbalance', vote.details)
        self.assertGreater(vote.details['imbalance'], 0.15)  # Positive imbalance

    def test_detailed_orderbook_strong_ask_imbalance(self):
        """Test detailed orderbook with strong ask imbalance."""
        data = {
            'orderbook': {
                'bids': [
                    {'price': '0.48', 'size': '150'},
                ],
                'asks': [
                    {'price': '0.52', 'size': '800'},
                    {'price': '0.53', 'size': '400'},
                    {'price': '0.54', 'size': '200'}
                ]
            }
        }

        vote = self.agent.analyze('xrp', 1234567890, data)

        # Should vote Down (more ask volume)
        self.assertEqual(vote.direction, "Down")
        self.assertGreater(vote.confidence, 0.5)
        self.assertLess(vote.details['imbalance'], -0.15)  # Negative imbalance

    def test_tight_spread_high_quality(self):
        """Test that tight spread results in high quality score."""
        data = {
            'orderbook': {
                'bids': [
                    {'price': '0.49', 'size': '500'},
                ],
                'asks': [
                    {'price': '0.51', 'size': '500'}
                ]
            }
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Tight spread should result in high quality
        self.assertGreater(vote.quality, 0.7)
        self.assertLess(vote.details['spread_pct'], 0.05)

    def test_wide_spread_low_quality(self):
        """Test that wide spread results in low quality score."""
        data = {
            'orderbook': {
                'bids': [
                    {'price': '0.30', 'size': '500'},
                ],
                'asks': [
                    {'price': '0.70', 'size': '500'}
                ]
            }
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Wide spread should result in low quality
        self.assertLess(vote.quality, 0.5)
        self.assertGreater(vote.details['spread_pct'], 0.10)

    def test_no_orderbook_data(self):
        """Test fallback when no orderbook data available."""
        data = {
            'orderbook': {}
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Should return low-confidence Up vote
        self.assertEqual(vote.direction, "Up")
        self.assertEqual(vote.confidence, 0.35)
        self.assertEqual(vote.quality, 0.3)
        self.assertIn("No orderbook data", vote.reasoning)

    def test_vote_validation(self):
        """Test that Vote structure is valid."""
        data = {
            'orderbook': {
                'Up': {'price': 0.45, 'ask': 0.45},
                'Down': {'price': 0.55, 'ask': 0.55}
            }
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Validate vote structure
        self.assertIn(vote.direction, ["Up", "Down"])
        self.assertGreaterEqual(vote.confidence, 0.0)
        self.assertLessEqual(vote.confidence, 1.0)
        self.assertGreaterEqual(vote.quality, 0.0)
        self.assertLessEqual(vote.quality, 1.0)
        self.assertTrue(len(vote.reasoning) > 0)

    def test_wall_detection(self):
        """Test detection of large order walls."""
        data = {
            'orderbook': {
                'bids': [
                    {'price': '0.48', 'size': '50'},    # Small order
                    {'price': '0.45', 'size': '500'},   # LARGE BID WALL
                ],
                'asks': [
                    {'price': '0.52', 'size': '100'}
                ]
            }
        }

        vote = self.agent.analyze('btc', 1234567890, data)

        # Should detect bid wall
        self.assertEqual(vote.details['largest_bid_wall'], 500)
        self.assertIn("bid wall", vote.reasoning)

    def test_historical_metrics_tracking(self):
        """Test that agent tracks historical metrics."""
        data = {
            'orderbook': {
                'Up': {'price': 0.45, 'ask': 0.45},
                'Down': {'price': 0.55, 'ask': 0.55}
            }
        }

        # Analyze multiple times
        self.agent.analyze('btc', 1234567890, data)
        self.agent.analyze('btc', 1234567891, data)
        self.agent.analyze('btc', 1234567892, data)

        # Should have 3 metrics stored
        self.assertEqual(len(self.agent.historical_metrics['btc']), 3)

    def test_historical_metrics_max_length(self):
        """Test that historical metrics are limited to 10 entries."""
        data = {
            'orderbook': {
                'Up': {'price': 0.45, 'ask': 0.45},
                'Down': {'price': 0.55, 'ask': 0.55}
            }
        }

        # Analyze 15 times
        for i in range(15):
            self.agent.analyze('btc', 1234567890 + i, data)

        # Should only keep last 10
        self.assertEqual(len(self.agent.historical_metrics['btc']), 10)


if __name__ == '__main__':
    unittest.main()
