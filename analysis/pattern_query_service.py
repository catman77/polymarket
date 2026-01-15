#!/usr/bin/env python3
"""
Pattern Query Service - Query historical time-dependent trading patterns.

Provides a lightweight, cacheable service for agents to access historical
pattern data for any crypto/hour/direction combination. Statistical analysis
of crypto directional bias by hour from historical epoch data.

Usage:
    from analysis.pattern_query_service import get_pattern_service

    service = get_pattern_service()
    signal = service.query_pattern('btc', 14, 'Up')
    print(f"BTC Up at 2pm: {signal.win_rate:.1%} win rate, {signal.edge:+.1%} edge")
"""

import sqlite3
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
from datetime import datetime
import math


@dataclass
class PatternSignal:
    """Historical pattern signal for crypto/hour/direction"""
    crypto: str
    hour: int
    direction: str
    win_rate: float         # 0.0-1.0 (e.g., 0.64 = 64% historical win rate)
    edge: float             # win_rate - 0.50 (edge over random)
    sample_size: int        # Number of historical epochs
    p_value: float          # Statistical significance (< 0.05 = significant)
    confidence: str         # 'high', 'moderate', 'low', 'insufficient'
    signal_strength: float  # 0.0-1.0 (combined metric for agent use)

    def __str__(self):
        """Human-readable representation"""
        emoji = "📈" if self.direction == "Up" else "📉"
        conf_emoji = {
            'high': '✓✓',
            'moderate': '✓',
            'low': '~',
            'insufficient': '✗'
        }.get(self.confidence, '?')

        return (
            f"{emoji} {self.crypto.upper()} {self.direction} @ {self.hour:02d}:00 UTC: "
            f"{self.win_rate:.1%} win rate ({self.edge:+.1%} edge, "
            f"n={self.sample_size}, p={self.p_value:.3f}) {conf_emoji}"
        )


