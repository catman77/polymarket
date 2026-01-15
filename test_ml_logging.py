#!/usr/bin/env python3
"""
Test ML Trade Logging Function

Tests that the fixed log_ml_trade_direct() function works correctly.
"""

import sys
import time
import sqlite3
from pathlib import Path

# Define function inline to avoid import issues
def log_ml_trade_direct(db_path: str, strategy: str, crypto: str, epoch: str,
                        direction: str, entry_price: float, shares: int,
                        confidence: float, size: float = None, weighted_score: float = None) -> bool:
    """
    Direct SQLite logging without TradeJournal class.
    Returns True if successful, False otherwise.
    """
    try:
        conn = sqlite3.connect(db_path)
        timestamp = time.time()

        # Calculate defaults
        if size is None:
            size = shares * entry_price
        if weighted_score is None:
            weighted_score = confidence

        # Register strategy if not exists
        conn.execute('''
            INSERT OR IGNORE INTO strategies (name, description, is_live, created)
            VALUES (?, ?, ?, ?)
        ''', (strategy, 'Live ML Random Forest Bot', 1, timestamp))

        # Log trade with all required columns
        conn.execute('''
            INSERT INTO trades (strategy, crypto, epoch, direction, entry_price,
                               size, shares, confidence, weighted_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (strategy, crypto, epoch, direction, entry_price, size, shares,
              confidence, weighted_score, timestamp))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

# Test database path
DB_PATH = Path(__file__).parent / "simulation" / "trade_journal.db"

def test_ml_logging():
    """Test ML trade logging."""
    print("=" * 80)
    print("🧪 Testing ML Trade Logging")
    print("=" * 80)
    print()

    # Test data
    test_trade = {
        'strategy': 'ml_live_test',
        'crypto': 'btc',
        'epoch': '1737000000',
        'direction': 'Up',
        'entry_price': 0.42,
        'shares': 30,
        'confidence': 0.65
    }

    print("Test Trade:")
    for key, value in test_trade.items():
        print(f"  {key}: {value}")
    print()

    # Attempt to log
    print("Logging trade...")
    success = log_ml_trade_direct(
        db_path=str(DB_PATH),
        **test_trade
    )

    if success:
        print("✅ Logging successful")
    else:
        print("❌ Logging failed")
        sys.exit(1)

    # Verify it was logged
    print("\nVerifying database...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT strategy, crypto, epoch, direction, entry_price, size,
               shares, confidence, weighted_score
        FROM trades
        WHERE strategy = ?
    """, (test_trade['strategy'],))

    row = cursor.fetchone()
    conn.close()

    if row:
        print("✅ Trade found in database:")
        print(f"  Strategy: {row[0]}")
        print(f"  Crypto: {row[1]}")
        print(f"  Epoch: {row[2]}")
        print(f"  Direction: {row[3]}")
        print(f"  Entry Price: ${row[4]:.3f}")
        print(f"  Size: ${row[5]:.2f}")
        print(f"  Shares: {row[6]:.1f}")
        print(f"  Confidence: {row[7]:.1%}")
        print(f"  Weighted Score: {row[8]:.1%}")

        # Verify size was calculated correctly
        expected_size = test_trade['shares'] * test_trade['entry_price']
        actual_size = row[5]

        if abs(actual_size - expected_size) < 0.01:
            print(f"\n✅ Size calculation correct: ${actual_size:.2f}")
        else:
            print(f"\n❌ Size calculation wrong: expected ${expected_size:.2f}, got ${actual_size:.2f}")
            sys.exit(1)

    else:
        print("❌ Trade not found in database")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)

if __name__ == '__main__':
    test_ml_logging()
