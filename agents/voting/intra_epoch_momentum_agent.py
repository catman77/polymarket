#!/usr/bin/env python3
"""
Intra-Epoch Momentum Agent

DATA-VALIDATED PATTERN (2,688 epochs, 7 days, 4 cryptos):
- If 4+ of first 5 minutes go UP → 79.7% chance epoch ends UP
- If 4+ of first 5 minutes go DOWN → 74.0% chance epoch ends DOWN
- If all first 3 minutes go UP → 78.0% chance epoch ends UP
- If all first 3 minutes go DOWN → 73.9% chance epoch ends DOWN

This agent checks early minute patterns within the current epoch
and predicts the final outcome based on momentum continuation.

TIMING: Only active from minute 3-10 of each epoch (need data but not too late)
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional

import requests

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from base_agent import BaseAgent, Vote

logger = logging.getLogger(__name__)

# Pattern accuracy from validation (2,688 epochs)
ACCURACY_4_OF_5_UP = 0.797      # 79.7% accuracy
ACCURACY_4_OF_5_DOWN = 0.740    # 74.0% accuracy
ACCURACY_ALL_3_UP = 0.780       # 78.0% accuracy
ACCURACY_ALL_3_DOWN = 0.739     # 73.9% accuracy

# Timing window (seconds into epoch)
MIN_EPOCH_TIME = 180   # Wait at least 3 minutes (need data)
MAX_EPOCH_TIME = 600   # Don't trade after 10 minutes (too late)


class IntraEpochMomentumAgent(BaseAgent):
    """
    Trades momentum continuation within 15-minute epochs.

    Checks 1-minute candle patterns in the first 3-5 minutes
    and predicts the final epoch outcome based on early momentum.

    Validated accuracy: 74-80% across 2,688 epochs.
    """

    def __init__(self, name: str = "IntraEpochMomentumAgent", weight: float = 1.0):
        """
        Initialize the IntraEpochMomentumAgent.

        Args:
            name: Agent identifier
            weight: Base voting weight
        """
        super().__init__(name=name, weight=weight)
        self._cache = {}  # Cache minute data to avoid repeated API calls
        self._cache_time = 0

    def _get_current_epoch_start(self) -> int:
        """Get the start timestamp of the current 15-minute epoch."""
        now = int(time.time())
        return now // 900 * 900

    def _get_time_in_epoch(self) -> int:
        """Get seconds elapsed in current epoch."""
        now = int(time.time())
        epoch_start = self._get_current_epoch_start()
        return now - epoch_start

    def _fetch_epoch_minutes(self, crypto: str, epoch_start: int) -> Optional[list]:
        """
        Fetch 1-minute candles for the current epoch so far.

        Returns list of "Up" or "Down" for each completed minute.
        """
        # Check cache (valid for 30 seconds)
        cache_key = f"{crypto}_{epoch_start}"
        if cache_key in self._cache and time.time() - self._cache_time < 30:
            return self._cache[cache_key]

        try:
            symbol = f"{crypto}USDT"
            url = "https://api.binance.com/api/v3/klines"

            params = {
                'symbol': symbol,
                'interval': '1m',
                'startTime': epoch_start * 1000,
                'limit': 15  # Max 15 minutes in epoch
            }

            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code != 200:
                logger.warning(f"[IntraEpochMomentum] Binance API error: {resp.status_code}")
                return None

            klines = resp.json()

            # Convert to Up/Down outcomes (skip current incomplete candle)
            minutes = []
            for k in klines[:-1]:  # Skip last (incomplete)
                open_p = float(k[1])
                close_p = float(k[4])
                minutes.append("Up" if close_p > open_p else "Down")

            # Cache result
            self._cache[cache_key] = minutes
            self._cache_time = time.time()

            return minutes

        except Exception as e:
            logger.warning(f"[IntraEpochMomentum] Error fetching data: {e}")
            return None

    def _analyze_pattern(self, minutes: list) -> Tuple[Optional[str], float, float, str]:
        """
        Analyze minute patterns and return prediction.

        Returns:
            (direction, confidence, quality, reasoning)
            direction: "Up", "Down", or None if no pattern
        """
        if not minutes or len(minutes) < 3:
            return (None, 0, 0, "Not enough minute data yet")

        # Count directions
        ups = sum(1 for m in minutes if m == "Up")
        downs = len(minutes) - ups

        # Pattern 1: All first 3 minutes same direction (strongest signal)
        first_3 = minutes[:3]
        if len(first_3) == 3:
            if all(m == "Up" for m in first_3):
                return ("Up", 0.78, ACCURACY_ALL_3_UP,
                       f"All first 3 minutes UP (78.0% historical accuracy)")
            elif all(m == "Down" for m in first_3):
                return ("Down", 0.74, ACCURACY_ALL_3_DOWN,
                       f"All first 3 minutes DOWN (73.9% historical accuracy)")

        # Pattern 2: 4+ of first 5 minutes same direction
        if len(minutes) >= 5:
            first_5 = minutes[:5]
            ups_5 = sum(1 for m in first_5 if m == "Up")
            downs_5 = 5 - ups_5

            if ups_5 >= 4:
                return ("Up", 0.80, ACCURACY_4_OF_5_UP,
                       f"{ups_5}/5 first minutes UP (79.7% historical accuracy)")
            elif downs_5 >= 4:
                return ("Down", 0.74, ACCURACY_4_OF_5_DOWN,
                       f"{downs_5}/5 first minutes DOWN (74.0% historical accuracy)")

        # Pattern 3: Weaker signal - 3 of first 5 same direction
        if len(minutes) >= 5:
            first_5 = minutes[:5]
            ups_5 = sum(1 for m in first_5 if m == "Up")

            if ups_5 >= 3:
                # Weaker confidence for 3/5
                return ("Up", 0.55, 0.65,
                       f"{ups_5}/5 first minutes UP (moderate signal)")
            elif ups_5 <= 2:
                downs_5 = 5 - ups_5
                return ("Down", 0.55, 0.65,
                       f"{downs_5}/5 first minutes DOWN (moderate signal)")

        return (None, 0, 0, "No clear momentum pattern")

    def analyze(self, crypto: str, epoch: int, data: dict) -> Vote:
        """
        Analyze intra-epoch momentum and return a vote.

        Args:
            crypto: Crypto symbol (BTC, ETH, SOL, XRP)
            epoch: Current epoch timestamp
            data: Market data context (contains time_in_epoch if available)

        Returns:
            Vote with direction, confidence, and quality based on early momentum
        """
        # Normalize crypto
        crypto_upper = crypto.upper() if crypto else ""

        if not crypto_upper:
            return Vote(
                direction="Skip",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning="No crypto specified",
                details={}
            )

        # Get time in epoch
        time_in_epoch = data.get('time_in_epoch', self._get_time_in_epoch())
        epoch_start = self._get_current_epoch_start()

        # Check timing window
        if time_in_epoch < MIN_EPOCH_TIME:
            return Vote(
                direction="Skip",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning=f"Too early in epoch ({time_in_epoch}s < {MIN_EPOCH_TIME}s minimum)",
                details={'time_in_epoch': time_in_epoch, 'min_time': MIN_EPOCH_TIME}
            )

        if time_in_epoch > MAX_EPOCH_TIME:
            return Vote(
                direction="Skip",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning=f"Too late in epoch ({time_in_epoch}s > {MAX_EPOCH_TIME}s maximum)",
                details={'time_in_epoch': time_in_epoch, 'max_time': MAX_EPOCH_TIME}
            )

        # Fetch minute data
        minutes = self._fetch_epoch_minutes(crypto_upper, epoch_start)

        if not minutes:
            return Vote(
                direction="Skip",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning="Could not fetch minute data from Binance",
                details={}
            )

        # Analyze pattern
        direction, confidence, quality, reasoning = self._analyze_pattern(minutes)

        details = {
            'crypto': crypto_upper,
            'epoch_start': epoch_start,
            'time_in_epoch': time_in_epoch,
            'minutes_data': minutes,
            'minutes_count': len(minutes),
            'ups': sum(1 for m in minutes if m == "Up"),
            'downs': sum(1 for m in minutes if m == "Down")
        }

        if direction:
            return Vote(
                direction=direction,
                confidence=confidence,
                quality=quality,
                agent_name=self.name,
                reasoning=reasoning,
                details=details
            )
        else:
            return Vote(
                direction="Skip",
                confidence=0.0,
                quality=0.0,
                agent_name=self.name,
                reasoning=reasoning,
                details=details
            )


# Standalone test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    agent = IntraEpochMomentumAgent()

    print("\n" + "="*70)
    print("  INTRA-EPOCH MOMENTUM AGENT TEST")
    print("="*70)

    # Get current epoch info
    epoch_start = agent._get_current_epoch_start()
    time_in_epoch = agent._get_time_in_epoch()

    print(f"\n  Current epoch started: {datetime.fromtimestamp(epoch_start, tz=timezone.utc)}")
    print(f"  Time in epoch: {time_in_epoch} seconds ({time_in_epoch // 60}m {time_in_epoch % 60}s)")
    print(f"  Trading window: {MIN_EPOCH_TIME}s - {MAX_EPOCH_TIME}s")

    for crypto in ['BTC', 'ETH', 'SOL', 'XRP']:
        print(f"\n  {'-'*60}")
        print(f"  Testing {crypto}...")

        # Fetch current minute data
        minutes = agent._fetch_epoch_minutes(crypto, epoch_start)

        if minutes:
            ups = sum(1 for m in minutes if m == "Up")
            downs = len(minutes) - ups
            print(f"    Minutes so far: {len(minutes)} ({ups} Up, {downs} Down)")
            print(f"    Pattern: {' '.join(minutes[:min(5, len(minutes))])}")

        # Get vote
        vote = agent.analyze(crypto, epoch_start, {'time_in_epoch': time_in_epoch})

        print(f"    Vote: {vote.direction}")
        print(f"    Confidence: {vote.confidence:.0%}")
        print(f"    Quality: {vote.quality:.0%}")
        print(f"    Reasoning: {vote.reasoning}")

    print("\n" + "="*70)
    print("  Test complete!")
    print("="*70 + "\n")
