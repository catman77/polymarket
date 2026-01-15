#!/usr/bin/env python3
"""
Unit tests for SocialSentimentAgent.

Tests social sentiment analysis including:
- Twitter mentions and sentiment
- Reddit sentiment and upvote ratios
- Google Trends momentum
- Contrarian signals (extreme sentiment)
- Momentum signals (moderate sentiment + volume)
- Quality scoring
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.voting.social_sentiment_agent import (
    SocialSentimentAgent,
    SocialMetrics,
    SENTIMENT_EXTREME_THRESHOLD,
    SENTIMENT_MODERATE_THRESHOLD,
    VOLUME_HIGH_THRESHOLD,
    TRENDS_RISING_THRESHOLD
)


class TestSocialSentimentAgent(unittest.TestCase):
    """Test SocialSentimentAgent functionality."""

    def setUp(self):
        """Initialize agent for testing."""
        self.agent = SocialSentimentAgent(
            name="TestSocialAgent",
            weight=1.0,
            twitter_api_key="test_key",
            reddit_client_id="test_id",
            reddit_client_secret="test_secret"
        )

    def test_init(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.name, "TestSocialAgent")
        self.assertEqual(self.agent.weight, 1.0)
        self.assertIsNotNone(self.agent._cache)
        self.assertIsNotNone(self.agent._volume_history)

    def test_analyze_extreme_bullish_sentiment(self):
        """Test contrarian DOWN signal on extreme bullishness."""
        # Mock social metrics
        mock_metrics = SocialMetrics(
            twitter_mentions=100,
            twitter_sentiment=0.75,  # Extreme bullish
            twitter_volume_ratio=1.5,
            reddit_mentions=50,
            reddit_sentiment=0.70,
            reddit_upvote_ratio=0.85,
            trends_score=80,
            trends_momentum=10,
            signal_direction="Down",
            signal_confidence=0.70,
            signal_quality=0.85,
            reasoning="Extreme bullish sentiment (0.72) = FOMO peak"
        )

        with patch.object(self.agent, '_get_social_metrics', return_value=mock_metrics):
            vote = self.agent.analyze('btc', 1234567890, {})

        self.assertEqual(vote.direction, "Down")
        self.assertGreaterEqual(vote.confidence, 0.70)
        self.assertGreater(vote.quality, 0.0)
        self.assertIn("FOMO", vote.reasoning)

    def test_analyze_extreme_bearish_sentiment(self):
        """Test contrarian UP signal on extreme bearishness."""
        mock_metrics = SocialMetrics(
            twitter_mentions=80,
            twitter_sentiment=-0.75,  # Extreme bearish
            twitter_volume_ratio=1.2,
            reddit_mentions=40,
            reddit_sentiment=-0.65,
            reddit_upvote_ratio=0.40,
            trends_score=30,
            trends_momentum=-5,
            signal_direction="Up",
            signal_confidence=0.70,
            signal_quality=0.80,
            reasoning="Extreme bearish sentiment (-0.70) = fear trough"
        )

        with patch.object(self.agent, '_get_social_metrics', return_value=mock_metrics):
            vote = self.agent.analyze('eth', 1234567890, {})

        self.assertEqual(vote.direction, "Up")
        self.assertGreaterEqual(vote.confidence, 0.70)
        self.assertGreater(vote.quality, 0.0)
        self.assertIn("fear", vote.reasoning)

    def test_analyze_moderate_bullish_sentiment(self):
        """Test momentum UP signal on moderate bullishness."""
        mock_metrics = SocialMetrics(
            twitter_mentions=60,
            twitter_sentiment=0.45,  # Moderate bullish
            twitter_volume_ratio=1.8,
            reddit_mentions=30,
            reddit_sentiment=0.40,
            reddit_upvote_ratio=0.75,
            trends_score=60,
            trends_momentum=15,
            signal_direction="Up",
            signal_confidence=0.50,
            signal_quality=0.75,
            reasoning="Moderate bullish sentiment (0.43) | High Twitter volume (1.8x)"
        )

        with patch.object(self.agent, '_get_social_metrics', return_value=mock_metrics):
            vote = self.agent.analyze('sol', 1234567890, {})

        self.assertEqual(vote.direction, "Up")
        self.assertGreaterEqual(vote.confidence, 0.50)
        self.assertGreater(vote.quality, 0.0)

    def test_analyze_moderate_bearish_sentiment(self):
        """Test momentum DOWN signal on moderate bearishness."""
        mock_metrics = SocialMetrics(
            twitter_mentions=50,
            twitter_sentiment=-0.45,  # Moderate bearish
            twitter_volume_ratio=1.3,
            reddit_mentions=25,
            reddit_sentiment=-0.40,
            reddit_upvote_ratio=0.55,
            trends_score=40,
            trends_momentum=-10,
            signal_direction="Down",
            signal_confidence=0.50,
            signal_quality=0.70,
            reasoning="Moderate bearish sentiment (-0.43)"
        )

        with patch.object(self.agent, '_get_social_metrics', return_value=mock_metrics):
            vote = self.agent.analyze('xrp', 1234567890, {})

        self.assertEqual(vote.direction, "Down")
        self.assertGreaterEqual(vote.confidence, 0.50)
        self.assertGreater(vote.quality, 0.0)

    def test_analyze_neutral_sentiment(self):
        """Test neutral signal on low sentiment."""
        mock_metrics = SocialMetrics(
            twitter_mentions=20,
            twitter_sentiment=0.10,  # Neutral
            twitter_volume_ratio=0.8,
            reddit_mentions=10,
            reddit_sentiment=0.05,
            reddit_upvote_ratio=0.65,
            trends_score=25,
            trends_momentum=0,
            signal_direction="Neutral",
            signal_confidence=0.0,
            signal_quality=0.50,
            reasoning="Neutral sentiment (0.07)"
        )

        with patch.object(self.agent, '_get_social_metrics', return_value=mock_metrics):
            vote = self.agent.analyze('btc', 1234567890, {})

        self.assertEqual(vote.direction, "Neutral")
        self.assertEqual(vote.confidence, 0.0)

    def test_twitter_volume_boost(self):
        """Test confidence boost from Twitter volume spike."""
        # Mock calculate_social_metrics to test volume boost logic
        twitter_data = {'mentions': 150, 'sentiment': 0.50, 'volume_ratio': 3.0}  # High volume
        reddit_data = {'mentions': 30, 'sentiment': 0.45, 'upvote_ratio': 0.75}
        trends_data = {'trends_score': 60, 'trends_momentum': 10}

        metrics = self.agent._calculate_social_metrics('btc', twitter_data, reddit_data, trends_data)

        # Should be UP direction with confidence boost
        self.assertEqual(metrics.signal_direction, "Up")
        self.assertGreater(metrics.signal_confidence, 0.50)  # Boosted by volume
        self.assertIn("Twitter volume", metrics.reasoning)

    def test_trends_momentum_boost(self):
        """Test confidence boost from Google Trends momentum."""
        twitter_data = {'mentions': 60, 'sentiment': 0.40, 'volume_ratio': 1.2}
        reddit_data = {'mentions': 25, 'sentiment': 0.38, 'upvote_ratio': 0.70}
        trends_data = {'trends_score': 70, 'trends_momentum': 35}  # Rising trends

        metrics = self.agent._calculate_social_metrics('eth', twitter_data, reddit_data, trends_data)

        # Should be UP with confidence boost from trends
        self.assertEqual(metrics.signal_direction, "Up")
        self.assertGreater(metrics.signal_confidence, 0.50)
        self.assertIn("Trends", metrics.reasoning)

    def test_quality_score_all_sources(self):
        """Test quality score with all data sources available."""
        quality = self.agent._calculate_quality_score(
            twitter_mentions=50,
            reddit_mentions=20,
            trends_score=60,
            volume_ratio=1.5
        )

        # Should have high quality (all sources + good sample size)
        self.assertGreaterEqual(quality, 0.80)

    def test_quality_score_partial_sources(self):
        """Test quality score with only some data sources."""
        quality = self.agent._calculate_quality_score(
            twitter_mentions=30,
            reddit_mentions=0,  # No Reddit
            trends_score=40,
            volume_ratio=1.2
        )

        # Should have medium quality (2/3 sources)
        self.assertGreaterEqual(quality, 0.50)
        self.assertLess(quality, 0.80)

    def test_quality_score_low_volume(self):
        """Test quality penalty for low volume."""
        quality = self.agent._calculate_quality_score(
            twitter_mentions=5,  # Low mentions
            reddit_mentions=2,
            trends_score=20,
            volume_ratio=0.2  # Very low volume
        )

        # Should have reduced quality (0.7 = 1.0 base * 0.7 penalty)
        self.assertLess(quality, 0.75)

    def test_basic_sentiment_analysis_bullish(self):
        """Test basic sentiment analysis with bullish keywords."""
        texts = [
            "Bitcoin to the moon! 🚀",
            "Very bullish on ETH right now",
            "This is going to pump hard"
        ]

        sentiment = self.agent._basic_sentiment_analysis(texts)

        # Should be positive sentiment
        self.assertGreater(sentiment, 0.3)

    def test_basic_sentiment_analysis_bearish(self):
        """Test basic sentiment analysis with bearish keywords."""
        texts = [
            "Bitcoin is going to crash",
            "Bearish on crypto right now 📉",
            "This is a dump, sell everything"
        ]

        sentiment = self.agent._basic_sentiment_analysis(texts)

        # Should be negative sentiment
        self.assertLess(sentiment, -0.3)

    def test_basic_sentiment_analysis_neutral(self):
        """Test basic sentiment analysis with neutral text."""
        texts = [
            "Bitcoin price is at $50,000",
            "Cryptocurrency trading volume today",
            "What is Ethereum?"
        ]

        sentiment = self.agent._basic_sentiment_analysis(texts)

        # Should be near neutral
        self.assertAlmostEqual(sentiment, 0.0, delta=0.2)

    def test_volume_ratio_calculation(self):
        """Test volume ratio calculation against 24h average."""
        # Add some historical volume
        self.agent._volume_history['btc'] = [50, 60, 55, 50, 65]

        # Current volume higher than average
        ratio = self.agent._calculate_volume_ratio('btc', 120)

        # Should be ~2x the average (56), allowing for floating point precision
        self.assertGreaterEqual(ratio, 1.75)
        self.assertLess(ratio, 2.5)

    def test_volume_ratio_no_history(self):
        """Test volume ratio with no historical data."""
        # First data point
        ratio = self.agent._calculate_volume_ratio('new_crypto', 100)

        # Should return 1.0 (no baseline)
        self.assertEqual(ratio, 1.0)

    def test_cache_functionality(self):
        """Test that social metrics are cached properly."""
        # Mock the fetch methods
        with patch.object(self.agent, '_fetch_twitter_data', return_value={'mentions': 50, 'sentiment': 0.5, 'volume_ratio': 1.0}):
            with patch.object(self.agent, '_fetch_reddit_data', return_value={'mentions': 20, 'sentiment': 0.4, 'upvote_ratio': 0.7}):
                with patch.object(self.agent, '_fetch_trends_data', return_value={'trends_score': 60, 'trends_momentum': 10}):
                    # First call - should fetch
                    metrics1 = self.agent._get_social_metrics('btc')

                    # Second call - should use cache
                    metrics2 = self.agent._get_social_metrics('btc')

                    # Should be same object (from cache)
                    self.assertEqual(metrics1, metrics2)

    def test_error_handling(self):
        """Test error handling in analyze method."""
        # Force an error by making _get_social_metrics raise exception
        with patch.object(self.agent, '_get_social_metrics', side_effect=Exception("API error")):
            vote = self.agent.analyze('btc', 1234567890, {})

        # Should return neutral vote with error message
        self.assertEqual(vote.direction, "Neutral")
        self.assertEqual(vote.confidence, 0.0)
        self.assertEqual(vote.quality, 0.0)
        self.assertIn("Error", vote.reasoning)


if __name__ == '__main__':
    unittest.main()
