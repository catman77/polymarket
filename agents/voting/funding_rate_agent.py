#!/usr/bin/env python3
"""
Funding Rate Expert Agent

Analyzes perpetual futures funding rates to generate trading signals based on:
- Funding rate (positive = long bias/bullish, negative = short bias/bearish)
- Open interest (rising = more positions, falling = unwinding)
- Funding rate trend (accelerating vs decelerating)
- Extreme funding (liquidation cascade risk)

This agent detects derivatives market sentiment that indicates:
- Overleveraged positions (extreme funding = reversal risk)
- Institutional positioning (open interest changes)
- Market bias (funding rate direction)
"""

import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import time

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_agent import BaseAgent, Vote

# Try importing requests (required for API calls)
try:
    import requests
except ImportError:
    requests = None

log = logging.getLogger(__name__)


# Funding rate analysis thresholds
FUNDING_NEUTRAL_THRESHOLD = 0.01    # ±0.01% = neutral funding
FUNDING_MODERATE_THRESHOLD = 0.05   # ±0.05% = moderate bias
FUNDING_EXTREME_THRESHOLD = 0.10    # ±0.10% = extreme bias (reversal risk)

# Open interest thresholds (in percentage, e.g., 5.0 = 5%)
OI_CHANGE_THRESHOLD = 5.0           # 5% change = significant
OI_SURGE_THRESHOLD = 15.0           # 15% change = surge

# Binance Futures API endpoints (no auth required for public data)
BINANCE_FUTURES_BASE = "https://fapi.binance.com"
FUNDING_RATE_ENDPOINT = "/fapi/v1/fundingRate"
OPEN_INTEREST_ENDPOINT = "/fapi/v1/openInterest"
TICKER_ENDPOINT = "/fapi/v1/ticker/24hr"

# Crypto symbol mapping (Polymarket -> Binance Futures)
SYMBOL_MAP = {
    'btc': 'BTCUSDT',
    'eth': 'ETHUSDT',
    'sol': 'SOLUSDT',
    'xrp': 'XRPUSDT'
}


@dataclass
class FundingMetrics:
    """Computed metrics from funding rate analysis."""

    # Funding rate
    current_funding_rate: float         # Current 8-hour funding rate (%)
    funding_bias: str                   # "long" (positive) or "short" (negative)
    funding_strength: float             # Magnitude of bias (0-1)

    # Open interest
    open_interest: float                # Current open interest (USD)
    oi_change_24h: Optional[float]      # 24h change in OI (%)

    # Derived signals
    signal_direction: str               # "Up", "Down", or "Neutral"
    signal_confidence: float            # 0.0 to 1.0
    signal_quality: float               # 0.0 to 1.0
    reasoning: str                      # Human-readable explanation


