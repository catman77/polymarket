#!/usr/bin/env python3
"""
US-RC-016: Identify optimal timing window (win rate by epoch second)

Persona: James "Jimmy the Greek" Martinez (Market Microstructure Specialist)
Context: "Early trades (0-300s) vs late trades (720-900s) have different edges.
          Data will tell us which is best."

Analyzes win rate by timing window within 15-minute epochs (900 seconds).
Buckets trades by entry timing and tests statistical significance of differences.
Generates heatmap-style report showing win rate by 60-second buckets.
"""

import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
import math


@dataclass
class TimedTrade:
    """Trade with timing information"""
    timestamp: datetime
    crypto: str
    direction: str
    entry_price: float
    epoch_second: int  # Seconds into epoch (0-899)
    outcome: str  # "WIN" or "LOSS"

    def is_complete(self) -> bool:
        return self.outcome in ["WIN", "LOSS"]

    def timing_bucket(self) -> str:
        """Classify timing: early (0-300s), mid (300-600s), late (600-900s)"""
        if self.epoch_second < 300:
            return "early"
        elif self.epoch_second < 600:
            return "mid"
        else:
            return "late"

    def timing_minute(self) -> int:
        """Get minute bucket (0-14) for heatmap"""
        return self.epoch_second // 60


class TimingAnalyzer:
    """Analyzes win rate by timing window within epochs"""

    def __init__(self, log_file: str):
        self.log_file = Path(log_file)
        self.trades: List[TimedTrade] = []

    def parse_trades(self) -> None:
        """Parse trades from bot.log with timing information"""
        if not self.log_file.exists():
            print(f"⚠️  Log file not found: {self.log_file}")
            return

        # Parse ORDER PLACED entries
        order_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*ORDER PLACED.*'
            r'(BTC|ETH|SOL|XRP).*?(Up|Down).*?'
            r'Entry:?\s*\$?([0-9.]+)',
            re.IGNORECASE
        )

        # Parse WIN/LOSS entries
        outcome_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*'
            r'(WIN|LOSS).*?(BTC|ETH|SOL|XRP).*?(Up|Down)',
            re.IGNORECASE
        )

        orders = []
        outcomes = []

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Parse orders
                    order_match = order_pattern.search(line)
                    if order_match:
                        timestamp = datetime.strptime(order_match.group(1), '%Y-%m-%d %H:%M:%S')
                        crypto = order_match.group(2).upper()
                        direction = order_match.group(3)
                        entry_price = float(order_match.group(4))
                        orders.append((timestamp, crypto, direction, entry_price))

                    # Parse outcomes
                    outcome_match = outcome_pattern.search(line)
                    if outcome_match:
                        timestamp = datetime.strptime(outcome_match.group(1), '%Y-%m-%d %H:%M:%S')
                        outcome = outcome_match.group(2).upper()
                        crypto = outcome_match.group(3).upper()
                        direction = outcome_match.group(4)
                        outcomes.append((timestamp, crypto, direction, outcome))

        except Exception as e:
            print(f"⚠️  Error reading log file: {e}")
            return

        # Fuzzy match orders to outcomes (20 min window)
        for order_ts, order_crypto, order_dir, order_price in orders:
            for outcome_ts, outcome_crypto, outcome_dir, outcome_result in outcomes:
                # Match by crypto, direction, and time window
                time_diff = abs((outcome_ts - order_ts).total_seconds())
                if (outcome_crypto == order_crypto and
                    outcome_dir == order_dir and
                    time_diff < 1200):  # 20 min window

                    # Calculate seconds into epoch (15-min = 900s)
                    # Epoch starts on 15-min boundaries (00, 15, 30, 45)
                    minute = order_ts.minute
                    second = order_ts.second
                    epoch_start_minute = (minute // 15) * 15
                    seconds_into_epoch = ((minute - epoch_start_minute) * 60) + second

                    # Clamp to 0-899 range
                    seconds_into_epoch = max(0, min(899, seconds_into_epoch))

                    trade = TimedTrade(
                        timestamp=order_ts,
                        crypto=order_crypto,
                        direction=order_dir,
                        entry_price=order_price,
                        epoch_second=seconds_into_epoch,
                        outcome=outcome_result
                    )
                    self.trades.append(trade)
                    break  # Found match, move to next order

        print(f"✅ Parsed {len(self.trades)} complete trades from {len(orders)} orders")

    def calculate_bucket_stats(self) -> Dict[str, Tuple[int, int, float]]:
        """Calculate win rate by timing bucket (early/mid/late)"""
        buckets = defaultdict(lambda: {"wins": 0, "losses": 0})

        for trade in self.trades:
            bucket = trade.timing_bucket()
            if trade.outcome == "WIN":
                buckets[bucket]["wins"] += 1
            elif trade.outcome == "LOSS":
                buckets[bucket]["losses"] += 1

        # Calculate win rates
        bucket_stats = {}
        for bucket, counts in buckets.items():
            wins = counts["wins"]
            losses = counts["losses"]
            total = wins + losses
            win_rate = (wins / total) if total > 0 else 0.0
            bucket_stats[bucket] = (wins, total, win_rate)

        return bucket_stats

    def calculate_minute_heatmap(self) -> Dict[int, Tuple[int, int, float]]:
        """Calculate win rate by minute (0-14) for heatmap"""
        minutes = defaultdict(lambda: {"wins": 0, "losses": 0})

        for trade in self.trades:
            minute = trade.timing_minute()
            if trade.outcome == "WIN":
                minutes[minute]["wins"] += 1
            elif trade.outcome == "LOSS":
                minutes[minute]["losses"] += 1

        # Calculate win rates for each minute
        minute_stats = {}
        for minute in range(15):  # 0-14 minutes
            counts = minutes[minute]
            wins = counts["wins"]
            losses = counts["losses"]
            total = wins + losses
            win_rate = (wins / total) if total > 0 else 0.0
            minute_stats[minute] = (wins, total, win_rate)

        return minute_stats

    def chi_square_test(self, bucket_stats: Dict[str, Tuple[int, int, float]]) -> Tuple[float, str, str]:
        """
        Chi-square test for independence (timing vs outcome)

        Returns: (chi_square_statistic, p_value_category, significance)
        """
        # Build contingency table
        observed = []
        for bucket in ["early", "mid", "late"]:
            if bucket in bucket_stats:
                wins, total, _ = bucket_stats[bucket]
                losses = total - wins
                observed.append([wins, losses])
            else:
                observed.append([0, 0])

        # Check if we have sufficient data
        total_trades = sum(sum(row) for row in observed)
        if total_trades < 30:
            return 0.0, ">0.10", "INSUFFICIENT_DATA"

        # Calculate expected frequencies
        row_totals = [sum(row) for row in observed]
        col_totals = [sum(observed[i][j] for i in range(3)) for j in range(2)]
        grand_total = sum(row_totals)

        if grand_total == 0:
            return 0.0, ">0.10", "INSUFFICIENT_DATA"

        expected = []
        for i in range(3):
            expected.append([
                (row_totals[i] * col_totals[0]) / grand_total,
                (row_totals[i] * col_totals[1]) / grand_total
            ])

        # Calculate chi-square statistic
        chi_square = 0.0
        for i in range(3):
            for j in range(2):
                if expected[i][j] > 0:
                    chi_square += ((observed[i][j] - expected[i][j]) ** 2) / expected[i][j]

        # Degrees of freedom = (rows - 1) * (cols - 1) = 2 * 1 = 2
        df = 2

        # Critical values for df=2: 5.99 (p=0.05), 9.21 (p=0.01)
        if chi_square > 9.21:
            p_value = "<0.01"
            significance = "HIGHLY_SIGNIFICANT"
        elif chi_square > 5.99:
            p_value = "<0.05"
            significance = "SIGNIFICANT"
        else:
            p_value = ">0.05"
            significance = "NOT_SIGNIFICANT"

        return chi_square, p_value, significance

    def anova_test(self, bucket_stats: Dict[str, Tuple[int, int, float]]) -> str:
        """
        One-way ANOVA test (simplified F-statistic)

        Returns: interpretation string
        """
        # Extract win rates and sample sizes
        buckets = ["early", "mid", "late"]
        win_rates = []
        sample_sizes = []

        for bucket in buckets:
            if bucket in bucket_stats:
                _, total, wr = bucket_stats[bucket]
                if total >= 5:  # Minimum sample size
                    win_rates.append(wr)
                    sample_sizes.append(total)

        if len(win_rates) < 2:
            return "Insufficient data for ANOVA test"

        # Calculate grand mean
        total_wins = sum(wr * n for wr, n in zip(win_rates, sample_sizes))
        total_n = sum(sample_sizes)
        grand_mean = total_wins / total_n if total_n > 0 else 0.0

        # Between-group variance (simplified)
        between_ss = sum(n * ((wr - grand_mean) ** 2) for wr, n in zip(win_rates, sample_sizes))

        # Critical threshold: if between_ss is high, timing matters
        if between_ss > 0.05:  # 5% variance explained
            return "Timing window significantly affects win rate (ANOVA F-test)"
        else:
            return "No significant effect of timing window on win rate (ANOVA F-test)"

    def generate_markdown_report(self, output_file: str) -> None:
        """Generate comprehensive markdown report"""
        bucket_stats = self.calculate_bucket_stats()
        minute_heatmap = self.calculate_minute_heatmap()
        chi_square, p_value, significance = self.chi_square_test(bucket_stats)
        anova_result = self.anova_test(bucket_stats)

        # Determine optimal timing window
        optimal_bucket = None
        optimal_wr = 0.0
        if bucket_stats:
            for bucket, (wins, total, wr) in bucket_stats.items():
                if total >= 10 and wr > optimal_wr:
                    optimal_bucket = bucket
                    optimal_wr = wr

        # Generate report
        report_lines = [
            "# Timing Window Analysis Report",
            "",
            "**Persona:** James \"Jimmy the Greek\" Martinez (Market Microstructure Specialist)",
            "**Analysis Date:** " + datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            "**Data Source:** " + str(self.log_file),
            "",
            "---",
            "",
            "## Executive Summary",
            "",
            f"**Total Trades Analyzed:** {len(self.trades)}",
            f"**Statistical Significance:** {significance}",
            f"**Optimal Timing Window:** {optimal_bucket.upper() if optimal_bucket else 'INSUFFICIENT DATA'} "
            f"({optimal_wr*100:.1f}% WR)" if optimal_bucket else "INSUFFICIENT DATA",
            ""
        ]

        if len(self.trades) < 30:
            report_lines.extend([
                "⚠️ **WARNING:** Insufficient data for reliable analysis (need ≥30 trades).",
                ""
            ])
        elif significance == "SIGNIFICANT" or significance == "HIGHLY_SIGNIFICANT":
            report_lines.extend([
                f"✅ **Finding:** Timing window **significantly affects** win rate (p{p_value}).",
                f"🎯 **Recommendation:** Prioritize {optimal_bucket.upper()} entries ({optimal_wr*100:.1f}% WR).",
                ""
            ])
        else:
            report_lines.extend([
                f"⚠️ **Finding:** No significant effect of timing window on win rate (p{p_value}).",
                "💡 **Recommendation:** Focus on other factors (entry price, strategy, regime).",
                ""
            ])

        report_lines.extend([
            "---",
            "",
            "## Win Rate by Timing Bucket",
            "",
            "| Bucket | Timing Range | Trades | Wins | Losses | Win Rate |",
            "|--------|--------------|--------|------|--------|----------|"
        ])

        for bucket in ["early", "mid", "late"]:
            if bucket in bucket_stats:
                wins, total, wr = bucket_stats[bucket]
                losses = total - wins
                timing_range = {
                    "early": "0-300s (0-5 min)",
                    "mid": "300-600s (5-10 min)",
                    "late": "600-900s (10-15 min)"
                }[bucket]
                report_lines.append(
                    f"| {bucket.capitalize()} | {timing_range} | {total} | {wins} | {losses} | "
                    f"{wr*100:.1f}% |"
                )
            else:
                report_lines.append(f"| {bucket.capitalize()} | - | 0 | 0 | 0 | N/A |")

        report_lines.extend([
            "",
            "---",
            "",
            "## Statistical Significance Testing",
            "",
            "### Hypothesis Test",
            "- **H0 (Null):** Timing window does NOT affect win rate (independence)",
            "- **H1 (Alternative):** Timing window DOES affect win rate",
            "- **Test:** Chi-square test for independence",
            "- **Significance Level:** α = 0.05",
            "",
            "### Results",
            f"- **Chi-square statistic:** {chi_square:.2f}",
            f"- **p-value:** {p_value}",
            f"- **Verdict:** {significance}",
            "",
            "### ANOVA Test",
            f"- {anova_result}",
            "",
            "---",
            "",
            "## Timing Heatmap (Win Rate by Minute)",
            "",
            "**Color Legend:** 🟢 >60% | 🟡 50-60% | 🔴 <50%",
            ""
        ])

        # Generate ASCII heatmap
        for minute in range(15):
            wins, total, wr = minute_heatmap[minute]

            # Color coding
            if total == 0:
                color = "⚪"
                bar = ""
            elif wr >= 0.60:
                color = "🟢"
                bar = "█" * int(wr * 20)
            elif wr >= 0.50:
                color = "🟡"
                bar = "█" * int(wr * 20)
            else:
                color = "🔴"
                bar = "█" * int(wr * 20)

            wr_display = f"{wr*100:.1f}%" if total > 0 else "N/A"
            report_lines.append(
                f"Min {minute:2d} ({minute*60:3d}-{(minute+1)*60-1:3d}s): "
                f"{color} {bar:<20} {wr_display:>6} ({wins}/{total} trades)"
            )

        report_lines.extend([
            "",
            "---",
            "",
            "## Recommendations",
            ""
        ])

        if optimal_bucket:
            report_lines.extend([
                f"### ✅ Immediate Actions",
                f"1. **Prioritize {optimal_bucket.upper()} entries** ({optimal_wr*100:.1f}% WR)",
                f"2. Filter trades to {optimal_bucket} timing window (reject other windows)",
                f"3. Monitor if win rate improvement persists over 50+ trades",
                ""
            ])
        else:
            report_lines.extend([
                "### ⚠️ Data Collection Phase",
                "1. Continue trading across all timing windows (no filtering yet)",
                "2. Collect ≥30 trades before making timing recommendations",
                "3. Re-run this analysis weekly as data accumulates",
                ""
            ])

        report_lines.extend([
            "### 📊 Long-term Monitoring",
            "1. Track timing distribution (are we biased toward one window?)",
            "2. Compare timing performance across different regimes (bull/bear/choppy)",
            "3. Test interaction effects (timing × entry price × strategy)",
            "",
            "---",
            "",
            "## Methodology",
            "",
            "### Data Sources",
            "- **Trade Log:** " + str(self.log_file),
            "- **Epoch Length:** 15 minutes (900 seconds)",
            "- **Timing Calculation:** Seconds elapsed since epoch start",
            "",
            "### Analysis Steps",
            "1. Parse ORDER PLACED entries from bot.log",
            "2. Match to WIN/LOSS outcomes (20 min fuzzy window)",
            "3. Calculate seconds into epoch (epoch starts on 15-min boundaries)",
            "4. Bucket trades: early (0-300s), mid (300-600s), late (600-900s)",
            "5. Calculate win rate per bucket and per minute (0-14)",
            "6. Chi-square test: Test independence of timing vs outcome",
            "7. ANOVA: Test if timing explains variance in win rates",
            "8. Identify optimal timing window (highest WR, n ≥ 10)",
            "",
            "### Assumptions",
            "- Epoch boundaries detected from timestamp (15-min intervals)",
            "- Fuzzy matching allows 20-min window for outcome resolution",
            "- Minimum 10 trades per bucket for reliable estimates",
            "- Statistical significance at α = 0.05 (95% confidence)",
            "",
            "### Limitations",
            "- Small sample sizes (<30 trades) reduce statistical power",
            "- Timing effects may vary by regime (bull/bear/choppy)",
            "- Does not account for entry price or strategy interactions",
            "",
            "---",
            "",
            "## Appendix: Sample Trades",
            "",
            "| Timestamp | Crypto | Direction | Entry | Epoch Second | Timing | Outcome |",
            "|-----------|--------|-----------|-------|--------------|--------|---------|"
        ])

        # Show first 20 trades
        for i, trade in enumerate(self.trades[:20]):
            report_lines.append(
                f"| {trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"{trade.crypto} | {trade.direction} | ${trade.entry_price:.2f} | "
                f"{trade.epoch_second}s | {trade.timing_bucket()} | {trade.outcome} |"
            )

        if len(self.trades) > 20:
            report_lines.append(f"| ... | ... | ... | ... | ... | ... | ... |")
            report_lines.append(f"| *({len(self.trades)-20} more trades not shown)* | | | | | | |")

        report_lines.extend([
            "",
            "---",
            "",
            "**Report Generated:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            ""
        ])

        # Write report
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))

        print(f"✅ Generated markdown report: {output_file}")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        log_file = "bot.log"
    else:
        log_file = sys.argv[1]

    output_dir = "reports/jimmy_martinez"
    output_file = f"{output_dir}/timing_window_analysis.md"

    print("=" * 80)
    print("TIMING WINDOW ANALYSIS")
    print("=" * 80)
    print()
    print(f"📂 Log file: {log_file}")
    print(f"📊 Output: {output_file}")
    print()

    analyzer = TimingAnalyzer(log_file)
    analyzer.parse_trades()
    analyzer.generate_markdown_report(output_file)

    print()
    print("=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
