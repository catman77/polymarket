#!/usr/bin/env python3
"""
US-RC-030: Analyze Regime Classification Accuracy

Persona: Prof. Eleanor Nash (Game Theory Economist)
Context: "RegimeAgent classifies markets as bull/bear/sideways/volatile. Is it accurate? Or is it noise?"

This script:
1. Parses bot.log for RegimeAgent classifications
2. Extracts regime labels (BULL, BEAR, SIDEWAYS, VOLATILE, etc.)
3. Analyzes classification frequency and patterns
4. Generates confusion matrix and accuracy metrics
5. Reports on misclassification patterns
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import os
import sys


@dataclass
class RegimeClassification:
    """Represents a single regime classification"""
    timestamp: datetime
    crypto: str
    regime: str
    confidence: Optional[float]
    raw_line: str

    def __hash__(self):
        return hash((self.timestamp.isoformat(), self.crypto, self.regime))


class RegimeValidator:
    """Validates regime classification accuracy and patterns"""

    REGIME_PATTERNS = {
        # Match RegimeAgent vote or classification messages
        'regime_vote': re.compile(
            r'RegimeAgent.*?(?:vote|classification|regime).*?(?:BULL|BEAR|SIDEWAYS|CHOPPY|VOLATILE|NEUTRAL)',
            re.IGNORECASE
        ),
        # Match explicit regime labels
        'regime_label': re.compile(
            r'\b(BULL|BEAR|SIDEWAYS|CHOPPY|VOLATILE|NEUTRAL)\b',
            re.IGNORECASE
        ),
        # Match regime with confidence
        'regime_confidence': re.compile(
            r'(BULL|BEAR|SIDEWAYS|CHOPPY|VOLATILE|NEUTRAL).*?(\d+\.?\d*)%',
            re.IGNORECASE
        ),
        # Match crypto symbol
        'crypto': re.compile(r'\b(BTC|ETH|SOL|XRP)\b')
    }

    def __init__(self, log_file: str):
        self.log_file = log_file
        self.classifications: List[RegimeClassification] = []

    def parse_logs(self) -> None:
        """Parse bot.log for regime classifications"""
        if not os.path.exists(self.log_file):
            print(f"⚠️  Log file not found: {self.log_file}")
            return

        print(f"📖 Parsing: {self.log_file}")

        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Look for RegimeAgent mentions
                if 'RegimeAgent' not in line and 'regime' not in line.lower():
                    continue

                # Try to extract regime classification
                classification = self._extract_classification(line)
                if classification:
                    self.classifications.append(classification)

        print(f"✅ Found {len(self.classifications)} regime classifications")

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
        crypto = crypto_match.group(1) if crypto_match else "UNKNOWN"

        # Extract regime label
        regime_match = self.REGIME_PATTERNS['regime_label'].search(line)
        if not regime_match:
            return None

        regime = regime_match.group(1).upper()

        # Extract confidence if present
        confidence_match = self.REGIME_PATTERNS['regime_confidence'].search(line)
        confidence = float(confidence_match.group(2)) if confidence_match else None

        return RegimeClassification(
            timestamp=timestamp,
            crypto=crypto,
            regime=regime,
            confidence=confidence,
            raw_line=line.strip()
        )

    def analyze_patterns(self) -> Dict:
        """Analyze classification patterns"""
        if not self.classifications:
            return {
                'total': 0,
                'by_regime': {},
                'by_crypto': {},
                'by_hour': {},
                'date_range': None,
                'avg_confidence': None
            }

        # Count by regime type
        by_regime = Counter(c.regime for c in self.classifications)

        # Count by crypto
        by_crypto = Counter(c.crypto for c in self.classifications)

        # Count by hour of day (market behavior patterns)
        by_hour = Counter(c.timestamp.hour for c in self.classifications)

        # Date range
        timestamps = sorted(c.timestamp for c in self.classifications)
        date_range = (timestamps[0], timestamps[-1]) if timestamps else None

        # Average confidence
        confidences = [c.confidence for c in self.classifications if c.confidence is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        return {
            'total': len(self.classifications),
            'by_regime': dict(by_regime),
            'by_crypto': dict(by_crypto),
            'by_hour': dict(by_hour),
            'date_range': date_range,
            'avg_confidence': avg_confidence,
            'confidence_count': len(confidences)
        }

    def analyze_transitions(self) -> List[Dict]:
        """Analyze regime transitions (BULL → BEAR, etc.)"""
        if len(self.classifications) < 2:
            return []

        # Sort by timestamp
        sorted_classifications = sorted(self.classifications, key=lambda c: c.timestamp)

        transitions = []
        for i in range(1, len(sorted_classifications)):
            prev = sorted_classifications[i-1]
            curr = sorted_classifications[i]

            # Only track transitions for same crypto
            if prev.crypto != curr.crypto:
                continue

            # Only track actual regime changes
            if prev.regime != curr.regime:
                time_diff = (curr.timestamp - prev.timestamp).total_seconds() / 60  # minutes
                transitions.append({
                    'crypto': curr.crypto,
                    'from': prev.regime,
                    'to': curr.regime,
                    'timestamp': curr.timestamp,
                    'time_since_last': time_diff
                })

        return transitions

    def detect_misclassification_patterns(self) -> Dict:
        """Detect potential misclassification patterns"""
        # Pattern 1: Rapid oscillation (BULL → BEAR → BULL within short time)
        transitions = self.analyze_transitions()
        rapid_oscillations = [
            t for t in transitions
            if t['time_since_last'] < 30  # Less than 30 minutes
        ]

        # Pattern 2: Dominant regime (one regime appears >70% of time)
        patterns = self.analyze_patterns()
        total = patterns['total']
        dominant_regime = None
        if total > 0:
            for regime, count in patterns['by_regime'].items():
                if count / total > 0.70:
                    dominant_regime = regime

        # Pattern 3: Crypto-specific bias (one crypto always classified same regime)
        crypto_regime_map = defaultdict(Counter)
        for c in self.classifications:
            crypto_regime_map[c.crypto][c.regime] += 1

        crypto_bias = {}
        for crypto, regime_counts in crypto_regime_map.items():
            total_for_crypto = sum(regime_counts.values())
            for regime, count in regime_counts.items():
                if count / total_for_crypto > 0.80:
                    crypto_bias[crypto] = regime

        return {
            'rapid_oscillations': rapid_oscillations,
            'dominant_regime': dominant_regime,
            'crypto_bias': crypto_bias
        }

    def generate_confusion_matrix(self) -> Dict:
        """
        Generate confusion matrix (predicted vs actual)

        Note: Without ground truth data, we analyze internal consistency:
        - Does the same market condition produce consistent classifications?
        - Are adjacent time periods classified consistently?
        """
        # For now, we'll analyze consistency rather than accuracy
        # Real accuracy requires manual validation of 20 epochs

        transitions = self.analyze_transitions()
        transition_matrix = defaultdict(lambda: defaultdict(int))

        for t in transitions:
            transition_matrix[t['from']][t['to']] += 1

        return dict(transition_matrix)

    def generate_report(self, output_file: str) -> None:
        """Generate validation report"""
        patterns = self.analyze_patterns()
        transitions = self.analyze_transitions()
        misclassifications = self.detect_misclassification_patterns()
        confusion_matrix = self.generate_confusion_matrix()

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            f.write("# Regime Classification Validation Report\n\n")
            f.write("**Persona:** Prof. Eleanor Nash (Game Theory Economist)\n\n")
            f.write("**Date:** " + datetime.now().strftime('%Y-%m-%d %H:%M UTC') + "\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            total = patterns['total']
            if total == 0:
                f.write("⚠️ **NO REGIME CLASSIFICATIONS FOUND IN LOGS**\n\n")
                f.write("This likely means:\n")
                f.write("1. RegimeAgent is disabled in config\n")
                f.write("2. Bot hasn't run yet on VPS\n")
                f.write("3. Logs don't contain regime classification messages\n\n")
                f.write("**Action Required:** Enable RegimeAgent and wait for bot to accumulate data.\n\n")
                return

            f.write(f"📊 **Total Classifications:** {total}\n\n")

            if patterns['date_range']:
                start, end = patterns['date_range']
                days = (end - start).days
                f.write(f"📅 **Date Range:** {start.date()} to {end.date()} ({days} days)\n\n")

            if patterns['avg_confidence']:
                f.write(f"🎯 **Average Confidence:** {patterns['avg_confidence']:.1f}%\n\n")

            # Regime Distribution
            f.write("## Regime Distribution\n\n")
            f.write("| Regime | Count | Percentage |\n")
            f.write("|--------|-------|------------|\n")
            for regime, count in sorted(patterns['by_regime'].items(), key=lambda x: -x[1]):
                pct = (count / total) * 100
                f.write(f"| {regime} | {count} | {pct:.1f}% |\n")
            f.write("\n")

            # Bias Analysis
            if misclassifications['dominant_regime']:
                f.write("### ⚠️ Dominant Regime Detected\n\n")
                regime = misclassifications['dominant_regime']
                count = patterns['by_regime'][regime]
                pct = (count / total) * 100
                f.write(f"**{regime}** appears {pct:.1f}% of the time (>70% threshold).\n\n")
                f.write("This suggests potential bias:\n")
                f.write("- RegimeAgent may be over-classifying one regime type\n")
                f.write("- Market may genuinely be in prolonged regime (needs validation)\n")
                f.write("- Classification logic may have threshold issues\n\n")

            # Crypto-Specific Analysis
            f.write("## Per-Crypto Analysis\n\n")
            f.write("| Crypto | Classifications | Dominant Regime |\n")
            f.write("|--------|----------------|------------------|\n")
            for crypto, count in sorted(patterns['by_crypto'].items()):
                bias = misclassifications['crypto_bias'].get(crypto, "NONE")
                f.write(f"| {crypto} | {count} | {bias} |\n")
            f.write("\n")

            if misclassifications['crypto_bias']:
                f.write("### ⚠️ Crypto-Specific Bias Detected\n\n")
                for crypto, regime in misclassifications['crypto_bias'].items():
                    f.write(f"- **{crypto}** classified as **{regime}** >80% of time\n")
                f.write("\nThis may indicate:\n")
                f.write("- Different cryptos have genuinely different regime behavior\n")
                f.write("- Or: RegimeAgent uses crypto-specific biases in classification\n\n")

            # Transition Analysis
            f.write("## Regime Transitions\n\n")
            f.write(f"**Total Transitions:** {len(transitions)}\n\n")

            if transitions:
                # Recent transitions
                f.write("### Recent Transitions (Last 10)\n\n")
                recent = sorted(transitions, key=lambda t: t['timestamp'], reverse=True)[:10]
                f.write("| Time | Crypto | From | To | Minutes Since Last |\n")
                f.write("|------|--------|------|----|--------------------|\\n")
                for t in recent:
                    f.write(f"| {t['timestamp'].strftime('%Y-%m-%d %H:%M')} | {t['crypto']} | {t['from']} | {t['to']} | {t['time_since_last']:.0f} |\n")
                f.write("\n")

                # Rapid oscillations
                rapid = misclassifications['rapid_oscillations']
                if rapid:
                    f.write("### ⚠️ Rapid Oscillations Detected\n\n")
                    f.write(f"**{len(rapid)} transitions** occurred within 30 minutes of previous classification.\n\n")
                    f.write("This suggests:\n")
                    f.write("- RegimeAgent may be too sensitive to short-term noise\n")
                    f.write("- Classification thresholds may need adjustment\n")
                    f.write("- Or: Markets genuinely transitioned rapidly during volatile periods\n\n")

            # Confusion Matrix (transition matrix)
            f.write("## Transition Matrix\n\n")
            f.write("Shows how often regime X transitions to regime Y.\n\n")

            if confusion_matrix:
                all_regimes = sorted(set(list(confusion_matrix.keys()) + [r for transitions in confusion_matrix.values() for r in transitions.keys()]))

                # Header
                f.write("| From \\ To |")
                for regime in all_regimes:
                    f.write(f" {regime} |")
                f.write("\n")

                # Separator
                f.write("|-----------|")
                for _ in all_regimes:
                    f.write("------|")
                f.write("\n")

                # Rows
                for from_regime in all_regimes:
                    f.write(f"| **{from_regime}** |")
                    for to_regime in all_regimes:
                        count = confusion_matrix.get(from_regime, {}).get(to_regime, 0)
                        f.write(f" {count} |")
                    f.write("\n")
                f.write("\n")

            # Accuracy Assessment (without ground truth)
            f.write("## Accuracy Assessment\n\n")
            f.write("### ⚠️ Manual Validation Required\n\n")
            f.write("To determine actual accuracy, we need:\n")
            f.write("1. Sample 20 epochs from logs\n")
            f.write("2. Manually check price charts for each epoch\n")
            f.write("3. Compare RegimeAgent classification to actual market behavior\n")
            f.write("4. Calculate accuracy percentage\n\n")
            f.write("**Sample Epochs for Manual Validation:**\n\n")

            # Sample 20 random classifications for manual validation
            import random
            sample_size = min(20, len(self.classifications))
            sample = random.sample(self.classifications, sample_size)

            f.write("| # | Timestamp | Crypto | Classified As | Raw Line |\n")
            f.write("|---|-----------|--------|---------------|----------|\n")
            for i, c in enumerate(sample, 1):
                # Truncate raw line to fit table
                raw_short = c.raw_line[:60] + "..." if len(c.raw_line) > 60 else c.raw_line
                f.write(f"| {i} | {c.timestamp.strftime('%Y-%m-%d %H:%M')} | {c.crypto} | {c.regime} | {raw_short} |\n")
            f.write("\n")

            f.write("**Manual Validation Instructions:**\n")
            f.write("1. For each epoch timestamp, open TradingView or CoinGecko\n")
            f.write("2. Check 15-minute price chart around that time\n")
            f.write("3. Classify the actual regime:\n")
            f.write("   - BULL: Clear uptrend (higher highs, higher lows)\n")
            f.write("   - BEAR: Clear downtrend (lower highs, lower lows)\n")
            f.write("   - SIDEWAYS/CHOPPY: No clear trend, range-bound\n")
            f.write("   - VOLATILE: Large swings, high volatility\n")
            f.write("4. Mark as CORRECT or INCORRECT\n")
            f.write("5. Calculate: Accuracy = Correct / Total\n\n")

            # Recommendations
            f.write("## Recommendations\n\n")

            if total < 50:
                f.write("### 📊 Insufficient Data\n\n")
                f.write(f"Only {total} classifications found. Need ≥50 for reliable analysis.\n\n")
                f.write("**Action:** Wait for VPS to accumulate more data (1-2 days).\n\n")

            if misclassifications['dominant_regime']:
                f.write("### 🔧 Address Dominant Regime Bias\n\n")
                f.write("- Review RegimeAgent classification thresholds\n")
                f.write("- Consider widening regime detection ranges\n")
                f.write("- Test with different regime indicators (volatility, trend strength)\n\n")

            if misclassifications['rapid_oscillations']:
                f.write("### 🔧 Reduce Rapid Oscillations\n\n")
                f.write("- Add smoothing/hysteresis to regime detection\n")
                f.write("- Require regime to persist for 2-3 classifications before switching\n")
                f.write("- Increase classification interval (currently every scan cycle)\n\n")

            f.write("### ✅ Next Steps\n\n")
            f.write("1. Complete manual validation of 20 sample epochs (see table above)\n")
            f.write("2. Calculate actual accuracy percentage\n")
            f.write("3. If accuracy <70%: Improve RegimeAgent classification logic\n")
            f.write("4. If accuracy >85%: RegimeAgent is reliable, keep enabled\n")
            f.write("5. Re-run this analysis weekly to monitor regime detection quality\n\n")

            # Prof. Nash's Assessment
            f.write("---\n\n")
            f.write("## Prof. Eleanor Nash's Game Theory Assessment\n\n")
            f.write("> \"In game theory, we care about whether regime detection provides exploitable information.\n")
            f.write("> If RegimeAgent can't accurately classify markets, it's just noise—worse than random.\n")
            f.write("> Manual validation is critical: Even 75% accuracy can be useful if misclassifications\n")
            f.write("> are symmetric (false BULL = false BEAR equally). But if biased toward one regime,\n")
            f.write("> we're trading on false signals.\"\n\n")

            f.write("**Strategic Implications:**\n\n")
            f.write("- **High Accuracy (>85%):** RegimeAgent adds value, enable regime-specific strategies\n")
            f.write("- **Moderate Accuracy (70-85%):** Useful but needs improvement, treat with caution\n")
            f.write("- **Low Accuracy (<70%):** Disable RegimeAgent, rely on other signals\n")
            f.write("- **Biased (dominant regime >70%):** Major concern, fix or remove\n\n")

        print(f"✅ Report generated: {output_file}")


def main():
    """Main execution"""
    # Default to bot.log in project root
    log_file = "bot.log"
    if len(sys.argv) > 1:
        log_file = sys.argv[1]

    validator = RegimeValidator(log_file)
    validator.parse_logs()

    output_file = "reports/eleanor_nash/regime_validation.md"
    validator.generate_report(output_file)

    # Summary stats
    patterns = validator.analyze_patterns()
    print(f"\n📊 Summary:")
    print(f"   Total classifications: {patterns['total']}")
    print(f"   Regimes found: {len(patterns['by_regime'])}")
    print(f"   Date range: {patterns['date_range']}")
    print(f"\n✅ Next: Manually validate 20 sample epochs in report")


if __name__ == "__main__":
    main()