class FundingRateAgent(BaseAgent):
    """
    Expert agent that analyzes perpetual futures funding rates.

    Key Insights:
    - Positive funding = longs pay shorts = too many longs = potential reversal DOWN
    - Negative funding = shorts pay longs = too many shorts = potential reversal UP
    - Extreme funding (>0.10%) = overleveraged = high reversal probability
    - Rising OI + extreme funding = cascade risk
    """

    def __init__(self, name: str = "FundingRateAgent", weight: float = 1.0):
        """Initialize the Funding Rate Agent."""
        super().__init__(name, weight)

        if requests is None:
            self.log.error("requests library not available - agent will return neutral votes")

        # Cache for API responses (60 second TTL)
        self._cache: Dict[str, Tuple[float, Dict]] = {}
        self._cache_ttl = 60.0  # seconds

    def analyze(self, crypto: str, epoch: int, data: dict) -> Vote:
        """
        Analyze funding rates and return a vote.

        Strategy:
        - Contrarian approach: extreme positive funding → DOWN, extreme negative funding → UP
        - Moderate funding: align with bias (positive → UP, negative → DOWN)
        - Track open interest changes for confirmation

        Args:
            crypto: Crypto symbol (btc, eth, sol, xrp)
            epoch: Current epoch timestamp
            data: Shared data context

        Returns:
            Vote: Agent's prediction with confidence and reasoning
        """
        if requests is None:
            return self._neutral_vote("requests library not available")

        # Get Binance symbol
        symbol = SYMBOL_MAP.get(crypto.lower())
        if not symbol:
            return self._neutral_vote(f"Unsupported crypto: {crypto}")

        try:
            # Fetch funding rate metrics
            metrics = self._fetch_funding_metrics(symbol)

            if metrics is None:
                return self._neutral_vote(f"Failed to fetch funding data for {symbol}")

            # Generate vote based on metrics
            vote = Vote(
                direction=metrics.signal_direction,
                confidence=metrics.signal_confidence,
                quality=metrics.signal_quality,
                agent_name=self.name,
                reasoning=metrics.reasoning,
                details={
                    'funding_rate': metrics.current_funding_rate,
                    'funding_bias': metrics.funding_bias,
                    'funding_strength': metrics.funding_strength,
                    'open_interest': metrics.open_interest,
                    'oi_change_24h': metrics.oi_change_24h,
                    'symbol': symbol
                }
            )

            self.log.info(
                f"{self.name} | {crypto.upper()} | {vote.direction} @ {vote.confidence:.2f} "
                f"| Funding: {metrics.current_funding_rate:+.4f}% | {metrics.reasoning}"
            )

            return vote

        except Exception as e:
            self.log.error(f"Error analyzing funding rates for {crypto}: {e}", exc_info=True)
            return self._neutral_vote(f"Analysis error: {e}")

    def _fetch_funding_metrics(self, symbol: str) -> Optional[FundingMetrics]:
        """
        Fetch and compute funding rate metrics from Binance Futures API.

        Args:
            symbol: Binance futures symbol (e.g., BTCUSDT)

        Returns:
            FundingMetrics object or None if fetch fails
        """
        # Check cache
        now = time.time()
        if symbol in self._cache:
            cached_time, cached_metrics = self._cache[symbol]
            if now - cached_time < self._cache_ttl:
                self.log.debug(f"Using cached metrics for {symbol}")
                return cached_metrics

        try:
            # Fetch current funding rate
            funding_resp = requests.get(
                f"{BINANCE_FUTURES_BASE}{FUNDING_RATE_ENDPOINT}",
                params={'symbol': symbol, 'limit': 1},
                timeout=5
            )
            funding_resp.raise_for_status()
            funding_data = funding_resp.json()

            if not funding_data:
                self.log.warning(f"No funding data returned for {symbol}")
                return None

            # Funding rate is returned as decimal (e.g., 0.0001 = 0.01%)
            current_funding = float(funding_data[0]['fundingRate']) * 100  # Convert to percentage

            # Fetch open interest
            oi_resp = requests.get(
                f"{BINANCE_FUTURES_BASE}{OPEN_INTEREST_ENDPOINT}",
                params={'symbol': symbol},
                timeout=5
            )
            oi_resp.raise_for_status()
            oi_data = oi_resp.json()

            open_interest = float(oi_data.get('openInterest', 0))

            # Fetch 24h ticker for OI change (Binance doesn't provide historical OI easily)
            # We'll use volume as a proxy for OI change
            ticker_resp = requests.get(
                f"{BINANCE_FUTURES_BASE}{TICKER_ENDPOINT}",
                params={'symbol': symbol},
                timeout=5
            )
            ticker_resp.raise_for_status()
            ticker_data = ticker_resp.json()

            # OI change approximation: compare volume to OI ratio
            # High volume relative to OI = likely OI change
            volume_24h = float(ticker_data.get('volume', 0))
            oi_change_24h = None  # We don't have historical OI, set to None

            # Compute metrics
            metrics = self._compute_metrics(
                current_funding=current_funding,
                open_interest=open_interest,
                oi_change_24h=oi_change_24h
            )

            # Cache result
            self._cache[symbol] = (now, metrics)

            return metrics

        except Exception as e:
            # Catch all exceptions (including mocked requests in tests)
            self.log.error(f"Failed to fetch/parse API response for {symbol}: {e}")
            return None

    def _compute_metrics(
        self,
        current_funding: float,
        open_interest: float,
        oi_change_24h: Optional[float]
    ) -> FundingMetrics:
        """
        Compute trading signals from funding rate data.

        Strategy:
        1. Extreme funding (>0.10% or <-0.10%) → CONTRARIAN (reversal expected)
        2. Moderate funding (0.05-0.10%) → ALIGNED with bias (trend continuation)
        3. Neutral funding (<0.05%) → NEUTRAL

        Quality factors:
        - Extreme funding = higher quality (clearer signal)
        - Rising OI = higher quality (more conviction)

        Args:
            current_funding: Current 8-hour funding rate (%)
            open_interest: Current open interest (USD)
            oi_change_24h: 24-hour change in OI (%) or None

        Returns:
            FundingMetrics with computed signals
        """
        # Determine funding bias
        funding_bias = "long" if current_funding >= 0 else "short"
        funding_magnitude = abs(current_funding)

        # Normalize funding strength (0-1 scale)
        # 0.10% or higher = 1.0 (extreme)
        funding_strength = min(funding_magnitude / FUNDING_EXTREME_THRESHOLD, 1.0)

        # Determine signal direction
        if funding_magnitude >= FUNDING_EXTREME_THRESHOLD:
            # EXTREME funding → CONTRARIAN (reversal trade)
            # Positive funding (longs overleveraged) → expect DOWN
            # Negative funding (shorts overleveraged) → expect UP
            signal_direction = "Down" if current_funding > 0 else "Up"
            base_confidence = 0.70  # High confidence in reversal
            reasoning = (
                f"EXTREME funding ({current_funding:+.4f}%) - overleveraged {funding_bias}s "
                f"→ reversal {signal_direction} expected"
            )

        elif funding_magnitude >= FUNDING_MODERATE_THRESHOLD:
            # MODERATE funding → ALIGNED with bias
            # Positive funding (bullish bias) → expect UP continuation
            # Negative funding (bearish bias) → expect DOWN continuation
            signal_direction = "Up" if current_funding > 0 else "Down"
            base_confidence = 0.50  # Moderate confidence in continuation
            reasoning = (
                f"MODERATE funding ({current_funding:+.4f}%) - {funding_bias} bias "
                f"→ {signal_direction} continuation likely"
            )

        else:
            # NEUTRAL funding → NO CLEAR SIGNAL
            signal_direction = "Neutral"
            base_confidence = 0.30
            reasoning = f"NEUTRAL funding ({current_funding:+.4f}%) - no clear bias"

        # Adjust confidence based on OI change (if available)
        confidence = base_confidence
        if oi_change_24h is not None:
            if abs(oi_change_24h) >= OI_SURGE_THRESHOLD:
                # Large OI change = stronger signal
                confidence = min(confidence * 1.2, 1.0)
                reasoning += f" + OI surge ({oi_change_24h:+.1f}%)"
            elif abs(oi_change_24h) >= OI_CHANGE_THRESHOLD:
                # Moderate OI change = slight boost
                confidence = min(confidence * 1.1, 1.0)
                reasoning += f" + OI change ({oi_change_24h:+.1f}%)"

        # Quality score based on signal clarity
        # Extreme/moderate funding = high quality, neutral = low quality
        if funding_magnitude >= FUNDING_EXTREME_THRESHOLD:
            quality = 0.90  # Very clear signal
        elif funding_magnitude >= FUNDING_MODERATE_THRESHOLD:
            quality = 0.70  # Clear signal
        elif funding_magnitude >= FUNDING_NEUTRAL_THRESHOLD:
            quality = 0.50  # Weak signal
        else:
            quality = 0.35  # Very weak signal

        # Boost quality if OI is rising (more conviction)
        if oi_change_24h is not None and oi_change_24h > OI_CHANGE_THRESHOLD:
            quality = min(quality * 1.1, 1.0)

        return FundingMetrics(
            current_funding_rate=current_funding,
            funding_bias=funding_bias,
            funding_strength=funding_strength,
            open_interest=open_interest,
            oi_change_24h=oi_change_24h,
            signal_direction=signal_direction,
            signal_confidence=confidence,
            signal_quality=quality,
            reasoning=reasoning
        )

    def _neutral_vote(self, reason: str) -> Vote:
        """Return a neutral vote with low confidence."""
        return Vote(
            direction="Neutral",
            confidence=0.30,
            quality=0.35,
            agent_name=self.name,
            reasoning=f"Neutral: {reason}",
            details={'error': reason}
        )


# Standalone test
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )

    agent = FundingRateAgent()

    # Test with BTC
    print("\n=== Testing FundingRateAgent with BTC ===")
    vote = agent.analyze('btc', int(time.time()), {})
    print(f"\nVote: {vote.direction} @ {vote.confidence:.2f} (quality: {vote.quality:.2f})")
    print(f"Reasoning: {vote.reasoning}")
    print(f"Details: {vote.details}")

    # Test with ETH
    print("\n=== Testing FundingRateAgent with ETH ===")
    vote = agent.analyze('eth', int(time.time()), {})
    print(f"\nVote: {vote.direction} @ {vote.confidence:.2f} (quality: {vote.quality:.2f})")
    print(f"Reasoning: {vote.reasoning}")
    print(f"Details: {vote.details}")

    # Test with invalid crypto
    print("\n=== Testing FundingRateAgent with invalid crypto ===")
    vote = agent.analyze('INVALID', int(time.time()), {})
    print(f"\nVote: {vote.direction} @ {vote.confidence:.2f} (quality: {vote.quality:.2f})")
    print(f"Reasoning: {vote.reasoning}")
