#!/usr/bin/env python3
"""
Shadow Trading Dashboard - Live Monitoring

Auto-refreshing terminal dashboard showing real-time performance of all shadow strategies.
Similar to dashboard/live_dashboard.py but for shadow strategy comparison.
"""

import sys
import time
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from simulation.trade_journal import TradeJournalDB
from config import agent_config


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def get_status_emoji(pnl: float) -> str:
    """Get status emoji based on P&L."""
    if pnl > 10:
        return "🟢🟢"  # Very profitable
    elif pnl > 0:
        return "🟢"    # Profitable
    elif pnl > -5:
        return "⚪"    # Small loss
    elif pnl > -10:
        return "🔴"    # Loss
    else:
        return "🔴🔴"  # Big loss


def format_roi(roi: float) -> str:
    """Format ROI with color indicators."""
    if roi > 0.10:
        return f"🟢 {roi*100:+.1f}%"
    elif roi > 0:
        return f"{roi*100:+.1f}%"
    elif roi > -0.10:
        return f"🔴 {roi*100:+.1f}%"
    else:
        return f"🔴🔴 {roi*100:+.1f}%"


def print_dashboard(db: TradeJournalDB):
    """Print the shadow trading dashboard."""
    clear_screen()

    print("=" * 110)
    print(" " * 35 + "🎯 SHADOW TRADING DASHBOARD 🎯")
    print("=" * 110)
    print()

    # Get all strategies
    strategies = db.conn.execute('SELECT name FROM strategies ORDER BY name').fetchall()

    if not strategies:
        print("No shadow strategies found in database.")
        print(f"\nDatabase: {db.db_path}")
        return

    # Get performance for each strategy
    performances = []
    for row in strategies:
        name = row['name']
        perf = db.get_strategy_performance(name)
        performances.append(perf)

    # Sort by total P&L (descending)
    performances.sort(key=lambda x: x.get('total_pnl', 0), reverse=True)

    # Table header
    print(f"{'Rank':<6} {'Strategy':<28} {'Trades':<8} {'W/L':<8} {'Win Rate':<10} {'Total P&L':<12} {'Avg P&L':<10} {'ROI':<12}")
    print("-" * 110)

    # Print each strategy
    for i, perf in enumerate(performances, 1):
        name = perf['strategy']
        total_trades = perf['total_trades']
        wins = perf['wins']
        losses = perf['losses']
        win_rate = perf['win_rate']
        total_pnl = perf['total_pnl']
        avg_pnl = perf['avg_pnl']
        resolved = perf['resolved']

        # Calculate ROI (assume $100 starting balance)
        roi = total_pnl / agent_config.SHADOW_STARTING_BALANCE if agent_config.SHADOW_STARTING_BALANCE > 0 else 0.0

        # Status emoji
        emoji = get_status_emoji(total_pnl)

        # Format win/loss
        wl_str = f"{wins}W/{losses}L"

        # Format win rate
        wr_str = f"{win_rate*100:.1f}%" if resolved > 0 else "N/A"

        # Print row
        print(f"{emoji} {i:<4} {name:<27} {total_trades:<8} {wl_str:<8} {wr_str:<10} ${total_pnl:+11.2f} ${avg_pnl:+9.2f} {format_roi(roi):<12}")

    print()
    print("=" * 110)

    # Summary stats
    if performances:
        best_pnl = performances[0]
        best_wr = max(performances, key=lambda x: x['win_rate'])

        print(f"🏆 Best P&L: {best_pnl['strategy']} (${best_pnl['total_pnl']:+.2f})")
        print(f"🎯 Best Win Rate: {best_wr['strategy']} ({best_wr['win_rate']*100:.1f}%)")

        total_resolved = sum(p['resolved'] for p in performances)
        total_wins = sum(p['wins'] for p in performances)
        overall_wr = (total_wins / total_resolved * 100) if total_resolved > 0 else 0

        print(f"📊 Overall: {total_resolved} resolved trades, {overall_wr:.1f}% win rate")

    print("=" * 110)
    print(f"Database: {db.db_path}")
    print(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Press Ctrl+C to exit")


def run_dashboard(db_path: str = None, refresh_interval: int = 5):
    """
    Run the auto-refreshing dashboard.

    Args:
        db_path: Path to SQLite database (default from config)
        refresh_interval: Refresh interval in seconds (default 5)
    """
    if db_path is None:
        db_path = agent_config.SHADOW_DB_PATH

    db = TradeJournalDB(db_path)

    try:
        while True:
            print_dashboard(db)
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        db.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Shadow Trading Dashboard')
    parser.add_argument('--db', type=str, default=None,
                       help=f'Path to SQLite database (default: {agent_config.SHADOW_DB_PATH})')
    parser.add_argument('--interval', type=int, default=5,
                       help='Refresh interval in seconds (default: 5)')

    args = parser.parse_args()

    run_dashboard(db_path=args.db, refresh_interval=args.interval)


if __name__ == '__main__':
    main()
