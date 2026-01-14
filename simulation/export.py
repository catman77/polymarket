#!/usr/bin/env python3
"""
Shadow Trading Export Tool

Export shadow trading data to CSV for external analysis.
"""

import sys
import csv
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from simulation.trade_journal import TradeJournalDB
from config import agent_config


def export_decisions(db: TradeJournalDB, output_file: str, strategy: Optional[str] = None):
    """
    Export decisions to CSV.

    Args:
        db: TradeJournalDB instance
        output_file: Output CSV file path
        strategy: Optional strategy filter
    """
    decisions = db.query_decisions(strategy=strategy, limit=10000)

    if not decisions:
        print("No decisions to export.")
        return

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['id', 'strategy', 'crypto', 'epoch', 'timestamp', 'should_trade',
                     'direction', 'confidence', 'weighted_score', 'reason', 'balance_before']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for dec in decisions:
            writer.writerow({
                'id': dec['id'],
                'strategy': dec['strategy'],
                'crypto': dec['crypto'],
                'epoch': dec['epoch'],
                'timestamp': dec['timestamp'],
                'should_trade': dec['should_trade'],
                'direction': dec['direction'] or '',
                'confidence': dec['confidence'],
                'weighted_score': dec['weighted_score'],
                'reason': dec['reason'] or '',
                'balance_before': dec['balance_before']
            })

    print(f"Exported {len(decisions)} decisions to {output_file}")


def export_trades(db: TradeJournalDB, output_file: str, strategy: Optional[str] = None):
    """
    Export trades to CSV.

    Args:
        db: TradeJournalDB instance
        output_file: Output CSV file path
        strategy: Optional strategy filter
    """
    trades = db.query_trades(strategy=strategy, limit=10000)

    if not trades:
        print("No trades to export.")
        return

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['id', 'strategy', 'crypto', 'epoch', 'direction', 'entry_price',
                     'size', 'shares', 'confidence', 'weighted_score', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for trade in trades:
            writer.writerow({
                'id': trade['id'],
                'strategy': trade['strategy'],
                'crypto': trade['crypto'],
                'epoch': trade['epoch'],
                'direction': trade['direction'],
                'entry_price': trade['entry_price'],
                'size': trade['size'],
                'shares': trade['shares'],
                'confidence': trade['confidence'],
                'weighted_score': trade['weighted_score'],
                'timestamp': trade['timestamp']
            })

    print(f"Exported {len(trades)} trades to {output_file}")


def export_outcomes(db: TradeJournalDB, output_file: str, strategy: Optional[str] = None):
    """
    Export outcomes to CSV.

    Args:
        db: TradeJournalDB instance
        output_file: Output CSV file path
        strategy: Optional strategy filter
    """
    outcomes = db.query_outcomes(strategy=strategy, limit=10000)

    if not outcomes:
        print("No outcomes to export.")
        return

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['id', 'strategy', 'crypto', 'epoch', 'predicted_direction',
                     'actual_direction', 'payout', 'pnl', 'timestamp']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for outcome in outcomes:
            writer.writerow({
                'id': outcome['id'],
                'strategy': outcome['strategy'],
                'crypto': outcome['crypto'],
                'epoch': outcome['epoch'],
                'predicted_direction': outcome['predicted_direction'],
                'actual_direction': outcome['actual_direction'],
                'payout': outcome['payout'],
                'pnl': outcome['pnl'],
                'timestamp': outcome['timestamp']
            })

    print(f"Exported {len(outcomes)} outcomes to {output_file}")


def export_performance(db: TradeJournalDB, output_file: str):
    """
    Export performance summary to CSV.

    Args:
        db: TradeJournalDB instance
        output_file: Output CSV file path
    """
    performances = db.get_all_strategies_performance()

    if not performances:
        print("No performance data to export.")
        return

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['strategy', 'total_trades', 'resolved', 'wins', 'losses',
                     'win_rate', 'total_pnl', 'avg_pnl']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for perf in performances:
            writer.writerow({
                'strategy': perf['strategy'],
                'total_trades': perf['total_trades'],
                'resolved': perf['resolved'],
                'wins': perf['wins'],
                'losses': perf['losses'],
                'win_rate': perf['win_rate'],
                'total_pnl': perf['total_pnl'],
                'avg_pnl': perf['avg_pnl']
            })

    print(f"Exported {len(performances)} strategies to {output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Shadow Trading Export')
    parser.add_argument('type', choices=['decisions', 'trades', 'outcomes', 'performance'],
                       help='Data type to export')
    parser.add_argument('--db', type=str, default=None,
                       help=f'Path to SQLite database (default: {agent_config.SHADOW_DB_PATH})')
    parser.add_argument('--strategy', type=str,
                       help='Strategy name filter')
    parser.add_argument('--output', '-o', type=str, required=True,
                       help='Output CSV file path')

    args = parser.parse_args()

    db_path = args.db if args.db else agent_config.SHADOW_DB_PATH
    db = TradeJournalDB(db_path)

    try:
        if args.type == 'decisions':
            export_decisions(db, args.output, strategy=args.strategy)
        elif args.type == 'trades':
            export_trades(db, args.output, strategy=args.strategy)
        elif args.type == 'outcomes':
            export_outcomes(db, args.output, strategy=args.strategy)
        elif args.type == 'performance':
            export_performance(db, args.output)

    finally:
        db.close()


if __name__ == '__main__':
    main()
