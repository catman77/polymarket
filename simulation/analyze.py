#!/usr/bin/env python3
"""
Shadow Trading Analysis Tool

CLI tool for querying and analyzing shadow trading performance.
"""

import sys
import time
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from simulation.trade_journal import TradeJournalDB
from config import agent_config


def print_comparison(db: TradeJournalDB, since: Optional[float] = None):
    """
    Print performance comparison across all strategies.

    Args:
        db: TradeJournalDB instance
        since: Optional timestamp to filter trades
    """
    print("=" * 100)
    print(" " * 30 + "SHADOW STRATEGY COMPARISON")
    print("=" * 100)
    print()

    performances = db.get_all_strategies_performance()

    if not performances:
        print("No strategies found.")
        return

    # Sort by total P&L (descending)
    performances.sort(key=lambda x: x['total_pnl'], reverse=True)

    # Table header
    print(f"{'Strategy':<25} {'Trades':<8} {'W/L':<10} {'Win Rate':<10} {'Total P&L':<12} {'Avg P&L':<10} {'ROI':<10}")
    print("-" * 100)

    for perf in performances:
        name = perf['strategy']
        total_trades = perf['total_trades']
        wins = perf['wins']
        losses = perf['losses']
        win_rate = perf['win_rate']
        total_pnl = perf['total_pnl']
        avg_pnl = perf['avg_pnl']

        # Calculate ROI
        roi = total_pnl / agent_config.SHADOW_STARTING_BALANCE if agent_config.SHADOW_STARTING_BALANCE > 0 else 0.0

        emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
        wl_str = f"{wins}W/{losses}L"

        print(f"{emoji} {name:<23} {total_trades:<8} {wl_str:<10} {win_rate*100:<9.1f}% ${total_pnl:+11.2f} ${avg_pnl:+9.2f} {roi*100:+9.1f}%")

    print()
    print("=" * 100)


def print_strategy_details(db: TradeJournalDB, strategy: str, limit: int = 20):
    """
    Print detailed information for a specific strategy.

    Args:
        db: TradeJournalDB instance
        strategy: Strategy name
        limit: Number of recent trades to show
    """
    print("=" * 100)
    print(f"STRATEGY DETAILS: {strategy}")
    print("=" * 100)
    print()

    # Get performance
    perf = db.get_strategy_performance(strategy)

    print("Performance Summary:")
    print(f"  Total Trades: {perf['total_trades']}")
    print(f"  Resolved: {perf['resolved']} ({perf['wins']}W / {perf['losses']}L)")
    print(f"  Win Rate: {perf['win_rate']*100:.1f}%")
    print(f"  Total P&L: ${perf['total_pnl']:+.2f}")
    print(f"  Avg P&L: ${perf['avg_pnl']:+.2f}")
    roi = perf['total_pnl'] / agent_config.SHADOW_STARTING_BALANCE if agent_config.SHADOW_STARTING_BALANCE > 0 else 0.0
    print(f"  ROI: {roi*100:+.1f}%")
    print()

    # Get recent trades
    trades = db.query_trades(strategy=strategy, limit=limit)

    if trades:
        print(f"Recent Trades (last {len(trades)}):")
        print(f"{'Crypto':<8} {'Epoch':<12} {'Direction':<10} {'Entry':<8} {'Size':<8} {'Confidence':<12}")
        print("-" * 100)

        for trade in trades:
            crypto = trade['crypto']
            epoch = trade['epoch']
            direction = trade['direction']
            entry_price = trade['entry_price']
            size = trade['size']
            confidence = trade['confidence']

            print(f"{crypto:<8} {epoch:<12} {direction:<10} ${entry_price:<7.2f} ${size:<7.2f} {confidence*100:<11.0f}%")

    # Get recent outcomes
    outcomes = db.query_outcomes(strategy=strategy, limit=limit)

    if outcomes:
        print()
        print(f"Recent Outcomes (last {len(outcomes)}):")
        print(f"{'Crypto':<8} {'Epoch':<12} {'Predicted':<12} {'Actual':<10} {'P&L':<10}")
        print("-" * 100)

        for outcome in outcomes:
            crypto = outcome['crypto']
            epoch = outcome['epoch']
            predicted = outcome['predicted_direction']
            actual = outcome['actual_direction']
            pnl = outcome['pnl']

            result = "✅ WIN" if pnl > 0 else "❌ LOSS"
            print(f"{crypto:<8} {epoch:<12} {predicted:<12} {actual:<10} ${pnl:+9.2f} {result}")

    print()
    print("=" * 100)


def print_decisions(db: TradeJournalDB, strategy: Optional[str] = None, limit: int = 50):
    """
    Print recent decisions.

    Args:
        db: TradeJournalDB instance
        strategy: Optional strategy filter
        limit: Number of decisions to show
    """
    decisions = db.query_decisions(strategy=strategy, limit=limit)

    if not decisions:
        print("No decisions found.")
        return

    print("=" * 120)
    print("RECENT DECISIONS")
    print("=" * 120)
    print()

    print(f"{'Strategy':<20} {'Crypto':<8} {'Trade?':<8} {'Direction':<10} {'Confidence':<12} {'Score':<8} {'Reason':<40}")
    print("-" * 120)

    for dec in decisions:
        strategy_name = dec['strategy']
        crypto = dec['crypto']
        should_trade = "✅ TRADE" if dec['should_trade'] else "⏭️  SKIP"
        direction = dec['direction'] or "N/A"
        confidence = dec['confidence']
        score = dec['weighted_score']
        reason = (dec['reason'] or "")[:38]

        print(f"{strategy_name:<20} {crypto:<8} {should_trade:<8} {direction:<10} {confidence*100:<11.0f}% {score*100:<7.0f}% {reason:<40}")

    print()
    print("=" * 120)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Shadow Trading Analysis')
    parser.add_argument('command', choices=['compare', 'details', 'decisions'],
                       help='Command to execute')
    parser.add_argument('--db', type=str, default=None,
                       help=f'Path to SQLite database (default: {agent_config.SHADOW_DB_PATH})')
    parser.add_argument('--strategy', type=str,
                       help='Strategy name (for details command)')
    parser.add_argument('--since', type=float,
                       help='Only show data since this timestamp')
    parser.add_argument('--limit', type=int, default=20,
                       help='Limit number of results (default: 20)')

    args = parser.parse_args()

    db_path = args.db if args.db else agent_config.SHADOW_DB_PATH
    db = TradeJournalDB(db_path)

    try:
        if args.command == 'compare':
            print_comparison(db, since=args.since)

        elif args.command == 'details':
            if not args.strategy:
                print("Error: --strategy required for details command")
                return
            print_strategy_details(db, args.strategy, limit=args.limit)

        elif args.command == 'decisions':
            print_decisions(db, strategy=args.strategy, limit=args.limit)

    finally:
        db.close()


if __name__ == '__main__':
    main()
