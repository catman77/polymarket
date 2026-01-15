#!/usr/bin/env python3
"""
GamblerAgent - Probability-based veto agent using handicap analysis.

Uses poker-style decision-making (FOLD/CALL/RAISE) based on win probability.
Blocks trades with insufficient edge (< 60% win probability threshold).

Philosophy:
- FOLD: Win probability < 60% (block trade)
- CALL: Win probability 60-80% (allow with moderate confidence)
- RAISE: Win probability > 80% (high confidence signal)

This is a VETO AGENT - it can block trades but doesn't initiate them.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, Optional, Dict

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.base_agent import VetoAgent, Vote as BaseVote


@dataclass
class HandicapAnalysis:
    """
    Probability assessment for a trade opportunity.

    Attributes:
        win_probability: Estimated probability of winning (0.0-1.0)
        risk_assessment: LOW, MEDIUM, HIGH, CRITICAL
        bankroll_impact: SMALL, MEDIUM, LARGE
        decision: FOLD, CALL, or RAISE
        explanation: Human-readable reasoning
        components: Dict of probability components for debugging
    """
    win_probability: float
    risk_assessment: str
    bankroll_impact: str
    decision: str
    explanation: str
    components: Dict[str, float]


class GamblerAgent(VetoAgent):
    """
    Veto agent that blocks trades with insufficient win probability.

    Uses handicap analysis combining:
    - Agent consensus (weighted_score from decision engine)
    - Agent confidence (average confidence across voting agents)
    - Entry price (market implied probability)
    - Optional: Historical patterns (if TimePatternAgent is active)

    Decision Thresholds:
    - FOLD: < 60% win probability (VETO trade)
    - CALL: 60-80% win probability (allow trade)
    - RAISE: > 80% win probability (high confidence)

    Example:
        >>> agent = GamblerAgent()
        >>> data = {
        ...     'weighted_score': 0.65,
        ...     'confidence': 0.55,
        ...     'direction': 'Up',
        ...     'orderbook': {'yes': {'price': 0.45}}
        ... }
        >>> should_veto, reason = agent.can_veto('btc', data)
        >>> print(f"Veto: {should_veto}, Reason: {reason}")
    """

    # Thresholds
    FOLD_THRESHOLD = 0.60   # Veto if win_probability < 60%
    RAISE_THRESHOLD = 0.80  # High confidence threshold

    # Component weights for win probability calculation
    CONSENSUS_WEIGHT = 0.40
    CONFIDENCE_WEIGHT = 0.30
    CONTRARIAN_WEIGHT = 0.30

    def __init__(self, name: str = "GamblerAgent", weight: float = 1.0):
        """
        Initialize GamblerAgent.

        Args:
            name: Agent name for identification
            weight: Agent weight (used by coordinator, typically 1.0 for veto agents)
        """
        super().__init__(name, weight)

        # Statistics tracking (optional)
        self.fold_count = 0
        self.call_count = 0
        self.raise_count = 0

    def analyze(self, crypto: str, epoch: int, data: dict) -> BaseVote:
        """
        Analyze trade opportunity and return vote (coordinator interface).

        Note: GamblerAgent always votes Neutral since it's a veto agent.
        The actual decision is made in can_veto().

        Args:
            crypto: Crypto symbol ('btc', 'eth', 'sol', 'xrp')
            epoch: Current epoch timestamp
            data: Trading context dict with:
                - weighted_score: Consensus score from decision engine (0-1)
                - confidence: Average agent confidence (0-1)
                - direction: 'Up' or 'Down'
                - orderbook: {'yes': {'price': ...}, 'no': {'price': ...}}

        Returns:
            BaseVote with Neutral direction, win_probability as confidence,
            and handicap analysis in details
        """
        handicap = self._perform_handicap_analysis(crypto, data)

        return BaseVote(
            direction="Neutral",  # Veto agents don't vote on direction
            confidence=handicap.win_probability,
            quality=handicap.win_probability,
            agent_name=self.name,
            reasoning=f"Handicap: {handicap.decision} | P(win)={handicap.win_probability:.1%} | {handicap.explanation}",
            details={
                'handicap': {
                    'win_probability': handicap.win_probability,
                    'risk_assessment': handicap.risk_assessment,
                    'bankroll_impact': handicap.bankroll_impact,
                    'decision': handicap.decision,
                    'explanation': handicap.explanation,
                    'components': handicap.components
                }
            }
        )

    def can_veto(self, crypto: str, data: dict) -> Tuple[bool, str]:
        """
        Determine if trade should be vetoed based on win probability.

        This is the core veto logic. Returns True to BLOCK the trade.

        Args:
            crypto: Crypto symbol
            data: Trading context dict (same as analyze())

        Returns:
            Tuple of (should_veto: bool, reason: str)
            - (True, reason) = VETO trade (block it)
            - (False, "") = Allow trade to proceed

        Example:
            >>> agent = GamblerAgent()
            >>> # Low probability trade
            >>> data = {'weighted_score': 0.40, 'confidence': 0.35,
            ...         'direction': 'Up', 'orderbook': {'yes': {'price': 0.15}}}
            >>> should_veto, reason = agent.can_veto('btc', data)
            >>> print(should_veto)  # True (FOLD)
            True
        """
        handicap = self._perform_handicap_analysis(crypto, data)

        if handicap.decision == "FOLD":
            self.fold_count += 1
            return True, f"❌ Handicap FOLD: {handicap.explanation}"

        # CALL or RAISE - allow trade
        if handicap.decision == "RAISE":
            self.raise_count += 1
        else:
            self.call_count += 1

        return False, ""

    def _perform_handicap_analysis(self, crypto: str, data: dict) -> HandicapAnalysis:
        """
        Calculate win probability from multiple signal components.

        Formula:
            win_prob = base + (consensus * w1) + (confidence * w2) + (contrarian_adj * w3)

            where:
            - base = 0.50 (starting point = coin flip)
            - consensus = weighted_score from decision engine
            - confidence = average agent confidence
            - contrarian_adj = adjustment based on entry price

        Contrarian Adjustment (penalizes expensive entries):
            - Entry < $0.15: -0.20 (extreme contrarian, very risky)
            - Entry < $0.30: -0.10 (moderate contrarian)
            - Entry ≥ $0.30: 0.0 (following market, no penalty)

        Args:
            crypto: Crypto symbol
            data: Trading context dict

        Returns:
            HandicapAnalysis with win_probability and decision
        """
        # Extract components
        weighted_score = data.get('weighted_score', 0.0)
        confidence = data.get('confidence', 0.0)
        direction = data.get('direction', '')
        orderbook = data.get('orderbook', {})

        # Get entry price
        side_key = 'yes' if direction == 'Up' else 'no'
        entry_price = orderbook.get(side_key, {}).get('price', 0.50)

        # Calculate probability components
        consensus_component = weighted_score * self.CONSENSUS_WEIGHT
        confidence_component = confidence * self.CONFIDENCE_WEIGHT

        # Contrarian adjustment (penalty for expensive entries)
        if entry_price < 0.15:
            contrarian_adj = -0.20  # Extreme risk (buying <$0.15 = market very bearish)
        elif entry_price < 0.30:
            contrarian_adj = -0.10  # Moderate risk
        else:
            contrarian_adj = 0.0     # Following market

        contrarian_component = contrarian_adj * self.CONTRARIAN_WEIGHT

        # Combined win probability
        # Base = 0.50, then add weighted components
        win_probability = 0.50 + consensus_component + confidence_component + contrarian_component

        # Clamp to [0.0, 1.0]
        win_probability = max(0.0, min(1.0, win_probability))

        # Determine decision
        if win_probability < self.FOLD_THRESHOLD:
            decision = "FOLD"
            explanation = f"Win probability {win_probability:.1%} < {self.FOLD_THRESHOLD:.0%} threshold"
        elif win_probability > self.RAISE_THRESHOLD:
            decision = "RAISE"
            explanation = f"High confidence: {win_probability:.1%} win probability"
        else:
            decision = "CALL"
            explanation = f"Moderate setup: {win_probability:.1%} win probability"

        # Risk assessment based on entry price and consensus
        if entry_price < 0.15:
            risk = "CRITICAL"
        elif entry_price < 0.30:
            risk = "HIGH"
        else:
            risk = "LOW" if weighted_score > 0.50 else "MEDIUM"

        # Bankroll impact (position sizing suggestion)
        if win_probability > 0.80:
            bankroll = "LARGE"    # High confidence = larger bet
        elif win_probability > 0.60:
            bankroll = "MEDIUM"
        else:
            bankroll = "SMALL"    # Low confidence = smaller bet

        return HandicapAnalysis(
            win_probability=win_probability,
            risk_assessment=risk,
            bankroll_impact=bankroll,
            decision=decision,
            explanation=explanation,
            components={
                'consensus': consensus_component,
                'confidence': confidence_component,
                'contrarian': contrarian_component,
                'entry_price': entry_price,
                'weighted_score': weighted_score,
                'agent_confidence': confidence
            }
        )

    def get_statistics(self) -> dict:
        """
        Get agent statistics for monitoring.

        Returns:
            Dict with fold/call/raise counts and percentages
        """
        total = self.fold_count + self.call_count + self.raise_count

        if total == 0:
            return {
                'total_decisions': 0,
                'fold_count': 0,
                'call_count': 0,
                'raise_count': 0,
                'fold_pct': 0.0,
                'call_pct': 0.0,
                'raise_pct': 0.0
            }

        return {
            'total_decisions': total,
            'fold_count': self.fold_count,
            'call_count': self.call_count,
            'raise_count': self.raise_count,
            'fold_pct': self.fold_count / total,
            'call_pct': self.call_count / total,
            'raise_pct': self.raise_count / total
        }

    def reset_statistics(self):
        """Reset decision counters."""
        self.fold_count = 0
        self.call_count = 0
        self.raise_count = 0


# CLI interface for testing
if __name__ == '__main__':
    print("=" * 80)
    print(" " * 25 + "GAMBLER AGENT TEST")
    print("=" * 80)
    print()

    agent = GamblerAgent()

    # Test 1: Low probability (should FOLD)
    print("Test 1: Low probability trade (expect FOLD)")
    print("-" * 80)
    low_prob_data = {
        'weighted_score': 0.45,
        'confidence': 0.35,
        'direction': 'Up',
        'orderbook': {'yes': {'price': 0.12}}  # Extreme contrarian
    }
    should_veto, reason = agent.can_veto('btc', low_prob_data)
    vote = agent.analyze('btc', 1234567890, low_prob_data)

    print(f"Should Veto: {should_veto}")
    print(f"Reason: {reason}")
    print(f"Vote Reasoning: {vote.reasoning}")
    print(f"Win Probability: {vote.confidence:.1%}")
    print()

    # Test 2: Moderate probability (should CALL)
    print("Test 2: Moderate probability trade (expect CALL)")
    print("-" * 80)
    mod_prob_data = {
        'weighted_score': 0.60,
        'confidence': 0.50,
        'direction': 'Up',
        'orderbook': {'yes': {'price': 0.40}}
    }
    should_veto, reason = agent.can_veto('eth', mod_prob_data)
    vote = agent.analyze('eth', 1234567890, mod_prob_data)

    print(f"Should Veto: {should_veto}")
    print(f"Reason: {reason if reason else '(none - trade allowed)'}")
    print(f"Vote Reasoning: {vote.reasoning}")
    print(f"Win Probability: {vote.confidence:.1%}")
    print()

    # Test 3: High probability (should RAISE)
    print("Test 3: High probability trade (expect RAISE)")
    print("-" * 80)
    high_prob_data = {
        'weighted_score': 0.75,
        'confidence': 0.70,
        'direction': 'Up',
        'orderbook': {'yes': {'price': 0.55}}
    }
    should_veto, reason = agent.can_veto('sol', high_prob_data)
    vote = agent.analyze('sol', 1234567890, high_prob_data)

    print(f"Should Veto: {should_veto}")
    print(f"Reason: {reason if reason else '(none - trade allowed)'}")
    print(f"Vote Reasoning: {vote.reasoning}")
    print(f"Win Probability: {vote.confidence:.1%}")
    print()

    # Test 4: Statistics
    print("Test 4: Agent Statistics")
    print("-" * 80)
    stats = agent.get_statistics()
    print(f"Total Decisions: {stats['total_decisions']}")
    print(f"FOLD: {stats['fold_count']} ({stats['fold_pct']:.1%})")
    print(f"CALL: {stats['call_count']} ({stats['call_pct']:.1%})")
    print(f"RAISE: {stats['raise_count']} ({stats['raise_pct']:.1%})")
    print()

    print("=" * 80)
    print("GamblerAgent test complete!")
    print("=" * 80)
