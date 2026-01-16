#!/usr/bin/env python3
"""
Detect Duplicate Trades in Bot Logs

Persona: Dr. Kenji Nakamoto (Data Forensics Specialist)
Context: "API retries or redemption bugs could create duplicate entries.
         These inflate win rates artificially."

This script identifies:
1. Exact duplicates (identical hash)
2. Near-duplicates (within 5s, same crypto/direction)
"""

import re
import hashlib
import csv
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple
from pathlib import Path


@dataclass
class Trade:
    """Represents a single trade from bot logs"""
    timestamp: datetime
    crypto: str
    direction: str
    entry_price: float
    shares: float
    line_number: int
    raw_line: str

    def hash_key(self) -> str:
        """Generate hash from trade attributes"""
        key = f"{self.timestamp.isoformat()}_{self.crypto}_{self.direction}_{self.entry_price:.6f}"
        return hashlib.md5(key.encode()).hexdigest()

    def is_near_duplicate(self, other: 'Trade', time_window_seconds: int = 5) -> bool:
        """Check if trade is near-duplicate of another"""
        if self.crypto != other.crypto or self.direction != other.direction:
            return False

        time_diff = abs((self.timestamp - other.timestamp).total_seconds())
        return time_diff <= time_window_seconds


class DuplicateDetector:
    """Detects duplicate and near-duplicate trades"""

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.trades: List[Trade] = []
        self.exact_duplicates: List[Tuple[Trade, Trade]] = []
        self.near_duplicates: List[Tuple[Trade, Trade]] = []

    def parse_logs(self):
        """Parse bot.log to extract ORDER PLACED entries"""
        order_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?'
            r'ORDER PLACED.*?'
            r'(BTC|ETH|SOL|XRP)\s+(Up|Down).*?'
            r'Entry:\s*\$?(\d+\.\d+).*?'
            r'Shares:\s*(\d+\.?\d*)',
            re.IGNORECASE
        )

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    match = order_pattern.search(line)
                    if match:
                        try:
                            timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                            crypto = match.group(2)
                            direction = match.group(3)
                            entry_price = float(match.group(4))
                            shares = float(match.group(5))

                            trade = Trade(
                                timestamp=timestamp,
                                crypto=crypto,
                                direction=direction,
                                entry_price=entry_price,
                                shares=shares,
                                line_number=line_num,
                                raw_line=line.strip()
                            )
                            self.trades.append(trade)
                        except (ValueError, IndexError) as e:
                            # Skip malformed entries
                            continue

        except FileNotFoundError:
            print(f"⚠️ Log file not found: {self.log_file}")
            print("   Using empty trade list (development environment)")

    def detect_exact_duplicates(self):
        """Find exact duplicates using hash comparison"""
        hash_map = {}

        for trade in self.trades:
            trade_hash = trade.hash_key()
            if trade_hash in hash_map:
                # Found exact duplicate
                original = hash_map[trade_hash]
                self.exact_duplicates.append((original, trade))
            else:
                hash_map[trade_hash] = trade

    def detect_near_duplicates(self, time_window: int = 5):
        """Find near-duplicates within time window"""
        # Sort trades by timestamp for efficient comparison
        sorted_trades = sorted(self.trades, key=lambda t: t.timestamp)

        for i in range(len(sorted_trades)):
            for j in range(i + 1, len(sorted_trades)):
                trade1 = sorted_trades[i]
                trade2 = sorted_trades[j]

                # Stop checking if time difference exceeds window
                time_diff = (trade2.timestamp - trade1.timestamp).total_seconds()
                if time_diff > time_window:
                    break

                # Check if near-duplicate (but not already exact duplicate)
                if trade1.is_near_duplicate(trade2, time_window):
                    # Verify not already in exact duplicates
                    is_exact = any(
                        (t1.line_number == trade1.line_number and t2.line_number == trade2.line_number) or
                        (t1.line_number == trade2.line_number and t2.line_number == trade1.line_number)
                        for t1, t2 in self.exact_duplicates
                    )
                    if not is_exact:
                        self.near_duplicates.append((trade1, trade2))

    def generate_report(self, output_csv: str):
        """Generate CSV report with duplicate analysis"""
        rows = []

        # Add exact duplicates
        for original, duplicate in self.exact_duplicates:
            rows.append({
                'type': 'EXACT',
                'trade1_timestamp': original.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trade1_line': original.line_number,
                'trade2_timestamp': duplicate.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trade2_line': duplicate.line_number,
                'crypto': original.crypto,
                'direction': original.direction,
                'entry_price': f"${original.entry_price:.2f}",
                'time_diff_seconds': 0,
                'suspected_cause': 'API retry or logging bug (identical timestamp)',
            })

        # Add near-duplicates
        for trade1, trade2 in self.near_duplicates:
            time_diff = abs((trade2.timestamp - trade1.timestamp).total_seconds())
            rows.append({
                'type': 'NEAR',
                'trade1_timestamp': trade1.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trade1_line': trade1.line_number,
                'trade2_timestamp': trade2.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'trade2_line': trade2.line_number,
                'crypto': trade1.crypto,
                'direction': trade1.direction,
                'entry_price': f"${trade1.entry_price:.2f}",
                'time_diff_seconds': int(time_diff),
                'suspected_cause': 'Possible retry within 5s or rapid re-entry',
            })

        # Write CSV
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if rows:
            with open(output_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'type', 'trade1_timestamp', 'trade1_line', 'trade2_timestamp',
                    'trade2_line', 'crypto', 'direction', 'entry_price',
                    'time_diff_seconds', 'suspected_cause'
                ])
                writer.writeheader()
                writer.writerows(rows)
        else:
            # Create empty CSV with headers
            with open(output_csv, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'type', 'trade1_timestamp', 'trade1_line', 'trade2_timestamp',
                    'trade2_line', 'crypto', 'direction', 'entry_price',
                    'time_diff_seconds', 'suspected_cause'
                ])
                writer.writeheader()

        return output_csv

    def generate_markdown_report(self, output_md: str):
        """Generate markdown summary report"""
        total_trades = len(self.trades)
        total_exact = len(self.exact_duplicates)
        total_near = len(self.near_duplicates)
        total_duplicates = total_exact + total_near

        duplicate_pct = (total_duplicates / total_trades * 100) if total_trades > 0 else 0

        report = f"""# Duplicate Trade Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analyst:** Dr. Kenji Nakamoto (Data Forensics Specialist)
**Purpose:** Detect API retries or logging bugs that inflate win rates artificially

---

## Executive Summary

- **Total Trades Analyzed:** {total_trades}
- **Exact Duplicates Found:** {total_exact}
- **Near-Duplicates Found:** {total_near} (within 5 seconds)
- **Total Duplicate Pairs:** {total_duplicates}
- **Duplicate Rate:** {duplicate_pct:.2f}%

"""

        # Assessment
        if duplicate_pct == 0:
            assessment = "🟢 **EXCELLENT** - No duplicates detected. Data integrity is high."
        elif duplicate_pct < 1:
            assessment = "🟡 **ACCEPTABLE** - Minor duplicate issues (<1%). Monitor for patterns."
        elif duplicate_pct < 5:
            assessment = "🟠 **WARNING** - Moderate duplicate rate (1-5%). Investigation recommended."
        else:
            assessment = "🔴 **CRITICAL** - High duplicate rate (>5%). Data integrity compromised."

        report += f"""### Data Integrity Assessment

{assessment}

---

## Findings

### Exact Duplicates

Exact duplicates share identical timestamp, crypto, direction, and entry price.
**Suspected Cause:** API retry logic, logging bug, or order placement retry.

"""

        if total_exact > 0:
            report += f"**Found {total_exact} exact duplicate pairs:**\n\n"
            report += "| Trade 1 Time | Trade 2 Time | Crypto | Direction | Entry Price | Line Numbers |\n"
            report += "|--------------|--------------|--------|-----------|-------------|-------------|\n"

            for original, duplicate in self.exact_duplicates[:10]:  # Show first 10
                report += f"| {original.timestamp.strftime('%H:%M:%S')} | {duplicate.timestamp.strftime('%H:%M:%S')} | {original.crypto} | {original.direction} | ${original.entry_price:.2f} | L{original.line_number}, L{duplicate.line_number} |\n"

            if total_exact > 10:
                report += f"\n_... and {total_exact - 10} more (see CSV for full list)_\n"
        else:
            report += "✅ No exact duplicates found.\n"

        report += "\n### Near-Duplicates\n\n"
        report += "Near-duplicates occur within 5 seconds with same crypto and direction.  \n"
        report += "**Suspected Cause:** Rapid re-entry, bot restart retry, or race condition.\n\n"

        if total_near > 0:
            report += f"**Found {total_near} near-duplicate pairs:**\n\n"
            report += "| Trade 1 Time | Trade 2 Time | Crypto | Direction | Entry Price | Time Diff (s) | Line Numbers |\n"
            report += "|--------------|--------------|--------|-----------|-------------|---------------|-------------|\n"

            for trade1, trade2 in self.near_duplicates[:10]:  # Show first 10
                time_diff = abs((trade2.timestamp - trade1.timestamp).total_seconds())
                report += f"| {trade1.timestamp.strftime('%H:%M:%S')} | {trade2.timestamp.strftime('%H:%M:%S')} | {trade1.crypto} | {trade1.direction} | ${trade1.entry_price:.2f} | {int(time_diff)} | L{trade1.line_number}, L{trade2.line_number} |\n"

            if total_near > 10:
                report += f"\n_... and {total_near - 10} more (see CSV for full list)_\n"
        else:
            report += "✅ No near-duplicates found.\n"

        report += "\n---\n\n## Recommendations\n\n"

        if total_duplicates == 0:
            report += "1. ✅ **No action needed** - Duplicate detection shows clean data\n"
            report += "2. 🔁 **Continue monitoring** - Run this check periodically\n"
        else:
            report += "1. 🔍 **Investigate root cause:**\n"
            report += "   - Check CLOB API retry logic in `bot/momentum_bot_v12.py`\n"
            report += "   - Review order placement error handling\n"
            report += "   - Verify idempotency keys are used (prevent duplicate orders)\n"
            report += "\n"
            report += "2. 🧹 **Clean data for analysis:**\n"
            report += "   - Remove duplicate entries before calculating win rate\n"
            report += f"   - Current inflated count: {total_duplicates} duplicate pairs\n"
            report += "   - True unique trades: ~{} (accounting for duplicates)\n".format(total_trades - total_duplicates)
            report += "\n"
            report += "3. 🛡️ **Prevent future duplicates:**\n"
            report += "   - Add unique trade ID to log entries\n"
            report += "   - Implement deduplication in log parser\n"
            report += "   - Use CLOB order ID as primary key (not timestamp)\n"

        report += "\n---\n\n## Data Sources\n\n"
        report += f"- **Log File:** `{self.log_file}`\n"
        report += f"- **CSV Export:** `reports/kenji_nakamoto/duplicate_analysis.csv`\n"
        report += f"- **Detection Method:** Hash-based (exact) + time-window (near)\n"
        report += f"- **Time Window:** 5 seconds (configurable)\n"

        report += "\n---\n\n## Technical Details\n\n"
        report += "### Detection Algorithm\n\n"
        report += "**Exact Duplicate Hash:**\n"
        report += "```python\n"
        report += "hash = MD5(timestamp + crypto + direction + entry_price)\n"
        report += "```\n\n"
        report += "**Near-Duplicate Logic:**\n"
        report += "```python\n"
        report += "if (same_crypto AND same_direction AND time_diff <= 5s):\n"
        report += "    flag_as_near_duplicate()\n"
        report += "```\n\n"

        # Write report
        output_path = Path(output_md)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_md, 'w') as f:
            f.write(report)

        return output_md


