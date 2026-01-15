#!/usr/bin/env python3
"""
Social Sentiment Expert Agent

Analyzes crowd psychology from social media to generate trading signals based on:
- Twitter mention volume and sentiment (spikes indicate attention)
- Reddit r/cryptocurrency sentiment (bullish/bearish ratio)
- Google Trends search momentum (increasing interest)
- Sentiment score via NLP (positive/negative tone)

This agent detects crowd psychology patterns that indicate:
- FOMO peaks (excessive bullishness = contrarian DOWN signal)
- Fear troughs (excessive bearishness = contrarian UP signal)
- Momentum shifts (rising interest = continuation signal)
- Sentiment divergence (social vs price action)
"""

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import time
import re

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_agent import BaseAgent, Vote

# Try importing optional dependencies
try:
    import requests
except ImportError:
    requests = None

try:
    # Reddit API client
    import praw
except ImportError:
    praw = None

try:
    # Google Trends client
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

try:
    # Sentiment analysis model (finbert or basic)
    from transformers import pipeline
    SENTIMENT_PIPELINE = None  # Initialize on first use to save memory
except ImportError:
    pipeline = None
    SENTIMENT_PIPELINE = None

log = logging.getLogger(__name__)


# Sentiment thresholds
SENTIMENT_NEUTRAL_THRESHOLD = 0.15   # ±15% = neutral sentiment
SENTIMENT_MODERATE_THRESHOLD = 0.35  # ±35% = moderate bias
SENTIMENT_EXTREME_THRESHOLD = 0.60   # ±60% = extreme bias (contrarian signal)

# Volume thresholds (for Twitter/Reddit activity)
VOLUME_LOW_THRESHOLD = 0.3           # 30% of average volume
VOLUME_HIGH_THRESHOLD = 2.0          # 200% of average volume (spike)
VOLUME_EXTREME_THRESHOLD = 4.0       # 400% of average volume (extreme spike)

# Trends momentum thresholds
TRENDS_RISING_THRESHOLD = 20         # +20 points = rising interest
TRENDS_SURGING_THRESHOLD = 50        # +50 points = surging interest

# Crypto keywords for social listening
CRYPTO_KEYWORDS = {
    'btc': ['bitcoin', 'btc', '$btc'],
    'eth': ['ethereum', 'eth', '$eth'],
    'sol': ['solana', 'sol', '$sol'],
    'xrp': ['ripple', 'xrp', '$xrp']
}

# Cache TTL (social data updates slowly, 5-minute cache is appropriate)
CACHE_TTL_SECONDS = 300


@dataclass
class SocialMetrics:
    """Computed metrics from social sentiment analysis."""

    # Twitter metrics
    twitter_mentions: int              # Number of mentions in last 15 min
    twitter_sentiment: float           # Average sentiment (-1 to +1)
    twitter_volume_ratio: float        # Volume vs 24h average

    # Reddit metrics
    reddit_mentions: int               # Number of mentions in r/cryptocurrency
    reddit_sentiment: float            # Bullish/bearish ratio
    reddit_upvote_ratio: float         # Average upvote ratio

    # Google Trends
    trends_score: int                  # Current trends score (0-100)
    trends_momentum: int               # Change from 1 hour ago

    # Derived signals
    signal_direction: str              # "Up", "Down", or "Neutral"
    signal_confidence: float           # 0.0 to 1.0
    signal_quality: float              # 0.0 to 1.0
    reasoning: str                     # Human-readable explanation


