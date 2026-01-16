#!/usr/bin/env python3
"""
US-RC-021: Test ML model on post-training data
Persona: Victor "Vic" Ramanujan (Quantitative Strategist)

Analyzes ML Random Forest performance on Jan 2026 data (unseen during training)
Compares to claimed 67.3% test accuracy and agent performance.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class StrategyPerformance:
    """Performance metrics for a trading strategy"""
    name: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    roi: float
    avg_confidence: float

    def __repr__(self):
        return (f"{self.name}: {self.total_trades} trades, "
                f"{self.win_rate:.1%} WR, ${self.total_pnl:.2f} P&L, "
                f"{self.roi:.1%} ROI")


class MLPerformanceAnalyzer:
    """Analyzes ML strategy performance vs agents"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

        # ML strategies to analyze
        self.ml_strategies = [
            'ml_random_forest_50',
            'ml_random_forest_55',
            'ml_random_forest_60',
            'ml_live_test'  # Current production ML
        ]

        # Claimed test accuracy (from training)
        self.claimed_test_accuracy = 0.673  # 67.3%

    def connect(self):
        """Connect to SQLite database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            return True
        except sqlite3.Error as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def query_strategy_performance(self, strategy_name: str) -> Optional[StrategyPerformance]:
        """Query performance metrics for a strategy"""
        if not self.conn:
            return None

        cursor = self.conn.cursor()

        # Get latest performance snapshot
        cursor.execute("""
            SELECT
                strategy,
                balance,
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
            # Strategy exists but hasn't traded yet
            return StrategyPerformance(
                name=strategy_name,
                total_trades=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_pnl=0.0,
                roi=0.0,
                avg_confidence=0.0
            )

        # Calculate average confidence from decisions
        cursor.execute("""
            SELECT AVG(confidence)
            FROM decisions
            WHERE strategy = ? AND should_trade = 1
        """, (strategy_name,))

        avg_conf_row = cursor.fetchone()
        avg_confidence = avg_conf_row[0] if avg_conf_row and avg_conf_row[0] else 0.0

        return StrategyPerformance(
            name=row[0],
            total_trades=row[2],
            wins=row[3],
            losses=row[4],
            win_rate=row[5],
            total_pnl=row[6],
            roi=row[7],
            avg_confidence=avg_confidence
        )

    def query_agent_baseline(self) -> Optional[StrategyPerformance]:
        """Query performance of default agent-based strategy"""
        return self.query_strategy_performance('default')

    def analyze_all_ml_strategies(self) -> List[StrategyPerformance]:
        """Analyze all ML strategies"""
        results = []

        for strategy_name in self.ml_strategies:
            perf = self.query_strategy_performance(strategy_name)
            if perf:
                results.append(perf)

        return results

    def compare_ml_vs_agents(self) -> Dict[str, any]:
        """Compare ML strategies to agent baseline"""
        ml_results = self.analyze_all_ml_strategies()
        agent_baseline = self.query_agent_baseline()

        comparison = {
            'ml_strategies': ml_results,
            'agent_baseline': agent_baseline,
            'claimed_test_accuracy': self.claimed_test_accuracy,
            'analysis': {}
        }

        # Analyze ML vs claimed accuracy
        for ml_perf in ml_results:
            if ml_perf.total_trades >= 10:  # Minimum sample size
                accuracy_diff = ml_perf.win_rate - self.claimed_test_accuracy
                comparison['analysis'][ml_perf.name] = {
                    'actual_vs_claimed': accuracy_diff,
                    'performance_degradation': accuracy_diff < -0.05,  # 5% worse
                    'sample_size_sufficient': ml_perf.total_trades >= 30
                }

        # Compare ML vs agents
        if agent_baseline and agent_baseline.total_trades >= 10:
            best_ml = max(ml_results, key=lambda x: x.win_rate) if ml_results else None

            if best_ml and best_ml.total_trades >= 10:
                comparison['ml_vs_agents'] = {
                    'best_ml': best_ml.name,
                    'ml_win_rate': best_ml.win_rate,
                    'agent_win_rate': agent_baseline.win_rate,
                    'ml_advantage': best_ml.win_rate - agent_baseline.win_rate,
                    'ml_is_better': best_ml.win_rate > agent_baseline.win_rate,
                    'significance_threshold': 0.03  # 3% improvement needed for significance
                }

        return comparison

    def generate_report(self, output_path: str):
        """Generate markdown report"""
        comparison = self.compare_ml_vs_agents()

        ml_results = comparison['ml_strategies']
        agent_baseline = comparison['agent_baseline']

        lines = [
            "# ML Model Performance Analysis",
            "",
            "**Persona:** Victor \"Vic\" Ramanujan (Quantitative Strategist)",
            "**Task:** US-RC-021 - Test ML model on post-training data",
            "**Mindset:** Data-driven decisions. Test everything. Trust nothing.",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"**Claimed Test Accuracy:** {self.claimed_test_accuracy:.1%} (during training)",
            ""
        ]

        # Check if ML strategies have run
        ml_with_data = [ml for ml in ml_results if ml.total_trades > 0]

        if not ml_with_data:
            lines.extend([
                "❌ **NO ML STRATEGY DATA FOUND**",
                "",
                "None of the ML Random Forest strategies have executed trades yet.",
                "This suggests:",
                "1. Shadow trading may not be enabled for ML strategies",
                "2. ML strategies are not in the active shadow strategy list",
                "3. Bot has not run long enough to generate ML decisions",
                "",
                "### Strategies Checked:",
                ""
            ])

            for ml in ml_results:
                lines.append(f"- `{ml.name}`: {ml.total_trades} trades")

            lines.extend([
                "",
                "---",
                "",
                "## Recommendations",
                "",
                "### Immediate Actions:",
                "",
                "1. **Enable ML shadow trading:**",
                "   - Add ML strategies to `config/agent_config.py` → `SHADOW_STRATEGIES`",
                "   - Ensure `ENABLE_SHADOW_TRADING = True`",
                "",
                "2. **Run bot for 24-48 hours:**",
                "   - Need minimum 20-30 trades per strategy for statistical validity",
                "   - Monitor shadow dashboard: `python3 simulation/dashboard.py`",
                "",
                "3. **Re-run this analysis after data collection:**",
                "   ```bash",
                "   python3 scripts/research/ml_performance_analysis.py",
                "   ```",
                "",
                "### Long-term Questions:",
                "",
                "1. **Why is ML not deployed if 67.3% test accuracy claimed?**",
                "   - Test accuracy > 60% target",
                "   - Should be production-ready",
                "   - Gap suggests: model exists but not integrated, or performance concerns",
                "",
                "2. **Is the ML model file missing?**",
                "   - Check `models/` directory for saved model",
                "   - If missing: retrain or retrieve from training environment",
                "",
                "3. **Compare ML to current live strategy:**"
            ])

            if agent_baseline and agent_baseline.total_trades > 0:
                lines.extend([
                    f"   - Current live (agents): {agent_baseline.win_rate:.1%} WR on {agent_baseline.total_trades} trades",
                    f"   - Claimed ML: {self.claimed_test_accuracy:.1%} WR",
                    f"   - **Potential improvement: {(self.claimed_test_accuracy - agent_baseline.win_rate) * 100:.1f}%**",
                ])
            else:
                lines.append("   - No agent baseline data available for comparison")

        else:
            # ML data exists - full analysis
            best_ml = max(ml_with_data, key=lambda x: x.win_rate)

            lines.extend([
                f"**Best ML Strategy:** `{best_ml.name}` - {best_ml.win_rate:.1%} WR on {best_ml.total_trades} trades",
                ""
            ])

            if agent_baseline and agent_baseline.total_trades > 0:
                ml_advantage = best_ml.win_rate - agent_baseline.win_rate
                lines.append(f"**ML vs Agents:** {ml_advantage:+.1%} difference")

                if ml_advantage > 0.03:
                    lines.append("✅ **ML significantly outperforms agents** (>3% advantage)")
                elif ml_advantage < -0.03:
                    lines.append("❌ **Agents significantly outperform ML** (>3% disadvantage)")
                else:
                    lines.append("⚠️ **No significant difference** (within 3% margin)")
            else:
                lines.append("**ML vs Agents:** No agent baseline data for comparison")

            lines.extend([
                "",
                "---",
                "",
                "## ML Strategy Performance Details",
                ""
            ])

            for ml in ml_results:
                lines.extend([
                    f"### {ml.name}",
                    ""
                ])

                if ml.total_trades == 0:
                    lines.extend([
                        "❌ **No trades executed**",
                        "",
                        "Strategy may be:",
                        "- Too conservative (threshold too high)",
                        "- Not enabled in shadow trading config",
                        "- Filtering out all trades",
                        ""
                    ])
                else:
                    # Performance metrics
                    lines.extend([
                        "**Performance Metrics:**",
                        f"- Total Trades: {ml.total_trades}",
                        f"- Wins: {ml.wins}",
                        f"- Losses: {ml.losses}",
                        f"- Win Rate: {ml.win_rate:.1%}",
                        f"- Total P&L: ${ml.total_pnl:+.2f}",
                        f"- ROI: {ml.roi:+.1%}",
                        f"- Avg Confidence: {ml.avg_confidence:.1%}",
                        ""
                    ])

                    # Compare to claimed test accuracy
                    accuracy_diff = ml.win_rate - self.claimed_test_accuracy
                    lines.extend([
                        "**vs Claimed Test Accuracy (67.3%):**",
                        f"- Actual WR: {ml.win_rate:.1%}",
                        f"- Test WR: {self.claimed_test_accuracy:.1%}",
                        f"- Difference: {accuracy_diff:+.1%}",
                        ""
                    ])

                    if accuracy_diff < -0.10:
                        lines.append("🔴 **Severe degradation** (>10% worse) - Model may be overfitted")
                    elif accuracy_diff < -0.05:
                        lines.append("🟡 **Performance degradation** (5-10% worse) - Investigate data drift")
                    elif accuracy_diff >= 0:
                        lines.append("🟢 **Meeting or exceeding test accuracy** - Model generalizes well")
                    else:
                        lines.append("🟡 **Slight degradation** (<5% worse) - Within acceptable range")

                    lines.append("")

                    # Sample size assessment
                    if ml.total_trades < 30:
                        lines.extend([
                            "⚠️ **Sample size too small** (<30 trades)",
                            "- Need 30-50 trades for statistical confidence",
                            "- Current results may be noise",
                            ""
                        ])
                    elif ml.total_trades < 100:
                        lines.extend([
                            "⚠️ **Sample size moderate** (30-100 trades)",
                            "- Sufficient for initial assessment",
                            "- Need 100+ trades for high confidence",
                            ""
                        ])
                    else:
                        lines.extend([
                            "✅ **Sample size sufficient** (100+ trades)",
                            "- Results are statistically meaningful",
                            ""
                        ])

            lines.extend([
                "---",
                "",
                "## Agent Baseline Performance",
                ""
            ])

            if agent_baseline and agent_baseline.total_trades > 0:
                lines.extend([
                    f"**Strategy:** `{agent_baseline.name}` (current production)",
                    f"- Total Trades: {agent_baseline.total_trades}",
                    f"- Win Rate: {agent_baseline.win_rate:.1%}",
                    f"- Total P&L: ${agent_baseline.total_pnl:+.2f}",
                    f"- ROI: {agent_baseline.roi:+.1%}",
                    ""
                ])
            else:
                lines.extend([
                    "❌ **No agent baseline data**",
                    "",
                    "Cannot compare ML to agent performance without baseline data.",
                    ""
                ])

            lines.extend([
                "---",
                "",
                "## Statistical Comparison",
                ""
            ])

            if 'ml_vs_agents' in comparison:
                ml_vs_agents = comparison['ml_vs_agents']

                lines.extend([
                    f"**Best ML:** `{ml_vs_agents['best_ml']}` at {ml_vs_agents['ml_win_rate']:.1%}",
                    f"**Agent Baseline:** {ml_vs_agents['agent_win_rate']:.1%}",
                    f"**ML Advantage:** {ml_vs_agents['ml_advantage']:+.1%}",
                    ""
                ])

                if ml_vs_agents['ml_is_better']:
                    if ml_vs_agents['ml_advantage'] > ml_vs_agents['significance_threshold']:
                        lines.extend([
                            "✅ **RECOMMENDATION: Deploy ML**",
                            "",
                            f"ML shows significant advantage (>{ml_vs_agents['significance_threshold']:.0%}) over agents.",
                            "Action: Switch production to ML strategy",
                            ""
                        ])
                    else:
                        lines.extend([
                            "⚠️ **RECOMMENDATION: More testing**",
                            "",
                            f"ML advantage is marginal (<{ml_vs_agents['significance_threshold']:.0%}).",
                            "Action: Collect more data before switching",
                            ""
                        ])
                else:
                    lines.extend([
                        "❌ **RECOMMENDATION: Stick with agents**",
                        "",
                        "ML underperforms agent baseline.",
                        "Action: Investigate model issues or retrain",
                        ""
                    ])
            else:
                lines.extend([
                    "⚠️ **Insufficient data for comparison**",
                    "",
                    "Need more trades from both ML and agent strategies.",
                    ""
                ])

        lines.extend([
            "---",
            "",
            "## Conclusion",
            ""
        ])

        if not ml_with_data:
            lines.extend([
                "**Status:** ❌ **INCOMPLETE ANALYSIS**",
                "",
                "Cannot validate ML performance without trade data.",
                "",
                "**Next Steps:**",
                "1. Enable ML shadow trading in config",
                "2. Run bot for 48 hours minimum",
                "3. Re-run analysis with collected data",
                "4. Make deployment decision based on data",
                ""
            ])
        else:
            lines.extend([
                "**Status:** ✅ **ANALYSIS COMPLETE**",
                "",
                "ML strategies have sufficient data for evaluation.",
                ""
            ])

            if 'ml_vs_agents' in comparison:
                if comparison['ml_vs_agents']['ml_is_better'] and comparison['ml_vs_agents']['ml_advantage'] > 0.03:
                    lines.append("**Recommendation:** Deploy ML to production")
                else:
                    lines.append("**Recommendation:** Continue with agent-based strategy")

        # Write report
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"✅ Report generated: {output_path}")

    def generate_csv(self, output_path: str):
        """Generate CSV export"""
        comparison = self.compare_ml_vs_agents()

        ml_results = comparison['ml_strategies']
        agent_baseline = comparison['agent_baseline']

        lines = [
            "strategy_name,strategy_type,total_trades,wins,losses,win_rate,total_pnl,roi,avg_confidence,vs_test_accuracy,vs_agents"
        ]

        # ML strategies
        for ml in ml_results:
            accuracy_diff = ml.win_rate - self.claimed_test_accuracy if ml.total_trades > 0 else 0.0

            agent_diff = ""
            if agent_baseline and agent_baseline.total_trades > 0 and ml.total_trades > 0:
                agent_diff = f"{ml.win_rate - agent_baseline.win_rate:+.4f}"

            lines.append(
                f"{ml.name},ML,"
                f"{ml.total_trades},{ml.wins},{ml.losses},"
                f"{ml.win_rate:.4f},{ml.total_pnl:.2f},{ml.roi:.4f},"
                f"{ml.avg_confidence:.4f},{accuracy_diff:+.4f},{agent_diff}"
            )

        # Agent baseline
        if agent_baseline:
            lines.append(
                f"{agent_baseline.name},Agents,"
                f"{agent_baseline.total_trades},{agent_baseline.wins},{agent_baseline.losses},"
                f"{agent_baseline.win_rate:.4f},{agent_baseline.total_pnl:.2f},{agent_baseline.roi:.4f},"
                f"{agent_baseline.avg_confidence:.4f},N/A,0.0000"
            )

        # Claimed test accuracy (reference)
        lines.append(
            f"ML_Test_Claimed,Reference,"
            f"N/A,N/A,N/A,"
            f"{self.claimed_test_accuracy:.4f},N/A,N/A,N/A,0.0000,N/A"
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"✅ CSV generated: {output_path}")


