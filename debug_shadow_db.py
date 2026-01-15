#!/usr/bin/env python3
"""
Debug script to diagnose why trade_journal.db is empty.

Tests:
1. Database initialization
2. Strategy registration
3. Decision logging
4. Trade logging
5. Outcome logging
"""

import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from simulation.trade_journal import TradeJournalDB
from simulation.strategy_configs import StrategyConfig, get_strategy

def test_database_initialization():
    """Test 1: Database initialization"""
    print("="*80)
    print("TEST 1: Database Initialization")
    print("="*80)

    db_path = 'simulation/test_trade_journal.db'

    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Removed existing test database: {db_path}")

    # Initialize database
    db = TradeJournalDB(db_path)
    print(f"✓ Created TradeJournalDB instance")

    # Check if tables exist
    tables = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = [row[0] for row in tables]
    print(f"✓ Tables created: {table_names}")

    expected_tables = ['strategies', 'decisions', 'trades', 'outcomes', 'agent_votes', 'performance']
    missing_tables = set(expected_tables) - set(table_names)

    if missing_tables:
        print(f"✗ FAIL: Missing tables: {missing_tables}")
        return False

    print(f"✓ PASS: All tables created successfully")

    # Check file size
    file_size = os.path.getsize(db_path)
    print(f"✓ Database file size: {file_size} bytes")

    db.close()
    return True

def test_strategy_registration():
    """Test 2: Strategy registration"""
    print("\n" + "="*80)
    print("TEST 2: Strategy Registration")
    print("="*80)

    db_path = 'simulation/test_trade_journal.db'
    db = TradeJournalDB(db_path)

    # Get default strategy config
    config = get_strategy('default')
    print(f"✓ Loaded strategy config: {config.name}")

    # Register strategy
    db.register_strategy(config)
    print(f"✓ Registered strategy: {config.name}")

    # Check if strategy was inserted
    result = db.conn.execute("SELECT * FROM strategies WHERE name=?", (config.name,)).fetchone()

    if result:
        print(f"✓ PASS: Strategy found in database")
        print(f"  - Name: {result['name']}")
        print(f"  - Description: {result['description'][:50]}...")
        print(f"  - Is Live: {result['is_live']}")
    else:
        print(f"✗ FAIL: Strategy not found in database")
        db.close()
        return False

    # Count strategies
    count = db.conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0]
    print(f"✓ Total strategies in DB: {count}")

    db.close()
    return True

def test_decision_logging():
    """Test 3: Decision logging"""
    print("\n" + "="*80)
    print("TEST 3: Decision Logging")
    print("="*80)

    db_path = 'simulation/test_trade_journal.db'
    db = TradeJournalDB(db_path)

    # Log a decision
    decision_id = db.log_decision(
        strategy='default',
        crypto='btc',
        epoch=1736971200,  # Example epoch
        should_trade=True,
        direction='Up',
        confidence=0.65,
        weighted_score=0.72,
        reason='Test decision',
        balance_before=100.0
    )

    print(f"✓ Logged decision with ID: {decision_id}")

    # Verify decision was inserted
    result = db.conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()

    if result:
        print(f"✓ PASS: Decision found in database")
        print(f"  - Strategy: {result['strategy']}")
        print(f"  - Crypto: {result['crypto']}")
        print(f"  - Direction: {result['direction']}")
        print(f"  - Confidence: {result['confidence']}")
    else:
        print(f"✗ FAIL: Decision not found in database")
        db.close()
        return False

    # Count decisions
    count = db.conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    print(f"✓ Total decisions in DB: {count}")

    db.close()
    return True

def test_trade_logging():
    """Test 4: Trade logging"""
    print("\n" + "="*80)
    print("TEST 4: Trade Logging")
    print("="*80)

    db_path = 'simulation/test_trade_journal.db'
    db = TradeJournalDB(db_path)

    # First log a decision (needed as foreign key)
    decision_id = db.log_decision(
        strategy='default',
        crypto='eth',
        epoch=1736971500,
        should_trade=True,
        direction='Down',
        confidence=0.68,
        weighted_score=0.75,
        reason='Test trade',
        balance_before=100.0
    )

    # Log a trade
    trade_id = db.log_trade(
        decision_id=decision_id,
        strategy='default',
        crypto='eth',
        epoch=1736971500,
        direction='Down',
        entry_price=0.15,
        size=10.0,
        shares=66.67,
        confidence=0.68,
        weighted_score=0.75
    )

    print(f"✓ Logged trade with ID: {trade_id}")

    # Verify trade was inserted
    result = db.conn.execute("SELECT * FROM trades WHERE id=?", (trade_id,)).fetchone()

    if result:
        print(f"✓ PASS: Trade found in database")
        print(f"  - Strategy: {result['strategy']}")
        print(f"  - Crypto: {result['crypto']}")
        print(f"  - Direction: {result['direction']}")
        print(f"  - Entry Price: ${result['entry_price']:.2f}")
        print(f"  - Size: ${result['size']:.2f}")
    else:
        print(f"✗ FAIL: Trade not found in database")
        db.close()
        return False

    # Count trades
    count = db.conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    print(f"✓ Total trades in DB: {count}")

    db.close()
    return True

