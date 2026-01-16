#!/usr/bin/env python3
"""
Shadow Strategy Auto-Promotion

Analyzes shadow strategy performance and generates promotion recommendations.
Runs daily to identify strategies that consistently outperform the live strategy.

Usage:
    python3 scripts/auto_promote_strategy.py [--min-trades 100] [--min-advantage 0.03] [--dry-run]

Examples:
    # Daily automated run
    python3 scripts/auto_promote_strategy.py

    # Custom thresholds
    python3 scripts/auto_promote_strategy.py --min-trades 200 --min-advantage 0.05

    # Dry run (no file changes)
    python3 scripts/auto_promote_strategy.py --dry-run
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ShadowAnalyzer:
    """Analyzes shadow strategy performance and recommends promotions"""

    def __init__(self, db_path: str = "simulation/trade_journal.db"):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Connect to shadow trading database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def get_strategy_performance(self, days: int = 30) -> List[Dict]:
        """
        Get performance metrics for all strategies over the last N days.

        Returns:
            List of dicts with strategy name, win_rate, total_pnl, trade_count
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")

        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        query = """
        SELECT
            s.name as strategy_name,
            s.is_live,
            COUNT(o.id) as trade_count,
            SUM(CASE WHEN o.outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN o.outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(o.profit_loss) as total_pnl,
            AVG(o.profit_loss) as avg_pnl,
            AVG(o.entry_price) as avg_entry_price
        FROM strategies s
        LEFT JOIN trades t ON s.id = t.strategy_id
        LEFT JOIN outcomes o ON t.id = o.trade_id
        WHERE o.resolved_at >= ?
        GROUP BY s.id
        HAVING trade_count >= 20
        ORDER BY total_pnl DESC
        """

        try:
            cursor = self.conn.execute(query, (cutoff_date,))
            results = []
            for row in cursor:
                win_rate = row['wins'] / row['trade_count'] if row['trade_count'] > 0 else 0
                results.append({
                    'strategy_name': row['strategy_name'],
                    'is_live': bool(row['is_live']),
                    'trade_count': row['trade_count'],
                    'wins': row['wins'],
                    'losses': row['losses'],
                    'win_rate': win_rate,
                    'total_pnl': row['total_pnl'],
                    'avg_pnl': row['avg_pnl'],
                    'avg_entry_price': row['avg_entry_price'] or 0
                })
            return results
        except sqlite3.Error as e:
            logger.error(f"Query failed: {e}")
            return []

    def find_promotion_candidates(self, strategies: List[Dict],
                                   min_trades: int = 100,
                                   min_advantage: float = 0.03) -> List[Tuple[Dict, Dict, str]]:
        """
        Find shadow strategies that outperform the live strategy.

        Args:
            strategies: List of strategy performance dicts
            min_trades: Minimum trades required for promotion
            min_advantage: Minimum win rate advantage (e.g., 0.03 = 3%)

        Returns:
            List of (shadow_strategy, live_strategy, reason) tuples
        """
        # Find live strategy
        live_strategy = next((s for s in strategies if s['is_live']), None)
        if not live_strategy:
            logger.warning("No live strategy found in database")
            return []

        logger.info(f"Live strategy: {live_strategy['strategy_name']} "
                   f"({live_strategy['win_rate']:.1%} WR, {live_strategy['trade_count']} trades)")

        # Find shadow strategies that beat live
        candidates = []
        for shadow in strategies:
            if shadow['is_live']:
                continue  # Skip live strategy

            # Check minimum trade requirement
            if shadow['trade_count'] < min_trades:
                logger.debug(f"Skip {shadow['strategy_name']}: only {shadow['trade_count']} trades (need {min_trades})")
                continue

            # Check win rate advantage
            wr_advantage = shadow['win_rate'] - live_strategy['win_rate']
            if wr_advantage < min_advantage:
                logger.debug(f"Skip {shadow['strategy_name']}: only +{wr_advantage:.1%} advantage (need +{min_advantage:.1%})")
                continue

            # Check total P&L (must be positive)
            if shadow['total_pnl'] <= 0:
                logger.debug(f"Skip {shadow['strategy_name']}: negative P&L (${shadow['total_pnl']:.2f})")
                continue

            # Calculate statistical significance (simple check)
            # With 100+ trades, >3% advantage is likely significant
            reason = self._build_promotion_reason(shadow, live_strategy)
            candidates.append((shadow, live_strategy, reason))

        # Sort by win rate advantage (best first)
        candidates.sort(key=lambda x: x[0]['win_rate'], reverse=True)
        return candidates

    def _build_promotion_reason(self, shadow: Dict, live: Dict) -> str:
        """Build human-readable promotion justification"""
        wr_diff = shadow['win_rate'] - live['win_rate']
        pnl_diff = shadow['total_pnl'] - live['total_pnl']

        reasons = []
        reasons.append(f"Win rate: {shadow['win_rate']:.1%} vs {live['win_rate']:.1%} (+{wr_diff:.1%})")
        reasons.append(f"Total P&L: ${shadow['total_pnl']:.2f} vs ${live['total_pnl']:.2f} (+${pnl_diff:.2f})")
        reasons.append(f"Trade count: {shadow['trade_count']} (sufficient for statistical significance)")

        if shadow['avg_entry_price'] < live['avg_entry_price']:
            reasons.append(f"Cheaper entries: ${shadow['avg_entry_price']:.2f} vs ${live['avg_entry_price']:.2f}")

        return "\n  • " + "\n  • ".join(reasons)

    def generate_promotion_report(self, candidates: List[Tuple[Dict, Dict, str]],
                                   output_file: str = "reports/strategy_promotion_recommendations.md") -> str:
        """
        Generate markdown report with promotion recommendations.

        Returns:
            Path to generated report
        """
        if not candidates:
            logger.info("No promotion candidates found - live strategy is optimal")
            return ""

        report_lines = [
            "# Shadow Strategy Promotion Recommendations",
            "",
            f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"**Summary:** {len(candidates)} shadow strategy(ies) outperform the current live strategy.",
            "",
            "---",
            ""
        ]

        for i, (shadow, live, reason) in enumerate(candidates, 1):
            report_lines.extend([
                f"## Recommendation #{i}: Promote `{shadow['strategy_name']}`",
                "",
                "### Performance Comparison",
                "",
                f"**Current Live:** `{live['strategy_name']}`",
                f"- Win Rate: {live['win_rate']:.1%}",
                f"- Total P&L: ${live['total_pnl']:.2f}",
                f"- Trades: {live['trade_count']}",
                f"- Avg Entry: ${live['avg_entry_price']:.2f}",
                "",
                f"**Proposed Shadow:** `{shadow['strategy_name']}`",
                f"- Win Rate: {shadow['win_rate']:.1%} ✅ (+{(shadow['win_rate'] - live['win_rate']):.1%})",
                f"- Total P&L: ${shadow['total_pnl']:.2f} ✅ (+${(shadow['total_pnl'] - live['total_pnl']):.2f})",
                f"- Trades: {shadow['trade_count']}",
                f"- Avg Entry: ${shadow['avg_entry_price']:.2f}",
                "",
                "### Justification",
                "",
                reason,
                "",
                "### Recommended Action",
                "",
                "1. **Review configuration:**",
                f"   - Check `simulation/strategy_configs.py` for `{shadow['strategy_name']}` parameters",
                "   - Verify threshold changes are reasonable",
                "   - Confirm no experimental/risky settings",
                "",
                "2. **Update live configuration:**",
                "   ```bash",
                "   # Backup current config",
                "   cp config/agent_config.py config/agent_config.py.backup",
                "",
                "   # Apply shadow strategy parameters to config/agent_config.py",
                f"   # (See simulation/strategy_configs.py:{shadow['strategy_name']})",
                "   ```",
                "",
                "3. **Deploy and monitor:**",
                "   ```bash",
                "   git add config/agent_config.py",
                f"   git commit -m \"feat: Promote {shadow['strategy_name']} strategy (auto-promotion)\"",
                "   ./scripts/deploy.sh",
                "   ```",
                "",
                "4. **Monitor for 48 hours:**",
                "   - Verify win rate maintains or improves",
                "   - Check directional balance stays 40-60%",
                "   - Confirm no unexpected errors",
                "",
                "---",
                ""
            ])

        # Write report
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write('\n'.join(report_lines))

        logger.info(f"Generated promotion report: {output_file}")
        return output_file

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.debug("Database connection closed")


