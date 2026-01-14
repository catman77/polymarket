#!/usr/bin/env python3
"""
Test script to verify outcome persistence fix.

This script simulates a resolution cycle and verifies that outcomes
are properly saved to the database.
"""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from simulation.strategy_configs import STRATEGY_LIBRARY
from simulation.orchestrator import SimulationOrchestrator
from config import agent_config

def test_outcome_persistence():
    """Test that outcomes persist to database."""
    print("="*60)
    print("Testing Outcome Persistence Fix")
    print("="*60)
    print()

    # Use test database
    test_db = 'simulation/test_journal.db'

    # Initialize orchestrator with test strategies
    strategies = [
        STRATEGY_LIBRARY['conservative'],
        STRATEGY_LIBRARY['aggressive']
    ]

    print("1. Creating orchestrator with test database...")
    orch = SimulationOrchestrator(
        strategies,
        db_path=test_db,
        starting_balance=100.0
    )
    print(f"   ✅ Created orchestrator with {len(orch.strategies)} strategies")
    print()

    # Check for existing unresolved positions
    print("2. Checking for unresolved positions...")
    total_positions = sum(len(s.positions) for s in orch.strategies.values())
    print(f"   Found {total_positions} open positions")

    if total_positions == 0:
        print("   ⚠️  No positions to resolve. Run the bot first to create shadow trades.")
        orch.close()
        return

    # Get first position to test
    for name, strategy in orch.strategies.items():
        if strategy.positions:
            position_key, pos = next(iter(strategy.positions.items()))
            crypto, epoch = position_key
            print(f"   Testing with: {name} {crypto.upper()} epoch {epoch}")
            print()

            # Check age
            current_time = int(time.time())
            age_sec = current_time - epoch
            age_min = age_sec // 60

            print(f"3. Position age: {age_min} minutes")

            if age_sec < 1020:
                print(f"   ⚠️  Position too young ({age_min} min < 17 min). Wait before testing.")
                orch.close()
                return

            # Simulate resolution with test outcome
            print(f"4. Simulating resolution with 'Up' outcome...")
            try:
                orch.on_epoch_resolution(crypto, epoch, "Up")
                print("   ✅ Resolution completed")
            except Exception as e:
                print(f"   ❌ Resolution failed: {e}")
                import traceback
                traceback.print_exc()
                orch.close()
                return

            print()
            print("5. Verifying outcome saved to database...")

            # Query database
            outcome_count = orch.db.conn.execute('''
                SELECT COUNT(*) FROM outcomes
                WHERE strategy=? AND crypto=? AND epoch=?
            ''', (name, crypto, epoch)).fetchone()[0]

            if outcome_count > 0:
                print(f"   ✅ SUCCESS: Outcome saved to database (count: {outcome_count})")

                # Get the outcome details
                outcome_row = orch.db.conn.execute('''
                    SELECT * FROM outcomes
                    WHERE strategy=? AND crypto=? AND epoch=?
                ''', (name, crypto, epoch)).fetchone()

                if outcome_row:
                    print(f"   Trade ID: {outcome_row['trade_id']}")
                    print(f"   Predicted: {outcome_row['predicted_direction']}")
                    print(f"   Actual: {outcome_row['actual_direction']}")
                    print(f"   PnL: ${outcome_row['pnl']:.2f}")
            else:
                print(f"   ❌ FAILED: Outcome NOT saved to database")
                print(f"   This indicates the bug is not fully fixed.")

            print()
            print("6. Checking total outcomes in database...")
            total_outcomes = orch.db.conn.execute('SELECT COUNT(*) FROM outcomes').fetchone()[0]
            print(f"   Total outcomes: {total_outcomes}")

            orch.close()
            return

    print("   ⚠️  No suitable positions found for testing")
    orch.close()

if __name__ == '__main__':
    try:
        test_outcome_persistence()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
