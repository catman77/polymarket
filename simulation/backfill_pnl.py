#!/usr/bin/env python3
"""
Backfill pnl and payout for existing outcomes that have 0.0 values.
Run this once after deploying the orchestrator fix.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from simulation.trade_journal import TradeJournalDB

db = TradeJournalDB('simulation/trade_journal.db')

# Get all outcomes with pnl=0
broken_outcomes = db.conn.execute('''
    SELECT id, strategy, crypto, epoch, predicted_direction, actual_direction
    FROM outcomes
    WHERE pnl = 0.0
''').fetchall()

print(f"Found {len(broken_outcomes)} outcomes to fix")

for outcome in broken_outcomes:
    outcome_id, strategy, crypto, epoch, pred, actual = outcome

    # Get the original trade to find position size
    trade = db.conn.execute('''
        SELECT size, shares FROM trades
        WHERE strategy=? AND crypto=? AND epoch=?
    ''', (strategy, crypto, epoch)).fetchone()

    if not trade:
        print(f"⚠️  No trade found for {strategy} {crypto} {epoch}")
        continue

    size, shares = trade

    # Recalculate payout and pnl
    if pred == actual:
        # Win
        payout = shares * 1.0
        pnl = payout - size
    else:
        # Loss
        payout = 0.0
        pnl = -size

    # Update outcome
    db.conn.execute('''
        UPDATE outcomes
        SET pnl = ?, payout = ?
        WHERE id = ?
    ''', (pnl, payout, outcome_id))

    result = "WIN" if pred == actual else "LOSS"
    print(f"✅ Fixed {strategy} {crypto} epoch {epoch} ({result}): payout=${payout:.2f}, pnl=${pnl:+.2f}")

db.conn.commit()
print(f"\nBackfill complete! Fixed {len(broken_outcomes)} outcomes.")
