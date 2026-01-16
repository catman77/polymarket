#!/usr/bin/env python3
"""
Survivorship Bias Check - Period Selection Analysis
Dr. Kenji Nakamoto - Data Forensics Specialist

Objective: Test for survivorship bias by checking if any time periods are excluded

Activities:
1. Parse all trade timestamps, identify date range coverage
2. Check for gaps: Missing days (>24h between trades)
3. Calculate win rate per day, per week
4. Generate report with full date range, gaps, and win rate by period
"""

import re
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class Trade:
    """Represents a single trade"""
    def __init__(self, timestamp: datetime, crypto: str, direction: str, outcome: Optional[str] = None):
        self.timestamp = timestamp
        self.crypto = crypto
        self.direction = direction
        self.outcome = outcome  # WIN, LOSS, or None (incomplete)

    def is_complete(self) -> bool:
        return self.outcome is not None


class SurvivorshipBiasChecker:
    """Checks for survivorship bias in trade history"""

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.trades: List[Trade] = []
        self.daily_stats: Dict[str, Dict] = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0})
        self.weekly_stats: Dict[str, Dict] = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0})

    def parse_log_file(self):
        """Parse bot.log to extract all trades with timestamps"""
        print(f"[INFO] Parsing log file: {self.log_file}")

        if not os.path.exists(self.log_file):
            print(f"[WARN] Log file not found: {self.log_file}")
            return

        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Pattern to match ORDER PLACED entries
        order_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?ORDER PLACED.*?(BTC|ETH|SOL|XRP).*?(Up|Down)'

        # Pattern to match WIN/LOSS entries
        outcome_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?(WIN|LOSS).*?(BTC|ETH|SOL|XRP).*?(Up|Down)'

        # Extract orders
        orders = []
        for match in re.finditer(order_pattern, content, re.IGNORECASE):
            timestamp_str, crypto, direction = match.groups()
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                orders.append({
                    'timestamp': timestamp,
                    'crypto': crypto,
                    'direction': direction
                })
            except ValueError:
                continue

        print(f"[INFO] Found {len(orders)} order entries")

        # Extract outcomes
        outcomes = []
        for match in re.finditer(outcome_pattern, content, re.IGNORECASE):
            timestamp_str, outcome, crypto, direction = match.groups()
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                outcomes.append({
                    'timestamp': timestamp,
                    'outcome': outcome.upper(),
                    'crypto': crypto,
                    'direction': direction
                })
            except ValueError:
                continue

        print(f"[INFO] Found {len(outcomes)} outcome entries")

        # Match orders to outcomes (fuzzy matching by time window + crypto + direction)
        for order in orders:
            trade = Trade(
                timestamp=order['timestamp'],
                crypto=order['crypto'],
                direction=order['direction']
            )

            # Find matching outcome within 20 minutes
            for outcome in outcomes:
                time_diff = abs((outcome['timestamp'] - order['timestamp']).total_seconds())
                if (time_diff <= 1200 and  # 20 minutes
                    outcome['crypto'] == order['crypto'] and
                    outcome['direction'] == order['direction']):
                    trade.outcome = outcome['outcome']
                    break

            self.trades.append(trade)

        print(f"[INFO] Matched {len([t for t in self.trades if t.is_complete()])} complete trades")

    def analyze_date_coverage(self) -> Dict:
        """Analyze date range coverage and identify gaps"""
        if not self.trades:
            return {
                'start_date': None,
                'end_date': None,
                'total_days': 0,
                'trading_days': 0,
                'gaps': []
            }

        # Sort trades by timestamp
        sorted_trades = sorted(self.trades, key=lambda t: t.timestamp)

        start_date = sorted_trades[0].timestamp
        end_date = sorted_trades[-1].timestamp

        # Get all unique trading days
        trading_days = set()
        for trade in sorted_trades:
            trading_days.add(trade.timestamp.date())

        # Calculate total days in range
        total_days = (end_date.date() - start_date.date()).days + 1

        # Identify gaps (days with no trades)
        gaps = []
        current_date = start_date.date()
        prev_trade_date = start_date.date()

        for trade in sorted_trades:
            trade_date = trade.timestamp.date()
            days_gap = (trade_date - prev_trade_date).days

            if days_gap > 1:  # Gap of more than 1 day (>24h)
                gaps.append({
                    'start': prev_trade_date,
                    'end': trade_date,
                    'days': days_gap
                })

            prev_trade_date = trade_date

        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': total_days,
            'trading_days': len(trading_days),
            'gaps': gaps
        }

    def calculate_daily_stats(self):
        """Calculate win rate per day"""
        for trade in self.trades:
            if not trade.is_complete():
                continue

            day_key = trade.timestamp.strftime('%Y-%m-%d')
            self.daily_stats[day_key]['trades'] += 1

            if trade.outcome == 'WIN':
                self.daily_stats[day_key]['wins'] += 1
            elif trade.outcome == 'LOSS':
                self.daily_stats[day_key]['losses'] += 1

    def calculate_weekly_stats(self):
        """Calculate win rate per week"""
        for trade in self.trades:
            if not trade.is_complete():
                continue

            # Get ISO week number (year-week format)
            week_key = trade.timestamp.strftime('%Y-W%W')
            self.weekly_stats[week_key]['trades'] += 1

            if trade.outcome == 'WIN':
                self.weekly_stats[week_key]['wins'] += 1
            elif trade.outcome == 'LOSS':
                self.weekly_stats[week_key]['losses'] += 1

    def generate_report(self, output_file: str):
        """Generate markdown report"""
        print(f"[INFO] Generating report: {output_file}")

        # Analyze data
        coverage = self.analyze_date_coverage()
        self.calculate_daily_stats()
        self.calculate_weekly_stats()

        # Build report
        report = "# Survivorship Bias Check - Period Selection Analysis\n\n"
        report += "**Researcher:** Dr. Kenji Nakamoto (Data Forensics Specialist)\n\n"
        report += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "---\n\n"

        # Executive Summary
        report += "## Executive Summary\n\n"

        if not self.trades:
            report += "⚠️ **NO DATA AVAILABLE**\n\n"
            report += "No trades found in log file. Cannot assess survivorship bias.\n\n"
        else:
            complete_trades = len([t for t in self.trades if t.is_complete()])
            incomplete_trades = len(self.trades) - complete_trades

            report += f"- **Total Trades:** {len(self.trades)}\n"
            report += f"- **Complete Trades:** {complete_trades}\n"
            report += f"- **Incomplete Trades:** {incomplete_trades}\n"
            report += f"- **Date Range:** {coverage['start_date'].strftime('%Y-%m-%d') if coverage['start_date'] else 'N/A'} to {coverage['end_date'].strftime('%Y-%m-%d') if coverage['end_date'] else 'N/A'}\n"
            report += f"- **Total Days:** {coverage['total_days']}\n"
            report += f"- **Trading Days:** {coverage['trading_days']}\n"
            report += f"- **Missing Days:** {coverage['total_days'] - coverage['trading_days']}\n"
            report += f"- **Gaps Detected:** {len(coverage['gaps'])}\n\n"

            # Assessment
            if len(coverage['gaps']) == 0:
                report += "✅ **ASSESSMENT:** No gaps detected (all days have trading data)\n\n"
            elif len(coverage['gaps']) <= 2:
                report += "🟡 **ASSESSMENT:** Minor gaps detected (likely intentional downtime)\n\n"
            else:
                report += "🔴 **ASSESSMENT:** Multiple gaps detected (potential survivorship bias)\n\n"

        report += "---\n\n"

        # Date Range Coverage
        report += "## Date Range Coverage\n\n"

        if coverage['start_date']:
            report += f"**First Trade:** {coverage['start_date'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            report += f"**Last Trade:** {coverage['end_date'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            report += f"**Coverage:** {coverage['trading_days']}/{coverage['total_days']} days ({(coverage['trading_days']/coverage['total_days']*100):.1f}%)\n\n"
        else:
            report += "No date range available (no trades found)\n\n"

        # Gaps Found
        if coverage['gaps']:
            report += "### Gaps Found (>24h between trades)\n\n"
            report += "| Gap # | Start Date | End Date | Days |\n"
            report += "|-------|------------|----------|------|\n"

            for i, gap in enumerate(coverage['gaps'], 1):
                report += f"| {i} | {gap['start']} | {gap['end']} | {gap['days']} |\n"

            report += "\n"
        else:
            report += "### Gaps Found\n\n"
            report += "✅ No gaps detected\n\n"

        # Win Rate by Day
        report += "## Win Rate by Day\n\n"

        if self.daily_stats:
            report += "| Date | Trades | Wins | Losses | Win Rate |\n"
            report += "|------|--------|------|--------|----------|\n"

            for day in sorted(self.daily_stats.keys()):
                stats = self.daily_stats[day]
                trades = stats['trades']
                wins = stats['wins']
                losses = stats['losses']
                win_rate = (wins / trades * 100) if trades > 0 else 0.0

                report += f"| {day} | {trades} | {wins} | {losses} | {win_rate:.1f}% |\n"

            report += "\n"

            # Daily statistics
            daily_win_rates = [
                (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0.0
                for stats in self.daily_stats.values()
            ]

            if daily_win_rates:
                avg_daily_wr = sum(daily_win_rates) / len(daily_win_rates)
                min_daily_wr = min(daily_win_rates)
                max_daily_wr = max(daily_win_rates)

                report += f"**Average Daily Win Rate:** {avg_daily_wr:.1f}%\n\n"
                report += f"**Min Daily Win Rate:** {min_daily_wr:.1f}%\n\n"
                report += f"**Max Daily Win Rate:** {max_daily_wr:.1f}%\n\n"
        else:
            report += "No daily statistics available (no complete trades)\n\n"

        # Win Rate by Week
        report += "## Win Rate by Week\n\n"

        if self.weekly_stats:
            report += "| Week | Trades | Wins | Losses | Win Rate |\n"
            report += "|------|--------|------|--------|----------|\n"

            for week in sorted(self.weekly_stats.keys()):
                stats = self.weekly_stats[week]
                trades = stats['trades']
                wins = stats['wins']
                losses = stats['losses']
                win_rate = (wins / trades * 100) if trades > 0 else 0.0

                report += f"| {week} | {trades} | {wins} | {losses} | {win_rate:.1f}% |\n"

            report += "\n"

            # Weekly statistics
            weekly_win_rates = [
                (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0.0
                for stats in self.weekly_stats.values()
            ]

            if weekly_win_rates:
                avg_weekly_wr = sum(weekly_win_rates) / len(weekly_win_rates)
                min_weekly_wr = min(weekly_win_rates)
                max_weekly_wr = max(weekly_win_rates)

                report += f"**Average Weekly Win Rate:** {avg_weekly_wr:.1f}%\n\n"
                report += f"**Min Weekly Win Rate:** {min_weekly_wr:.1f}%\n\n"
                report += f"**Max Weekly Win Rate:** {max_weekly_wr:.1f}%\n\n"
        else:
            report += "No weekly statistics available (no complete trades)\n\n"

        # Survivorship Bias Assessment
        report += "## Survivorship Bias Assessment\n\n"

        if not self.trades:
            report += "⚠️ **INCONCLUSIVE:** No data available for assessment\n\n"
        elif len(coverage['gaps']) == 0:
            report += "✅ **LOW RISK:** All days in date range have trading data\n\n"
            report += "**Recommendation:** Data appears complete with no obvious period selection bias.\n\n"
        elif len(coverage['gaps']) <= 2:
            report += "🟡 **MODERATE RISK:** Minor gaps detected\n\n"
            report += "**Recommendation:** Review gap periods to verify they are intentional (e.g., maintenance, strategy changes).\n\n"
            report += "**Action Items:**\n"
            for i, gap in enumerate(coverage['gaps'], 1):
                report += f"- Investigate gap {i}: {gap['start']} to {gap['end']} ({gap['days']} days)\n"
            report += "\n"
        else:
            report += "🔴 **HIGH RISK:** Multiple gaps detected (potential survivorship bias)\n\n"
            report += "**Recommendation:** Data integrity compromised. Performance claims may be cherry-picked from favorable periods.\n\n"
            report += "**Action Items:**\n"
            report += "- Verify all gap periods are intentional and documented\n"
            report += "- Recalculate win rate including ALL periods (no exclusions)\n"
            report += "- If gaps are due to data loss, flag performance metrics as unreliable\n\n"

        # Write report
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(report)

        print(f"[SUCCESS] Report generated: {output_file}")


def main():
    """Main execution"""
    # Default paths
    log_file = "/opt/polymarket-autotrader/bot.log"

    # Check if running locally (development) or on VPS (production)
    if not os.path.exists(log_file):
        # Try local path
        log_file = "bot.log"
        if not os.path.exists(log_file):
            print("[WARN] bot.log not found in production or local path")
            print("[INFO] Creating report with empty data (development environment)")

    # Output file
    output_file = "reports/kenji_nakamoto/survivorship_bias_report.md"

    # Run analysis
    checker = SurvivorshipBiasChecker(log_file)
    checker.parse_log_file()
    checker.generate_report(output_file)

    print(f"\n[COMPLETE] Survivorship bias check complete")
    print(f"[COMPLETE] Review report: {output_file}")


if __name__ == "__main__":
    main()