class PatternQueryService:
    """
    Service for querying historical time-dependent patterns.
    Provides statistical analysis of crypto directional bias by hour.

    Features:
    - Preloads all patterns into cache for fast queries
    - Chi-square tests for statistical significance
    - Confidence levels based on sample size and p-value
    - Signal strength scoring for agent decision-making
    """

    def __init__(self, db_path: str = 'analysis/epoch_history.db'):
        """
        Initialize pattern query service.

        Args:
            db_path: Path to epoch history SQLite database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Cache for pattern data (doesn't change unless new data added)
        self._cache: Dict[Tuple[str, int, str], PatternSignal] = {}
        self._cache_timestamp: Optional[datetime] = None

        # Preload all patterns into cache
        self._preload_patterns()

    def _preload_patterns(self):
        """Preload all hourly patterns into cache for fast queries."""
        print("[PatternQuery] Loading historical patterns...")

        # For each crypto, hour, direction combination
        for crypto in ['btc', 'eth', 'sol', 'xrp']:
            for hour in range(24):
                for direction in ['Up', 'Down']:
                    signal = self._calculate_pattern_signal(crypto, hour, direction)
                    cache_key = (crypto.lower(), hour, direction)
                    self._cache[cache_key] = signal

        self._cache_timestamp = datetime.now()
        print(f"[PatternQuery] Preloaded {len(self._cache)} pattern signals")

    def _calculate_pattern_signal(self, crypto: str, hour: int, direction: str) -> PatternSignal:
        """
        Calculate pattern signal from historical data.

        Args:
            crypto: Crypto symbol ('btc', 'eth', 'sol', 'xrp')
            hour: Hour of day (0-23 UTC)
            direction: 'Up' or 'Down'

        Returns:
            PatternSignal with win rate, edge, statistical metrics
        """

        # Query historical data
        query = '''
            SELECT
                COUNT(*) as total_epochs,
                SUM(CASE WHEN direction = ? THEN 1 ELSE 0 END) as direction_count
            FROM epoch_outcomes
            WHERE crypto = ? AND hour = ?
        '''

        row = self.conn.execute(query, (direction, crypto, hour)).fetchone()

        total = row['total_epochs']
        count = row['direction_count']

        if total == 0:
            # No data for this combination
            return PatternSignal(
                crypto=crypto,
                hour=hour,
                direction=direction,
                win_rate=0.50,
                edge=0.0,
                sample_size=0,
                p_value=1.0,
                confidence='insufficient',
                signal_strength=0.5
            )

        # Calculate win rate
        win_rate = count / total
        edge = win_rate - 0.50

        # Chi-square test for significance
        expected = total / 2.0
        chi_square = ((count - expected) ** 2 / expected) + \
                    ((total - count - expected) ** 2 / expected)

        # P-value approximation (chi-square with df=1)
        p_value = self._chi2_pvalue(chi_square)

        # Confidence level based on sample size and p-value
        if total < 10:
            confidence = 'insufficient'
        elif total >= 20 and p_value < 0.05:
            confidence = 'high'
        elif total >= 15 and p_value < 0.10:
            confidence = 'moderate'
        elif total >= 10:
            confidence = 'low'
        else:
            confidence = 'insufficient'

        # Signal strength (0-1 scale, accounting for statistical confidence)
        # Formula: base strength from win_rate, modulated by confidence
        base_strength = win_rate

        # Adjust for confidence
        confidence_multiplier = {
            'high': 1.0,
            'moderate': 0.8,
            'low': 0.6,
            'insufficient': 0.5
        }

        signal_strength = 0.5 + (base_strength - 0.5) * confidence_multiplier[confidence]

        return PatternSignal(
            crypto=crypto,
            hour=hour,
            direction=direction,
            win_rate=win_rate,
            edge=edge,
            sample_size=total,
            p_value=p_value,
            confidence=confidence,
            signal_strength=signal_strength
        )

    def _chi2_pvalue(self, chi_square: float) -> float:
        """
        Approximate p-value for chi-square statistic (df=1).

        Uses lookup table for quick approximation without scipy.

        Args:
            chi_square: Chi-square statistic value

        Returns:
            Approximate p-value
        """
        # Simplified approximation using chi-square critical values (df=1)
        if chi_square < 0.004:
            return 1.0
        elif chi_square < 0.02:
            return 0.90
        elif chi_square < 0.10:
            return 0.75
        elif chi_square < 0.45:
            return 0.50
        elif chi_square < 1.32:
            return 0.25
        elif chi_square < 2.71:
            return 0.10
        elif chi_square < 3.84:
            return 0.05
        elif chi_square < 5.02:
            return 0.025
        elif chi_square < 6.63:
            return 0.01
        else:
            return 0.001

    def query_pattern(self, crypto: str, hour: int, direction: str) -> PatternSignal:
        """
        Query historical pattern for crypto/hour/direction.

        Args:
            crypto: 'btc', 'eth', 'sol', 'xrp' (case-insensitive)
            hour: 0-23 (UTC hour)
            direction: 'Up' or 'Down'

        Returns:
            PatternSignal with win_rate, edge, statistical significance

        Example:
            >>> service = PatternQueryService()
            >>> signal = service.query_pattern('btc', 14, 'Up')
            >>> print(f"BTC Up at 2pm: {signal.win_rate:.1%}, edge {signal.edge:+.1%}")
        """
        cache_key = (crypto.lower(), hour, direction)

        if cache_key in self._cache:
            return self._cache[cache_key]
        else:
            # Not in cache (shouldn't happen after preload, but handle gracefully)
            signal = self._calculate_pattern_signal(crypto, hour, direction)
            self._cache[cache_key] = signal
            return signal

    def get_best_opportunities(self, min_edge: float = 0.10,
                              min_confidence: str = 'moderate') -> List[PatternSignal]:
        """
        Get all crypto/hour/direction combinations with strong patterns.

        Args:
            min_edge: Minimum edge required (default 10pp = 10% above 50%)
            min_confidence: Minimum confidence level ('high', 'moderate', 'low')

        Returns:
            List of PatternSignals sorted by edge (descending)

        Example:
            >>> opportunities = service.get_best_opportunities(min_edge=0.10)
            >>> for sig in opportunities[:5]:
            ...     print(sig)
        """
        confidence_rank = {'high': 3, 'moderate': 2, 'low': 1, 'insufficient': 0}
        min_rank = confidence_rank[min_confidence]

        opportunities = [
            signal for signal in self._cache.values()
            if signal.edge >= min_edge and confidence_rank[signal.confidence] >= min_rank
        ]

        return sorted(opportunities, key=lambda s: s.edge, reverse=True)

    def get_hourly_summary(self, crypto: str) -> Dict[int, Dict[str, PatternSignal]]:
        """
        Get summary of all hours for a crypto.

        Args:
            crypto: Crypto symbol

        Returns:
            Dict mapping hour -> {'Up': signal, 'Down': signal}
        """
        summary = {}
        for hour in range(24):
            summary[hour] = {
                'Up': self.query_pattern(crypto, hour, 'Up'),
                'Down': self.query_pattern(crypto, hour, 'Down')
            }
        return summary

    def get_best_hour_for_crypto(self, crypto: str, direction: str) -> Optional[Tuple[int, PatternSignal]]:
        """
        Get the best hour to trade crypto in given direction.

        Args:
            crypto: Crypto symbol
            direction: 'Up' or 'Down'

        Returns:
            Tuple of (hour, signal) with highest signal strength, or None if no good hours
        """
        best_hour = None
        best_signal = None

        for hour in range(24):
            signal = self.query_pattern(crypto, hour, direction)
            if best_signal is None or signal.signal_strength > best_signal.signal_strength:
                if signal.confidence in ['high', 'moderate']:
                    best_hour = hour
                    best_signal = signal

        return (best_hour, best_signal) if best_hour is not None else None

    def refresh_cache(self):
        """Refresh cache with latest data (call after new epochs added)."""
        print("[PatternQuery] Refreshing pattern cache...")
        self._cache.clear()
        self._preload_patterns()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# Global singleton
_pattern_service: Optional[PatternQueryService] = None


def get_pattern_service() -> PatternQueryService:
    """
    Get or create global pattern service instance (singleton).

    Returns:
        PatternQueryService instance

    Example:
        >>> from analysis.pattern_query_service import get_pattern_service
        >>> service = get_pattern_service()
        >>> signal = service.query_pattern('btc', 14, 'Up')
    """
    global _pattern_service
    if _pattern_service is None:
        _pattern_service = PatternQueryService()
    return _pattern_service


# CLI interface for testing
if __name__ == '__main__':
    import sys

    print("=" * 80)
    print(" " * 20 + "PATTERN QUERY SERVICE TEST")
    print("=" * 80)
    print()

    service = PatternQueryService()

    # Test 1: Query known strong pattern (2pm BTC Up)
    print("Test 1: Query 2pm BTC Up pattern (expected: strong)")
    print("-" * 80)
    signal = service.query_pattern('btc', 14, 'Up')
    print(signal)
    print()

    # Test 2: Get best opportunities
    print("Test 2: Best opportunities (min 10% edge)")
    print("-" * 80)
    opportunities = service.get_best_opportunities(min_edge=0.10)
    print(f"Found {len(opportunities)} strong patterns:\n")
    for i, sig in enumerate(opportunities[:10], 1):
        print(f"{i}. {sig}")
    print()

    # Test 3: Get best hour for each crypto
    print("Test 3: Best hour for UP direction per crypto")
    print("-" * 80)
    for crypto in ['btc', 'eth', 'sol', 'xrp']:
        result = service.get_best_hour_for_crypto(crypto, 'Up')
        if result:
            hour, sig = result
            print(f"{crypto.upper()}: {hour:02d}:00 UTC ({sig.win_rate:.1%}, "
                  f"edge {sig.edge:+.1%}, n={sig.sample_size})")
        else:
            print(f"{crypto.upper()}: No strong patterns found")
    print()

    # Test 4: Hourly summary for BTC
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        print("Test 4: Full hourly summary for BTC")
        print("-" * 80)
        summary = service.get_hourly_summary('btc')
        print(f"{'Hour':<6} {'Up WR':<10} {'Up Edge':<10} {'Down WR':<10} {'Down Edge':<10}")
        print("-" * 80)
        for hour in range(24):
            up_sig = summary[hour]['Up']
            down_sig = summary[hour]['Down']
            print(f"{hour:02d}:00  {up_sig.win_rate:<10.1%} {up_sig.edge:+10.1%} "
                  f"{down_sig.win_rate:<10.1%} {down_sig.edge:+10.1%}")

    print("=" * 80)
    print("Pattern Query Service test complete!")
    print("=" * 80)