class SocialSentimentAgent(BaseAgent):
    """
    Expert agent that analyzes social media sentiment and crowd psychology.

    Key Insights:
    - Extreme bullishness (>60% positive) = FOMO peak = contrarian DOWN signal
    - Extreme bearishness (>60% negative) = fear trough = contrarian UP signal
    - Volume spikes (>4x average) + extreme sentiment = contrarian opportunity
    - Rising trends + moderate sentiment = momentum continuation signal
    - Sentiment-price divergence = reversal indicator
    """

    def __init__(self, name: str = "SocialSentimentAgent", weight: float = 1.0,
                 twitter_api_key: Optional[str] = None,
                 reddit_client_id: Optional[str] = None,
                 reddit_client_secret: Optional[str] = None):
        """
        Initialize the Social Sentiment Agent.

        Args:
            name: Agent name
            weight: Base voting weight
            twitter_api_key: Twitter API v2 bearer token (optional)
            reddit_client_id: Reddit app client ID (optional)
            reddit_client_secret: Reddit app secret (optional)
        """
        super().__init__(name, weight)

        # API credentials
        self.twitter_api_key = twitter_api_key or os.getenv('TWITTER_API_KEY')
        self.reddit_client_id = reddit_client_id or os.getenv('REDDIT_CLIENT_ID')
        self.reddit_client_secret = reddit_client_secret or os.getenv('REDDIT_CLIENT_SECRET')

        # Check dependencies
        if requests is None:
            self.log.warning("requests library not available - agent will return low-quality votes")

        if praw is None:
            self.log.warning("praw library not available - Reddit analysis disabled")
        elif not self.reddit_client_id or not self.reddit_client_secret:
            self.log.warning("Reddit API credentials not configured - Reddit analysis disabled")

        if TrendReq is None:
            self.log.warning("pytrends library not available - Google Trends analysis disabled")

        if pipeline is None:
            self.log.warning("transformers library not available - sentiment analysis will use basic method")

        # Initialize Reddit client if credentials available
        self.reddit_client = None
        if praw and self.reddit_client_id and self.reddit_client_secret:
            try:
                self.reddit_client = praw.Reddit(
                    client_id=self.reddit_client_id,
                    client_secret=self.reddit_client_secret,
                    user_agent='polymarket-autotrader/1.0'
                )
                self.log.info("Reddit client initialized successfully")
            except Exception as e:
                self.log.error(f"Failed to initialize Reddit client: {e}")

        # Initialize Google Trends client
        self.trends_client = None
        if TrendReq:
            try:
                self.trends_client = TrendReq(hl='en-US', tz=0)
                self.log.info("Google Trends client initialized successfully")
            except Exception as e:
                self.log.error(f"Failed to initialize Google Trends client: {e}")

        # Cache for API responses (5-minute TTL)
        self._cache: Dict[str, Tuple[float, SocialMetrics]] = {}

        # Historical volume tracking (for volume ratio calculation)
        self._volume_history: Dict[str, List[int]] = {}

    def analyze(self, crypto: str, epoch: int, data: dict) -> Vote:
        """
        Analyze social sentiment and return a vote.

        Args:
            crypto: Crypto symbol (btc, eth, sol, xrp)
            epoch: Current epoch timestamp
            data: Shared data context (not heavily used by this agent)

        Returns:
            Vote: Agent's prediction based on social sentiment
        """
        try:
            # Get social metrics (cached)
            metrics = self._get_social_metrics(crypto)

            # Convert to vote
            return Vote(
                direction=metrics.signal_direction,
                confidence=metrics.signal_confidence,
                quality=metrics.signal_quality,
                agent_name=self.name,
                reasoning=metrics.reasoning,
                details={
                    'twitter_mentions': metrics.twitter_mentions,
                    'twitter_sentiment': metrics.twitter_sentiment,
                    'twitter_volume_ratio': metrics.twitter_volume_ratio,
                    'reddit_mentions': metrics.reddit_mentions,
                    'reddit_sentiment': metrics.reddit_sentiment,
                    'reddit_upvote_ratio': metrics.reddit_upvote_ratio,
                    'trends_score': metrics.trends_score,
                    'trends_momentum': metrics.trends_momentum
                }
            )

        except Exception as e:
            self.log.error(f"Error analyzing social sentiment for {crypto}: {e}")
            return Vote(
                direction="Neutral",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning=f"Error: {str(e)}"
            )

    def _get_social_metrics(self, crypto: str) -> SocialMetrics:
        """
        Fetch and analyze social sentiment data.

        Uses caching to reduce API load (5-minute TTL).

        Args:
            crypto: Crypto symbol

        Returns:
            SocialMetrics with all computed signals
        """
        # Check cache
        cache_key = f"{crypto}:social"
        if cache_key in self._cache:
            cached_time, cached_metrics = self._cache[cache_key]
            if time.time() - cached_time < CACHE_TTL_SECONDS:
                return cached_metrics

        # Fetch fresh data
        twitter_data = self._fetch_twitter_data(crypto)
        reddit_data = self._fetch_reddit_data(crypto)
        trends_data = self._fetch_trends_data(crypto)

        # Calculate metrics
        metrics = self._calculate_social_metrics(
            crypto,
            twitter_data,
            reddit_data,
            trends_data
        )

        # Cache result
        self._cache[cache_key] = (time.time(), metrics)

        return metrics

    def _fetch_twitter_data(self, crypto: str) -> Dict:
        """
        Fetch Twitter mentions and sentiment.

        Uses Twitter API v2 to search recent tweets.

        Args:
            crypto: Crypto symbol

        Returns:
            Dict with mentions, sentiment, volume_ratio
        """
        if not self.twitter_api_key or not requests:
            return {'mentions': 0, 'sentiment': 0.0, 'volume_ratio': 0.0}

        try:
            # Search for crypto keywords in last 15 minutes
            keywords = CRYPTO_KEYWORDS.get(crypto, [crypto])
            query = ' OR '.join(keywords)

            # Twitter API v2 recent search endpoint
            url = 'https://api.twitter.com/2/tweets/search/recent'
            headers = {'Authorization': f'Bearer {self.twitter_api_key}'}
            params = {
                'query': query,
                'max_results': 100,
                'tweet.fields': 'created_at,public_metrics'
            }

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            tweets = data.get('data', [])
            mentions = len(tweets)

            # Calculate sentiment
            sentiment_score = self._analyze_sentiment([t.get('text', '') for t in tweets])

            # Calculate volume ratio (vs 24h average)
            volume_ratio = self._calculate_volume_ratio(crypto, mentions)

            return {
                'mentions': mentions,
                'sentiment': sentiment_score,
                'volume_ratio': volume_ratio
            }

        except Exception as e:
            self.log.debug(f"Twitter API error for {crypto}: {e}")
            return {'mentions': 0, 'sentiment': 0.0, 'volume_ratio': 0.0}

    def _fetch_reddit_data(self, crypto: str) -> Dict:
        """
        Fetch Reddit mentions and sentiment from r/cryptocurrency.

        Args:
            crypto: Crypto symbol

        Returns:
            Dict with mentions, sentiment, upvote_ratio
        """
        if not self.reddit_client:
            return {'mentions': 0, 'sentiment': 0.0, 'upvote_ratio': 0.0}

        try:
            # Search r/cryptocurrency for crypto mentions
            subreddit = self.reddit_client.subreddit('cryptocurrency')
            keywords = CRYPTO_KEYWORDS.get(crypto, [crypto])

            posts = []
            for keyword in keywords:
                # Get recent posts mentioning the crypto
                search_results = subreddit.search(
                    keyword,
                    time_filter='hour',
                    sort='new',
                    limit=50
                )
                posts.extend(list(search_results))

            mentions = len(posts)

            # Calculate sentiment from post titles and upvote ratios
            titles = [p.title for p in posts]
            sentiment_score = self._analyze_sentiment(titles)

            # Average upvote ratio (higher = more bullish community response)
            upvote_ratios = [p.upvote_ratio for p in posts if hasattr(p, 'upvote_ratio')]
            avg_upvote_ratio = sum(upvote_ratios) / len(upvote_ratios) if upvote_ratios else 0.5

            return {
                'mentions': mentions,
                'sentiment': sentiment_score,
                'upvote_ratio': avg_upvote_ratio
            }

        except Exception as e:
            self.log.debug(f"Reddit API error for {crypto}: {e}")
            return {'mentions': 0, 'sentiment': 0.0, 'upvote_ratio': 0.0}

    def _fetch_trends_data(self, crypto: str) -> Dict:
        """
        Fetch Google Trends search momentum.

        Args:
            crypto: Crypto symbol

        Returns:
            Dict with trends_score, trends_momentum
        """
        if not self.trends_client:
            return {'trends_score': 0, 'trends_momentum': 0}

        try:
            # Get search interest for last 4 hours
            keywords = CRYPTO_KEYWORDS.get(crypto, [crypto])
            kw_list = [keywords[0]]  # Use primary keyword

            self.trends_client.build_payload(
                kw_list,
                timeframe='now 4-H',
                geo='US'
            )

            interest_over_time = self.trends_client.interest_over_time()

            if interest_over_time.empty:
                return {'trends_score': 0, 'trends_momentum': 0}

            # Current score (most recent data point)
            current_score = int(interest_over_time[kw_list[0]].iloc[-1])

            # Momentum (change from 1 hour ago)
            if len(interest_over_time) >= 2:
                prev_score = int(interest_over_time[kw_list[0]].iloc[-2])
                momentum = current_score - prev_score
            else:
                momentum = 0

            return {
                'trends_score': current_score,
                'trends_momentum': momentum
            }

        except Exception as e:
            self.log.debug(f"Google Trends error for {crypto}: {e}")
            return {'trends_score': 0, 'trends_momentum': 0}

    def _analyze_sentiment(self, texts: List[str]) -> float:
        """
        Analyze sentiment of text list using NLP.

        Returns sentiment score from -1.0 (bearish) to +1.0 (bullish).

        Args:
            texts: List of text strings to analyze

        Returns:
            float: Average sentiment score (-1 to +1)
        """
        if not texts:
            return 0.0

        # Try using transformers pipeline if available
        if pipeline:
            try:
                global SENTIMENT_PIPELINE
                if SENTIMENT_PIPELINE is None:
                    # Initialize sentiment pipeline (use finbert for financial sentiment)
                    SENTIMENT_PIPELINE = pipeline(
                        "sentiment-analysis",
                        model="ProsusAI/finbert",
                        device=-1  # CPU only (GPU not available on VPS)
                    )

                # Analyze each text
                scores = []
                for text in texts[:20]:  # Limit to 20 texts to avoid timeout
                    result = SENTIMENT_PIPELINE(text[:512])[0]  # Max 512 chars
                    label = result['label'].lower()
                    confidence = result['score']

                    # Convert to -1 to +1 scale
                    if 'positive' in label or 'bullish' in label:
                        scores.append(confidence)
                    elif 'negative' in label or 'bearish' in label:
                        scores.append(-confidence)
                    else:
                        scores.append(0.0)

                return sum(scores) / len(scores) if scores else 0.0

            except Exception as e:
                self.log.debug(f"Sentiment pipeline error: {e}")
                # Fall through to basic method

        # Basic sentiment analysis (keyword-based)
        return self._basic_sentiment_analysis(texts)

    def _basic_sentiment_analysis(self, texts: List[str]) -> float:
        """
        Basic sentiment analysis using keyword matching.

        Args:
            texts: List of text strings

        Returns:
            float: Sentiment score (-1 to +1)
        """
        # Bullish keywords
        bullish = [
            'moon', 'bullish', 'up', 'pump', 'rally', 'surge', 'breakout',
            'buy', 'long', 'ath', 'gains', 'profit', 'rocket', '🚀', '📈'
        ]

        # Bearish keywords
        bearish = [
            'crash', 'bearish', 'down', 'dump', 'sell', 'short', 'dip',
            'fall', 'drop', 'loss', 'rekt', 'bear', '📉', '💩'
        ]

        bullish_count = 0
        bearish_count = 0

        for text in texts:
            text_lower = text.lower()

            # Count keyword occurrences
            for word in bullish:
                bullish_count += text_lower.count(word)

            for word in bearish:
                bearish_count += text_lower.count(word)

        # Calculate sentiment ratio
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        sentiment = (bullish_count - bearish_count) / total
        return max(-1.0, min(1.0, sentiment))  # Clamp to [-1, 1]

    def _calculate_volume_ratio(self, crypto: str, current_volume: int) -> float:
        """
        Calculate volume ratio (current vs 24h average).

        Args:
            crypto: Crypto symbol
            current_volume: Current mention count

        Returns:
            float: Volume ratio (1.0 = average, 2.0 = 2x average)
        """
        if crypto not in self._volume_history:
            self._volume_history[crypto] = []

        # Add current volume to history
        self._volume_history[crypto].append(current_volume)

        # Keep last 96 data points (24 hours at 15-min intervals)
        self._volume_history[crypto] = self._volume_history[crypto][-96:]

        # Calculate 24h average
        avg_volume = sum(self._volume_history[crypto]) / len(self._volume_history[crypto])

        if avg_volume == 0:
            return 1.0

        return current_volume / avg_volume

    def _calculate_social_metrics(
        self,
        crypto: str,
        twitter_data: Dict,
        reddit_data: Dict,
        trends_data: Dict
    ) -> SocialMetrics:
        """
        Calculate social sentiment metrics and generate trading signal.

        Args:
            crypto: Crypto symbol
            twitter_data: Twitter metrics
            reddit_data: Reddit metrics
            trends_data: Google Trends metrics

        Returns:
            SocialMetrics with direction, confidence, quality, reasoning
        """
        # Extract metrics
        twitter_mentions = twitter_data['mentions']
        twitter_sentiment = twitter_data['sentiment']
        twitter_volume_ratio = twitter_data['volume_ratio']

        reddit_mentions = reddit_data['mentions']
        reddit_sentiment = reddit_data['sentiment']
        reddit_upvote_ratio = reddit_data['upvote_ratio']

        trends_score = trends_data['trends_score']
        trends_momentum = trends_data['trends_momentum']

        # Aggregate sentiment (weighted average)
        # Twitter = 40%, Reddit = 40%, Trends = 20%
        total_weight = 0.0
        weighted_sentiment = 0.0

        if twitter_mentions > 0:
            weighted_sentiment += twitter_sentiment * 0.4
            total_weight += 0.4

        if reddit_mentions > 0:
            weighted_sentiment += reddit_sentiment * 0.4
            total_weight += 0.4

        if trends_score > 0:
            # Normalize trends momentum to -1 to +1
            trends_sentiment = max(-1.0, min(1.0, trends_momentum / 50.0))
            weighted_sentiment += trends_sentiment * 0.2
            total_weight += 0.2

        if total_weight > 0:
            avg_sentiment = weighted_sentiment / total_weight
        else:
            avg_sentiment = 0.0

        # Determine signal direction and confidence
        direction = "Neutral"
        confidence = 0.0
        reasoning_parts = []

        # Contrarian signals (extreme sentiment)
        if avg_sentiment >= SENTIMENT_EXTREME_THRESHOLD:
            # Extreme bullishness = contrarian DOWN
            direction = "Down"
            confidence = 0.70
            reasoning_parts.append(f"Extreme bullish sentiment ({avg_sentiment:.2f}) = FOMO peak")

        elif avg_sentiment <= -SENTIMENT_EXTREME_THRESHOLD:
            # Extreme bearishness = contrarian UP
            direction = "Up"
            confidence = 0.70
            reasoning_parts.append(f"Extreme bearish sentiment ({avg_sentiment:.2f}) = fear trough")

        # Momentum signals (moderate sentiment + volume)
        elif avg_sentiment >= SENTIMENT_MODERATE_THRESHOLD:
            # Moderate bullishness = continuation UP
            direction = "Up"
            confidence = 0.50
            reasoning_parts.append(f"Moderate bullish sentiment ({avg_sentiment:.2f})")

        elif avg_sentiment <= -SENTIMENT_MODERATE_THRESHOLD:
            # Moderate bearishness = continuation DOWN
            direction = "Down"
            confidence = 0.50
            reasoning_parts.append(f"Moderate bearish sentiment ({avg_sentiment:.2f})")

        else:
            # Neutral sentiment
            direction = "Neutral"
            confidence = 0.0
            reasoning_parts.append(f"Neutral sentiment ({avg_sentiment:.2f})")

        # Boost confidence for volume spikes
        if twitter_volume_ratio >= VOLUME_EXTREME_THRESHOLD:
            confidence = min(1.0, confidence + 0.15)
            reasoning_parts.append(f"Twitter volume spike ({twitter_volume_ratio:.1f}x)")

        elif twitter_volume_ratio >= VOLUME_HIGH_THRESHOLD:
            confidence = min(1.0, confidence + 0.10)
            reasoning_parts.append(f"High Twitter volume ({twitter_volume_ratio:.1f}x)")

        # Boost confidence for trends momentum
        if trends_momentum >= TRENDS_SURGING_THRESHOLD:
            confidence = min(1.0, confidence + 0.15)
            reasoning_parts.append(f"Google Trends surging (+{trends_momentum})")

        elif trends_momentum >= TRENDS_RISING_THRESHOLD:
            confidence = min(1.0, confidence + 0.10)
            reasoning_parts.append(f"Google Trends rising (+{trends_momentum})")

        # Calculate quality score
        quality = self._calculate_quality_score(
            twitter_mentions,
            reddit_mentions,
            trends_score,
            twitter_volume_ratio
        )

        # Build reasoning
        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "No clear signal"

        return SocialMetrics(
            twitter_mentions=twitter_mentions,
            twitter_sentiment=twitter_sentiment,
            twitter_volume_ratio=twitter_volume_ratio,
            reddit_mentions=reddit_mentions,
            reddit_sentiment=reddit_sentiment,
            reddit_upvote_ratio=reddit_upvote_ratio,
            trends_score=trends_score,
            trends_momentum=trends_momentum,
            signal_direction=direction,
            signal_confidence=confidence,
            signal_quality=quality,
            reasoning=reasoning
        )

    def _calculate_quality_score(
        self,
        twitter_mentions: int,
        reddit_mentions: int,
        trends_score: int,
        volume_ratio: float
    ) -> float:
        """
        Calculate signal quality based on data availability and volume.

        Args:
            twitter_mentions: Number of Twitter mentions
            reddit_mentions: Number of Reddit mentions
            trends_score: Google Trends score
            volume_ratio: Twitter volume ratio

        Returns:
            float: Quality score (0.0 to 1.0)
        """
        quality = 0.0

        # Base quality from data sources available
        sources_available = 0

        if twitter_mentions > 0:
            sources_available += 1
            quality += 0.33

        if reddit_mentions > 0:
            sources_available += 1
            quality += 0.33

        if trends_score > 0:
            sources_available += 1
            quality += 0.34

        # Boost quality for sufficient sample size
        if twitter_mentions >= 20:
            quality += 0.10
        elif twitter_mentions >= 10:
            quality += 0.05

        if reddit_mentions >= 10:
            quality += 0.10
        elif reddit_mentions >= 5:
            quality += 0.05

        # Reduce quality for low volume
        if volume_ratio < VOLUME_LOW_THRESHOLD:
            quality *= 0.7  # 30% penalty for low activity

        # Cap quality at 1.0
        return min(1.0, quality)