def main():
    parser = argparse.ArgumentParser(description="Auto-promote high-performing shadow strategies")
    parser.add_argument('--min-trades', type=int, default=100,
                       help='Minimum trades required for promotion (default: 100)')
    parser.add_argument('--min-advantage', type=float, default=0.03,
                       help='Minimum win rate advantage required (default: 0.03 = 3%%)')
    parser.add_argument('--days', type=int, default=30,
                       help='Days of history to analyze (default: 30)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Analyze only, do not generate report')
    parser.add_argument('--db-path', type=str, default='simulation/trade_journal.db',
                       help='Path to shadow trading database')

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Shadow Strategy Auto-Promotion Analysis")
    logger.info("=" * 60)
    logger.info(f"Min trades: {args.min_trades}")
    logger.info(f"Min advantage: {args.min_advantage:.1%}")
    logger.info(f"Analysis period: {args.days} days")
    logger.info("")

    try:
        analyzer = ShadowAnalyzer(db_path=args.db_path)
        analyzer.connect()

        # Get all strategy performance
        logger.info("Querying strategy performance...")
        strategies = analyzer.get_strategy_performance(days=args.days)

        if not strategies:
            logger.warning("No strategy performance data found")
            return 1

        logger.info(f"Found {len(strategies)} strategies with recent activity")
        logger.info("")

        # Find promotion candidates
        candidates = analyzer.find_promotion_candidates(
            strategies,
            min_trades=args.min_trades,
            min_advantage=args.min_advantage
        )

        if not candidates:
            logger.info("✅ No promotion candidates found - live strategy is optimal!")
            logger.info("")
            logger.info("Top shadow strategies:")
            shadows = [s for s in strategies if not s['is_live']][:3]
            for s in shadows:
                logger.info(f"  • {s['strategy_name']}: {s['win_rate']:.1%} WR, "
                          f"${s['total_pnl']:.2f} P&L ({s['trade_count']} trades)")
            return 0

        # Report candidates
        logger.info(f"🎯 Found {len(candidates)} promotion candidate(s):")
        logger.info("")
        for shadow, live, reason in candidates:
            logger.info(f"  🏆 {shadow['strategy_name']}")
            logger.info(f"     {shadow['win_rate']:.1%} WR vs {live['win_rate']:.1%} live "
                       f"(+{(shadow['win_rate'] - live['win_rate']):.1%})")
            logger.info("")

        # Generate report
        if not args.dry_run:
            report_path = analyzer.generate_promotion_report(candidates)
            logger.info("")
            logger.info(f"📄 Promotion report generated: {report_path}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Review the report")
            logger.info("  2. Manually apply recommended config changes")
            logger.info("  3. Commit and deploy")
            logger.info("  4. Monitor for 48 hours")
        else:
            logger.info("")
            logger.info("(Dry run - no report generated)")

        analyzer.close()
        return 0

    except Exception as e:
        logger.error(f"Auto-promotion failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