def test_outcome_logging():
    """Test 5: Outcome logging"""
    print("\n" + "="*80)
    print("TEST 5: Outcome Logging")
    print("="*80)

    db_path = 'simulation/test_trade_journal.db'
    db = TradeJournalDB(db_path)

    # First log a decision and trade (needed as foreign keys)
    decision_id = db.log_decision(
        strategy='default',
        crypto='sol',
        epoch=1736971800,
        should_trade=True,
        direction='Up',
        confidence=0.70,
        weighted_score=0.78,
        reason='Test outcome',
        balance_before=100.0
    )

    trade_id = db.log_trade(
        decision_id=decision_id,
        strategy='default',
        crypto='sol',
        epoch=1736971800,
        direction='Up',
        entry_price=0.18,
        size=12.0,
        shares=66.67,
        confidence=0.70,
        weighted_score=0.78
    )

    # Log outcome (WIN)
    outcome_id = db.log_outcome(
        trade_id=trade_id,
        strategy='default',
        crypto='sol',
        epoch=1736971800,
        predicted_direction='Up',
        actual_direction='Up',
        payout=66.67,  # $1.00 per share * 66.67 shares
        pnl=54.67      # payout - size = 66.67 - 12.0
    )

    print(f"✓ Logged outcome with ID: {outcome_id}")

    # Verify outcome was inserted
    result = db.conn.execute("SELECT * FROM outcomes WHERE id=?", (outcome_id,)).fetchone()

    if result:
        print(f"✓ PASS: Outcome found in database")
        print(f"  - Strategy: {result['strategy']}")
        print(f"  - Crypto: {result['crypto']}")
        print(f"  - Predicted: {result['predicted_direction']}")
        print(f"  - Actual: {result['actual_direction']}")
        print(f"  - Payout: ${result['payout']:.2f}")
        print(f"  - P&L: ${result['pnl']:.2f}")
    else:
        print(f"✗ FAIL: Outcome not found in database")
        db.close()
        return False

    # Count outcomes
    count = db.conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0]
    print(f"✓ Total outcomes in DB: {count}")

    db.close()
    return True

def check_live_database():
    """Check the actual live database"""
    print("\n" + "="*80)
    print("LIVE DATABASE CHECK")
    print("="*80)

    db_path = 'simulation/trade_journal.db'

    # Check file size
    if os.path.exists(db_path):
        file_size = os.path.getsize(db_path)
        print(f"✓ Database exists: {db_path}")
        print(f"✓ File size: {file_size} bytes")

        if file_size == 0:
            print(f"⚠ WARNING: Database file is empty (0 bytes)")
            print(f"  This means the database was created but never initialized.")
            print(f"  The TradeJournalDB.__init__() may never have been called.")
            return False
    else:
        print(f"✗ Database does not exist: {db_path}")
        return False

    # Try to connect and check tables
    try:
        db = TradeJournalDB(db_path)
        tables = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [row[0] for row in tables]

        if table_names:
            print(f"✓ Tables found: {table_names}")

            # Count rows in each table
            for table in table_names:
                count = db.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  - {table}: {count} rows")
        else:
            print(f"⚠ WARNING: No tables found in database")
            print(f"  Database connection works but schema was never created.")

        db.close()
        return len(table_names) > 0

    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("\n" + "🔍 SHADOW TRADING DATABASE DIAGNOSTIC")
    print("="*80)

    # Run tests
    tests = [
        ("Database Initialization", test_database_initialization),
        ("Strategy Registration", test_strategy_registration),
        ("Decision Logging", test_decision_logging),
        ("Trade Logging", test_trade_logging),
        ("Outcome Logging", test_outcome_logging),
    ]

    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"✗ FAIL: {name} threw exception: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    # Check live database
    print("\n")
    live_db_ok = check_live_database()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"Test Results: {passed}/{total} tests passed")
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")

    print(f"\nLive Database: {'✓ OK' if live_db_ok else '✗ EMPTY'}")

    if not live_db_ok:
        print("\n" + "🔥 ROOT CAUSE ANALYSIS:")
        print("="*80)
        print("The live database (simulation/trade_journal.db) is empty.")
        print("This suggests one of the following:")
        print("")
        print("1. TradeJournalDB is never being instantiated in the live bot")
        print("2. SimulationOrchestrator is never being created")
        print("3. ENABLE_SHADOW_TRADING is False in config")
        print("4. SHADOW_TRADING_AVAILABLE import is failing silently")
        print("5. The bot is not calling orchestrator.on_market_data()")
        print("")
        print("NEXT STEPS:")
        print("1. Check bot logs for 'SHADOW TRADING INITIALIZED' message")
        print("2. Verify ENABLE_SHADOW_TRADING = True in config/agent_config.py")
        print("3. Add logging to SimulationOrchestrator.__init__()")
        print("4. Check bot logs for any import errors")

    print("="*80)

    # Clean up test database
    test_db_path = 'simulation/test_trade_journal.db'
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
        print(f"\n✓ Cleaned up test database: {test_db_path}")

if __name__ == '__main__':
    main()
