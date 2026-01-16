#!/usr/bin/env python3
"""
Task 7.4: Statistical Anomaly Detection
Researcher: Dr. Kenji Nakamoto - Data Forensics Specialist

Identifies suspicious patterns in trading data through:
1. Win rate clustering (rolling 20-trade window)
2. Outcome distribution analysis (Bernoulli test)
3. Entry price anomalies (impossible/suspicious prices)
4. Temporal patterns (performance by hour)
5. Crypto-specific anomalies (win rate consistency)
6. Shadow strategy sanity checks
7. Outlier detection (extreme P&L events)
"""

import os
import re
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class Trade:
    """Trade data structure"""
    timestamp: datetime
    crypto: str
    direction: str
    entry_price: float
    outcome: Optional[str] = None  # WIN/LOSS
    pnl: float = 0.0

@dataclass
class AnomalyResult:
    """Anomaly detection result"""
    category: str
    severity: str  # 🟢 LOW, 🟡 MODERATE, 🔴 HIGH
    description: str
    evidence: str

def parse_bot_logs(log_path: str = "bot.log") -> List[Trade]:
    """Parse bot.log to extract all trades"""
    trades = []

    if not os.path.exists(log_path):
        print(f"⚠️  Log file not found: {log_path}")
        return trades

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Parse ORDER PLACED entries
        order_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*ORDER PLACED.*?([A-Z]{3,4}).*?(Up|Down).*?Entry[:\s]*\$?([\d.]+)'
        outcome_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*?(WIN|LOSS).*?([A-Z]{3,4}).*?(Up|Down).*?\$?([-\d.]+)'

        # First pass: collect orders
        orders = []
        for line in lines:
            match = re.search(order_pattern, line, re.IGNORECASE)
            if match:
                timestamp_str, crypto, direction, entry = match.groups()
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    entry_price = float(entry)

                    orders.append(Trade(
                        timestamp=timestamp,
                        crypto=crypto,
                        direction=direction,
                        entry_price=entry_price
                    ))
                except (ValueError, AttributeError):
                    continue

        # Second pass: match outcomes
        for line in lines:
            match = re.search(outcome_pattern, line, re.IGNORECASE)
            if match:
                timestamp_str, outcome, crypto, direction, pnl_str = match.groups()
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    pnl = float(pnl_str)

                    # Find matching order within 20 minutes
                    for order in orders:
                        time_diff = abs((timestamp - order.timestamp).total_seconds())
                        if (time_diff < 1200 and  # 20 minutes
                            order.crypto == crypto and
                            order.direction == direction and
                            order.outcome is None):
                            order.outcome = outcome
                            order.pnl = pnl
                            break
                except (ValueError, AttributeError):
                    continue

        trades = [t for t in orders if t.outcome is not None]

    except Exception as e:
        print(f"⚠️  Error parsing logs: {e}")

    return trades

def analyze_win_rate_clustering(trades: List[Trade], window: int = 20) -> List[AnomalyResult]:
    """Detect suspicious clustering in rolling win rate"""
    anomalies = []

    if len(trades) < window:
        return anomalies

    rolling_win_rates = []
    for i in range(len(trades) - window + 1):
        window_trades = trades[i:i+window]
        wins = sum(1 for t in window_trades if t.outcome == 'WIN')
        win_rate = wins / window
        rolling_win_rates.append(win_rate)

    # Check for sudden jumps
    for i in range(1, len(rolling_win_rates)):
        jump = abs(rolling_win_rates[i] - rolling_win_rates[i-1])
        if jump > 0.30:  # 30% jump
            anomalies.append(AnomalyResult(
                category='Win Rate Clustering',
                severity='🔴 HIGH',
                description=f'Sudden {jump*100:.1f}% jump in rolling win rate',
                evidence=f'Window {i-1}: {rolling_win_rates[i-1]*100:.1f}% → Window {i}: {rolling_win_rates[i]*100:.1f}%'
            ))

    # Check for suspiciously stable win rate
    if len(rolling_win_rates) >= 5:
        variance = sum((wr - sum(rolling_win_rates)/len(rolling_win_rates))**2 for wr in rolling_win_rates) / len(rolling_win_rates)
        if variance < 0.001:  # Too stable
            anomalies.append(AnomalyResult(
                category='Win Rate Clustering',
                severity='🟡 MODERATE',
                description='Win rate suspiciously stable (low variance)',
                evidence=f'Variance: {variance:.6f} (expected >0.01 for random process)'
            ))

    return anomalies

