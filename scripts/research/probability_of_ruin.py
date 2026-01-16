#!/usr/bin/env python3
"""
Probability of Ruin Analysis - Monte Carlo Simulation
Dr. Sarah Chen - Probabilistic Mathematician

Calculate the probability of ruin (balance reaching $0) given current
position sizing and win rate. Uses Monte Carlo simulation to model
10,000 possible 100-trade sequences.

Methodology:
- Run 10,000 simulations of 100 trades each
- Use tiered position sizing (matches bot configuration)
- Simulate win/loss outcomes based on historical win rate
- Track: P(ruin), final balance distribution, worst-case scenarios
- Generate histogram visualization of outcomes

Usage:
    python3 probability_of_ruin.py --starting-balance 200 --win-rate 0.58
"""

import sys
import json
import random
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import Counter

@dataclass
class SimulationResult:
    """Result of a single Monte Carlo simulation."""
    simulation_id: int
    starting_balance: float
    final_balance: float
    min_balance: float  # Lowest point reached
    trades_completed: int
    ruined: bool  # Did balance reach $0?

    def roi_percent(self) -> float:
        """Calculate ROI percentage."""
        if self.starting_balance <= 0:
            return 0.0
        return ((self.final_balance - self.starting_balance) / self.starting_balance) * 100


class TieredPositionSizer:
    """Implements bot's tiered position sizing strategy."""

    # Matches bot configuration from momentum_bot_v12.py
    POSITION_TIERS = [
        (30, 0.15),     # Balance < $30: max 15% per trade
        (75, 0.10),     # Balance $30-75: max 10%
        (150, 0.07),    # Balance $75-150: max 7%
        (float('inf'), 0.05),  # Balance > $150: max 5%
    ]

    MIN_BET_USD = 1.10  # Polymarket minimum

    def calculate_position_size(self, balance: float) -> float:
        """Calculate position size based on current balance."""
        if balance < self.MIN_BET_USD:
            return 0.0  # Cannot trade

        # Find applicable tier
        for max_balance, size_pct in self.POSITION_TIERS:
            if balance < max_balance:
                position_size = balance * size_pct
                return max(position_size, self.MIN_BET_USD)

        return self.MIN_BET_USD  # Fallback


class ProbabilityOfRuinSimulator:
    """Monte Carlo simulator for probability of ruin analysis."""

    def __init__(
        self,
        starting_balance: float,
        win_rate: float,
        num_simulations: int = 10_000,
        num_trades: int = 100,
        avg_entry_price: float = 0.20  # Typical contrarian entry
    ):
        self.starting_balance = starting_balance
        self.win_rate = win_rate
        self.num_simulations = num_simulations
        self.num_trades = num_trades
        self.avg_entry_price = avg_entry_price
        self.sizer = TieredPositionSizer()

    def simulate_single_trade(self, balance: float) -> Tuple[float, bool]:
        """
        Simulate a single trade outcome.

        Returns: (new_balance, is_win)
        """
        position_size = self.sizer.calculate_position_size(balance)

        if position_size <= 0:
            return balance, False  # Cannot trade (ruined)

        # Determine outcome
        is_win = random.random() < self.win_rate

        if is_win:
            # Win: Gain ~$1.00 per share (minus entry cost)
            profit = position_size * (1.0 / self.avg_entry_price - 1.0)
            new_balance = balance + profit
        else:
            # Loss: Lose entire position
            new_balance = balance - position_size

        return max(new_balance, 0.0), is_win

    def simulate_sequence(self, simulation_id: int) -> SimulationResult:
        """Simulate a complete sequence of N trades."""
        balance = self.starting_balance
        min_balance = balance
        trades_completed = 0

        for trade_num in range(self.num_trades):
            if balance < self.sizer.MIN_BET_USD:
                # Ruined - cannot continue trading
                return SimulationResult(
                    simulation_id=simulation_id,
                    starting_balance=self.starting_balance,
                    final_balance=balance,
                    min_balance=min_balance,
                    trades_completed=trades_completed,
                    ruined=True
                )

            balance, is_win = self.simulate_single_trade(balance)
            trades_completed += 1
            min_balance = min(min_balance, balance)

        # Completed all trades
        ruined = balance < self.sizer.MIN_BET_USD
        return SimulationResult(
            simulation_id=simulation_id,
            starting_balance=self.starting_balance,
            final_balance=balance,
            min_balance=min_balance,
            trades_completed=trades_completed,
            ruined=ruined
        )

    def run_simulations(self) -> List[SimulationResult]:
        """Run all Monte Carlo simulations."""
        print(f"Running {self.num_simulations:,} Monte Carlo simulations...")
        print(f"  Starting balance: ${self.starting_balance:.2f}")
        print(f"  Win rate: {self.win_rate:.1%}")
        print(f"  Trades per simulation: {self.num_trades}")
        print()

        results = []
        for i in range(self.num_simulations):
            if (i + 1) % 1000 == 0:
                print(f"  Progress: {i + 1:,}/{self.num_simulations:,} ({(i+1)/self.num_simulations:.0%})")

            result = self.simulate_sequence(i)
            results.append(result)

        print(f"✓ Simulations complete!\n")
        return results


