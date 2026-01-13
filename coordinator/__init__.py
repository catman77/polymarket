"""Coordinator system for aggregating votes and making decisions."""

from .vote_aggregator import VoteAggregator, AggregatePrediction, calculate_agent_weights
from .decision_engine import DecisionEngine, TradeDecision

__all__ = [
    'VoteAggregator',
    'AggregatePrediction',
    'calculate_agent_weights',
    'DecisionEngine',
    'TradeDecision'
]
