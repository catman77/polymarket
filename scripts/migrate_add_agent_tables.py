#!/usr/bin/env python3
"""
Database migration to add agent performance tracking tables.

Adds:
- agent_performance: Tracks win rates per agent
- agent_votes_outcomes: Links agent votes to trade outcomes

These tables were defined in schema but not created in existing databases.
"""

import sqlite3
import os
import sys


def migrate_database(db_path: str):
    """Add agent performance tables to existing database"""

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_performance'")
    if cursor.fetchone():
        print("✓ agent_performance table already exists")
    else:
        print("Creating agent_performance table...")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agent_performance (
                agent_name TEXT PRIMARY KEY,
                total_votes INTEGER DEFAULT 0,
                correct_votes INTEGER DEFAULT 0,
                incorrect_votes INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                avg_confidence REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✓ agent_performance table created")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_votes_outcomes'")
    if cursor.fetchone():
        print("✓ agent_votes_outcomes table already exists")
    else:
        print("Creating agent_votes_outcomes table...")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS agent_votes_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_vote_id INTEGER NOT NULL,
                outcome_id INTEGER NOT NULL,
                was_correct BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_vote_id) REFERENCES agent_votes(id),
                FOREIGN KEY (outcome_id) REFERENCES outcomes(id)
            )
        ''')
        print("✓ agent_votes_outcomes table created")

    conn.commit()
    conn.close()

    print("\nMigration complete!")


if __name__ == "__main__":
    # Detect environment
    if os.path.exists("/opt/polymarket-autotrader/simulation/trade_journal.db"):
        db_path = "/opt/polymarket-autotrader/simulation/trade_journal.db"
    elif os.path.exists("simulation/trade_journal.db"):
        db_path = "simulation/trade_journal.db"
    else:
        print("Error: Cannot find trade_journal.db")
        sys.exit(1)

    migrate_database(db_path)
