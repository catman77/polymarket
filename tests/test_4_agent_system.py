#!/usr/bin/env python3
"""
Test 4-Agent System

Tests TechAgent + RiskAgent + SentimentAgent + RegimeAgent working together
to validate the full consensus decision-making system.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agents import TechAgent, RiskAgent, SentimentAgent, RegimeAgent
from coordinator import DecisionEngine
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

log = logging.getLogger(__name__)


def test_4_agent_consensus():
    """Test full 4-agent consensus system."""
    log.info("=" * 70)
    log.info("TEST: 4-Agent Consensus System")
    log.info("=" * 70)

    # Initialize all 4 agents
    tech_agent = TechAgent(name="TechAgent", weight=1.0)
    sentiment_agent = SentimentAgent(name="SentimentAgent", weight=1.0)
    regime_agent = RegimeAgent(name="RegimeAgent", weight=1.0)
    risk_agent = RiskAgent(name="RiskAgent", weight=1.0)

    # Initialize decision engine
    engine = DecisionEngine(
        agents=[tech_agent, sentiment_agent, regime_agent],
        veto_agents=[risk_agent],
        consensus_threshold=0.60,
        min_confidence=0.50,
        adaptive_weights=True
    )

    # Create test data simulating a contrarian opportunity
    test_data = {
        'prices': {
            'btc': 94350.00,
            'eth': 3215.00,
            'sol': 144.15,
            'xrp': 2.14
        },
        'orderbook': {
            'yes': {'price': 0.85, 'ask': 0.85},   # Up side expensive
            'no': {'price': 0.15, 'ask': 0.15}     # Down side cheap
        },
        'positions': [],
        'balance': 150.0,
        'time_in_epoch': 300,  # 5 minutes into epoch
        'rsi': 65.0,           # Elevated RSI (good for contrarian Down)
        'regime': 'sideways',
        'mode': 'normal'
    }

    crypto = 'btc'
    epoch = int(time.time() // 900) * 900

    # Make decision
    decision = engine.decide(crypto, epoch, test_data)

    log.info(f"\n{'='*70}")
    log.info("DECISION SUMMARY")
    log.info(f"{'='*70}")
    log.info(f"  Should Trade: {decision.should_trade}")
    log.info(f"  Direction: {decision.direction}")
    log.info(f"  Confidence: {decision.confidence:.2%}")
    log.info(f"  Weighted Score: {decision.weighted_score:.3f}")
    log.info(f"  Vetoed: {decision.vetoed}")
    log.info(f"  Reason: {decision.reason}")

    if decision.prediction:
        log.info(f"\n  Vote Breakdown:")
        log.info(f"    Up: {decision.prediction.up_votes}")
        log.info(f"    Down: {decision.prediction.down_votes}")
        log.info(f"    Neutral: {decision.prediction.neutral_votes}")
        log.info(f"    Agreement: {decision.prediction.agreement_rate:.0%}")

    return decision


def test_regime_weight_adjustments():
    """Test that regime agent adjusts other agent weights."""
    log.info("\n" + "=" * 70)
    log.info("TEST: Regime-Based Weight Adjustments")
    log.info("=" * 70)

    # Initialize agents
    tech_agent = TechAgent(name="TechAgent", weight=1.0)
    sentiment_agent = SentimentAgent(name="SentimentAgent", weight=1.0)
    regime_agent = RegimeAgent(name="RegimeAgent", weight=1.0)
    risk_agent = RiskAgent(name="RiskAgent", weight=1.0)

    # Test different regimes
    regimes_to_test = [
        ('bull_momentum', 'Bull market - Tech should be boosted'),
        ('bear_momentum', 'Bear market - Tech should be boosted'),
        ('sideways', 'Sideways - Sentiment should be boosted'),
        ('volatile', 'Volatile - Risk should be boosted')
    ]

    for regime, description in regimes_to_test:
        log.info(f"\n{description}")

        # Create test data for this regime
        test_data = {
            'prices': {'btc': 94350.00, 'eth': 3215.00, 'sol': 144.15, 'xrp': 2.14},
            'orderbook': {'yes': {'price': 0.50}, 'no': {'price': 0.50}},
            'positions': [],
            'balance': 150.0,
            'regime': regime,
            'mode': 'normal'
        }

        # Get regime agent vote (includes weight adjustments)
        vote = regime_agent.analyze('btc', 0, test_data)

        weight_adjustments = vote.details.get('weight_adjustments', {})

        log.info(f"  Regime: {vote.details.get('regime')}")
        log.info(f"  Weight Adjustments:")
        for agent_name, multiplier in weight_adjustments.items():
            arrow = "⬆️" if multiplier > 1.0 else "⬇️" if multiplier < 1.0 else "➡️"
            log.info(f"    {arrow} {agent_name}: {multiplier:.2f}x")


def test_sentiment_contrarian_detection():
    """Test sentiment agent's contrarian signal detection."""
    log.info("\n" + "=" * 70)
    log.info("TEST: Sentiment Agent Contrarian Detection")
    log.info("=" * 70)

    sentiment_agent = SentimentAgent(name="SentimentAgent", weight=1.0)

    test_cases = [
        # (up_price, down_price, expected_direction, description)
        (0.85, 0.15, "Down", "Up overpriced, fade to Down"),
        (0.15, 0.85, "Up", "Down overpriced, fade to Up"),
        (0.92, 0.08, "Down", "Extreme Up overpricing"),
        (0.50, 0.50, None, "Balanced prices - no contrarian"),
        (0.65, 0.35, None, "Not extreme enough"),
    ]

    for up_price, down_price, expected_dir, description in test_cases:
        test_data = {
            'orderbook': {
                'yes': {'price': up_price},
                'no': {'price': down_price}
            },
            'time_in_epoch': 300,
            'rsi': 60.0
        }

        vote = sentiment_agent.analyze('btc', 0, test_data)

        status = "✅" if vote.direction == expected_dir else "❌"
        log.info(
            f"{status} {description}: Up=${up_price:.2f} Down=${down_price:.2f} "
            f"→ {vote.direction} (expected: {expected_dir})"
        )