def analyze_outcome_distribution(trades: List[Trade]) -> List[AnomalyResult]:
    """Test if outcomes follow Bernoulli distribution"""
    anomalies = []

    if len(trades) < 30:
        return anomalies

    wins = sum(1 for t in trades if t.outcome == 'WIN')
    losses = len(trades) - wins

    # Check for unnatural clustering (runs test)
    runs = 1
    for i in range(1, len(trades)):
        if trades[i].outcome != trades[i-1].outcome:
            runs += 1

    # Expected runs for independent outcomes
    n = len(trades)
    expected_runs = (2 * wins * losses) / n + 1 if n > 0 else 0

    if expected_runs > 0:
        # If actual runs much lower than expected, outcomes are clustered
        if runs < expected_runs * 0.7:
            anomalies.append(AnomalyResult(
                category='Outcome Distribution',
                severity='🔴 HIGH',
                description='Outcomes clustered together (not independent)',
                evidence=f'Actual runs: {runs}, Expected: {expected_runs:.1f} (too few runs = clustering)'
            ))
        elif runs > expected_runs * 1.3:
            anomalies.append(AnomalyResult(
                category='Outcome Distribution',
                severity='🟡 MODERATE',
                description='Outcomes alternating too frequently',
                evidence=f'Actual runs: {runs}, Expected: {expected_runs:.1f} (too many runs = alternating pattern)'
            ))

    return anomalies

def analyze_entry_prices(trades: List[Trade]) -> List[AnomalyResult]:
    """Detect suspicious entry price patterns"""
    anomalies = []

    if not trades:
        return anomalies

    entry_prices = [t.entry_price for t in trades]

    # Check for impossible prices
    for i, price in enumerate(entry_prices):
        if price < 0.01 or price > 0.99:
            anomalies.append(AnomalyResult(
                category='Entry Price',
                severity='🔴 HIGH',
                description=f'Impossible entry price: ${price:.2f}',
                evidence=f'Trade {i+1}: {trades[i].crypto} {trades[i].direction} at ${price:.2f} (binary options must be $0.01-$0.99)'
            ))

    # Check for suspicious uniformity (all same price)
    if len(set(entry_prices)) == 1 and len(entry_prices) >= 5:
        anomalies.append(AnomalyResult(
            category='Entry Price',
            severity='🟡 MODERATE',
            description=f'All {len(entry_prices)} trades at identical price',
            evidence=f'All entries at ${entry_prices[0]:.2f} (suspicious uniformity)'
        ))

    # Check for unrealistic precision (e.g., always .250000)
    precision_counts = defaultdict(int)
    for price in entry_prices:
        decimal_places = len(str(price).split('.')[-1]) if '.' in str(price) else 0
        precision_counts[decimal_places] += 1

    if any(count >= len(entry_prices) * 0.9 for count in precision_counts.values()):
        anomalies.append(AnomalyResult(
            category='Entry Price',
            severity='🟢 LOW',
            description='Entry prices have consistent decimal precision',
            evidence=f'Most prices have same decimal places (likely normal)'
        ))

    return anomalies

def analyze_temporal_patterns(trades: List[Trade]) -> List[AnomalyResult]:
    """Detect time-based anomalies"""
    anomalies = []

    if len(trades) < 20:
        return anomalies

    # Group by hour of day
    hourly_performance = defaultdict(lambda: {'wins': 0, 'total': 0})
    for trade in trades:
        hour = trade.timestamp.hour
        hourly_performance[hour]['total'] += 1
        if trade.outcome == 'WIN':
            hourly_performance[hour]['wins'] += 1

    # Check for hours with perfect/terrible win rates
    for hour, stats in hourly_performance.items():
        if stats['total'] >= 5:  # Require minimum sample
            win_rate = stats['wins'] / stats['total']
            if win_rate == 1.0:
                anomalies.append(AnomalyResult(
                    category='Temporal Pattern',
                    severity='🔴 HIGH',
                    description=f'100% win rate during hour {hour}:00',
                    evidence=f'{stats["wins"]}/{stats["total"]} wins (suspicious perfection)'
                ))
            elif win_rate == 0.0:
                anomalies.append(AnomalyResult(
                    category='Temporal Pattern',
                    severity='🔴 HIGH',
                    description=f'0% win rate during hour {hour}:00',
                    evidence=f'0/{stats["total"]} wins (suspicious failure)'
                ))

    return anomalies

