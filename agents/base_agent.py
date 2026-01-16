#!/usr/bin/env python3
"""
Base Agent Interface for Multi-Expert Trading System

All expert agents inherit from BaseAgent and implement the analyze() method.
This provides a standardized interface for the coordinator to aggregate votes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import logging

log = logging.getLogger(__name__)


@dataclass
class Vote:
    """
    Standardized vote structure from an expert agent.

    All agents return this structure so the coordinator can aggregate them.

    When to use each direction:
    - "Up": Predict price will increase
    - "Down": Predict price will decrease
    - "Neutral": Weak signal, leaning neither direction
    - "Skip": No signal or uncertain - agent abstains from voting

    Skip votes should have confidence=0.0 and quality=0.0 by convention.
    Use Skip to prevent default-to-direction bias in unclear situations.
    """
    # Core prediction
    direction: str  # "Up", "Down", "Neutral", or "Skip"
    confidence: float  # 0.0 to 1.0 (how confident in the direction)
    quality: float  # 0.0 to 1.0 (how good is the signal itself)

    # Metadata
    agent_name: str  # Which agent generated this vote
    reasoning: str  # Human-readable explanation
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    # Optional details
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate vote values."""
        assert self.direction in ["Up", "Down", "Neutral", "Skip"], f"Invalid direction: {self.direction}"
        assert 0.0 <= self.confidence <= 1.0, f"Confidence must be 0-1, got {self.confidence}"
        assert 0.0 <= self.quality <= 1.0, f"Quality must be 0-1, got {self.quality}"

    def weighted_score(self, weight: float = 1.0) -> float:
        """
        Calculate weighted score for aggregation.

        Formula: confidence × quality × weight

        Args:
            weight: Agent weight (expert weighting system)

        Returns:
            float: Weighted score for this vote
        """
        return self.confidence * self.quality * weight

    def to_dict(self) -> dict:
        """Convert to dictionary for logging."""
        return {
            'direction': self.direction,
            'confidence': self.confidence,
            'quality': self.quality,
            'agent': self.agent_name,
            'reasoning': self.reasoning,
            'timestamp': self.timestamp,
            'weighted_score': self.weighted_score(),
            'details': self.details
        }


@dataclass
class AgentPerformance:
    """
    Track performance metrics for an agent.

    Used to adjust expert weights over time based on accuracy.
    """
    agent_name: str
    total_votes: int = 0
    correct_predictions: int = 0
    total_confidence: float = 0.0

    # Regime-specific performance
    bull_correct: int = 0
    bull_total: int = 0
    bear_correct: int = 0
    bear_total: int = 0
    sideways_correct: int = 0
    sideways_total: int = 0

    def accuracy(self) -> float:
        """Overall accuracy rate."""
        if self.total_votes == 0:
            return 0.0
        return self.correct_predictions / self.total_votes

    def calibration(self) -> float:
        """
        How well does confidence match actual accuracy?

        Perfect calibration = 1.0 (80% confidence = 80% accuracy)
        """
        if self.total_votes == 0:
            return 0.0

        avg_confidence = self.total_confidence / self.total_votes
        accuracy = self.accuracy()

        # Smaller difference = better calibration
        calibration_error = abs(avg_confidence - accuracy)
        return 1.0 - calibration_error

    def regime_accuracy(self, regime: str) -> float:
        """Accuracy in specific regime."""
        if regime == 'bull':
            return self.bull_correct / max(self.bull_total, 1)
        elif regime == 'bear':
            return self.bear_correct / max(self.bear_total, 1)
        elif regime == 'sideways':
            return self.sideways_correct / max(self.sideways_total, 1)
        return 0.0

    def record_vote(self, correct: bool, confidence: float, regime: str = 'unknown'):
        """Record a vote outcome for tracking."""
        self.total_votes += 1
        self.total_confidence += confidence

        if correct:
            self.correct_predictions += 1

            if regime == 'bull':
                self.bull_correct += 1
            elif regime == 'bear':
                self.bear_correct += 1
            elif regime == 'sideways':
                self.sideways_correct += 1

        # Update regime totals
        if regime == 'bull':
            self.bull_total += 1
        elif regime == 'bear':
            self.bear_total += 1
        elif regime == 'sideways':
            self.sideways_total += 1

    def to_dict(self) -> dict:
        """Export performance metrics."""
        return {
            'agent_name': self.agent_name,
            'total_votes': self.total_votes,
            'accuracy': self.accuracy(),
            'calibration': self.calibration(),
            'bull_accuracy': self.regime_accuracy('bull'),
            'bear_accuracy': self.regime_accuracy('bear'),
            'sideways_accuracy': self.regime_accuracy('sideways')
        }


class BaseAgent(ABC):
    """
    Abstract base class for all expert agents.

    Each agent specializes in one aspect of market analysis:
    - TechAgent: Technical indicators and price confluence
    - SentimentAgent: Orderbook analysis and contrarian signals
    - RiskAgent: Position sizing and portfolio safety
    - RegimeAgent: Market regime classification
    - FutureAgent: Future window analysis
    - HistoryAgent: Pattern learning from past trades

    All agents implement analyze() to return a Vote.
    """

    def __init__(self, name: str, weight: float = 1.0):
        """
        Initialize agent.

        Args:
            name: Agent name (e.g., "TechAgent")
            weight: Base weight for voting (adjusted by coordinator)
        """
        self.name = name
        self.weight = weight
        self.performance = AgentPerformance(agent_name=name)
        self.log = logging.getLogger(f"Agent.{name}")

    @abstractmethod
    def analyze(self, crypto: str, epoch: int, data: dict) -> Vote:
        """
        Analyze market conditions and return a vote.

        This is the core method every agent must implement.

        Args:
            crypto: Crypto symbol (btc, eth, sol, xrp)
            epoch: Current epoch timestamp
            data: Shared data context with:
                - prices: Multi-exchange price data
                - orderbook: Current orderbook (if available)
                - positions: Open positions
                - balance: Current balance
                - regime: Current market regime
                - historical: Past trade data

        Returns:
            Vote: Agent's prediction with confidence and reasoning
        """
        pass

    def record_outcome(self, vote: Vote, actual_direction: str, regime: str = 'unknown'):
        """
        Record vote outcome for performance tracking.

        Args:
            vote: The vote that was cast
            actual_direction: What actually happened ("Up" or "Down")
            regime: Market regime at the time
        """
        correct = (vote.direction == actual_direction)
        self.performance.record_vote(correct, vote.confidence, regime)

        self.log.info(
            f"{self.name} vote: {vote.direction} @ {vote.confidence:.2f} "
            f"| Actual: {actual_direction} | {'✅' if correct else '❌'}"
        )

    def get_performance_summary(self) -> dict:
        """Get performance metrics."""
        return self.performance.to_dict()

    def adjust_weight(self, new_weight: float):
        """Update agent weight based on performance."""
        old_weight = self.weight
        self.weight = new_weight
        self.log.info(f"{self.name} weight adjusted: {old_weight:.3f} → {new_weight:.3f}")


class VetoAgent(BaseAgent):
    """
    Special agent type that can VETO trades.

    Example: RiskAgent can veto if position limits exceeded.
    """

    @abstractmethod
    def can_veto(self, crypto: str, data: dict) -> tuple[bool, str]:
        """
        Check if this agent wants to veto the trade.

        Returns:
            (veto, reason): (True, "reason") to block, (False, "") to allow
        """
        pass