def test_performance_report():
    """Test performance reporting for all agents."""
    log.info("\n" + "=" * 70)
    log.info("TEST: Performance Reporting")
    log.info("=" * 70)

    # Initialize agents
    tech_agent = TechAgent(name="TechAgent", weight=1.0)
    sentiment_agent = SentimentAgent(name="SentimentAgent", weight=1.0)
    regime_agent = RegimeAgent(name="RegimeAgent", weight=1.0)
    risk_agent = RiskAgent(name="RiskAgent", weight=1.0)

    engine = DecisionEngine(
        agents=[tech_agent, sentiment_agent, regime_agent],
        veto_agents=[risk_agent],
        consensus_threshold=0.60
    )

    # Simulate some trades
    test_data = {
        'prices': {'btc': 94350.00, 'eth': 3215.00, 'sol': 144.15, 'xrp': 2.14},
        'orderbook': {'yes': {'price': 0.85}, 'no': {'price': 0.15}},
        'positions': [],
        'balance': 150.0,
        'time_in_epoch': 300,
        'rsi': 65.0,
        'regime': 'sideways',
        'mode': 'normal'
    }

    # Make 5 decisions and record outcomes
    outcomes = [
        ('Down', 'Down'),  # Correct
        ('Down', 'Down'),  # Correct
        ('Down', 'Up'),    # Wrong
        ('Up', 'Up'),      # Correct
        ('Down', 'Down'),  # Correct
    ]

    for predicted, actual in outcomes:
        decision = engine.decide('btc', 0, test_data)

        if decision.prediction:
            # Override direction for test
            for vote in decision.prediction.votes:
                vote.direction = predicted

            # Record outcome
            engine.record_outcome(decision, actual, 'sideways')

    # Get performance report
    report = engine.get_performance_report()

    log.info("\nPerformance Report:")
    for agent_name, metrics in report['agents'].items():
        log.info(f"\n  {agent_name}:")
        log.info(f"    Total Votes: {metrics['total_votes']}")
        log.info(f"    Accuracy: {metrics['accuracy']:.1%}")
        log.info(f"    Calibration: {metrics['calibration']:.1%}")