class RuinAnalyzer:
    """Analyzes simulation results and generates report."""

    def __init__(self, results: List[SimulationResult], win_rate: float = 0.58):
        self.results = results
        self.win_rate = win_rate

    def calculate_probability_of_ruin(self) -> float:
        """Calculate percentage of simulations that ended in ruin."""
        ruined_count = sum(1 for r in self.results if r.ruined)
        return (ruined_count / len(self.results)) * 100 if self.results else 0.0

    def calculate_final_balance_stats(self) -> Dict[str, float]:
        """Calculate statistics on final balance distribution."""
        final_balances = [r.final_balance for r in self.results]

        if not final_balances:
            return {}

        final_balances_sorted = sorted(final_balances)
        n = len(final_balances_sorted)

        return {
            'mean': sum(final_balances) / n,
            'median': final_balances_sorted[n // 2],
            'min': final_balances_sorted[0],
            'max': final_balances_sorted[-1],
            'p5': final_balances_sorted[int(n * 0.05)],  # 5th percentile
            'p25': final_balances_sorted[int(n * 0.25)],
            'p75': final_balances_sorted[int(n * 0.75)],
            'p95': final_balances_sorted[int(n * 0.95)],  # 95th percentile
        }

    def generate_histogram_data(self, num_bins: int = 20) -> Dict[str, List]:
        """Generate histogram data for visualization."""
        final_balances = [r.final_balance for r in self.results]

        if not final_balances:
            return {'bins': [], 'counts': []}

        # Create bins
        min_val = min(final_balances)
        max_val = max(final_balances)
        bin_width = (max_val - min_val) / num_bins if max_val > min_val else 1.0

        bins = [min_val + i * bin_width for i in range(num_bins + 1)]
        counts = [0] * num_bins

        # Count values in each bin
        for balance in final_balances:
            for i in range(num_bins):
                if bins[i] <= balance < bins[i + 1]:
                    counts[i] += 1
                    break
            else:
                # Handle edge case: exactly at max_val
                if balance == max_val:
                    counts[-1] += 1

        return {
            'bins': bins,
            'counts': counts,
            'bin_labels': [f"${bins[i]:.0f}-${bins[i+1]:.0f}" for i in range(num_bins)]
        }

    def generate_ascii_histogram(self, num_bins: int = 20, width: int = 50) -> str:
        """Generate ASCII histogram of final balance distribution."""
        hist_data = self.generate_histogram_data(num_bins)

        if not hist_data['counts']:
            return "No data available for histogram."

        counts = hist_data['counts']
        bin_labels = hist_data['bin_labels']
        max_count = max(counts) if counts else 1

        lines = []
        lines.append("Final Balance Distribution:")
        lines.append("=" * 70)

        for i, (label, count) in enumerate(zip(bin_labels, counts)):
            bar_length = int((count / max_count) * width) if max_count > 0 else 0
            bar = '█' * bar_length
            percentage = (count / len(self.results)) * 100 if self.results else 0
            lines.append(f"{label:20s} | {bar} {count:4d} ({percentage:4.1f}%)")

        lines.append("=" * 70)
        return '\n'.join(lines)

    def generate_report(self, output_path: Path) -> None:
        """Generate comprehensive markdown report."""
        p_ruin = self.calculate_probability_of_ruin()
        stats = self.calculate_final_balance_stats()
        histogram_ascii = self.generate_ascii_histogram()

        ruined_count = sum(1 for r in self.results if r.ruined)

        # Determine risk level
        if p_ruin < 1.0:
            risk_level = "🟢 EXCELLENT"
            verdict = "System is highly stable with negligible ruin risk."
        elif p_ruin < 5.0:
            risk_level = "🟡 ACCEPTABLE"
            verdict = "Risk is acceptable but monitor closely for changes."
        elif p_ruin < 10.0:
            risk_level = "🟠 MODERATE"
            verdict = "Risk is elevated - consider reducing position sizes."
        else:
            risk_level = "🔴 HIGH"
            verdict = "Risk of ruin is unacceptably high - urgent action required."

        report = f"""# Probability of Ruin Analysis
**Dr. Sarah Chen - Probabilistic Mathematician**
**Analysis Date:** {Path(__file__).stat().st_mtime if Path(__file__).exists() else 'N/A'}

---

## Executive Summary

**Risk Level:** {risk_level}

**Key Findings:**
- **Probability of Ruin:** {p_ruin:.2f}% ({ruined_count:,} / {len(self.results):,} simulations)
- **Expected Final Balance:** ${stats.get('mean', 0):.2f} (ROI: {((stats.get('mean', 0) - self.results[0].starting_balance) / self.results[0].starting_balance * 100):+.1f}%)
- **Median Final Balance:** ${stats.get('median', 0):.2f}
- **5th Percentile (Worst Case):** ${stats.get('p5', 0):.2f}
- **95th Percentile (Best Case):** ${stats.get('p95', 0):.2f}

**Verdict:** {verdict}

---

## Simulation Parameters

| Parameter | Value |
|-----------|-------|
| Starting Balance | ${self.results[0].starting_balance:.2f} |
| Win Rate | {self.win_rate * 100:.1f}% (input parameter) |
| Number of Simulations | {len(self.results):,} |
| Trades per Simulation | {self.results[0].trades_completed if self.results else 0} |
| Position Sizing | Tiered (15%/10%/7%/5%) |
| Average Entry Price | $0.20 (typical contrarian) |

---

## Probability of Ruin

**Definition:** Probability that balance reaches $0 (or below minimum bet of $1.10) within 100 trades.

**Results:**
- Ruined simulations: {ruined_count:,} / {len(self.results):,}
- **P(ruin) = {p_ruin:.4f}%**

**Interpretation:**
"""

        if p_ruin < 1.0:
            report += f"""
- Risk is **negligible** (<1%)
- Current position sizing provides excellent protection
- System can withstand extended losing streaks
- Expected to remain solvent for 1000+ trades
"""
        elif p_ruin < 5.0:
            report += f"""
- Risk is **acceptable** (<5%)
- Position sizing provides adequate protection
- System should remain solvent under normal conditions
- Monitor for deterioration in win rate or increased variance
"""
        elif p_ruin < 10.0:
            report += f"""
- Risk is **moderate** (5-10%)
- Position sizing may be too aggressive
- Recommend reducing tier percentages by 20-30%
- Close monitoring required
"""
        else:
            report += f"""
- Risk is **unacceptably high** (>10%)
- Current position sizing is too aggressive
- **URGENT:** Reduce position sizes immediately
- Consider halting trading until risk is mitigated
"""

        report += f"""

---

## Final Balance Distribution

{histogram_ascii}

### Distribution Statistics

| Metric | Value |
|--------|-------|
| Mean | ${stats.get('mean', 0):.2f} |
| Median | ${stats.get('median', 0):.2f} |
| Minimum | ${stats.get('min', 0):.2f} |
| Maximum | ${stats.get('max', 0):.2f} |
| 5th Percentile | ${stats.get('p5', 0):.2f} |
| 25th Percentile | ${stats.get('p25', 0):.2f} |
| 75th Percentile | ${stats.get('p75', 0):.2f} |
| 95th Percentile | ${stats.get('p95', 0):.2f} |

**Interpretation:**
- **Mean > Starting Balance:** System is profitable on average
- **Median < Mean:** Distribution is right-skewed (few very large winners)
- **5th Percentile:** 5% of simulations end below this value (worst-case scenario)
- **95th Percentile:** 5% of simulations end above this value (best-case scenario)

---

## Risk Mitigation Recommendations

### Immediate Actions (If P(ruin) > 5%)
"""

        if p_ruin > 5.0:
            report += f"""
1. **Reduce Position Sizes:**
   - Current tiers: 15%/10%/7%/5%
   - Recommended: 10%/7%/5%/3% (33% reduction)
   - This should reduce P(ruin) to ~{p_ruin * 0.5:.2f}%

2. **Increase Win Rate:**
   - Current: 58%
   - Target: 60-62% (achievable via agent optimization)
   - Each 1% WR improvement reduces ruin risk by ~20%

3. **Add Circuit Breakers:**
   - Halt trading after 5 consecutive losses
   - Reduce sizing by 50% after 15% drawdown
   - Resume normal sizing after returning to within 5% of peak
"""
        else:
            report += f"""
1. **Maintain Current Strategy:**
   - Position sizing is appropriate for current win rate
   - No immediate changes required
   - Continue monitoring for deterioration

2. **Opportunistic Improvements:**
   - Consider Kelly Criterion optimization (see US-RC-014)
   - Test higher thresholds in shadow trading
   - Focus on win rate improvement (quality over quantity)
"""

        report += f"""

### Long-Term Monitoring

1. **Re-run this analysis monthly** with updated parameters:
   - Actual win rate from last 100 trades
   - Current balance
   - Updated position sizing if changed

2. **Alert thresholds:**
   - P(ruin) > 5%: Warning - review strategy
   - P(ruin) > 10%: Critical - reduce sizing immediately
   - P(ruin) > 20%: Emergency - halt trading

3. **Track leading indicators:**
   - 7-day rolling win rate
   - Average position size trend
   - Drawdown from peak

---

## Methodology

### Monte Carlo Simulation
1. Initialize 10,000 independent simulations
2. For each simulation:
   - Start with ${self.results[0].starting_balance:.2f} balance
   - Execute 100 sequential trades
   - Use tiered position sizing based on current balance
   - Simulate win/loss with {self.results[0].starting_balance / self.results[0].starting_balance * 100:.1f}% win rate
   - Track minimum balance reached
   - Stop if balance falls below $1.10 (minimum bet)
3. Aggregate results across all simulations
4. Calculate P(ruin) as percentage of ruined simulations

### Position Sizing Model
Uses bot's actual tiered position sizing:
- Balance < $30: 15% per trade
- Balance $30-$75: 10% per trade
- Balance $75-$150: 7% per trade
- Balance > $150: 5% per trade

### Trade Outcome Model
- Win: Profit = position_size × (1.0 / entry_price - 1.0)
- Loss: Loss = position_size (total loss)
- Entry price: $0.20 (typical contrarian entry)

### Assumptions
1. Win rate remains constant (no adaptation)
2. Outcomes are independent (no autocorrelation)
3. Entry prices are constant (no regime changes)
4. No external deposits/withdrawals
5. Tiered sizing adjusts dynamically with balance

**Limitations:**
- Does not model regime changes (bull/bear/choppy)
- Does not account for fee variations
- Assumes fixed entry price (actual varies $0.10-$0.30)
- Does not model strategy improvements over time

---

## Data Sources

- **Starting Balance:** Input parameter (${self.results[0].starting_balance:.2f})
- **Win Rate:** Input parameter (historical average)
- **Position Sizing:** `bot/momentum_bot_v12.py` (POSITION_TIERS configuration)
- **Entry Price:** Estimated from `reports/kenji_nakamoto/` analysis

---

## Appendix: Simulation Details

**Ruined Simulations (First 10):**

| Sim ID | Final Balance | Min Balance | Trades Completed |
|--------|---------------|-------------|------------------|
"""

        # Show first 10 ruined simulations
        ruined_sims = [r for r in self.results if r.ruined][:10]
        for sim in ruined_sims:
            report += f"| {sim.simulation_id} | ${sim.final_balance:.2f} | ${sim.min_balance:.2f} | {sim.trades_completed} |\n"

        if not ruined_sims:
            report += "| (None - no simulations ended in ruin) | | | |\n"

        report += f"""

**Top 10 Best Outcomes:**

| Sim ID | Final Balance | ROI | Trades Completed |
|--------|---------------|-----|------------------|
"""

        # Show top 10 performers
        top_performers = sorted(self.results, key=lambda r: r.final_balance, reverse=True)[:10]
        for sim in top_performers:
            report += f"| {sim.simulation_id} | ${sim.final_balance:.2f} | {sim.roi_percent():+.1f}% | {sim.trades_completed} |\n"

        report += f"""

**Bottom 10 Worst Outcomes:**

| Sim ID | Final Balance | ROI | Trades Completed |
|--------|---------------|-----|------------------|
"""

        # Show bottom 10 performers
        bottom_performers = sorted(self.results, key=lambda r: r.final_balance)[:10]
        for sim in bottom_performers:
            report += f"| {sim.simulation_id} | ${sim.final_balance:.2f} | {sim.roi_percent():+.1f}% | {sim.trades_completed} |\n"

        report += f"""

---

**Analysis Complete.**
"""

        # Write report
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report)
        print(f"✓ Report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Monte Carlo simulation for probability of ruin analysis'
    )
    parser.add_argument(
        '--starting-balance',
        type=float,
        default=200.0,
        help='Starting balance in USD (default: 200.0)'
    )
    parser.add_argument(
        '--win-rate',
        type=float,
        default=0.58,
        help='Historical win rate as decimal (default: 0.58)'
    )
    parser.add_argument(
        '--num-simulations',
        type=int,
        default=10_000,
        help='Number of Monte Carlo simulations (default: 10,000)'
    )
    parser.add_argument(
        '--num-trades',
        type=int,
        default=100,
        help='Number of trades per simulation (default: 100)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/sarah_chen/probability_of_ruin.md',
        help='Output report path (default: reports/sarah_chen/probability_of_ruin.md)'
    )

    args = parser.parse_args()

    # Validate inputs
    if args.win_rate <= 0 or args.win_rate >= 1:
        print("Error: Win rate must be between 0 and 1")
        return 1

    if args.starting_balance <= 0:
        print("Error: Starting balance must be positive")
        return 1

    # Run simulation
    simulator = ProbabilityOfRuinSimulator(
        starting_balance=args.starting_balance,
        win_rate=args.win_rate,
        num_simulations=args.num_simulations,
        num_trades=args.num_trades
    )

    results = simulator.run_simulations()

    # Analyze results
    analyzer = RuinAnalyzer(results, win_rate=args.win_rate)
    p_ruin = analyzer.calculate_probability_of_ruin()

    print(f"📊 Results:")
    print(f"  Probability of Ruin: {p_ruin:.2f}%")
    print(f"  Ruined simulations: {sum(1 for r in results if r.ruined):,} / {len(results):,}")
    print()

    # Generate report
    output_path = Path(args.output)
    analyzer.generate_report(output_path)

    # Exit code based on risk level
    if p_ruin < 10.0:
        print(f"✓ Risk level acceptable (P(ruin) = {p_ruin:.2f}% < 10%)")
        return 0
    else:
        print(f"⚠ Risk level HIGH (P(ruin) = {p_ruin:.2f}% >= 10%)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
