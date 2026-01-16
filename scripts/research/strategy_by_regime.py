#!/usr/bin/env python3
"""
US-RC-031: Calculate Strategy Performance by Regime

Persona: Prof. Eleanor Nash (Game Theory Economist)
Context: "Does contrarian work in sideways markets? Does momentum work in trending
markets? Data will reveal regime-strategy fit."

This script:
1. Parses bot.log for RegimeAgent classifications (BULL, BEAR, SIDEWAYS, etc.)
2. Queries shadow trading database for strategy trades
3. Joins trades with regime classifications by epoch timestamp
4. Calculates win rate for each (strategy, regime) pair
5. Generates performance matrix showing best strategy per regime
6. Provides adaptive strategy switching recommendations
"""

import re
import sqlite3
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import os
import sys


@dataclass
class RegimeClassification:
    """Represents a regime classification at a specific time"""
    timestamp: datetime
    crypto: str
    regime: str
    confidence: Optional[float]

    def matches_epoch(self, epoch_start: datetime, epoch_end: datetime) -> bool:
        """Check if this classification overlaps with epoch time window"""
        return epoch_start <= self.timestamp <= epoch_end


@dataclass
class TradeWithRegime:
    """Trade with associated regime classification"""
    strategy: str
    crypto: str
    epoch: int
    direction: str
    timestamp: datetime
    regime: str
    won: bool
    pnl: float


