#!/usr/bin/env python3
"""
Unit tests for FundingRateAgent

Tests funding rate analysis, signal generation, and edge cases.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.voting.funding_rate_agent import (
    FundingRateAgent,
    FundingMetrics,
    FUNDING_EXTREME_THRESHOLD,
    FUNDING_MODERATE_THRESHOLD,
    FUNDING_NEUTRAL_THRESHOLD
)


class TestFundingRateAgent(unittest.TestCase):
    """Test FundingRateAgent voting logic."""

    def setUp(self):
        """Set up test agent."""
        self.agent = FundingRateAgent()

    def test_extreme_positive_funding_contrarian_down(self):
        """Extreme positive funding (>0.10%) should signal DOWN (reversal)."""
        metrics = self.agent._compute_metrics(
            current_funding=0.15,  # 0.15% = extreme positive
            open_interest=1000000,
            oi_change_24h=None
        )

        self.assertEqual(metrics.signal_direction, "Down")
        self.assertGreaterEqual(metrics.signal_confidence, 0.70)  # High confidence
        self.assertGreaterEqual(metrics.signal_quality, 0.85)      # High quality
        self.assertEqual(metrics.funding_bias, "long")
        self.assertIn("EXTREME", metrics.reasoning)
        self.assertIn("reversal", metrics.reasoning.lower())

    def test_extreme_negative_funding_contrarian_up(self):
        """Extreme negative funding (<-0.10%) should signal UP (reversal)."""
        metrics = self.agent._compute_metrics(
            current_funding=-0.12,  # -0.12% = extreme negative
            open_interest=1000000,
            oi_change_24h=None
        )

        self.assertEqual(metrics.signal_direction, "Up")
        self.assertGreaterEqual(metrics.signal_confidence, 0.70)
        self.assertGreaterEqual(metrics.signal_quality, 0.85)
        self.assertEqual(metrics.funding_bias, "short")
        self.assertIn("EXTREME", metrics.reasoning)
        self.assertIn("reversal", metrics.reasoning.lower())

    def test_moderate_positive_funding_aligned_up(self):
        """Moderate positive funding (0.05-0.10%) should signal UP (continuation)."""
        metrics = self.agent._compute_metrics(
            current_funding=0.07,  # 0.07% = moderate positive
            open_interest=1000000,
            oi_change_24h=None
        )

        self.assertEqual(metrics.signal_direction, "Up")
        self.assertGreaterEqual(metrics.signal_confidence, 0.50)
        self.assertGreaterEqual(metrics.signal_quality, 0.65)
        self.assertEqual(metrics.funding_bias, "long")
        self.assertIn("MODERATE", metrics.reasoning)
        self.assertIn("continuation", metrics.reasoning.lower())

    def test_moderate_negative_funding_aligned_down(self):
        """Moderate negative funding (-0.05 to -0.10%) should signal DOWN (continuation)."""
        metrics = self.agent._compute_metrics(
            current_funding=-0.06,  # -0.06% = moderate negative
            open_interest=1000000,
            oi_change_24h=None
        )

        self.assertEqual(metrics.signal_direction, "Down")
        self.assertGreaterEqual(metrics.signal_confidence, 0.50)
        self.assertGreaterEqual(metrics.signal_quality, 0.65)
        self.assertEqual(metrics.funding_bias, "short")
        self.assertIn("MODERATE", metrics.reasoning)
        self.assertIn("continuation", metrics.reasoning.lower())

    def test_neutral_funding_returns_neutral(self):
        """Near-zero funding (<0.05%) should return Neutral."""
        metrics = self.agent._compute_metrics(
            current_funding=0.02,  # 0.02% = neutral
            open_interest=1000000,
            oi_change_24h=None
        )

        self.assertEqual(metrics.signal_direction, "Neutral")
        self.assertLess(metrics.signal_confidence, 0.50)
        self.assertLess(metrics.signal_quality, 0.60)
        self.assertIn("NEUTRAL", metrics.reasoning)

    def test_oi_surge_boosts_confidence(self):
        """Large OI change (>15%) should boost confidence."""
        # Without OI change
        metrics_no_oi = self.agent._compute_metrics(
            current_funding=0.12,
            open_interest=1000000,
            oi_change_24h=None
        )

        # With OI surge
        metrics_with_oi = self.agent._compute_metrics(
            current_funding=0.12,
            open_interest=1000000,
            oi_change_24h=20.0  # 20% surge
        )

        self.assertGreater(metrics_with_oi.signal_confidence, metrics_no_oi.signal_confidence)
        self.assertIn("OI surge", metrics_with_oi.reasoning)

    def test_moderate_oi_change_boosts_confidence(self):
        """Moderate OI change (5-15%) should slightly boost confidence."""
        metrics_no_oi = self.agent._compute_metrics(
            current_funding=0.08,
            open_interest=1000000,
            oi_change_24h=None
        )

        metrics_with_oi = self.agent._compute_metrics(
            current_funding=0.08,
            open_interest=1000000,
            oi_change_24h=8.0  # 8% change
        )

        self.assertGreater(metrics_with_oi.signal_confidence, metrics_no_oi.signal_confidence)
        self.assertIn("OI change", metrics_with_oi.reasoning)

    def test_funding_strength_calculation(self):
        """Funding strength should scale from 0 to 1."""
        # Zero funding
        metrics_zero = self.agent._compute_metrics(0.0, 1000000, None)
        self.assertEqual(metrics_zero.funding_strength, 0.0)

        # Half of extreme threshold
        metrics_half = self.agent._compute_metrics(0.05, 1000000, None)
        self.assertAlmostEqual(metrics_half.funding_strength, 0.5, places=1)

        # At extreme threshold
        metrics_extreme = self.agent._compute_metrics(0.10, 1000000, None)
        self.assertAlmostEqual(metrics_extreme.funding_strength, 1.0, places=1)

        # Beyond extreme threshold (capped at 1.0)
        metrics_beyond = self.agent._compute_metrics(0.20, 1000000, None)
        self.assertEqual(metrics_beyond.funding_strength, 1.0)

    def test_quality_score_tiers(self):
        """Quality score should vary by funding magnitude."""
        # Extreme funding = highest quality
        metrics_extreme = self.agent._compute_metrics(0.15, 1000000, None)
        self.assertGreaterEqual(metrics_extreme.signal_quality, 0.85)

        # Moderate funding = medium quality
        metrics_moderate = self.agent._compute_metrics(0.07, 1000000, None)
        self.assertGreaterEqual(metrics_moderate.signal_quality, 0.65)
        self.assertLess(metrics_moderate.signal_quality, 0.85)

        # Neutral funding = low quality
        metrics_neutral = self.agent._compute_metrics(0.02, 1000000, None)
        self.assertLess(metrics_neutral.signal_quality, 0.60)

    @patch('agents.voting.funding_rate_agent.requests')
    def test_analyze_returns_vote(self, mock_requests):
        """analyze() should return a valid Vote object."""
        # Mock API responses
        mock_funding_resp = Mock()
        mock_funding_resp.json.return_value = [{'fundingRate': 0.0008}]  # 0.08%
        mock_funding_resp.raise_for_status = Mock()

        mock_oi_resp = Mock()
        mock_oi_resp.json.return_value = {'openInterest': 1000000}
        mock_oi_resp.raise_for_status = Mock()

        mock_ticker_resp = Mock()
        mock_ticker_resp.json.return_value = {'volume': 500000}
        mock_ticker_resp.raise_for_status = Mock()

        mock_requests.get.side_effect = [mock_funding_resp, mock_oi_resp, mock_ticker_resp]

        vote = self.agent.analyze('btc', 1234567890, {})

        self.assertIn(vote.direction, ["Up", "Down", "Neutral"])
        self.assertGreaterEqual(vote.confidence, 0.0)
        self.assertLessEqual(vote.confidence, 1.0)
        self.assertGreaterEqual(vote.quality, 0.0)
        self.assertLessEqual(vote.quality, 1.0)
        self.assertEqual(vote.agent_name, "FundingRateAgent")
        self.assertTrue(len(vote.reasoning) > 0)
        self.assertIn('funding_rate', vote.details)

    def test_analyze_invalid_crypto_returns_neutral(self):
        """analyze() with invalid crypto should return neutral vote."""
        vote = self.agent.analyze('INVALID', 1234567890, {})

        self.assertEqual(vote.direction, "Neutral")
        self.assertLessEqual(vote.confidence, 0.35)
        self.assertIn("Unsupported", vote.reasoning)

    @patch('agents.voting.funding_rate_agent.requests')
    def test_analyze_api_failure_returns_neutral(self, mock_requests):
        """analyze() should return neutral vote if API fails."""
        mock_requests.get.side_effect = Exception("API Error")

        vote = self.agent.analyze('btc', 1234567890, {})

        self.assertEqual(vote.direction, "Neutral")
        self.assertIn("failed", vote.reasoning.lower())

    @patch('agents.voting.funding_rate_agent.requests')
    def test_caching_reduces_api_calls(self, mock_requests):
        """Second call within cache TTL should use cached data."""
        # Mock first call
        mock_funding_resp = Mock()
        mock_funding_resp.json.return_value = [{'fundingRate': 0.0008}]
        mock_funding_resp.raise_for_status = Mock()

        mock_oi_resp = Mock()
        mock_oi_resp.json.return_value = {'openInterest': 1000000}
        mock_oi_resp.raise_for_status = Mock()

        mock_ticker_resp = Mock()
        mock_ticker_resp.json.return_value = {'volume': 500000}
        mock_ticker_resp.raise_for_status = Mock()

        mock_requests.get.side_effect = [mock_funding_resp, mock_oi_resp, mock_ticker_resp]

        # First call - should hit API
        vote1 = self.agent.analyze('btc', 1234567890, {})

        # Second call - should use cache (no new API calls)
        vote2 = self.agent.analyze('btc', 1234567890, {})

        # Should have made 3 API calls total (funding, OI, ticker)
        self.assertEqual(mock_requests.get.call_count, 3)

        # Results should be identical
        self.assertEqual(vote1.direction, vote2.direction)
        self.assertEqual(vote1.confidence, vote2.confidence)


if __name__ == '__main__':
    unittest.main()