def main():
    """Main execution"""
    import sys

    # Default to production log path, fallback to local
    log_file = sys.argv[1] if len(sys.argv) > 1 else 'bot.log'

    print(f"🔬 Dr. Kenji Nakamoto - Duplicate Trade Detection")
    print(f"📂 Analyzing: {log_file}\n")

    detector = DuplicateDetector(log_file)

    # Parse logs
    print("📊 Parsing trade logs...")
    detector.parse_logs()
    print(f"   Found {len(detector.trades)} total trades\n")

    # Detect duplicates
    print("🔍 Detecting exact duplicates...")
    detector.detect_exact_duplicates()
    print(f"   Found {len(detector.exact_duplicates)} exact duplicate pairs\n")

    print("🔍 Detecting near-duplicates (within 5s)...")
    detector.detect_near_duplicates(time_window=5)
    print(f"   Found {len(detector.near_duplicates)} near-duplicate pairs\n")

    # Generate reports
    print("📝 Generating reports...")
    csv_path = detector.generate_report('reports/kenji_nakamoto/duplicate_analysis.csv')
    print(f"   ✅ CSV: {csv_path}")

    md_path = detector.generate_markdown_report('reports/kenji_nakamoto/duplicate_analysis.md')
    print(f"   ✅ Report: {md_path}\n")

    # Summary
    total_duplicates = len(detector.exact_duplicates) + len(detector.near_duplicates)
    if total_duplicates == 0:
        print("✅ CLEAN - No duplicates detected!")
    else:
        duplicate_pct = (total_duplicates / len(detector.trades) * 100) if len(detector.trades) > 0 else 0
        print(f"⚠️ DUPLICATES FOUND: {total_duplicates} pairs ({duplicate_pct:.2f}% of trades)")
        print(f"   See reports for details and recommendations")


if __name__ == '__main__':
    main()