def main():
    """Main entry point"""
    print("=" * 80)
    print("ML Performance Analysis (US-RC-021)")
    print("Persona: Victor 'Vic' Ramanujan - Quantitative Strategist")
    print("=" * 80)
    print()

    # Database path
    db_path = "simulation/trade_journal.db"

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        print()
        print("Shadow trading database doesn't exist yet.")
        print("This suggests shadow trading hasn't been enabled or run.")
        print()
        print("To enable shadow trading:")
        print("1. Edit config/agent_config.py")
        print("2. Set ENABLE_SHADOW_TRADING = True")
        print("3. Add ML strategies to SHADOW_STRATEGIES list")
        print("4. Run bot for 24-48 hours")
        print("5. Re-run this analysis")
        return 1

    # Initialize analyzer
    analyzer = MLPerformanceAnalyzer(db_path)

    if not analyzer.connect():
        return 1

    # Generate reports
    try:
        analyzer.generate_report("reports/vic_ramanujan/ml_vs_agents.md")
        analyzer.generate_csv("reports/vic_ramanujan/ml_vs_agents.csv")

        print()
        print("✅ Analysis complete!")
        print()
        print("View results:")
        print("  - Markdown: reports/vic_ramanujan/ml_vs_agents.md")
        print("  - CSV: reports/vic_ramanujan/ml_vs_agents.csv")

    finally:
        analyzer.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
