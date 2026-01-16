#!/usr/bin/env python3
"""
Test US-BF-016: Shadow strategy independent execution

Verifies that fixed_bugs strategy can be loaded by orchestrator and will execute independently.
This is a minimal smoke test - full validation requires 24hr live monitoring.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.strategy_configs import get_strategy
from config import agent_config


def test_strategy_can_be_loaded():
    """Test: Strategy can be loaded by name"""
    print("✓ Test 1: Strategy can be loaded by get_strategy()")
    strategy = get_strategy('fixed_bugs')
    assert strategy is not None
    assert strategy.name == 'fixed_bugs'
    print(f"  Loaded strategy: {strategy.name}")


def test_strategy_has_required_fields():
    """Test: Strategy has all required fields for orchestrator"""
    print("\n✓ Test 2: Strategy has required fields for orchestrator")
    strategy = get_strategy('fixed_bugs')

    # Required fields for shadow trading
    required_fields = [
        'name',
        'description',
        'consensus_threshold',
        'min_confidence',
        'min_individual_confidence',
        'agent_weights',
        'adaptive_weights',
        'regime_adjustment_enabled',
        'max_position_pct',
        'max_same_direction',
        'is_live'
    ]

    for field in required_fields:
        assert hasattr(strategy, field), f"Missing required field: {field}"
        print(f"  ✓ {field}: {getattr(strategy, field)}")


def test_strategy_is_shadow_not_live():
    """Test: Strategy is marked as shadow (not live)"""
    print("\n✓ Test 3: Strategy is marked as shadow (is_live=False)")
    strategy = get_strategy('fixed_bugs')
    assert strategy.is_live == False, "Shadow strategy should have is_live=False"
    print(f"  is_live: {strategy.is_live}")


def test_strategy_in_shadow_list():
    """Test: Strategy is in SHADOW_STRATEGIES list"""
    print("\n✓ Test 4: Strategy is in SHADOW_STRATEGIES config")
    assert 'fixed_bugs' in agent_config.SHADOW_STRATEGIES
    index = agent_config.SHADOW_STRATEGIES.index('fixed_bugs')
    print(f"  Position in list: {index + 1}/{len(agent_config.SHADOW_STRATEGIES)}")


def test_strategy_config_overrides():
    """Test: Strategy config overrides will be applied by orchestrator"""
    print("\n✓ Test 5: Config overrides present for orchestrator")
    strategy = get_strategy('fixed_bugs')

    # Tech config overrides (US-BF-011)
    assert strategy.tech_config is not None
    assert 'TECH_CONFLUENCE_THRESHOLD' in strategy.tech_config
    print(f"  Tech config: {strategy.tech_config}")

    # Sentiment config overrides (US-BF-014)
    assert strategy.sentiment_config is not None
    assert 'SENTIMENT_CONTRARIAN_MAX_ENTRY' in strategy.sentiment_config
    print(f"  Sentiment config: {strategy.sentiment_config}")


def test_ml_mode_disabled():
    """Test: ML mode is disabled (US-BF-013)"""
    print("\n✓ Test 6: ML mode disabled (agent-only mode)")
    strategy = get_strategy('fixed_bugs')
    assert strategy.use_ml_model == False, "ML mode should be disabled"
    print(f"  use_ml_model: {strategy.use_ml_model}")


def test_comparison_with_live():
    """Test: Show key differences between live and fixed_bugs"""
    print("\n✓ Test 7: Key differences vs live 'default' strategy")

    live = get_strategy('default')
    fixed = get_strategy('fixed_bugs')

    print(f"  Consensus threshold: {live.consensus_threshold} → {fixed.consensus_threshold}")
    print(f"  ML mode: {live.use_ml_model} → {fixed.use_ml_model}")
    print(f"  Tech config: {live.tech_config} → {fixed.tech_config}")
    print(f"  Sentiment config: {live.sentiment_config} → {fixed.sentiment_config}")


def main():
    """Run all tests"""
    print("=" * 80)
    print("Testing US-BF-016: Shadow strategy independent execution")
    print("=" * 80)

    try:
        test_strategy_can_be_loaded()
        test_strategy_has_required_fields()
        test_strategy_is_shadow_not_live()
        test_strategy_in_shadow_list()
        test_strategy_config_overrides()
        test_ml_mode_disabled()
        test_comparison_with_live()

        print("\n" + "=" * 80)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 80)
        print("\nShadow strategy setup complete!")
        print("\nTo verify independent execution:")
        print("1. Start bot: python3 bot/momentum_bot_v12.py")
        print("2. Check logs for: 'Shadow strategy: fixed_bugs'")
        print("3. Monitor dashboard: python3 simulation/dashboard.py")
        print("4. Verify trades logged in: simulation/trade_journal.db")
        print("\nNote: Full validation requires 24 hours of monitoring.")
        return 0

    except AssertionError as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        return 1
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
