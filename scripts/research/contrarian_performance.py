#!/usr/bin/env python3
"""
US-RC-017: Evaluate contrarian strategy performance

Persona: James "Jimmy the Greek" Martinez (Market Microstructure Specialist)

Analyzes contrarian strategy trades from bot logs to determine if this strategy
should be re-enabled after being disabled.

Contrarian definition:
- Entry price <$0.20 (cheap entry on underpriced side)
- Opposite side >70% (fading overpriced market)
- Or: Log contains "SentimentAgent" or "CONTRARIAN" reasoning
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from collections import defaultdict


@dataclass
class Trade:
    """Represents a single trade from bot logs"""
    timestamp: datetime
    crypto: str
    direction: str
    entry_price: float
    shares: float = 0.0
    outcome: Optional[str] = None  # "WIN" or "LOSS"
    pnl: float = 0.0
    reasoning: str = ""  # Decision reasoning from logs

    def is_complete(self) -> bool:
        """Check if trade has outcome"""
        return self.outcome is not None

    def is_contrarian(self) -> bool:
        """
        Identify if this is a contrarian trade based on:
        1. Entry price <$0.20 (cheap entry)
        2. Reasoning contains "CONTRARIAN" or "SentimentAgent" with high confidence
        3. Opposite side was >70% (inferred from entry <$0.20)
        """
        # Cheap entry suggests contrarian (fading expensive opposite side)
        cheap_entry = self.entry_price < 0.20

        # Reasoning contains contrarian indicators
        contrarian_keywords = ["contrarian", "fade", "overpriced", "sentimentagent"]
        has_contrarian_reasoning = any(
            keyword in self.reasoning.lower()
            for keyword in contrarian_keywords
        )

        return cheap_entry or has_contrarian_reasoning

    def roi(self) -> float:
        """Calculate ROI as percentage"""
        cost = self.entry_price * self.shares
        if cost == 0:
            return 0.0
        return (self.pnl / cost) * 100


class ContrarianPerformanceAnalyzer:
    """Analyzes contrarian strategy performance from bot logs"""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.trades: List[Trade] = []
        self.contrarian_trades: List[Trade] = []
        self.non_contrarian_trades: List[Trade] = []

    def parse_trades(self) -> None:
        """Parse trades from bot log"""
        if not self.log_file.exists():
            print(f"Warning: Log file not found: {self.log_file}")
            return

        # Pattern for ORDER PLACED messages
        order_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*'
            r'ORDER PLACED.*?(BTC|ETH|SOL|XRP).*?(Up|Down).*?'
            r'Entry[:\s]*\$?([0-9.]+).*?'
            r'(\d+(?:\.\d+)?)\s+shares'
        )

        # Pattern for WIN/LOSS messages
        outcome_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?'
            r'(WIN|LOSS).*?(BTC|ETH|SOL|XRP).*?(Up|Down).*?'
            r'P&L[:\s]*\$?([+-]?[0-9.]+)'
        )

        orders = {}

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

                for line in lines:
                    # Parse ORDER PLACED
                    order_match = order_pattern.search(line)
                    if order_match:
                        timestamp_str = order_match.group(1)
                        crypto = order_match.group(2)
                        direction = order_match.group(3)
                        entry_price = float(order_match.group(4))
                        shares = float(order_match.group(5))

                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue

                        # Extract reasoning from log line (if available)
                        reasoning = ""
                        if "reasoning" in line.lower() or "agent" in line.lower():
                            reasoning = line

                        trade = Trade(
                            timestamp=timestamp,
                            crypto=crypto,
                            direction=direction,
                            entry_price=entry_price,
                            shares=shares,
                            reasoning=reasoning
                        )

                        # Store by key for fuzzy matching with outcome
                        key = f"{crypto}_{direction}_{timestamp.strftime('%Y%m%d%H%M')}"
                        orders[key] = trade

                    # Parse WIN/LOSS
                    outcome_match = outcome_pattern.search(line)
                    if outcome_match:
                        timestamp_str = outcome_match.group(1)
                        outcome = outcome_match.group(2)
                        crypto = outcome_match.group(3)
                        direction = outcome_match.group(4)
                        pnl = float(outcome_match.group(5))

                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            continue

                        # Fuzzy match to order (within 20 min window)
                        for time_offset in range(0, 21):
                            check_time = timestamp.replace(
                                minute=(timestamp.minute - time_offset) % 60,
                                second=0
                            )
                            key = f"{crypto}_{direction}_{check_time.strftime('%Y%m%d%H%M')}"

                            if key in orders:
                                orders[key].outcome = outcome
                                orders[key].pnl = pnl
                                break

        except Exception as e:
            print(f"Error parsing log file: {e}")

        # Convert to list and classify
        self.trades = list(orders.values())
        self.contrarian_trades = [t for t in self.trades if t.is_contrarian()]
        self.non_contrarian_trades = [t for t in self.trades if not t.is_contrarian()]

    def calculate_win_rate(self, trades: List[Trade]) -> Dict:
        """Calculate win rate for list of trades"""
        complete_trades = [t for t in trades if t.is_complete()]
        if not complete_trades:
            return {
                "total": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "avg_roi": 0.0
            }

        wins = [t for t in complete_trades if t.outcome == "WIN"]
        losses = [t for t in complete_trades if t.outcome == "LOSS"]
        total_pnl = sum(t.pnl for t in complete_trades)
        avg_pnl = total_pnl / len(complete_trades)
        avg_roi = sum(t.roi() for t in complete_trades) / len(complete_trades)

        return {
            "total": len(complete_trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(complete_trades) if complete_trades else 0.0,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "avg_roi": avg_roi
        }

    def generate_markdown_report(self, output_file: str) -> None:
        """Generate comprehensive markdown report"""
        contrarian_stats = self.calculate_win_rate(self.contrarian_trades)
        non_contrarian_stats = self.calculate_win_rate(self.non_contrarian_trades)
        all_stats = self.calculate_win_rate(self.trades)

        # Assessment
        assessment = self._assess_contrarian_performance(contrarian_stats, non_contrarian_stats)

        report_lines = [
            "# Contrarian Strategy Performance Analysis",
            "",
            "**Analyst:** James \"Jimmy the Greek\" Martinez (Market Microstructure Specialist)",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Data Source:** {self.log_file}",
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"**Assessment:** {assessment['verdict']}",
            f"**Recommendation:** {assessment['recommendation']}",
            "",
            "**Key Metrics:**",
            f"- Total Trades Analyzed: {len(self.trades)}",
            f"- Contrarian Trades: {len(self.contrarian_trades)} ({len(self.contrarian_trades)/max(1, len(self.trades))*100:.1f}%)",
            f"- Contrarian Win Rate: {contrarian_stats['win_rate']*100:.1f}% (n={contrarian_stats['total']})",
            f"- Non-Contrarian Win Rate: {non_contrarian_stats['win_rate']*100:.1f}% (n={non_contrarian_stats['total']})",
            "",
            "---",
            "",
            "## Strategy Performance Comparison",
            "",
            "### Contrarian Strategy",
            "",
            f"- **Total Trades:** {contrarian_stats['total']}",
            f"- **Wins:** {contrarian_stats['wins']}",
            f"- **Losses:** {contrarian_stats['losses']}",
            f"- **Win Rate:** {contrarian_stats['win_rate']*100:.1f}%",
            f"- **Total P&L:** ${contrarian_stats['total_pnl']:.2f}",
            f"- **Average P&L per Trade:** ${contrarian_stats['avg_pnl']:.2f}",
            f"- **Average ROI:** {contrarian_stats['avg_roi']:.1f}%",
            "",
            "### Non-Contrarian Strategy",
            "",
            f"- **Total Trades:** {non_contrarian_stats['total']}",
            f"- **Wins:** {non_contrarian_stats['wins']}",
            f"- **Losses:** {non_contrarian_stats['losses']}",
            f"- **Win Rate:** {non_contrarian_stats['win_rate']*100:.1f}%",
            f"- **Total P&L:** ${non_contrarian_stats['total_pnl']:.2f}",
            f"- **Average P&L per Trade:** ${non_contrarian_stats['avg_pnl']:.2f}",
            f"- **Average ROI:** {non_contrarian_stats['avg_roi']:.1f}%",
            "",
            "### All Trades (Baseline)",
            "",
            f"- **Total Trades:** {all_stats['total']}",
            f"- **Win Rate:** {all_stats['win_rate']*100:.1f}%",
            f"- **Total P&L:** ${all_stats['total_pnl']:.2f}",
            "",
            "---",
            "",
            "## ROI Analysis",
            "",
            self._generate_roi_comparison(contrarian_stats, non_contrarian_stats),
            "",
            "---",
            "",
            "## Assessment: Contrarian Strategy Value",
            "",
            assessment['detailed_analysis'],
            "",
            "---",
            "",
            "## Recommendations",
            "",
            assessment['recommendations'],
            "",
            "---",
            "",
            "## Sample Contrarian Trades",
            "",
            self._generate_sample_trades_table(self.contrarian_trades[:10]),
            "",
            "---",
            "",
            "## Methodology",
            "",
            "**Contrarian Trade Definition:**",
            "1. Entry price <$0.20 (cheap entry on underpriced side)",
            "2. Log reasoning contains 'contrarian', 'fade', 'overpriced', or 'SentimentAgent'",
            "3. Opposite side implied >70% probability (inferred from cheap entry)",
            "",
            "**Data Sources:**",
            f"- Bot log file: `{self.log_file}`",
            "- ORDER PLACED messages (entry data)",
            "- WIN/LOSS messages (outcome data)",
            "- Fuzzy matching within 20-minute window",
            "",
            "**Limitations:**",
            "- Reasoning text not always captured in logs (relying on entry price as proxy)",
            "- Opposite side probability not directly logged (inferred)",
            "- Sample size dependent on historical data availability",
            "",
            "---",
            "",
            "**Report Status:** COMPLETE ✅"
        ]

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))

        print(f"✅ Report generated: {output_path}")

    def _assess_contrarian_performance(self, contrarian: Dict, non_contrarian: Dict) -> Dict:
        """Assess contrarian strategy performance"""
        if contrarian['total'] == 0 and non_contrarian['total'] == 0:
            return {
                "verdict": "⚠️ INSUFFICIENT DATA",
                "recommendation": "COLLECT MORE DATA - No trades found in logs. Bot is currently halted (drawdown) and has not placed any trades yet. Re-run analysis after bot resumes trading and accumulates ≥20 contrarian trades.",
                "detailed_analysis": (
                    "**Current Status:** No trade data available.\n\n"
                    "**Data Collection Phase:** Bot is currently halted due to 30.8% drawdown. "
                    "Once peak_balance is reset and trading resumes, this analysis can be re-run.\n\n"
                    "**Required Sample Size:** ≥20 contrarian trades for meaningful statistical comparison."
                ),
                "recommendations": (
                    "**Immediate Actions:**\n"
                    "1. Reset peak_balance on VPS to resume trading\n"
                    "2. Enable contrarian trades temporarily (ENABLE_CONTRARIAN_TRADES=True)\n"
                    "3. Monitor for 5-10 days to accumulate sample size\n\n"
                    "**Analysis Re-run:**\n"
                    "- After ≥20 contrarian trades collected\n"
                    "- Compare win rate to non-contrarian baseline\n"
                    "- Evaluate ROI (accounting for cheap entry advantages)\n"
                )
            }

        if contrarian['total'] < 10:
            return {
                "verdict": "⚠️ INSUFFICIENT DATA",
                "recommendation": f"COLLECT MORE DATA - Only {contrarian['total']} contrarian trades found. Need ≥10 for reliable comparison.",
                "detailed_analysis": (
                    f"**Sample Size:** {contrarian['total']} contrarian trades (insufficient)\n\n"
                    "**Statistical Validity:** Minimum 10 trades required for reliable win rate estimate. "
                    "Current sample too small to determine if strategy is effective.\n\n"
                    "**Comparison:** Cannot reliably compare to non-contrarian trades yet."
                ),
                "recommendations": (
                    "**Immediate Actions:**\n"
                    "1. Continue data collection phase\n"
                    "2. Re-run analysis after 10+ contrarian trades\n\n"
                    "**Long-term:**\n"
                    "- Target ≥20 contrarian trades for robust statistical testing\n"
                    "- Monitor for regime-dependent performance (choppy vs trending)"
                )
            }

        # Calculate relative performance
        contrarian_wr = contrarian['win_rate']
        non_contrarian_wr = non_contrarian['win_rate']
        wr_diff = contrarian_wr - non_contrarian_wr
        roi_diff = contrarian['avg_roi'] - non_contrarian['avg_roi']

        # Decision logic
        if contrarian_wr > 0.65 and contrarian['avg_roi'] > 0:
            verdict = "🟢 EXCELLENT - Re-enable immediately"
            recommendation = "RE-ENABLE CONTRARIAN TRADES - Strong performance with 65%+ win rate"
        elif contrarian_wr > 0.60 and wr_diff > 0.05:
            verdict = "🟢 GOOD - Re-enable"
            recommendation = "RE-ENABLE CONTRARIAN TRADES - Outperforms non-contrarian by 5%+"
        elif contrarian_wr > 0.55 and contrarian['total_pnl'] > 0:
            verdict = "🟡 ACCEPTABLE - Re-enable with monitoring"
            recommendation = "RE-ENABLE WITH MONITORING - Positive ROI but moderate win rate"
        elif contrarian_wr < 0.50:
            verdict = "🔴 POOR - Keep disabled"
            recommendation = "KEEP DISABLED - Below breakeven performance"
        else:
            verdict = "🟡 MARGINAL - Keep disabled"
            recommendation = "KEEP DISABLED - No clear edge over non-contrarian"

        detailed_analysis = (
            f"**Win Rate Comparison:**\n"
            f"- Contrarian: {contrarian_wr*100:.1f}%\n"
            f"- Non-Contrarian: {non_contrarian_wr*100:.1f}%\n"
            f"- Difference: {wr_diff*100:+.1f} percentage points\n\n"
            f"**ROI Comparison:**\n"
            f"- Contrarian Avg ROI: {contrarian['avg_roi']:.1f}%\n"
            f"- Non-Contrarian Avg ROI: {non_contrarian['avg_roi']:.1f}%\n"
            f"- Difference: {roi_diff:+.1f} percentage points\n\n"
            f"**Profitability:**\n"
            f"- Contrarian Total P&L: ${contrarian['total_pnl']:.2f}\n"
            f"- Non-Contrarian Total P&L: ${non_contrarian['total_pnl']:.2f}\n\n"
            f"**Interpretation:** {self._interpret_performance(wr_diff, roi_diff, contrarian)}"
        )

        recommendations_text = self._generate_recommendations(verdict, contrarian, non_contrarian)

        return {
            "verdict": verdict,
            "recommendation": recommendation,
            "detailed_analysis": detailed_analysis,
            "recommendations": recommendations_text
        }

    def _interpret_performance(self, wr_diff: float, roi_diff: float, contrarian: Dict) -> str:
        """Interpret performance differences"""
        if contrarian['total'] == 0:
            return "No data available for interpretation."

        if wr_diff > 0.10:
            return (
                "Contrarian strategy significantly outperforms (+10% WR). "
                "Strong evidence for re-enabling. Cheap entries provide both better odds and higher ROI."
            )
        elif wr_diff > 0.05:
            return (
                "Contrarian strategy moderately outperforms (+5% WR). "
                "Clear edge over non-contrarian. Recommend re-enabling."
            )
        elif wr_diff > 0 and roi_diff > 0:
            return (
                "Contrarian strategy slightly outperforms on both WR and ROI. "
                "Marginal but positive edge. Consider re-enabling with monitoring."
            )
        elif wr_diff < -0.05:
            return (
                "Contrarian strategy underperforms (-5% WR). "
                "No edge detected. Recommend keeping disabled."
            )
        else:
            return (
                "Performance difference within random variance. "
                "No clear edge. Additional data needed or keep disabled as default."
            )

    def _generate_recommendations(self, verdict: str, contrarian: Dict, non_contrarian: Dict) -> str:
        """Generate actionable recommendations based on verdict"""
        if "INSUFFICIENT DATA" in verdict:
            return (
                "**Immediate Actions:**\n"
                "1. Reset peak_balance to resume trading\n"
                "2. Enable contrarian temporarily (ENABLE_CONTRARIAN_TRADES=True in config)\n"
                "3. Monitor for 5-10 days\n\n"
                "**Data Collection:**\n"
                "- Target: ≥20 contrarian trades\n"
                "- Re-run analysis after collection phase\n"
            )
        elif "EXCELLENT" in verdict:
            return (
                "**Immediate Actions:**\n"
                "1. Set ENABLE_CONTRARIAN_TRADES=True in config/agent_config.py\n"
                "2. Deploy to VPS immediately\n"
                "3. Monitor performance for first 20 trades\n\n"
                "**Expected Impact:**\n"
                f"- Win rate improvement: {contrarian['win_rate']*100:.1f}% (contrarian component)\n"
                f"- ROI boost from cheap entries (<$0.20)\n"
                "- Better performance in choppy/sideways regimes\n"
            )
        elif "GOOD" in verdict:
            return (
                "**Immediate Actions:**\n"
                "1. Set ENABLE_CONTRARIAN_TRADES=True\n"
                "2. Deploy to VPS\n"
                "3. Set up monitoring alerts\n\n"
                "**Monitoring:**\n"
                "- Track contrarian win rate daily\n"
                "- Alert if WR drops below 55%\n"
                "- Disable if 10-trade rolling WR <50%\n"
            )
        elif "ACCEPTABLE" in verdict:
            return (
                "**Immediate Actions:**\n"
                "1. Enable contrarian with higher consensus threshold (0.75 → 0.80)\n"
                "2. Deploy to VPS\n"
                "3. Close monitoring required\n\n"
                "**Risk Mitigation:**\n"
                "- Increase SentimentAgent weight requirement\n"
                "- Only trade in sideways regime (disable in strong trends)\n"
                "- Stop if cumulative P&L turns negative\n"
            )
        else:  # POOR or MARGINAL
            return (
                "**Immediate Actions:**\n"
                "1. Keep ENABLE_CONTRARIAN_TRADES=False (current setting)\n"
                "2. Focus on non-contrarian strategies\n"
                "3. Re-evaluate in 30 days with more data\n\n"
                "**Alternative Approaches:**\n"
                "- Test higher entry thresholds ($0.15-$0.25 instead of <$0.20)\n"
                "- Combine with regime filter (only in sideways markets)\n"
                "- Adjust SentimentAgent calibration\n"
            )

    def _generate_roi_comparison(self, contrarian: Dict, non_contrarian: Dict) -> str:
        """Generate ROI comparison analysis"""
        if contrarian['total'] == 0 and non_contrarian['total'] == 0:
            return (
                "**ROI Comparison:** No data available.\n\n"
                "ROI analysis requires completed trades with P&L data. "
                "Re-run after data collection phase."
            )

        lines = [
            "**ROI per $1 Wagered:**",
            "",
            "| Strategy | Avg Entry Price | Avg ROI | Total P&L | Trades |",
            "|----------|----------------|---------|-----------|--------|",
        ]

        if contrarian['total'] > 0:
            avg_entry = sum(t.entry_price for t in self.contrarian_trades if t.is_complete()) / max(1, len([t for t in self.contrarian_trades if t.is_complete()]))
            lines.append(
                f"| Contrarian | ${avg_entry:.3f} | {contrarian['avg_roi']:+.1f}% | ${contrarian['total_pnl']:+.2f} | {contrarian['total']} |"
            )

        if non_contrarian['total'] > 0:
            avg_entry = sum(t.entry_price for t in self.non_contrarian_trades if t.is_complete()) / max(1, len([t for t in self.non_contrarian_trades if t.is_complete()]))
            lines.append(
                f"| Non-Contrarian | ${avg_entry:.3f} | {non_contrarian['avg_roi']:+.1f}% | ${non_contrarian['total_pnl']:+.2f} | {non_contrarian['total']} |"
            )

        lines.extend([
            "",
            "**Key Insight:**",
            (
                "Contrarian trades benefit from cheaper entry prices (<$0.20), "
                "which provide higher ROI multipliers when winning. "
                "A $0.10 entry that wins pays 10x, vs a $0.25 entry that pays 4x."
            )
        ])

        return '\n'.join(lines)

    def _generate_sample_trades_table(self, trades: List[Trade]) -> str:
        """Generate sample trades table"""
        if not trades:
            return "No contrarian trades found in logs."

        lines = [
            "| Timestamp | Crypto | Direction | Entry | Outcome | P&L | ROI |",
            "|-----------|--------|-----------|-------|---------|-----|-----|",
        ]

        for trade in trades:
            timestamp_str = trade.timestamp.strftime('%Y-%m-%d %H:%M')
            outcome_str = trade.outcome if trade.outcome else "PENDING"
            pnl_str = f"${trade.pnl:+.2f}" if trade.outcome else "N/A"
            roi_str = f"{trade.roi():+.1f}%" if trade.outcome else "N/A"

            lines.append(
                f"| {timestamp_str} | {trade.crypto} | {trade.direction} | "
                f"${trade.entry_price:.3f} | {outcome_str} | {pnl_str} | {roi_str} |"
            )

        return '\n'.join(lines)


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze contrarian strategy performance')
    parser.add_argument(
        '--log-file',
        default='bot.log',
        help='Path to bot log file (default: bot.log)'
    )
    parser.add_argument(
        '--output',
        default='reports/jimmy_martinez/contrarian_performance.md',
        help='Output markdown report path'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Contrarian Strategy Performance Analysis")
    print("=" * 80)
    print()

    analyzer = ContrarianPerformanceAnalyzer(args.log_file)

    print(f"📂 Parsing trades from: {args.log_file}")
    analyzer.parse_trades()

    print(f"📊 Total trades parsed: {len(analyzer.trades)}")
    print(f"   - Contrarian: {len(analyzer.contrarian_trades)}")
    print(f"   - Non-Contrarian: {len(analyzer.non_contrarian_trades)}")
    print()

    print(f"📝 Generating report: {args.output}")
    analyzer.generate_markdown_report(args.output)
    print()

    print("=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    sys.exit(main())
