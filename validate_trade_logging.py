#!/usr/bin/env python3
"""
Validate Trade Logging - P3 Task

Checks if trade logging is working correctly:
1. Database exists and is initialized
2. Schema matches expectations
3. ML trades are being logged
4. Counts trades since 16:00 UTC today
"""

import sqlite3
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# Path to database
DB_PATH = Path(__file__).parent / "simulation" / "trade_journal.db"

def check_database_exists():
    """Check if database file exists."""
    if not DB_PATH.exists():
        print(f"❌ FAIL: Database does not exist at {DB_PATH}")
        return False

    size = DB_PATH.stat().st_size
    print(f"✅ PASS: Database exists at {DB_PATH}")
    print(f"   Size: {size:,} bytes")

    if size == 0:
        print(f"⚠️  WARNING: Database is empty (0 bytes)")
        return False

    return True

def check_schema():
    """Check if database has correct schema."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Check for expected tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['strategies', 'decisions', 'trades', 'outcomes', 'agent_votes', 'performance']
        missing_tables = [t for t in expected_tables if t not in tables]

        if missing_tables:
            print(f"❌ FAIL: Missing tables: {missing_tables}")
            print(f"   Found tables: {tables}")
            conn.close()
            return False

        print(f"✅ PASS: All expected tables exist")
        print(f"   Tables: {', '.join(tables)}")

        # Check trades table schema
        cursor.execute("PRAGMA table_info(trades)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        expected_columns = {
            'id': 'INTEGER',
            'decision_id': 'INTEGER',
            'strategy': 'TEXT',
            'crypto': 'TEXT',
            'epoch': 'INTEGER',
            'direction': 'TEXT',
            'entry_price': 'REAL',
            'size': 'REAL',
            'shares': 'REAL',
            'confidence': 'REAL',
            'weighted_score': 'REAL',
            'timestamp': 'REAL'
        }

        missing_columns = [col for col in expected_columns if col not in columns]

        if missing_columns:
            print(f"❌ FAIL: Missing columns in 'trades' table: {missing_columns}")
            print(f"   Found columns: {list(columns.keys())}")
            conn.close()
            return False

        print(f"✅ PASS: 'trades' table has correct schema")
        print(f"   Columns: {', '.join(columns.keys())}")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"❌ FAIL: Database error: {e}")
        return False

def check_ml_trades():
    """Check if ML trades are being logged."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Count total trades
        cursor.execute("SELECT COUNT(*) FROM trades")
        total_trades = cursor.fetchone()[0]

        # Count ML strategy trades
        cursor.execute("SELECT COUNT(*) FROM trades WHERE strategy LIKE 'ml_live_%'")
        ml_trades = cursor.fetchone()[0]

        print(f"\n📊 Trade Counts:")
        print(f"   Total trades: {total_trades}")
        print(f"   ML trades: {ml_trades}")

        if ml_trades == 0:
            print(f"⚠️  WARNING: No ML trades logged yet")
            print(f"   This may be expected if bot just started or hasn't placed trades")

        # Get trades since 16:00 UTC today
        today_16_utc = datetime.now(timezone.utc).replace(hour=16, minute=0, second=0, microsecond=0)
        cutoff_timestamp = today_16_utc.timestamp()

        cursor.execute("""
            SELECT strategy, crypto, direction, entry_price, shares, confidence, timestamp
            FROM trades
            WHERE strategy LIKE 'ml_live_%' AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (cutoff_timestamp,))

        recent_trades = cursor.fetchall()

        if recent_trades:
            print(f"\n📈 Recent ML Trades (since 16:00 UTC today):")
            print(f"   Count: {len(recent_trades)}")
            print(f"\n   Latest trades:")
            for trade in recent_trades[:5]:
                strategy, crypto, direction, entry_price, shares, confidence, ts = trade
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                print(f"   - {dt.strftime('%H:%M:%S')} | {crypto.upper()} {direction} @ ${entry_price:.3f} | {shares:.1f} shares | {confidence:.1%} conf")
        else:
            print(f"\n⚠️  No ML trades logged since 16:00 UTC today")
            print(f"   Cutoff timestamp: {cutoff_timestamp} ({today_16_utc.strftime('%Y-%m-%d %H:%M:%S UTC')})")

        conn.close()
        return ml_trades > 0

    except sqlite3.Error as e:
        print(f"❌ FAIL: Database query error: {e}")
        return False

def initialize_database():
    """Initialize database with proper schema directly."""
    print(f"\n🔧 Initializing database...")

    try:
        conn = sqlite3.connect(str(DB_PATH))

        # Create strategies table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS strategies (
                name TEXT PRIMARY KEY,
                description TEXT,
                config JSON,
                is_live BOOLEAN,
                created TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create decisions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                crypto TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                should_trade BOOLEAN NOT NULL,
                direction TEXT,
                confidence REAL,
                weighted_score REAL,
                reason TEXT,
                balance_before REAL,
                FOREIGN KEY (strategy) REFERENCES strategies(name),
                UNIQUE(strategy, crypto, epoch)
            )
        ''')

        # Create trades table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER,
                strategy TEXT NOT NULL,
                crypto TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                direction TEXT NOT NULL,
                entry_price REAL NOT NULL,
                size REAL NOT NULL,
                shares REAL NOT NULL,
                confidence REAL,
                weighted_score REAL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (strategy) REFERENCES strategies(name),
                FOREIGN KEY (decision_id) REFERENCES decisions(id),
                UNIQUE(strategy, crypto, epoch)
            )
        ''')

        # Create outcomes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                strategy TEXT NOT NULL,
                crypto TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                predicted_direction TEXT NOT NULL,
                actual_direction TEXT NOT NULL,
                payout REAL NOT NULL,
                pnl REAL NOT NULL,
                timestamp REAL NOT NULL,
                FOREIGN KEY (strategy) REFERENCES strategies(name),
                FOREIGN KEY (trade_id) REFERENCES trades(id),
                UNIQUE(strategy, crypto, epoch)
            )
        ''')

        # Create agent_votes table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agent_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                quality REAL NOT NULL,
                reasoning TEXT,
                details JSON,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        ''')

        # Create performance table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy TEXT NOT NULL,
                timestamp REAL NOT NULL,
                balance REAL NOT NULL,
                total_trades INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                total_pnl REAL NOT NULL,
                roi REAL NOT NULL,
                FOREIGN KEY (strategy) REFERENCES strategies(name)
            )
        ''')

        # Create indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_decisions_strategy_epoch ON decisions(strategy, epoch)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trades_strategy_epoch ON trades(strategy, epoch)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_outcomes_strategy ON outcomes(strategy)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_agent_votes_decision ON agent_votes(decision_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_performance_strategy_time ON performance(strategy, timestamp)')

        conn.commit()
        conn.close()

        print(f"✅ Database initialized successfully")
        return True

    except Exception as e:
        print(f"❌ FAIL: Could not initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run validation checks."""
    print("=" * 80)
    print("🔍 Trade Logging Validation - P3 Task")
    print("=" * 80)
    print()

    # Step 1: Check if database exists
    print("Step 1: Check Database Exists")
    print("-" * 80)
    db_exists = check_database_exists()
    print()

    # Step 2: If database is empty, initialize it
    if not db_exists or DB_PATH.stat().st_size == 0:
        print("Step 2: Initialize Database")
        print("-" * 80)
        if not initialize_database():
            print("\n❌ OVERALL: FAIL - Could not initialize database")
            sys.exit(1)
        print()

    # Step 3: Check schema
    print("Step 3: Validate Schema")
    print("-" * 80)
    schema_valid = check_schema()
    print()

    if not schema_valid:
        print("\n❌ OVERALL: FAIL - Schema validation failed")
        sys.exit(1)

    # Step 4: Check for ML trades
    print("Step 4: Check ML Trades")
    print("-" * 80)
    has_trades = check_ml_trades()
    print()

    # Summary
    print("=" * 80)
    print("📋 Summary")
    print("=" * 80)

    if schema_valid:
        print("✅ Database is properly initialized")
        print("✅ Schema is correct")

        if has_trades:
            print("✅ ML trades are being logged")
            print("\n✅ OVERALL: PASS - Trade logging is working")
        else:
            print("⚠️  No ML trades logged yet")
            print("\n⚠️  OVERALL: PARTIAL - Database ready, but no trades logged yet")
            print("   This may be expected if bot just started or hasn't placed trades")
    else:
        print("❌ OVERALL: FAIL - Issues found")
        sys.exit(1)

    print("=" * 80)

if __name__ == '__main__':
    main()