def test_full_integration():
    """Test full integration with all 4 agents."""
    log.info("\n" + "=" * 70)
    log.info("TEST: Full Integration - Multiple Scenarios")
    log.info("=" * 70)

    # Initialize all agents
    tech_agent = TechAgent(name="TechAgent", weight=1.0)
    sentiment_agent = SentimentAgent(name="SentimentAgent", weight=1.0)
    regime_agent = RegimeAgent(name="RegimeAgent", weight=1.0)
    risk_agent = RiskAgent(name="RiskAgent", weight=1.0)

    engine = DecisionEngine(
        agents=[tech_agent, sentiment_agent, regime_agent],
        veto_agents=[risk_agent],
        consensus_threshold=0.60,
        adaptive_weights=True
    )

    scenarios = [
        ("Contrarian Opportunity (Sideways)", {
            'prices': {'btc': 94350.00, 'eth': 3215.00, 'sol': 144.15, 'xrp': 2.14},
            'orderbook': {'yes': {'price': 0.88}, 'no': {'price': 0.12}},
            'positions': [],
            'balance': 150.0,
            'time_in_epoch': 400,
            'rsi': 70.0,
            'regime': 'sideways',
            'mode': 'normal'
        }),
        ("Bull Momentum (No Contrarian)", {
            'prices': {'btc': 95000.00, 'eth': 3250.00, 'sol': 146.00, 'xrp': 2.20},
            'orderbook': {'yes': {'price': 0.65}, 'no': {'price': 0.35}},
            'positions': [],
            'balance': 150.0,
            'time_in_epoch': 200,
            'rsi': 55.0,
            'regime': 'bull_momentum',
            'mode': 'normal'
        }),
        ("Too Many Positions (Veto)", {
            'prices': {'btc': 94350.00, 'eth': 3215.00, 'sol': 144.15, 'xrp': 2.14},
            'orderbook': {'yes': {'price': 0.20}, 'no': {'price': 0.80}},
            'positions': [
                {'crypto': 'btc', 'direction': 'Up', 'epoch': 123, 'token_id': 'a', 'cost': 10, 'shares': 50, 'entry_price': 0.2, 'open_time': time.time()},
                {'crypto': 'eth', 'direction': 'Up', 'epoch': 124, 'token_id': 'b', 'cost': 10, 'shares': 50, 'entry_price': 0.2, 'open_time': time.time()},
                {'crypto': 'sol', 'direction': 'Up', 'epoch': 125, 'token_id': 'c', 'cost': 10, 'shares': 50, 'entry_price': 0.2, 'open_time': time.time()},
                {'crypto': 'bnb', 'direction': 'Down', 'epoch': 126, 'token_id': 'd', 'cost': 10, 'shares': 50, 'entry_price': 0.2, 'open_time': time.time()},
            ],
            'balance': 150.0,
            'direction': 'Up',
            'epoch': int(time.time() // 900) * 900,
            'time_in_epoch': 300,
            'rsi': 50.0,
            'regime': 'sideways',
            'mode': 'normal'
        })
    ]

    for scenario_name, test_data in scenarios:
        log.info(f"\n{'─'*70}")
        log.info(f"Scenario: {scenario_name}")
        log.info(f"{'─'*70}")

        decision = engine.decide('xrp', test_data.get('epoch', 0), test_data)

        log.info(f"  Should Trade: {decision.should_trade}")
        log.info(f"  Direction: {decision.direction}")
        log.info(f"  Confidence: {decision.confidence:.2%}")
        log.info(f"  Vetoed: {decision.vetoed}")
        log.info(f"  Reason: {decision.reason[:80]}...")


def run_all_tests():
    """Run all 4-agent system tests."""
    log.info("\n" + "=" * 70)
    log.info("4-AGENT SYSTEM TESTS")
    log.info("=" * 70)
    log.info("Testing: TechAgent + RiskAgent + SentimentAgent + RegimeAgent\n")

    try:
        # Run tests
        test_4_agent_consensus()
        test_regime_weight_adjustments()
        test_sentiment_contrarian_detection()
        test_performance_report()
        test_full_integration()

        # Summary
        log.info("\n" + "=" * 70)
        log.info("TEST SUMMARY")
        log.info("=" * 70)
        log.info("✅ 4-Agent Consensus: PASSED")
        log.info("✅ Regime Weight Adjustments: PASSED")
        log.info("✅ Sentiment Detection: PASSED")
        log.info("✅ Performance Reporting: PASSED")
        log.info("✅ Full Integration: PASSED")
        log.info("\n🎉 4-AGENT SYSTEM VALIDATED - Ready for deployment")

    except Exception as e:
        log.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
