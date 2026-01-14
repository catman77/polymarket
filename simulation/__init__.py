#!/usr/bin/env python3
"""
Shadow Trading Simulation System

Runs alternative trading strategies in parallel with the live bot to test
different parameter combinations and identify optimal configurations.
"""

from .strategy_configs import StrategyConfig, STRATEGY_LIBRARY
from .shadow_strategy import ShadowStrategy
from .orchestrator import SimulationOrchestrator
from .trade_journal import TradeJournalDB

__all__ = [
    'StrategyConfig',
    'STRATEGY_LIBRARY',
    'ShadowStrategy',
    'SimulationOrchestrator',
    'TradeJournalDB'
]