class StrategyRegimeAnalyzer:
    """Analyzes strategy performance across different market regimes"""

    REGIME_PATTERNS = {
        'regime_label': re.compile(
            r'\b(BULL|BEAR|SIDEWAYS|CHOPPY|VOLATILE|NEUTRAL|BEARISH|BULLISH)\b',
            re.IGNORECASE
        ),
        'crypto': re.compile(r'\b(BTC|ETH|SOL|XRP)\b')
    }

    # Normalize regime names
    REGIME_MAPPING = {
        'BULL': 'BULL',
        'BULLISH': 'BULL',
        'BEAR': 'BEAR',
        'BEARISH': 'BEAR',
        'SIDEWAYS': 'SIDEWAYS',
        'CHOPPY': 'CHOPPY',
        'VOLATILE': 'VOLATILE',
        'NEUTRAL': 'SIDEWAYS'  # Map neutral to sideways
    }

    def __init__(self, log_file: str, db_path: str):
        self.log_file = log_file
        self.db_path = db_path
        self.regime_classifications: List[RegimeClassification] = []
        self.trades_with_regimes: List[TradeWithRegime] = []

    def parse_regime_classifications(self) -> None:
        """Parse bot.log for regime classifications"""
        if not os.path.exists(self.log_file):
            print(f"⚠️  Log file not found: {self.log_file}")
            print(f"   Using VPS path: /opt/polymarket-autotrader/bot.log")
            return

        print(f"📖 Parsing regime classifications from: {self.log_file}")

        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'RegimeAgent' not in line and 'regime' not in line.lower():
                    continue

                classification = self._extract_classification(line)
                if classification:
                    self.regime_classifications.append(classification)

        print(f"✅ Found {len(self.regime_classifications)} regime classifications")

    def _extract_classification(self, line: str) -> Optional[RegimeClassification]:
        """Extract regime classification from log line"""
        # Extract timestamp
        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if not timestamp_match:
            return None

        try:
            timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None

        # Extract crypto
        crypto_match = self.REGIME_PATTERNS['crypto'].search(line)
        crypto = crypto_match.group(1) if crypto_match else 'UNKNOWN'

        # Extract regime
        regime_match = self.REGIME_PATTERNS['regime_label'].search(line)
        if not regime_match:
            return None

        regime_raw = regime_match.group(1).upper()
        regime = self.REGIME_MAPPING.get(regime_raw, regime_raw)

        # Try to extract confidence (optional)
        confidence_match = re.search(r'(\d+\.?\d*)%', line)
        confidence = float(confidence_match.group(1)) if confidence_match else None

        return RegimeClassification(
            timestamp=timestamp,
            crypto=crypto,
            regime=regime,
            confidence=confidence
        )

    def query_trades(self) -> None:
        """Query shadow trading database for trades with outcomes"""
        if not os.path.exists(self.db_path):
            print(f"⚠️  Database not found: {self.db_path}")
            return

        print(f"📊 Querying trades from: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Query trades with outcomes
        query = """
        SELECT
            t.strategy,
            t.crypto,
            t.epoch,
            t.direction,
            t.timestamp,
            o.actual_direction,
            o.pnl
        FROM trades t
        INNER JOIN outcomes o ON t.id = o.trade_id
        WHERE o.pnl IS NOT NULL
        ORDER BY t.timestamp
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        print(f"✅ Found {len(rows)} resolved trades")

        # Match trades with regime classifications
        for strategy, crypto, epoch, direction, timestamp, actual_dir, pnl in rows:
            trade_time = datetime.fromtimestamp(timestamp)

            # Find regime classification within ±15 minutes of trade
            regime = self._find_matching_regime(trade_time, crypto)

            if regime:
                won = pnl > 0
                self.trades_with_regimes.append(TradeWithRegime(
                    strategy=strategy,
                    crypto=crypto,
                    epoch=epoch,
                    direction=direction,
                    timestamp=trade_time,
                    regime=regime,
                    won=won,
                    pnl=pnl
                ))

        conn.close()

        print(f"✅ Matched {len(self.trades_with_regimes)} trades with regimes")

    def _find_matching_regime(self, trade_time: datetime, crypto: str) -> Optional[str]:
        """Find the regime classification closest to trade time for this crypto"""
        # Look for classifications within ±15 minutes
        window = timedelta(minutes=15)

        matches = [
            c for c in self.regime_classifications
            if c.crypto == crypto and abs((c.timestamp - trade_time).total_seconds()) <= window.total_seconds()
        ]

        if not matches:
            return None

        # Return the closest match
        closest = min(matches, key=lambda c: abs((c.timestamp - trade_time).total_seconds()))
        return closest.regime

    def calculate_performance_matrix(self) -> Dict[Tuple[str, str], Dict[str, float]]:
        """Calculate win rate and P&L for each (strategy, regime) pair"""
        # Group trades by (strategy, regime)
        grouped = defaultdict(list)
        for trade in self.trades_with_regimes:
            key = (trade.strategy, trade.regime)
            grouped[key].append(trade)

        # Calculate metrics
        matrix = {}
        for (strategy, regime), trades in grouped.items():
            total = len(trades)
            wins = sum(1 for t in trades if t.won)
            win_rate = wins / total if total > 0 else 0.0
            total_pnl = sum(t.pnl for t in trades)
            avg_pnl = total_pnl / total if total > 0 else 0.0

            matrix[(strategy, regime)] = {
                'total_trades': total,
                'wins': wins,
                'losses': total - wins,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl
            }

        return matrix

    def generate_report(self, output_dir: str) -> None:
        """Generate performance matrix and recommendations"""
        os.makedirs(output_dir, exist_ok=True)

        matrix = self.calculate_performance_matrix()

        if not matrix:
            print("⚠️  No data to analyze (no trades matched with regimes)")
            self._generate_empty_report(output_dir)
            return

        # Generate CSV
        csv_path = os.path.join(output_dir, 'strategy_by_regime.csv')
        self._write_csv(matrix, csv_path)

        # Generate markdown report
        md_path = os.path.join(output_dir, 'strategy_by_regime_analysis.md')
        self._write_markdown(matrix, md_path)

        print(f"\n✅ Reports generated:")
        print(f"   CSV: {csv_path}")
        print(f"   Report: {md_path}")

    def _write_csv(self, matrix: Dict[Tuple[str, str], Dict], csv_path: str) -> None:
        """Write performance matrix to CSV"""
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Strategy', 'Regime', 'Total Trades', 'Wins', 'Losses',
                'Win Rate (%)', 'Total P&L ($)', 'Avg P&L ($)'
            ])

            # Sort by total P&L descending
            sorted_items = sorted(
                matrix.items(),
                key=lambda x: x[1]['total_pnl'],
                reverse=True
            )

            for (strategy, regime), metrics in sorted_items:
                writer.writerow([
                    strategy,
                    regime,
                    metrics['total_trades'],
                    metrics['wins'],
                    metrics['losses'],
                    f"{metrics['win_rate'] * 100:.1f}",
                    f"{metrics['total_pnl']:.2f}",
                    f"{metrics['avg_pnl']:.2f}"
                ])

    def _write_markdown(self, matrix: Dict[Tuple[str, str], Dict], md_path: str) -> None:
        """Write analysis report in markdown"""
        with open(md_path, 'w') as f:
            f.write("# Strategy Performance by Market Regime\n\n")
            f.write("**Analyst:** Prof. Eleanor Nash (Game Theory Economist)\n\n")
            f.write("**Analysis Date:** " + datetime.now().strftime('%Y-%m-%d %H:%M UTC') + "\n\n")

            f.write("## Executive Summary\n\n")

            # Calculate overall stats
            total_matched = len(self.trades_with_regimes)
            total_trades_with_outcomes = sum(m['total_trades'] for m in matrix.values())
            unique_strategies = len(set(k[0] for k in matrix.keys()))
            unique_regimes = len(set(k[1] for k in matrix.keys()))

            f.write(f"- **Total trades matched with regimes:** {total_matched}\n")
            f.write(f"- **Strategies analyzed:** {unique_strategies}\n")
            f.write(f"- **Regimes identified:** {unique_regimes}\n")
            f.write(f"- **Coverage:** {unique_strategies} strategies × {unique_regimes} regimes\n\n")

            # Best strategy per regime
            f.write("## Best Strategy Per Regime\n\n")
            regime_best = self._find_best_per_regime(matrix)
            f.write("| Regime | Best Strategy | Win Rate | Total P&L | Sample Size |\n")
            f.write("|--------|---------------|----------|-----------|-------------|\n")
            for regime, (strategy, metrics) in sorted(regime_best.items()):
                wr = metrics['win_rate'] * 100
                pnl = metrics['total_pnl']
                n = metrics['total_trades']
                f.write(f"| {regime} | {strategy} | {wr:.1f}% | ${pnl:+.2f} | {n} trades |\n")

            f.write("\n")

            # Full performance matrix
            f.write("## Full Performance Matrix\n\n")
            f.write("| Strategy | Regime | Win Rate | P&L | Trades |\n")
            f.write("|----------|--------|----------|-----|--------|\n")

            sorted_items = sorted(
                matrix.items(),
                key=lambda x: (x[0][0], x[1]['total_pnl']),  # Sort by strategy, then P&L
                reverse=True
            )

            for (strategy, regime), metrics in sorted_items:
                wr = metrics['win_rate'] * 100
                pnl = metrics['total_pnl']
                n = metrics['total_trades']

                # Color-code win rate
                if wr >= 60:
                    wr_str = f"🟢 {wr:.1f}%"
                elif wr >= 50:
                    wr_str = f"🟡 {wr:.1f}%"
                else:
                    wr_str = f"🔴 {wr:.1f}%"

                f.write(f"| {strategy} | {regime} | {wr_str} | ${pnl:+.2f} | {n} |\n")

            f.write("\n")

            # Strategy insights
            f.write("## Strategic Insights\n\n")
            insights = self._generate_insights(matrix)
            for insight in insights:
                f.write(f"- {insight}\n")

            f.write("\n")

            # Recommendations
            f.write("## Prof. Nash's Recommendations\n\n")
            recommendations = self._generate_recommendations(matrix, regime_best)
            for rec in recommendations:
                f.write(f"{rec}\n\n")

    def _find_best_per_regime(self, matrix: Dict) -> Dict[str, Tuple[str, Dict]]:
        """Find best strategy for each regime (by total P&L)"""
        regime_strategies = defaultdict(list)
        for (strategy, regime), metrics in matrix.items():
            regime_strategies[regime].append((strategy, metrics))

        best_per_regime = {}
        for regime, strategies in regime_strategies.items():
            # Require minimum sample size (3+ trades)
            valid = [(s, m) for s, m in strategies if m['total_trades'] >= 3]
            if valid:
                best = max(valid, key=lambda x: x[1]['total_pnl'])
                best_per_regime[regime] = best

        return best_per_regime

    def _generate_insights(self, matrix: Dict) -> List[str]:
        """Generate strategic insights from data"""
        insights = []

        # Find strategies that excel in specific regimes
        for (strategy, regime), metrics in matrix.items():
            if metrics['total_trades'] >= 5 and metrics['win_rate'] >= 0.65:
                insights.append(
                    f"**{strategy}** excels in **{regime}** markets: "
                    f"{metrics['win_rate']*100:.1f}% WR ({metrics['total_trades']} trades)"
                )

        # Find strategies that struggle in specific regimes
        for (strategy, regime), metrics in matrix.items():
            if metrics['total_trades'] >= 5 and metrics['win_rate'] < 0.45:
                insights.append(
                    f"⚠️ **{strategy}** struggles in **{regime}** markets: "
                    f"{metrics['win_rate']*100:.1f}% WR ({metrics['total_trades']} trades)"
                )

        # Check for regime-agnostic strategies
        strategy_regimes = defaultdict(list)
        for (strategy, regime), metrics in matrix.items():
            if metrics['total_trades'] >= 3:
                strategy_regimes[strategy].append((regime, metrics['win_rate']))

        for strategy, regime_wrs in strategy_regimes.items():
            if len(regime_wrs) >= 3:  # Must have data in 3+ regimes
                wrs = [wr for _, wr in regime_wrs]
                avg_wr = sum(wrs) / len(wrs)
                std_wr = (sum((wr - avg_wr)**2 for wr in wrs) / len(wrs))**0.5

                if std_wr < 0.10:  # Low variance = regime-agnostic
                    insights.append(
                        f"**{strategy}** is regime-agnostic: consistent {avg_wr*100:.1f}% WR "
                        f"across {len(regime_wrs)} regimes (std dev: {std_wr*100:.1f}%)"
                    )

        if not insights:
            insights.append("Insufficient data for regime-specific insights (need 5+ trades per strategy-regime pair)")

        return insights

    def _generate_recommendations(self, matrix: Dict, best_per_regime: Dict) -> List[str]:
        """Generate adaptive strategy switching recommendations"""
        recs = []

        recs.append("### 1. Adaptive Strategy Switching Rules\n")
        recs.append("Implement regime-aware strategy selection:\n")

        if best_per_regime:
            recs.append("```python")
            recs.append("def select_strategy(current_regime: str) -> str:")
            recs.append("    regime_strategy_map = {")
            for regime, (strategy, metrics) in sorted(best_per_regime.items()):
                wr = metrics['win_rate'] * 100
                recs.append(f"        '{regime}': '{strategy}',  # {wr:.1f}% WR")
            recs.append("    }")
            recs.append("    return regime_strategy_map.get(current_regime, 'default')")
            recs.append("```\n")
        else:
            recs.append("⚠️ **Insufficient data** - Need more trades per regime to recommend switching rules.\n")

        recs.append("### 2. Minimum Sample Size Requirements\n")
        recs.append(
            "Current analysis is based on shadow trading data. For statistical confidence:\n"
            "- Minimum 20 trades per (strategy, regime) pair\n"
            "- Require 4+ weeks of continuous trading\n"
            "- Test adaptive switching with shadow strategies before live deployment\n"
        )

        recs.append("### 3. Game Theory Perspective\n")
        recs.append(
            '> "In game theory, regime-adaptive strategies are Nash equilibrium candidates '
            'when market dynamics shift faster than opponents adapt. The key question: '
            'Does RegimeAgent detect transitions fast enough to exploit them?"\n'
        )
        recs.append(
            "**Next Steps:**\n"
            "1. Validate regime detection accuracy (see `regime_validation.py`)\n"
            "2. Measure regime transition lag (time from shift to detection)\n"
            "3. If lag < 2 epochs: Enable adaptive switching\n"
            "4. If lag > 3 epochs: Adaptive switching adds noise, not signal\n"
        )

        return recs

    def _generate_empty_report(self, output_dir: str) -> None:
        """Generate report when no data is available"""
        md_path = os.path.join(output_dir, 'strategy_by_regime_analysis.md')

        with open(md_path, 'w') as f:
            f.write("# Strategy Performance by Market Regime\n\n")
            f.write("**Status:** ⚠️ Insufficient Data\n\n")
            f.write("## Issue\n\n")
            f.write("No trades could be matched with regime classifications. Possible reasons:\n\n")
            f.write("1. **RegimeAgent not enabled** - Check `config/agent_config.py`\n")
            f.write("2. **No regime classifications in logs** - Bot may not be logging regime decisions\n")
            f.write("3. **Shadow trading database empty** - No resolved trades yet\n")
            f.write("4. **Timestamp mismatch** - Regime logs and trade timestamps don't overlap\n\n")
            f.write("## Next Steps\n\n")
            f.write("1. Verify RegimeAgent is enabled and logging classifications\n")
            f.write("2. Wait for 20+ resolved trades in shadow database\n")
            f.write("3. Re-run this analysis: `python3 scripts/research/strategy_by_regime.py`\n")

        csv_path = os.path.join(output_dir, 'strategy_by_regime.csv')
        with open(csv_path, 'w') as f:
            f.write("Strategy,Regime,Total Trades,Wins,Losses,Win Rate (%),Total P&L ($),Avg P&L ($)\n")
            f.write("# No data available\n")


def main():
    """Main execution"""
    print("=" * 80)
    print("US-RC-031: Strategy Performance by Regime Analysis")
    print("Persona: Prof. Eleanor Nash (Game Theory Economist)")
    print("=" * 80)
    print()

    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_file = os.path.join(project_root, 'bot.log')
    db_path = os.path.join(project_root, 'simulation', 'trade_journal.db')
    output_dir = os.path.join(project_root, 'reports', 'eleanor_nash')

    # Initialize analyzer
    analyzer = StrategyRegimeAnalyzer(log_file, db_path)

    # Parse regime classifications
    analyzer.parse_regime_classifications()

    # Query trades
    analyzer.query_trades()

    # Generate reports
    analyzer.generate_report(output_dir)

    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
