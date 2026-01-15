#!/usr/bin/env python3
"""
Tests for Phase 1 Agent Monitor
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from analytics.phase1_monitor import Phase1Monitor, AgentPerformance


class TestPhase1Monitor(unittest.TestCase):
    """Test Phase1Monitor class."""

    def setUp(self):
        """Create temporary database with test data."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        self.conn = sqlite3.connect(self.db_path)

        # Create minimal schema
        self.conn.execute('''
            CREATE TABLE strategies (
                name TEXT PRIMARY KEY,
                description TEXT,
                config JSON,
                is_live BOOLEAN,
                created TIMESTAMP,
                last_updated TIMESTAMP
            )
        ''')

        self.conn.execute('''
            CREATE TABLE decisions (
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
                balance_before REAL
            )
        ''')

        self.conn.execute('''
            CREATE TABLE trades (
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
                timestamp REAL NOT NULL
            )
        ''')

        self.conn.execute('''
            CREATE TABLE outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER,
                strategy TEXT NOT NULL,
                crypto TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                predicted_direction TEXT NOT NULL,
                actual_direction TEXT NOT NULL,
                payout REAL NOT NULL,
                pnl REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        ''')

        self.conn.execute('''
            CREATE TABLE agent_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                confidence REAL NOT NULL,
                quality REAL NOT NULL,
                reasoning TEXT,
                details JSON
            )
        ''')

        self.conn.commit()

    def tearDown(self):
        """Clean up temporary database."""
        self.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_init(self):
        """Test monitor initialization."""
        monitor = Phase1Monitor(self.db_path)
        self.assertEqual(monitor.db_path, self.db_path)
        self.assertIsNotNone(monitor.conn)
        monitor.close()

    def test_get_agent_vote_count_empty(self):
        """Test vote count with no votes."""
        monitor = Phase1Monitor(self.db_path)
        count = monitor.get_agent_vote_count('OrderBookAgent')
        self.assertEqual(count, 0)
        monitor.close()

    def test_get_agent_vote_count_with_votes(self):
        """Test vote count with votes."""
        # Insert test decision
        cursor = self.conn.execute(
            'INSERT INTO decisions (strategy, crypto, epoch, timestamp, should_trade, direction, confidence, weighted_score) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            ('default', 'BTC', 1000, 1.0, True, 'Up', 0.6, 0.5)
        )
        decision_id = cursor.lastrowid

        # Insert test votes
        self.conn.execute(
            'INSERT INTO agent_votes (decision_id, agent_name, direction, confidence, quality) '
            'VALUES (?, ?, ?, ?, ?)',
            (decision_id, 'OrderBookAgent', 'Up', 0.65, 0.80)
        )
        self.conn.execute(
            'INSERT INTO agent_votes (decision_id, agent_name, direction, confidence, quality) '
            'VALUES (?, ?, ?, ?, ?)',
            (decision_id, 'OrderBookAgent', 'Down', 0.55, 0.70)
        )
        self.conn.commit()

        monitor = Phase1Monitor(self.db_path)
        count = monitor.get_agent_vote_count('OrderBookAgent')
        self.assertEqual(count, 2)
        monitor.close()

    def test_get_agent_performance_no_votes(self):
        """Test performance calculation with no votes."""
        monitor = Phase1Monitor(self.db_path)
        perf = monitor.get_agent_performance('OrderBookAgent')

        self.assertEqual(perf.agent_name, 'OrderBookAgent')
        self.assertEqual(perf.total_votes, 0)
        self.assertEqual(perf.avg_confidence, 0.0)
        self.assertEqual(perf.win_rate, 0.0)

        monitor.close()

    def test_get_agent_performance_with_votes(self):
        """Test performance calculation with votes but no outcomes."""
        # Insert test decision
        cursor = self.conn.execute(
            'INSERT INTO decisions (strategy, crypto, epoch, timestamp, should_trade, direction, confidence, weighted_score) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            ('default', 'BTC', 1000, 1.0, True, 'Up', 0.6, 0.5)
        )
        decision_id = cursor.lastrowid

        # Insert test votes
        self.conn.execute(
            'INSERT INTO agent_votes (decision_id, agent_name, direction, confidence, quality) '
            'VALUES (?, ?, ?, ?, ?)',
            (decision_id, 'FundingRateAgent', 'Up', 0.70, 0.85)
        )
        self.conn.execute(
            'INSERT INTO agent_votes (decision_id, agent_name, direction, confidence, quality) '
            'VALUES (?, ?, ?, ?, ?)',
            (decision_id, 'FundingRateAgent', 'Down', 0.50, 0.60)
        )
        self.conn.commit()

        monitor = Phase1Monitor(self.db_path)
        perf = monitor.get_agent_performance('FundingRateAgent')

        self.assertEqual(perf.agent_name, 'FundingRateAgent')
        self.assertEqual(perf.total_votes, 2)
        self.assertEqual(perf.votes_up, 1)
        self.assertEqual(perf.votes_down, 1)
        self.assertAlmostEqual(perf.avg_confidence, 0.60, places=2)
        self.assertAlmostEqual(perf.avg_quality, 0.725, places=2)
        self.assertEqual(perf.pending_predictions, 2)  # No outcomes yet

        monitor.close()

    def test_get_agent_performance_with_outcomes(self):
        """Test performance calculation with resolved outcomes."""
        # Insert test decision
        cursor = self.conn.execute(
            'INSERT INTO decisions (strategy, crypto, epoch, timestamp, should_trade, direction, confidence, weighted_score) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            ('default', 'BTC', 1000, 1.0, True, 'Up', 0.6, 0.5)
        )
        decision_id = cursor.lastrowid

        # Insert test trade
        cursor = self.conn.execute(
            'INSERT INTO trades (decision_id, strategy, crypto, epoch, direction, entry_price, size, shares, timestamp) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (decision_id, 'default', 'BTC', 1000, 'Up', 0.50, 10.0, 10.0, 1.0)
        )
        trade_id = cursor.lastrowid

        # Insert test outcome (win)
        self.conn.execute(
            'INSERT INTO outcomes (trade_id, strategy, crypto, epoch, predicted_direction, actual_direction, payout, pnl, timestamp) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (trade_id, 'default', 'BTC', 1000, 'Up', 'Up', 10.0, 5.0, 2.0)
        )

        # Insert agent vote
        self.conn.execute(
            'INSERT INTO agent_votes (decision_id, agent_name, direction, confidence, quality) '
            'VALUES (?, ?, ?, ?, ?)',
            (decision_id, 'OrderBookAgent', 'Up', 0.75, 0.90)
        )

        self.conn.commit()

        monitor = Phase1Monitor(self.db_path)
        perf = monitor.get_agent_performance('OrderBookAgent')

        self.assertEqual(perf.total_votes, 1)
        self.assertEqual(perf.correct_predictions, 1)
        self.assertEqual(perf.incorrect_predictions, 0)
        self.assertEqual(perf.win_rate, 1.0)
        self.assertGreater(perf.impact_score, 0.0)  # Positive impact from correct prediction

        monitor.close()

    def test_get_baseline_performance_empty(self):
        """Test baseline performance with no data."""
        monitor = Phase1Monitor(self.db_path)
        baseline = monitor.get_baseline_performance()

        self.assertEqual(baseline['total_trades'], 0)
        self.assertEqual(baseline['win_rate'], 0.0)
        self.assertEqual(baseline['avg_pnl'], 0.0)

        monitor.close()

    def test_get_phase1_strategy_performance_empty(self):
        """Test Phase 1 strategy performance with no data."""
        monitor = Phase1Monitor(self.db_path)
        phase1 = monitor.get_phase1_strategy_performance()

        self.assertEqual(phase1['total_trades'], 0)
        self.assertEqual(phase1['win_rate'], 0.0)
        self.assertEqual(phase1['avg_pnl'], 0.0)

        monitor.close()

    def test_print_summary_no_crash(self):
        """Test that print_summary doesn't crash with empty database."""
        monitor = Phase1Monitor(self.db_path)

        # Should not raise exception
        try:
            monitor.print_summary()
        except Exception as e:
            self.fail(f"print_summary raised exception: {e}")

        monitor.close()


if __name__ == '__main__':
    unittest.main()
