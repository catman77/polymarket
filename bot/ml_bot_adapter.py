#!/usr/bin/env python3
"""
ML Bot Adapter - Integrates ML predictions into live bot

Replaces agent consensus system with ML Random Forest predictions.
This is the LIVE TRADING integration for the ML model.

WARNING: This bypasses all agent voting and uses pure ML predictions.
Only use if ML has been validated in shadow testing.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import logging
from typing import Dict, Optional
from datetime import datetime

from simulation.ml_strategy import create_random_forest_strategy

log = logging.getLogger(__name__)


class MLBotAdapter:
    """
    Adapter to integrate ML predictions into the live bot.

    Replaces the agent voting system with ML Random Forest predictions.
    """

    def __init__(self, threshold: float = 0.55):
        """
        Initialize ML bot adapter.

        Args:
            threshold: Minimum win probability to trade (default 0.55 = 55%)
        """
        self.threshold = threshold
        self.ml_strategy = None
        self.predictions_made = 0
        self.trades_recommended = 0

        # Load ML strategy
        try:
            self.ml_strategy = create_random_forest_strategy(threshold=threshold)
            log.info(f"[ML Bot] ✅ Random Forest model loaded (threshold {threshold:.0%})")
        except Exception as e:
            log.error(f"[ML Bot] ❌ Failed to load ML model: {e}")
            raise

    def make_decision(
        self,
        crypto: str,
        epoch: int,
        market_data: dict
    ) -> Dict:
        """
        Make trading decision using ML model.

        Args:
            crypto: Cryptocurrency (BTC, ETH, SOL, XRP)
            epoch: Epoch timestamp
            market_data: Market data with prices, RSI, features, etc.

        Returns:
            Decision dict with:
                - should_trade: bool
                - direction: 'Up' or 'Down'
                - confidence: 0-1 (win probability)
                - entry_price: float
                - size: float (shares to buy)
                - reason: str
        """
        self.predictions_made += 1

        # Get ML prediction
        decision = self.ml_strategy.get_decision(crypto, epoch, market_data)

        if decision['should_trade']:
            self.trades_recommended += 1
            log.info(
                f"[ML Bot] 🤖 {crypto.upper()} {decision['direction']} "
                f"@ ${decision['entry_price']:.3f} "
                f"(confidence {decision['confidence']:.1%})"
            )
        else:
            log.debug(
                f"[ML Bot] ⏭️  {crypto.upper()} skip "
                f"(confidence {decision['confidence']:.1%} < {self.threshold:.0%})"
            )

        # Add size calculation (will be done by RiskAgent in main bot)
        decision['size'] = 0.0  # Placeholder - bot will calculate actual size

        return decision

    def get_stats(self) -> Dict:
        """Get adapter statistics."""
        return {
            'predictions_made': self.predictions_made,
            'trades_recommended': self.trades_recommended,
            'threshold': self.threshold,
            'recommendation_rate': (
                self.trades_recommended / self.predictions_made
                if self.predictions_made > 0 else 0.0
            )
        }


# Global ML adapter instance (will be initialized by bot)
_ml_adapter = None


def get_ml_adapter(threshold: float = 0.55) -> MLBotAdapter:
    """
    Get or create ML bot adapter (singleton pattern).

    Args:
        threshold: Win probability threshold for trading

    Returns:
        MLBotAdapter instance
    """
    global _ml_adapter

    if _ml_adapter is None:
        _ml_adapter = MLBotAdapter(threshold=threshold)

    return _ml_adapter


def ml_decision_override(
    crypto: str,
    epoch: int,
    market_data: dict,
    agent_decision: Optional[Dict] = None,
    threshold: float = 0.55
) -> Dict:
    """
    Override agent decision with ML prediction.

    This function can be called from the main bot to replace agent consensus
    with ML predictions.

    Args:
        crypto: Cryptocurrency
        epoch: Epoch timestamp
        market_data: Market data
        agent_decision: Original agent decision (ignored)
        threshold: ML win probability threshold

    Returns:
        ML decision dict
    """
    adapter = get_ml_adapter(threshold=threshold)
    return adapter.make_decision(crypto, epoch, market_data)


if __name__ == '__main__':
    """Test ML bot adapter."""
    logging.basicConfig(level=logging.INFO)

    # Create adapter
    adapter = MLBotAdapter(threshold=0.55)

    # Sample market data
    sample_data = {
        'crypto': 'BTC',
        'epoch': 1234567890,
        'datetime': datetime.now(),
        'up_price': 0.25,
        'down_price': 0.75,
        'rsi': 42.0,
        'volatility': 0.018,
        'price_momentum': -0.003,
        'spread_proxy': 0.015,
        'position_in_range': 0.25,
        'price_z_score': -0.8,
        'epoch_sequence': 15,
        'is_market_open': 1
    }

    print("\n" + "="*80)
    print("ML BOT ADAPTER TEST")
    print("="*80 + "\n")

    # Make decision
    decision = adapter.make_decision('BTC', 1234567890, sample_data)

    print(f"Should Trade: {decision['should_trade']}")
    print(f"Direction: {decision['direction']}")
    print(f"Confidence: {decision['confidence']:.1%}")
    print(f"Entry Price: ${decision['entry_price']:.3f}")
    print(f"Reason: {decision['reason']}")
    print()

    # Show stats
    stats = adapter.get_stats()
    print("Adapter Stats:")
    print(f"  Predictions Made: {stats['predictions_made']}")
    print(f"  Trades Recommended: {stats['trades_recommended']}")
    print(f"  Recommendation Rate: {stats['recommendation_rate']:.1%}")
    print()

    print("="*80)
    print("✓ ML bot adapter working correctly")
    print("="*80 + "\n")
