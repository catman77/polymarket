#!/usr/bin/env python3
"""
Agent Performance Tracker

Analyzes individual agent performance by matching their votes to trade outcomes.
Identifies which agents contribute positively vs negatively to overall win rate.
"""

import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

class AgentPerformanceTracker:
    def __init__(self, db_path: str = "simulation/trade_journal.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def update_agent_outcomes(self):
        """
        Match agent votes to outcomes and update agent_votes_outcomes table.
        Called after new outcomes are resolved.
        """
        # Get all outcomes that haven't been matched to agent votes yet
        self.cursor.execute('''
            SELECT o.id, o.trade_id, o.pnl
            FROM outcomes o
            WHERE o.id NOT IN (SELECT outcome_id FROM agent_votes_outcomes WHERE outcome_id IS NOT NULL)
        ''')

        new_outcomes = self.cursor.fetchall()

        for outcome_id, trade_id, pnl in new_outcomes:
            # Get the decision_id for this trade
            self.cursor.execute('''
                SELECT decision_id FROM trades WHERE id = ?
            ''', (trade_id,))

            trade_result = self.cursor.fetchone()
            if not trade_result:
                continue

            decision_id = trade_result[0]

            # Get all agent votes for this decision
            self.cursor.execute('''
                SELECT av.id, av.agent_name, av.direction
                FROM agent_votes av
                WHERE av.decision_id = ?
            ''', (decision_id,))

            agent_votes = self.cursor.fetchall()

            # Determine if the trade won or lost
            was_winner = pnl > 0

            for vote_id, agent, direction in agent_votes:
                # Agent is correct if the trade won (agent voted for winning direction)
                was_correct = was_winner

                # Insert into agent_votes_outcomes
                self.cursor.execute('''
                    INSERT INTO agent_votes_outcomes (agent_vote_id, outcome_id, was_correct)
                    VALUES (?, ?, ?)
                ''', (vote_id, outcome_id, was_correct))

        self.conn.commit()

    def calculate_agent_performance(self) -> Dict[str, Dict]:
        """
        Calculate performance metrics for each agent.
        Returns dict: {agent_name: {total_votes, correct_votes, win_rate, avg_confidence}}
        """
        # Update outcomes first
        self.update_agent_outcomes()

        # Calculate per-agent metrics
        self.cursor.execute('''
            SELECT
                av.agent_name,
                COUNT(*) as total_votes,
                SUM(CASE WHEN avo.was_correct THEN 1 ELSE 0 END) as correct_votes,
                AVG(av.confidence) as avg_confidence
            FROM agent_votes av
            JOIN agent_votes_outcomes avo ON av.id = avo.agent_vote_id
            GROUP BY av.agent_name
        ''')

        results = {}
        for agent, total, correct, avg_conf in self.cursor.fetchall():
            win_rate = (correct / total * 100) if total > 0 else 0.0
            results[agent] = {
                'total_votes': total,
                'correct_votes': correct,
                'incorrect_votes': total - correct,
                'win_rate': win_rate,
                'avg_confidence': avg_conf or 0.0
            }

        return results

    def update_agent_performance_table(self):
        """
        Update the agent_performance table with latest metrics.
        """
        performance = self.calculate_agent_performance()

        for agent, metrics in performance.items():
            self.cursor.execute('''
                INSERT OR REPLACE INTO agent_performance
                (agent_name, total_votes, correct_votes, incorrect_votes, win_rate, avg_confidence, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent,
                metrics['total_votes'],
                metrics['correct_votes'],
                metrics['incorrect_votes'],
                metrics['win_rate'],
                metrics['avg_confidence'],
                datetime.now().isoformat()
            ))

        self.conn.commit()

    def get_underperforming_agents(self, threshold: float = 50.0, min_votes: int = 20) -> List[str]:
        """
        Identify agents with win rate below threshold and sufficient votes.

        Args:
            threshold: Win rate threshold (default: 50%)
            min_votes: Minimum votes required for evaluation (default: 20)

        Returns:
            List of underperforming agent names
        """
        self.update_agent_performance_table()

        self.cursor.execute('''
            SELECT agent_name, win_rate, total_votes
            FROM agent_performance
            WHERE win_rate < ? AND total_votes >= ?
            ORDER BY win_rate ASC
        ''', (threshold, min_votes))

        return [row[0] for row in self.cursor.fetchall()]

    def print_agent_report(self):
        """
        Print a formatted report of agent performance.
        """
        self.update_agent_performance_table()

        self.cursor.execute('''
            SELECT agent_name, total_votes, correct_votes, win_rate, avg_confidence
            FROM agent_performance
            ORDER BY win_rate DESC
        ''')

        print("=" * 80)
        print("AGENT PERFORMANCE REPORT")
        print("=" * 80)
        print(f"{'Agent':<20} {'Votes':>6} {'Correct':>8} {'Win Rate':>10} {'Avg Conf':>10}")
        print("-" * 80)

        for agent, total, correct, win_rate, avg_conf in self.cursor.fetchall():
            status = "🟢" if win_rate >= 55 else "🟡" if win_rate >= 50 else "🔴"
            print(f"{agent:<20} {total:>6} {correct:>8} {win_rate:>9.1f}% {avg_conf:>9.2f} {status}")

        print("=" * 80)

    def close(self):
        self.conn.close()


if __name__ == "__main__":
    tracker = AgentPerformanceTracker()
    tracker.print_agent_report()

    underperformers = tracker.get_underperforming_agents(threshold=50.0, min_votes=20)
    if underperformers:
        print(f"\n🔴 Underperforming agents (<50% win rate, 20+ votes):")
        for agent in underperformers:
            print(f"  - {agent}")
    else:
        print("\n✅ No underperforming agents identified")

    tracker.close()