def analyze_crypto_specific(trades: List[Trade]) -> List[AnomalyResult]:
    """Detect crypto-specific anomalies"""
    anomalies = []

    if len(trades) < 20:
        return anomalies

    # Group by crypto
    crypto_performance = defaultdict(lambda: {'wins': 0, 'total': 0})
    for trade in trades:
        crypto_performance[trade.crypto]['total'] += 1
        if trade.outcome == 'WIN':
            crypto_performance[trade.crypto]['wins'] += 1

    # Calculate win rates
    crypto_win_rates = {}
    for crypto, stats in crypto_performance.items():
        if stats['total'] >= 5:
            crypto_win_rates[crypto] = stats['wins'] / stats['total']

    # Check for large disparities
    if len(crypto_win_rates) >= 2:
        max_wr = max(crypto_win_rates.values())
        min_wr = min(crypto_win_rates.values())

        if max_wr - min_wr > 0.40:  # 40% disparity
            max_crypto = max(crypto_win_rates, key=crypto_win_rates.get)
            min_crypto = min(crypto_win_rates, key=crypto_win_rates.get)

            anomalies.append(AnomalyResult(
                category='Crypto-Specific',
                severity='🔴 HIGH',
                description=f'Large win rate disparity between cryptos',
                evidence=f'{max_crypto}: {max_wr*100:.1f}% vs {min_crypto}: {min_wr*100:.1f}% (strategy should be crypto-agnostic)'
            ))

    return anomalies

def analyze_shadow_strategies(db_path: str = "simulation/trade_journal.db") -> List[AnomalyResult]:
    """Sanity check shadow strategy results"""
    anomalies = []

    if not os.path.exists(db_path):
        return anomalies

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if random baseline beats default
        query = """
        SELECT
            s.name,
            COUNT(DISTINCT o.id) as trades,
            SUM(CASE WHEN o.actual_direction = o.predicted_direction THEN 1 ELSE 0 END) as wins,
            SUM(o.pnl) as total_pnl
        FROM strategies s
        LEFT JOIN outcomes o ON s.name = o.strategy
        WHERE o.id IS NOT NULL
        GROUP BY s.name
        """

        cursor.execute(query)
        results = cursor.fetchall()

        baseline_pnl = None
        default_pnl = None
        inverse_winners = []

        for name, trades, wins, pnl in results:
            win_rate = (wins / trades * 100) if trades > 0 else 0

            if 'baseline' in name.lower() or 'random' in name.lower():
                baseline_pnl = pnl
            elif 'default' in name.lower():
                default_pnl = pnl
            elif 'inverse' in name.lower() and win_rate > 50:
                inverse_winners.append((name, win_rate))

        # Sanity check: baseline shouldn't beat default
        if baseline_pnl is not None and default_pnl is not None:
            if baseline_pnl > default_pnl * 1.5:
                anomalies.append(AnomalyResult(
                    category='Shadow Strategy',
                    severity='🔴 HIGH',
                    description='Random baseline outperforming default strategy',
                    evidence=f'Baseline: ${baseline_pnl:.2f} vs Default: ${default_pnl:.2f} (impossible if default has edge)'
                ))

        # Check inverse strategies
        if inverse_winners:
            anomalies.append(AnomalyResult(
                category='Shadow Strategy',
                severity='🔴 HIGH',
                description='Inverse strategies winning',
                evidence=f'{len(inverse_winners)} inverse strategies with >50% WR (agents are anti-predictive!)'
            ))

        conn.close()

    except Exception as e:
        print(f"⚠️  Error analyzing shadow strategies: {e}")

    return anomalies

def detect_outliers(trades: List[Trade]) -> List[AnomalyResult]:
    """Identify extreme P&L events"""
    anomalies = []

    if not trades:
        return anomalies

    pnl_values = [t.pnl for t in trades]

    # Calculate mean and std dev
    mean_pnl = sum(pnl_values) / len(pnl_values)
    variance = sum((pnl - mean_pnl)**2 for pnl in pnl_values) / len(pnl_values)
    std_dev = variance ** 0.5

    # Find outliers (>3 std dev from mean)
    outliers = []
    for i, trade in enumerate(trades):
        if abs(trade.pnl - mean_pnl) > 3 * std_dev:
            outliers.append((i, trade))

    if outliers:
        for idx, trade in outliers[:5]:  # Show top 5
            anomalies.append(AnomalyResult(
                category='Outlier P&L',
                severity='🟡 MODERATE',
                description=f'Extreme P&L event (>3σ from mean)',
                evidence=f'Trade {idx+1}: {trade.crypto} {trade.direction} → ${trade.pnl:.2f} (mean: ${mean_pnl:.2f}, σ: ${std_dev:.2f})'
            ))

    return anomalies

