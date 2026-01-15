#!/usr/bin/env python3
"""
Auto-Promoter Module
====================

Automatically identifies outperforming shadow strategies and promotes them to live trading.

Promotion criteria:
- Win rate at least 5% better than live strategy
- Minimum 100 trades for statistical significance
- Sharpe ratio ≥ 1.2
- Max drawdown ≤ 25%

Usage:
    # Dry run (default) - shows recommendations without making changes
    python3 simulation/auto_promoter.py --dry-run

    # Live mode - actually updates config file
    python3 simulation/auto_promoter.py --live
"""

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""
    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    roi: float
    sharpe_ratio: float
    max_drawdown_pct: float
    avg_position_size: float

    def __str__(self) -> str:
        return (
            f"{self.strategy_name}: "
            f"{self.total_trades} trades, "
            f"{self.win_rate:.1%} win rate, "
            f"${self.total_pnl:+.2f} P&L, "
            f"{self.roi:+.1%} ROI, "
            f"Sharpe {self.sharpe_ratio:.2f}, "
            f"DD {self.max_drawdown_pct:.1%}"
        )


class AutoPromoter:
    """Automatically promotes high-performing shadow strategies to live trading."""

    def __init__(
        self,
        db_path: str = "simulation/trade_journal.db",
        config_path: str = "config/agent_config.py",
        dry_run: bool = True
    ):
        """
        Initialize AutoPromoter.

        Args:
            db_path: Path to SQLite trade journal database
            config_path: Path to agent_config.py file
            dry_run: If True, only show recommendations without making changes
        """
        self.db_path = Path(db_path)
        self.config_path = Path(config_path)
        self.dry_run = dry_run

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

    def get_live_performance(self) -> Optional[StrategyPerformance]:
        """
        Get performance metrics for the current live strategy.

        Returns:
            StrategyPerformance for live strategy, or None if not found
        """
        # Query the database for the strategy marked as live
        # The live strategy is tracked under 'default' or 'live' in decisions table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get live strategy name from strategies table (is_live=1)
        cursor.execute("""
            SELECT name FROM strategies WHERE is_live = 1 LIMIT 1
        """)
        result = cursor.fetchone()

        if not result:
            # Fallback: assume 'default' is live
            live_strategy = 'default'
        else:
            live_strategy = result[0]

        perf = self._calculate_performance(cursor, live_strategy)
        conn.close()

        return perf

    def get_shadow_performance(self, strategy_name: str) -> Optional[StrategyPerformance]:
        """
        Get performance metrics for a specific shadow strategy.

        Args:
            strategy_name: Name of the shadow strategy

        Returns:
            StrategyPerformance for the strategy, or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        perf = self._calculate_performance(cursor, strategy_name)
        conn.close()

        return perf

    def _calculate_performance(
        self,
        cursor: sqlite3.Cursor,
        strategy_name: str
    ) -> Optional[StrategyPerformance]:
        """
        Calculate performance metrics for a strategy from database.

        Args:
            cursor: Database cursor
            strategy_name: Strategy name to analyze

        Returns:
            StrategyPerformance object or None if no data
        """
        # Get trade stats (join trades with outcomes)
        cursor.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN o.predicted_direction = o.actual_direction THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN o.predicted_direction != o.actual_direction THEN 1 ELSE 0 END) as losses,
                SUM(o.pnl) as total_pnl,
                AVG(t.size) as avg_position_size
            FROM trades t
            JOIN outcomes o ON t.id = o.trade_id
            WHERE t.strategy = ?
        """, (strategy_name,))

        result = cursor.fetchone()

        if not result or result[0] == 0:
            return None

        total_trades, wins, losses, total_pnl, avg_position_size = result

        # Calculate win rate
        win_rate = wins / total_trades if total_trades > 0 else 0.0

        # Get starting balance from strategy config
        cursor.execute("""
            SELECT starting_balance FROM strategies WHERE name = ?
        """, (strategy_name,))
        starting_balance_result = cursor.fetchone()
        starting_balance = starting_balance_result[0] if starting_balance_result else 100.0

        # Calculate ROI
        roi = total_pnl / starting_balance if starting_balance > 0 else 0.0

        # Calculate Sharpe ratio (simplified: mean return / std dev of returns)
        cursor.execute("""
            SELECT o.pnl FROM outcomes o
            WHERE o.strategy = ?
            ORDER BY o.timestamp
        """, (strategy_name,))

        pnls = [row[0] for row in cursor.fetchall()]
        sharpe_ratio = self._calculate_sharpe(pnls)

        # Calculate max drawdown
        max_drawdown_pct = self._calculate_max_drawdown(cursor, strategy_name, starting_balance)

        return StrategyPerformance(
            strategy_name=strategy_name,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_pnl=total_pnl,
            roi=roi,
            sharpe_ratio=sharpe_ratio,
            max_drawdown_pct=max_drawdown_pct,
            avg_position_size=avg_position_size or 0.0
        )

    def _calculate_sharpe(self, pnls: List[float]) -> float:
        """
        Calculate Sharpe ratio from list of P&Ls.

        Sharpe = mean(returns) / std(returns)
        Assuming risk-free rate = 0 for simplicity.

        Args:
            pnls: List of trade P&Ls

        Returns:
            Sharpe ratio (0.0 if insufficient data)
        """
        if len(pnls) < 2:
            return 0.0

        # Calculate mean
        mean_pnl = sum(pnls) / len(pnls)

        # Calculate standard deviation
        variance = sum((x - mean_pnl) ** 2 for x in pnls) / len(pnls)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        # Sharpe ratio
        return mean_pnl / std_dev

    def _calculate_max_drawdown(
        self,
        cursor: sqlite3.Cursor,
        strategy_name: str,
        starting_balance: float
    ) -> float:
        """
        Calculate maximum drawdown percentage for a strategy.

        Args:
            cursor: Database cursor
            strategy_name: Strategy to analyze
            starting_balance: Starting balance for the strategy

        Returns:
            Max drawdown as percentage (e.g., 0.25 = 25% drawdown)
        """
        # Get all trades in chronological order
        cursor.execute("""
            SELECT o.pnl FROM outcomes o
            WHERE o.strategy = ?
            ORDER BY o.timestamp
        """, (strategy_name,))

        pnls = [row[0] for row in cursor.fetchall()]

        if not pnls:
            return 0.0

        # Calculate running balance
        balance = starting_balance
        peak = starting_balance
        max_dd = 0.0

        for pnl in pnls:
            balance += pnl
            if balance > peak:
                peak = balance

            # Calculate drawdown from peak
            if peak > 0:
                dd = (peak - balance) / peak
                if dd > max_dd:
                    max_dd = dd

        return max_dd

    def get_promotion_candidates(
        self,
        min_win_rate_improvement: float = 0.05,
        min_trades: int = 100,
        min_sharpe: float = 1.2,
        max_drawdown: float = 0.25
    ) -> List[Tuple[StrategyPerformance, StrategyPerformance]]:
        """
        Find shadow strategies that qualify for promotion.

        Args:
            min_win_rate_improvement: Minimum win rate advantage over live (e.g., 0.05 = 5%)
            min_trades: Minimum number of trades for statistical significance
            min_sharpe: Minimum Sharpe ratio required
            max_drawdown: Maximum drawdown allowed (e.g., 0.25 = 25%)

        Returns:
            List of (shadow_perf, live_perf) tuples for candidates
        """
        live_perf = self.get_live_performance()

        if not live_perf:
            print("⚠️  No live strategy performance data found")
            return []

        # Get all shadow strategies
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM strategies WHERE is_live = 0 OR is_live IS NULL
        """)

        shadow_strategies = [row[0] for row in cursor.fetchall()]
        conn.close()

        candidates = []

        for shadow_name in shadow_strategies:
            shadow_perf = self.get_shadow_performance(shadow_name)

            if not shadow_perf:
                continue

            # Check promotion criteria
            if shadow_perf.total_trades < min_trades:
                continue

            win_rate_improvement = shadow_perf.win_rate - live_perf.win_rate
            if win_rate_improvement < min_win_rate_improvement:
                continue

            if shadow_perf.sharpe_ratio < min_sharpe:
                continue

            if shadow_perf.max_drawdown_pct > max_drawdown:
                continue

            candidates.append((shadow_perf, live_perf))

        # Sort by win rate improvement (descending)
        candidates.sort(key=lambda x: x[0].win_rate - x[1].win_rate, reverse=True)

        return candidates

    def promote_strategy(self, strategy_name: str, allocation: float = 0.25) -> bool:
        """
        Promote a shadow strategy to live trading (updates config file).

        Args:
            strategy_name: Name of shadow strategy to promote
            allocation: Allocation percentage for staged rollout (0.0-1.0)
                       0.25 = 25% of trades, 1.0 = 100% of trades

        Returns:
            True if promotion successful, False otherwise
        """
        if self.dry_run:
            print(f"[DRY RUN] Would promote {strategy_name} with {allocation:.0%} allocation")
            return True

        # Read config file
        config_content = self.config_path.read_text()

        # Update LIVE_STRATEGY variable
        # Look for pattern: LIVE_STRATEGY = '...'
        updated_content = config_content

        # Update or add LIVE_STRATEGY
        if "LIVE_STRATEGY =" in config_content:
            # Replace existing
            lines = config_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith("LIVE_STRATEGY ="):
                    lines[i] = f"LIVE_STRATEGY = '{strategy_name}'  # Updated by auto_promoter on {datetime.now().isoformat()}"
                    break
            updated_content = '\n'.join(lines)
        else:
            # Add new (shouldn't happen, but handle gracefully)
            updated_content += f"\n\n# Added by auto_promoter on {datetime.now().isoformat()}\n"
            updated_content += f"LIVE_STRATEGY = '{strategy_name}'\n"

        # Update or add LIVE_STRATEGY_ALLOCATION
        if "LIVE_STRATEGY_ALLOCATION =" in updated_content:
            lines = updated_content.split('\n')
            for i, line in enumerate(lines):
                if line.strip().startswith("LIVE_STRATEGY_ALLOCATION ="):
                    lines[i] = f"LIVE_STRATEGY_ALLOCATION = {allocation}  # Updated by auto_promoter on {datetime.now().isoformat()}"
                    break
            updated_content = '\n'.join(lines)
        else:
            updated_content += f"LIVE_STRATEGY_ALLOCATION = {allocation}  # Added by auto_promoter on {datetime.now().isoformat()}\n"

        # Write updated config
        self.config_path.write_text(updated_content)

        print(f"✅ Promoted {strategy_name} with {allocation:.0%} allocation")
        print(f"   Updated config: {self.config_path}")

        # Also update database to mark strategy as live
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Clear previous live flag
        cursor.execute("UPDATE strategies SET is_live = 0")

        # Set new live flag
        cursor.execute("UPDATE strategies SET is_live = 1 WHERE name = ?", (strategy_name,))

        conn.commit()
        conn.close()

        return True

    def run_promotion_check(self) -> None:
        """
        Main workflow: Check for promotion candidates and recommend/promote.
        """
        print("=" * 80)
        print("🚀 AUTO-PROMOTER: Checking for high-performing shadow strategies")
        print("=" * 80)
        print()

        # Get current live performance
        live_perf = self.get_live_performance()

        if not live_perf:
            print("❌ Error: No live strategy performance data available")
            return

        print(f"📊 Current Live Strategy Performance:")
        print(f"   {live_perf}")
        print()

        # Get promotion candidates
        candidates = self.get_promotion_candidates()

        if not candidates:
            print("✅ No shadow strategies meet promotion criteria")
            print()
            print("Criteria:")
            print("  • Win rate at least +5% better than live")
            print("  • Minimum 100 trades")
            print("  • Sharpe ratio ≥ 1.2")
            print("  • Max drawdown ≤ 25%")
            print()
            return

        # Show candidates
        print(f"🎯 Found {len(candidates)} promotion candidate(s):")
        print()

        for i, (shadow_perf, _) in enumerate(candidates, 1):
            win_rate_improvement = shadow_perf.win_rate - live_perf.win_rate
            print(f"{i}. {shadow_perf.strategy_name}")
            print(f"   Win Rate: {shadow_perf.win_rate:.1%} (+{win_rate_improvement:.1%} vs live)")
            print(f"   Sharpe: {shadow_perf.sharpe_ratio:.2f}")
            print(f"   Drawdown: {shadow_perf.max_drawdown_pct:.1%}")
            print(f"   Trades: {shadow_perf.total_trades}")
            print(f"   P&L: ${shadow_perf.total_pnl:+.2f} ({shadow_perf.roi:+.1%} ROI)")
            print()

        # Promote top candidate
        top_candidate = candidates[0][0]

        print("=" * 80)

        if self.dry_run:
            print(f"[DRY RUN] Recommendation: Promote {top_candidate.strategy_name}")
            print(f"          Suggested allocation: 25% (staged rollout)")
            print()
            print("To actually promote, run with --live flag")
        else:
            print(f"🚀 Promoting {top_candidate.strategy_name} with 25% allocation (staged rollout)")
            success = self.promote_strategy(top_candidate.strategy_name, allocation=0.25)

            if success:
                print()
                print("✅ Promotion complete!")
                print()
                print("Next steps:")
                print("  1. Monitor performance for 50 trades (2-3 days)")
                print("  2. If still outperforming: Increase to 50% allocation")
                print("  3. Monitor for 50 more trades")
                print("  4. If still outperforming: Increase to 100% allocation")
                print()
                print("Auto-rollback: If win rate drops below 50%, revert to previous strategy")
            else:
                print()
                print("❌ Promotion failed - check logs for details")

        print("=" * 80)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Auto-Promoter: Identify and promote high-performing shadow strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (default) - show recommendations without making changes
  python3 simulation/auto_promoter.py
  python3 simulation/auto_promoter.py --dry-run

  # Live mode - actually update config and promote strategy
  python3 simulation/auto_promoter.py --live

  # Custom paths
  python3 simulation/auto_promoter.py --db simulation/trade_journal.db --config config/agent_config.py
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Show recommendations without making changes (default)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually promote strategies (updates config file)'
    )

    parser.add_argument(
        '--db',
        default='simulation/trade_journal.db',
        help='Path to trade journal database (default: simulation/trade_journal.db)'
    )

    parser.add_argument(
        '--config',
        default='config/agent_config.py',
        help='Path to agent_config.py (default: config/agent_config.py)'
    )

    args = parser.parse_args()

    # --live overrides --dry-run
    dry_run = not args.live

    try:
        promoter = AutoPromoter(
            db_path=args.db,
            config_path=args.config,
            dry_run=dry_run
        )

        promoter.run_promotion_check()

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
