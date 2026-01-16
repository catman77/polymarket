#!/usr/bin/env python3
"""
Compare random baseline (coin flip) vs default strategy performance.

This is the ULTIMATE sanity check - if random beats default, we have negative edge.

Persona: Victor "Vic" Ramanujan - Quantitative Strategist
"Data-driven decisions. Test everything. Trust nothing."
"""

import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import sys

@dataclass
class StrategyPerformance:
    """Performance metrics for a single strategy."""
    name: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    avg_pnl_per_trade: float
    roi: float

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Trades: {self.total_trades}\n"
            f"  W/L: {self.wins}W/{self.losses}L\n"
            f"  Win Rate: {self.win_rate*100:.1f}%\n"
            f"  Total P&L: ${self.total_pnl:.2f}\n"
            f"  Avg P&L: ${self.avg_pnl_per_trade:.3f}/trade\n"
            f"  ROI: {self.roi*100:.1f}%"
        )


class RandomBaselineComparator:
    """Compare random baseline vs default strategy."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def get_strategy_performance(self, strategy_name: str) -> Optional[StrategyPerformance]:
        """Query performance for a specific strategy."""

        # Get latest performance snapshot
        cursor = self.conn.execute("""
            SELECT
                strategy,
                total_trades,
                wins,
                losses,
                win_rate,
                total_pnl,
                roi
            FROM performance
            WHERE strategy = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (strategy_name,))

        row = cursor.fetchone()

        if not row:
            # No performance data yet - try to calculate from outcomes
            return self._calculate_performance_from_outcomes(strategy_name)

        return StrategyPerformance(
            name=row['strategy'],
            total_trades=row['total_trades'],
            wins=row['wins'],
            losses=row['losses'],
            win_rate=row['win_rate'],
            total_pnl=row['total_pnl'],
            avg_pnl_per_trade=row['total_pnl'] / row['total_trades'] if row['total_trades'] > 0 else 0.0,
            roi=row['roi']
        )

    def _calculate_performance_from_outcomes(self, strategy_name: str) -> Optional[StrategyPerformance]:
        """Calculate performance directly from outcomes table if performance table is empty."""

        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN predicted_direction = actual_direction THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN predicted_direction != actual_direction THEN 1 ELSE 0 END) as losses,
                SUM(pnl) as total_pnl
            FROM outcomes
            WHERE strategy = ?
        """, (strategy_name,))

        row = cursor.fetchone()

        if not row or row['total_trades'] == 0:
            return None

        total_trades = row['total_trades']
        wins = row['wins']
        losses = row['losses']
        total_pnl = row['total_pnl']

        # Assume starting balance of $100 for ROI calculation
        starting_balance = 100.0
        roi = total_pnl / starting_balance

        return StrategyPerformance(
            name=strategy_name,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=wins / total_trades if total_trades > 0 else 0.0,
            total_pnl=total_pnl,
            avg_pnl_per_trade=total_pnl / total_trades if total_trades > 0 else 0.0,
            roi=roi
        )

    def perform_t_test(self, random: StrategyPerformance, default: StrategyPerformance) -> tuple[float, float, str]:
        """
        Perform independent samples t-test to test if default is significantly better than random.

        Returns: (t_statistic, p_value, conclusion)

        Note: For binary outcomes (win/loss), we use proportions test instead of t-test.
        This is more appropriate for binomial data.
        """
        from scipy import stats
        import numpy as np

        # For win rates, use proportions z-test
        # H0: p_default = p_random (no difference)
        # H1: p_default > p_random (default is better)

        n1 = random.total_trades
        n2 = default.total_trades
        p1 = random.win_rate
        p2 = default.win_rate

        # Check if we have enough data
        if n1 < 5 or n2 < 5:
            return 0.0, 1.0, "INSUFFICIENT_DATA (need ≥5 trades per strategy)"

        # Pooled proportion
        p_pooled = (random.wins + default.wins) / (n1 + n2)

        # Standard error
        se = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

        if se == 0:
            return 0.0, 1.0, "DEGENERATE (zero variance)"

        # Z-statistic
        z = (p2 - p1) / se

        # One-tailed p-value (testing if default > random)
        p_value = 1 - stats.norm.cdf(z)

        # Interpret results
        if p_value < 0.05:
            if p2 > p1:
                conclusion = "SIGNIFICANT (default > random, p<0.05)"
            else:
                conclusion = "SIGNIFICANT (random > default, p<0.05) ⚠️ NEGATIVE EDGE"
        else:
            conclusion = "NOT_SIGNIFICANT (no edge detected, p≥0.05)"

        return z, p_value, conclusion

    def generate_report(self, random: StrategyPerformance, default: StrategyPerformance) -> List[str]:
        """Generate markdown report comparing random vs default."""

        lines = []
        lines.append("# Random Baseline vs Default Strategy Comparison")
        lines.append("")
        lines.append("**Persona:** Victor 'Vic' Ramanujan - Quantitative Strategist")
        lines.append("")
        lines.append("**Question:** Does our default strategy have positive edge, or could a coin flip do better?")
        lines.append("")
        lines.append("**Methodology:** Compare shadow trading performance of `random_baseline` (50/50 coin flip) vs `default` (live strategy).")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Performance Comparison")
        lines.append("")
        lines.append("| Metric | Random Baseline | Default (Live) | Difference |")
        lines.append("|--------|----------------|----------------|------------|")
        lines.append(f"| Total Trades | {random.total_trades} | {default.total_trades} | {default.total_trades - random.total_trades:+d} |")
        lines.append(f"| Win Rate | {random.win_rate*100:.1f}% | {default.win_rate*100:.1f}% | {(default.win_rate - random.win_rate)*100:+.1f}% |")
        lines.append(f"| Total P&L | ${random.total_pnl:.2f} | ${default.total_pnl:.2f} | ${default.total_pnl - random.total_pnl:+.2f} |")
        lines.append(f"| Avg P&L/Trade | ${random.avg_pnl_per_trade:.3f} | ${default.avg_pnl_per_trade:.3f} | ${default.avg_pnl_per_trade - random.avg_pnl_per_trade:+.3f} |")
        lines.append(f"| ROI | {random.roi*100:.1f}% | {default.roi*100:.1f}% | {(default.roi - random.roi)*100:+.1f}% |")
        lines.append("")

        # Statistical test
        lines.append("## Statistical Significance Test")
        lines.append("")
        lines.append("**Test:** Proportions z-test (one-tailed)")
        lines.append("**Hypothesis:**")
        lines.append("- H0: Win_Rate(default) = Win_Rate(random) - No edge")
        lines.append("- H1: Win_Rate(default) > Win_Rate(random) - Positive edge")
        lines.append("")

        try:
            z_stat, p_value, conclusion = self.perform_t_test(random, default)
            lines.append(f"**Results:**")
            lines.append(f"- Z-statistic: {z_stat:.3f}")
            lines.append(f"- P-value: {p_value:.4f}")
            lines.append(f"- Conclusion: **{conclusion}**")
        except ImportError:
            lines.append("⚠️ scipy not installed - statistical test skipped")
            lines.append("Install with: `pip install scipy`")
            conclusion = "MANUAL_INSPECTION_REQUIRED"
        except Exception as e:
            lines.append(f"⚠️ Statistical test failed: {e}")
            conclusion = "TEST_ERROR"

        lines.append("")

        # Interpretation
        lines.append("## Interpretation")
        lines.append("")

        if "INSUFFICIENT_DATA" in conclusion:
            lines.append("⚠️ **Not Enough Data:** Need ≥5 trades per strategy for meaningful comparison.")
            lines.append("")
            lines.append("**Recommendation:** Wait for more shadow trading data to accumulate.")
        elif "NEGATIVE EDGE" in conclusion or random.total_pnl > default.total_pnl:
            lines.append("❌ **CRITICAL ISSUE: Random baseline is outperforming default strategy!**")
            lines.append("")
            lines.append("This indicates:")
            lines.append("- Default strategy has NEGATIVE EDGE")
            lines.append("- Agent consensus is WORSE than coin flip")
            lines.append("- Trading fees are destroying value faster than strategy creates it")
            lines.append("")
            lines.append("**Action Required:**")
            lines.append("1. HALT live trading immediately")
            lines.append("2. Review agent performance (use US-RC-020 per-agent analysis)")
            lines.append("3. Disable underperforming agents")
            lines.append("4. Raise consensus threshold (reduce trade frequency)")
            lines.append("5. Only resume trading after shadow testing shows positive edge")
        elif "NOT_SIGNIFICANT" in conclusion:
            lines.append("⚪ **No Significant Edge Detected:** Default strategy is not significantly better than random.")
            lines.append("")
            lines.append("This could mean:")
            lines.append("- Sample size too small (need more trades)")
            lines.append("- True edge is small (<5% win rate improvement)")
            lines.append("- Agents are barely better than guessing")
            lines.append("")
            lines.append("**Recommendation:**")
            lines.append("- Continue shadow trading to collect more data")
            lines.append("- Target: ≥100 trades per strategy for robust comparison")
            lines.append("- If edge remains insignificant after 100+ trades, consider strategy overhaul")
        else:
            lines.append("✅ **Positive Edge Confirmed:** Default strategy significantly outperforms random baseline.")
            lines.append("")
            lines.append(f"**Edge Magnitude:** {(default.win_rate - random.win_rate)*100:.1f}% win rate improvement over coin flip")
            lines.append(f"**Profit Advantage:** ${default.total_pnl - random.total_pnl:.2f} more P&L than random")
            lines.append("")
            lines.append("**Interpretation:**")
            if default.win_rate - random.win_rate >= 0.10:
                lines.append("- **Strong edge** (≥10% WR improvement): Strategy is working well")
            elif default.win_rate - random.win_rate >= 0.05:
                lines.append("- **Moderate edge** (5-10% WR improvement): Strategy has value, room for optimization")
            else:
                lines.append("- **Weak edge** (<5% WR improvement): Strategy barely profitable, needs improvement")

        lines.append("")

        # Sample size adequacy
        lines.append("## Sample Size Adequacy")
        lines.append("")
        lines.append(f"- Random baseline: {random.total_trades} trades")
        lines.append(f"- Default strategy: {default.total_trades} trades")
        lines.append("")

        min_trades = min(random.total_trades, default.total_trades)
        if min_trades < 30:
            lines.append(f"⚠️ **Small sample** ({min_trades} trades): Results may be noisy. Target: ≥30 trades per strategy.")
        elif min_trades < 100:
            lines.append(f"✅ **Adequate sample** ({min_trades} trades): Results are reasonably reliable. Ideal: ≥100 trades.")
        else:
            lines.append(f"✅ **Large sample** ({min_trades} trades): Results are statistically robust.")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("**Generated by:** `scripts/research/random_baseline_comparison.py`")
        lines.append("")
        lines.append("**Data Source:** `simulation/trade_journal.db`")

        return lines


def main():
    # Database path
    db_path = Path(__file__).parent.parent.parent / 'simulation' / 'trade_journal.db'

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Shadow trading database does not exist yet.")
        sys.exit(1)

    print(f"Reading shadow trading data from: {db_path}")
    print()

    comparator = RandomBaselineComparator(db_path)

    # Get performance for random_baseline
    print("Querying random_baseline performance...")
    random = comparator.get_strategy_performance('random_baseline')

    if not random:
        print("❌ No data for 'random_baseline' strategy")
        print()
        print("This could mean:")
        print("1. Shadow trading is not enabled (check config/agent_config.py)")
        print("2. Bot hasn't run long enough to accumulate trades")
        print("3. random_baseline strategy is not configured")
        print()
        print("Generate placeholder report with explanation...")

        # Generate placeholder report
        report_dir = Path(__file__).parent.parent / 'reports' / 'vic_ramanujan'
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / 'random_baseline_comparison.md'

        with open(report_path, 'w') as f:
            f.write("# Random Baseline vs Default Strategy Comparison\n\n")
            f.write("**Persona:** Victor 'Vic' Ramanujan - Quantitative Strategist\n\n")
            f.write("**Status:** ❌ INSUFFICIENT DATA\n\n")
            f.write("## Issue\n\n")
            f.write("No shadow trading data found for `random_baseline` strategy.\n\n")
            f.write("**Database:** `simulation/trade_journal.db`\n\n")
            f.write("**Strategies found:** (query returned 0 results)\n\n")
            f.write("## Root Cause\n\n")
            f.write("Shadow trading system may not be actively logging trades, or:\n")
            f.write("1. Bot is not running (no live trades = no shadow trades)\n")
            f.write("2. Shadow trading disabled in config\n")
            f.write("3. Database initialization incomplete\n\n")
            f.write("## Recommendation\n\n")
            f.write("1. Check if bot is running: `ssh root@216.238.85.11 'systemctl status polymarket-bot'`\n")
            f.write("2. Check shadow trading config: `config/agent_config.py` → `ENABLE_SHADOW_TRADING`\n")
            f.write("3. Check if strategies are configured: `config/agent_config.py` → `SHADOW_STRATEGIES`\n")
            f.write("4. Wait for bot to accumulate ≥10 trades, then re-run this script\n\n")
            f.write("## Placeholder Comparison\n\n")
            f.write("Cannot compare random vs default until data is available.\n\n")
            f.write("**Expected timeline:** 24-48 hours of live trading should produce sufficient data.\n\n")
            f.write("---\n\n")
            f.write("**Generated by:** `scripts/research/random_baseline_comparison.py`\n")

        print(f"✅ Placeholder report generated: {report_path}")
        sys.exit(1)

    print(f"✅ Found {random.total_trades} trades for random_baseline")
    print()

    # Get performance for default
    print("Querying default strategy performance...")
    default = comparator.get_strategy_performance('default')

    if not default:
        # Try alternative names
        for alt_name in ['ml_live_test', 'live', 'production']:
            default = comparator.get_strategy_performance(alt_name)
            if default:
                print(f"✅ Found default strategy as '{alt_name}'")
                break

        if not default:
            print("❌ No data for 'default' or alternative live strategy")
            print()
            print("Generating partial report with random_baseline only...")

            report_dir = Path(__file__).parent.parent / 'reports' / 'vic_ramanujan'
            report_dir.mkdir(parents=True, exist_ok=True)
            report_path = report_dir / 'random_baseline_comparison.md'

            with open(report_path, 'w') as f:
                f.write("# Random Baseline vs Default Strategy Comparison\n\n")
                f.write("**Status:** ⚠️ PARTIAL DATA\n\n")
                f.write("## Random Baseline Performance\n\n")
                f.write(f"```\n{random}\n```\n\n")
                f.write("## Default Strategy Performance\n\n")
                f.write("❌ No data found for default/live strategy\n\n")
                f.write("**Recommendation:** Verify shadow trading is configured to track live strategy.\n")

            print(f"✅ Partial report generated: {report_path}")
            sys.exit(1)

    print(f"✅ Found {default.total_trades} trades for default strategy")
    print()

    # Generate comparison report
    print("Generating comparison report...")
    report_lines = comparator.generate_report(random, default)

    # Save report
    report_dir = Path(__file__).parent.parent / 'reports' / 'vic_ramanujan'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'random_baseline_comparison.md'

    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"✅ Report generated: {report_path}")
    print()

    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print()
    print(f"Random Baseline: {random.win_rate*100:.1f}% WR, ${random.total_pnl:.2f} P&L ({random.total_trades} trades)")
    print(f"Default Strategy: {default.win_rate*100:.1f}% WR, ${default.total_pnl:.2f} P&L ({default.total_trades} trades)")
    print()

    if default.total_pnl > random.total_pnl:
        print(f"✅ Default BEATS random by ${default.total_pnl - random.total_pnl:.2f}")
    elif default.total_pnl < random.total_pnl:
        print(f"❌ Random BEATS default by ${random.total_pnl - default.total_pnl:.2f} (NEGATIVE EDGE)")
    else:
        print("⚪ Tie (no edge detected)")

    print()
    print(f"Full report: {report_path}")


if __name__ == '__main__':
    main()