def generate_summary_report(all_anomalies: List[AnomalyResult], trades: List[Trade], output_path: str):
    """Generate comprehensive anomaly summary report"""

    report = f"""# Task 7.4: Statistical Anomaly Detection Report

**Researcher:** Dr. Kenji Nakamoto - Data Forensics Specialist
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
**Status:** {'✅ COMPLETE' if trades else '⚠️ NO DATA'}

---

## Executive Summary

This report identifies suspicious patterns in trading data through statistical analysis.

**Data Coverage:**
- **Total Trades Analyzed:** {len(trades)}
- **Anomalies Detected:** {len(all_anomalies)}
- **High Severity:** {len([a for a in all_anomalies if '🔴' in a.severity])}
- **Moderate Severity:** {len([a for a in all_anomalies if '🟡' in a.severity])}
- **Low Severity:** {len([a for a in all_anomalies if '🟢' in a.severity])}

**Overall Verdict:**
"""

    high_severity = [a for a in all_anomalies if '🔴' in a.severity]
    if len(high_severity) >= 3:
        report += "🔴 **CRITICAL:** Multiple high-severity anomalies detected - data integrity questionable\n"
    elif len(high_severity) >= 1:
        report += "🟡 **WARNING:** High-severity anomalies found - requires investigation\n"
    else:
        report += "🟢 **CLEAN:** No critical anomalies - data appears trustworthy\n"

    report += """

---

## Anomaly Categories

"""

    # Group by category
    by_category = defaultdict(list)
    for anomaly in all_anomalies:
        by_category[anomaly.category].append(anomaly)

    for category, anomalies in by_category.items():
        report += f"### {category}\n\n"
        for anomaly in anomalies:
            report += f"**{anomaly.severity}** - {anomaly.description}\n"
            report += f"- Evidence: {anomaly.evidence}\n\n"

    if not all_anomalies:
        report += "✅ **No anomalies detected** - all statistical tests passed\n\n"

    report += """---

## Detailed Analysis

"""

    # Win rate statistics
    if trades:
        wins = sum(1 for t in trades if t.outcome == 'WIN')
        win_rate = (wins / len(trades)) * 100

        report += f"""### Win Rate Statistics

- **Overall Win Rate:** {win_rate:.1f}% ({wins}/{len(trades)})
- **Expected (coin flip):** 50.0%
- **Difference:** {win_rate - 50:.1f} percentage points

"""

        # Crypto breakdown
        crypto_stats = defaultdict(lambda: {'wins': 0, 'total': 0})
        for trade in trades:
            crypto_stats[trade.crypto]['total'] += 1
            if trade.outcome == 'WIN':
                crypto_stats[trade.crypto]['wins'] += 1

        report += "### Per-Crypto Performance\n\n"
        report += "| Crypto | Trades | Win Rate |\n"
        report += "|--------|--------|----------|\n"

        for crypto in sorted(crypto_stats.keys()):
            stats = crypto_stats[crypto]
            wr = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
            report += f"| {crypto} | {stats['total']} | {wr:.1f}% |\n"

        report += "\n"

        # Entry price distribution
        entry_prices = [t.entry_price for t in trades]
        avg_entry = sum(entry_prices) / len(entry_prices)
        min_entry = min(entry_prices)
        max_entry = max(entry_prices)

        report += f"""### Entry Price Distribution

- **Average Entry:** ${avg_entry:.3f}
- **Min Entry:** ${min_entry:.3f}
- **Max Entry:** ${max_entry:.3f}
- **Range:** ${max_entry - min_entry:.3f}

"""

    else:
        report += "⚠️ **No trade data available for analysis**\n\n"

    report += """---

## Statistical Tests Performed

1. **Rolling Win Rate Analysis**
   - Window size: 20 trades
   - Checks for sudden jumps (>30%)
   - Checks for suspiciously stable variance

2. **Outcome Distribution Test**
   - Runs test for independence
   - Expected: Random Bernoulli process
   - Detects: Clustering or alternating patterns

3. **Entry Price Validation**
   - Range check: $0.01 - $0.99 (valid for binary options)
   - Uniformity check: Detects identical prices
   - Precision analysis: Decimal place consistency

4. **Temporal Pattern Analysis**
   - Performance by hour of day
   - Detects: Time-based biases
   - Expected: Consistent across hours

5. **Crypto-Specific Analysis**
   - Win rate by asset (BTC/ETH/SOL/XRP)
   - Expected: Similar across cryptos (strategy agnostic)
   - Detects: Large disparities (>40%)

6. **Shadow Strategy Sanity Checks**
   - Random baseline should not beat default
   - Inverse strategies should not win consistently
   - Detects: Impossible results

7. **Outlier Detection**
   - P&L events >3 standard deviations from mean
   - Identifies: Extreme wins/losses
   - Requires: Manual review for legitimacy

---

## Recommendations

"""

    if len(high_severity) >= 3:
        report += "🔴 **CRITICAL ACTIONS REQUIRED:**\n"
        report += "1. Halt trading immediately until anomalies investigated\n"
        report += "2. Audit data collection pipeline for corruption\n"
        report += "3. Validate on-chain data against logs\n"
        report += "4. Do NOT use current data for strategy optimization\n\n"
    elif len(high_severity) >= 1:
        report += "🟡 **INVESTIGATION REQUIRED:**\n"
        report += "1. Review high-severity anomalies in detail\n"
        report += "2. Cross-reference with system logs for explanations\n"
        report += "3. Validate suspicious trades on-chain\n"
        report += "4. Consider excluding anomalous data from analysis\n\n"
    else:
        report += "🟢 **DATA CLEAN:**\n"
        report += "1. Continue with strategy optimization\n"
        report += "2. Maintain regular anomaly monitoring\n"
        report += "3. Set up automated alerts for future anomalies\n\n"

    if len(trades) < 100:
        report += "📈 **DATA VOLUME:**\n"
        report += f"- Only {len(trades)} trades analyzed (need ≥100 for statistical significance)\n"
        report += "- Continue collecting data before drawing conclusions\n\n"

    report += """---

## Appendix: All Detected Anomalies

"""

    if all_anomalies:
        report += "| # | Category | Severity | Description | Evidence |\n"
        report += "|---|----------|----------|-------------|----------|\n"

        for i, anomaly in enumerate(all_anomalies, 1):
            report += f"| {i} | {anomaly.category} | {anomaly.severity} | {anomaly.description} | {anomaly.evidence} |\n"
    else:
        report += "✅ No anomalies detected\n"

    report += """

---

**END OF REPORT**

Generated by Dr. Kenji Nakamoto's Statistical Anomaly Detection System
"""

    # Write report
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Report generated: {output_path}")

