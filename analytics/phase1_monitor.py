#!/usr/bin/env python3
"""
Phase 1 Agent Performance Monitor

Tracks OrderBookAgent and FundingRateAgent performance to validate
they meet success criteria (50+ trades, +3-5% win rate improvement).
"""

import sys
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

sys.path.append(str(Path(__file__).parent.parent))

from config import agent_config


@dataclass
class AgentPerformance:
    """Performance metrics for a single agent."""
    agent_name: str
    total_votes: int
    avg_confidence: float
    avg_quality: float
    votes_up: int
    votes_down: int
    correct_predictions: int
    incorrect_predictions: int
    pending_predictions: int
    win_rate: float
    impact_score: float  # How much this agent contributed to wins


class Phase1Monitor:
    """Monitor for Phase 1 agents (OrderBook and FundingRate)."""

    PHASE1_AGENTS = ['OrderBookAgent', 'FundingRateAgent']
    MIN_TRADES_TARGET = 50

    def __init__(self, db_path: str):
        """
        Initialize monitor.

        Args:
            db_path: Path to SQLite trade journal database
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_agent_vote_count(self, agent_name: str) -> int:
        """
        Get total number of votes cast by agent.

        Args:
            agent_name: Name of agent

        Returns:
            Total vote count
        """
        cursor = self.conn.execute(
            'SELECT COUNT(*) as count FROM agent_votes WHERE agent_name = ?',
            (agent_name,)
        )
        return cursor.fetchone()['count']

    def get_agent_performance(self, agent_name: str) -> AgentPerformance:
        """
        Calculate comprehensive performance metrics for an agent.

        Args:
            agent_name: Name of agent

        Returns:
            AgentPerformance dataclass
        """
        # Get all votes for this agent
        cursor = self.conn.execute('''
            SELECT
                agent_name,
                direction,
                confidence,
                quality,
                decision_id
            FROM agent_votes
            WHERE agent_name = ?
        ''', (agent_name,))

        votes = cursor.fetchall()

        if not votes:
            return AgentPerformance(
                agent_name=agent_name,
                total_votes=0,
                avg_confidence=0.0,
                avg_quality=0.0,
                votes_up=0,
                votes_down=0,
                correct_predictions=0,
                incorrect_predictions=0,
                pending_predictions=0,
                win_rate=0.0,
                impact_score=0.0
            )

        # Basic stats
        total_votes = len(votes)
        votes_up = sum(1 for v in votes if v['direction'] == 'Up')
        votes_down = sum(1 for v in votes if v['direction'] == 'Down')
        avg_confidence = sum(v['confidence'] for v in votes) / total_votes
        avg_quality = sum(v['quality'] for v in votes) / total_votes

        # Calculate correctness by joining with outcomes
        cursor = self.conn.execute('''
            SELECT
                av.direction as predicted,
                o.actual_direction as actual,
                o.pnl,
                av.confidence
            FROM agent_votes av
            JOIN decisions d ON av.decision_id = d.id
            JOIN trades t ON d.id = t.decision_id
            JOIN outcomes o ON t.id = o.trade_id
            WHERE av.agent_name = ?
        ''', (agent_name,))

        outcomes = cursor.fetchall()

        correct = 0
        incorrect = 0
        total_impact = 0.0

        for outcome in outcomes:
            if outcome['predicted'] == outcome['actual']:
                correct += 1
                # Weight impact by confidence (high confidence correct = high impact)
                total_impact += outcome['confidence']
            else:
                incorrect += 1
                # Penalize impact for confident wrong predictions
                total_impact -= outcome['confidence'] * 0.5

        resolved = correct + incorrect
        pending = total_votes - resolved
        win_rate = correct / resolved if resolved > 0 else 0.0
        impact_score = total_impact / resolved if resolved > 0 else 0.0

        return AgentPerformance(
            agent_name=agent_name,
            total_votes=total_votes,
            avg_confidence=avg_confidence,
            avg_quality=avg_quality,
            votes_up=votes_up,
            votes_down=votes_down,
            correct_predictions=correct,
            incorrect_predictions=incorrect,
            pending_predictions=pending,
            win_rate=win_rate,
            impact_score=impact_score
        )

    def get_baseline_performance(self) -> Dict[str, float]:
        """
        Get baseline performance from strategies without Phase 1 agents.

        Returns:
            Dict with baseline win_rate and avg_pnl
        """
        # Strategies without Phase 1 agents (legacy strategies)
        baseline_strategies = ['default', 'conservative', 'aggressive']

        total_wins = 0
        total_losses = 0
        total_pnl = 0.0

        for strategy in baseline_strategies:
            cursor = self.conn.execute('''
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl
                FROM outcomes
                WHERE strategy = ?
            ''', (strategy,))

            row = cursor.fetchone()
            if row and row['total_trades'] > 0:
                total_wins += row['wins'] or 0
                total_losses += row['losses'] or 0
                total_pnl += row['total_pnl'] or 0.0

        total_trades = total_wins + total_losses
        baseline_win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        baseline_avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

        return {
            'win_rate': baseline_win_rate,
            'avg_pnl': baseline_avg_pnl,
            'total_trades': total_trades
        }

    def get_phase1_strategy_performance(self) -> Dict[str, float]:
        """
        Get performance from strategies WITH Phase 1 agents.

        Returns:
            Dict with phase1 win_rate and avg_pnl
        """
        # Strategies with Phase 1 agents
        phase1_strategies = [
            'orderbook_focused',
            'funding_rate_focused',
            'phase1_combo',
            'orderbook_only',
            'funding_rate_only',
            'phase1_only'
        ]

        total_wins = 0
        total_losses = 0
        total_pnl = 0.0

        for strategy in phase1_strategies:
            cursor = self.conn.execute('''
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl
                FROM outcomes
                WHERE strategy = ?
            ''', (strategy,))

            row = cursor.fetchone()
            if row and row['total_trades'] > 0:
                total_wins += row['wins'] or 0
                total_losses += row['losses'] or 0
                total_pnl += row['total_pnl'] or 0.0

        total_trades = total_wins + total_losses
        phase1_win_rate = total_wins / total_trades if total_trades > 0 else 0.0
        phase1_avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0

        return {
            'win_rate': phase1_win_rate,
            'avg_pnl': phase1_avg_pnl,
            'total_trades': total_trades
        }

    def print_summary(self):
        """Print monitoring summary for Phase 1 agents."""
        print("=" * 100)
        print(" " * 35 + "PHASE 1 AGENT MONITOR")
        print(" " * 25 + "OrderBookAgent + FundingRateAgent Performance")
        print("=" * 100)
        print()

        # Individual agent performance
        print("Agent Performance:")
        print("-" * 100)
        print(f"{'Agent':<20} {'Votes':<8} {'Conf':<8} {'Quality':<8} {'Up/Down':<12} {'Resolved':<12} {'Win Rate':<10} {'Impact':<10}")
        print("-" * 100)

        for agent_name in self.PHASE1_AGENTS:
            perf = self.get_agent_performance(agent_name)

            up_down = f"{perf.votes_up}/{perf.votes_down}"
            resolved = f"{perf.correct_predictions + perf.incorrect_predictions} ({perf.pending_predictions}p)"

            # Status indicators
            vote_status = "✅" if perf.total_votes >= self.MIN_TRADES_TARGET else f"⏳ {perf.total_votes}/{self.MIN_TRADES_TARGET}"
            win_status = "✅" if perf.win_rate >= 0.60 else "⚠️" if perf.win_rate >= 0.50 else "🔴"

            print(f"{agent_name:<20} {vote_status:<8} {perf.avg_confidence*100:<7.1f}% {perf.avg_quality*100:<7.1f}% {up_down:<12} {resolved:<12} {win_status} {perf.win_rate*100:<8.1f}% {perf.impact_score:+9.2f}")

        print()

        # Baseline vs Phase 1 comparison
        baseline = self.get_baseline_performance()
        phase1 = self.get_phase1_strategy_performance()

        if baseline['total_trades'] > 0 and phase1['total_trades'] > 0:
            print("Strategy Comparison (Baseline vs Phase 1):")
            print("-" * 100)
            print(f"{'Strategy Type':<25} {'Trades':<10} {'Win Rate':<15} {'Avg P&L':<15} {'Improvement':<15}")
            print("-" * 100)

            win_rate_diff = (phase1['win_rate'] - baseline['win_rate']) * 100
            pnl_diff = phase1['avg_pnl'] - baseline['avg_pnl']

            print(f"{'Baseline (no Phase 1)':<25} {baseline['total_trades']:<10} {baseline['win_rate']*100:<14.1f}% ${baseline['avg_pnl']:<14.2f} {'--':<15}")

            improvement_status = "🟢" if win_rate_diff >= 3 else "⚠️" if win_rate_diff >= 1 else "🔴"
            print(f"{'Phase 1 Strategies':<25} {phase1['total_trades']:<10} {phase1['win_rate']*100:<14.1f}% ${phase1['avg_pnl']:<14.2f} {improvement_status} {win_rate_diff:+.1f}% WR")

            print()
            print(f"Win Rate Improvement: {win_rate_diff:+.1f}% (target: +3-5%)")
            print(f"P&L Improvement: ${pnl_diff:+.2f} per trade")
            print()
        else:
            print("⚠️  Insufficient data for baseline comparison")
            print(f"   Baseline trades: {baseline['total_trades']}")
            print(f"   Phase 1 trades: {phase1['total_trades']}")
            print()

        # Success criteria check
        print("Success Criteria:")
        print("-" * 100)

        orderbook_perf = self.get_agent_performance('OrderBookAgent')
        funding_perf = self.get_agent_performance('FundingRateAgent')

        # Criterion 1: 50+ trades each
        trades_met = orderbook_perf.total_votes >= self.MIN_TRADES_TARGET and funding_perf.total_votes >= self.MIN_TRADES_TARGET
        trades_status = "✅" if trades_met else "⏳"
        print(f"{trades_status} Both agents have 50+ votes (OrderBook: {orderbook_perf.total_votes}, FundingRate: {funding_perf.total_votes})")

        # Criterion 2: Win rate improvement
        if phase1['total_trades'] > 0 and baseline['total_trades'] > 0:
            improvement_met = win_rate_diff >= 3.0
            improvement_status = "✅" if improvement_met else "⏳" if win_rate_diff >= 1.0 else "🔴"
            print(f"{improvement_status} Win rate improvement +3-5% (actual: {win_rate_diff:+.1f}%)")
        else:
            print(f"⏳ Win rate improvement pending (need more trades)")

        # Criterion 3: Agents returning valid votes
        valid_votes = orderbook_perf.total_votes > 0 and funding_perf.total_votes > 0
        valid_status = "✅" if valid_votes else "🔴"
        print(f"{valid_status} All agents returning valid votes")

        # Criterion 4: No performance degradation
        if phase1['total_trades'] > 10:
            no_degradation = phase1['win_rate'] >= 0.45  # Minimum acceptable
            degradation_status = "✅" if no_degradation else "🔴"
            print(f"{degradation_status} No performance degradation (win rate {phase1['win_rate']*100:.1f}% >= 45%)")
        else:
            print(f"⏳ Performance check pending (only {phase1['total_trades']} trades)")

        print()
        print("=" * 100)

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Phase 1 Agent Performance Monitor')
    parser.add_argument('--db', type=str, default=None,
                       help=f'Path to SQLite database (default: {agent_config.SHADOW_DB_PATH})')

    args = parser.parse_args()

    db_path = args.db if args.db else agent_config.SHADOW_DB_PATH

    monitor = Phase1Monitor(db_path)

    try:
        monitor.print_summary()
    finally:
        monitor.close()


if __name__ == '__main__':
    main()