def main():
    """Main execution function"""

    print("=" * 80)
    print("Task 7.4: Statistical Anomaly Detection")
    print("Researcher: Dr. Kenji Nakamoto - Data Forensics Specialist")
    print("=" * 80)
    print()

    # Parse trade data
    print("📋 Parsing trade data from bot.log...")
    trades = parse_bot_logs()
    print(f"   Found {len(trades)} complete trades")
    print()

    # Run all anomaly detection tests
    all_anomalies = []

    print("🔍 Running anomaly detection tests...")
    print()

    print("   1. Win rate clustering analysis...")
    anomalies = analyze_win_rate_clustering(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   2. Outcome distribution test...")
    anomalies = analyze_outcome_distribution(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   3. Entry price validation...")
    anomalies = analyze_entry_prices(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   4. Temporal pattern analysis...")
    anomalies = analyze_temporal_patterns(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   5. Crypto-specific analysis...")
    anomalies = analyze_crypto_specific(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   6. Shadow strategy sanity checks...")
    anomalies = analyze_shadow_strategies()
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print("   7. Outlier detection...")
    anomalies = detect_outliers(trades)
    all_anomalies.extend(anomalies)
    print(f"      Found {len(anomalies)} anomalies")

    print()

    # Generate report
    output_path = "reports/kenji_nakamoto/statistical_anomaly_report.md"
    print(f"📝 Generating report: {output_path}")
    generate_summary_report(all_anomalies, trades, output_path)
    print()

    # Summary
    print("=" * 80)
    print("✅ Task 7.4 Complete")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  - Trades Analyzed: {len(trades)}")
    print(f"  - Anomalies Detected: {len(all_anomalies)}")
    print(f"  - High Severity: {len([a for a in all_anomalies if '🔴' in a.severity])}")
    print(f"  - Moderate Severity: {len([a for a in all_anomalies if '🟡' in a.severity])}")
    print(f"  - Low Severity: {len([a for a in all_anomalies if '🟢' in a.severity])}")
    print()
    print("Next steps:")
    print("  1. Review detailed report at:", output_path)
    print("  2. Investigate high-severity anomalies")
    print("  3. Validate suspicious trades on-chain if needed")
    print()

if __name__ == '__main__':
    main()
