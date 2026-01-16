#!/usr/bin/env python3
"""
Position Sizing Stress Test - Monte Carlo Simulation

PERSONA: Colonel Rita "The Guardian" Stevens (Risk Management Architect)
MINDSET: "Plan for failure. Stress test everything. Hope is not a strategy."

Tests whether tiered position sizing protects the account during loss streaks.
Simulates 10 consecutive losses at different balance levels to measure drawdown.

Author: Ralph (autonomous research agent)
Date: 2026-01-16
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class StressTestResult:
    """Results from a stress test scenario"""
    scenario_name: str
    starting_balance: float
    ending_balance: float
    total_loss_usd: float
    drawdown_pct: float
    max_bet_size: float
    min_bet_size: float
    avg_bet_size: float
    bet_sizes: List[float]
    exceeds_halt_threshold: bool


class PositionSizingStressTest:
    """Stress tests tiered position sizing with consecutive loss scenarios"""

    # Position sizing tiers (from bot config)
    POSITION_TIERS = [
        (30, 0.15),     # Balance < $30: max 15% per trade
        (75, 0.10),     # Balance $30-75: max 10% per trade
        (150, 0.07),    # Balance $75-150: max 7% per trade
        (float('inf'), 0.05),  # Balance > $150: max 5% per trade
    ]

    MAX_POSITION_USD = 15.0   # Absolute max regardless of balance
    MIN_BET_USD = 1.10        # Minimum CLOB order value
    DRAWDOWN_HALT_THRESHOLD = 0.30  # 30% drawdown triggers halt

    def calculate_position_size(self, balance: float) -> float:
        """
        Calculate position size based on current balance using tiered sizing.

        Args:
            balance: Current account balance in USD

        Returns:
            Position size in USD (clamped to MIN_BET_USD and MAX_POSITION_USD)
        """
        # Find appropriate tier
        for max_balance, size_pct in self.POSITION_TIERS:
            if balance < max_balance:
                position_size = balance * size_pct
                # Clamp to min/max limits
                position_size = max(position_size, self.MIN_BET_USD)
                position_size = min(position_size, self.MAX_POSITION_USD)
                return position_size

        # Fallback (should never reach here due to inf tier)
        return self.MIN_BET_USD

    def simulate_loss_streak(self, starting_balance: float, num_losses: int = 10) -> StressTestResult:
        """
        Simulate N consecutive losses and track drawdown.

        Each loss results in complete loss of bet amount (worst case: all bets finish at $0).

        Args:
            starting_balance: Initial balance in USD
            num_losses: Number of consecutive losses to simulate (default 10)

        Returns:
            StressTestResult with detailed metrics
        """
        balance = starting_balance
        bet_sizes: List[float] = []

        # Simulate each loss
        for loss_num in range(num_losses):
            # Calculate bet size for current balance
            bet_size = self.calculate_position_size(balance)
            bet_sizes.append(bet_size)

            # Apply loss (total loss of bet)
            balance -= bet_size

            # Stop if balance hits zero or below
            if balance <= 0:
                balance = 0
                break

        # Calculate metrics
        ending_balance = balance
        total_loss_usd = starting_balance - ending_balance
        drawdown_pct = total_loss_usd / starting_balance if starting_balance > 0 else 1.0
        exceeds_halt = drawdown_pct >= self.DRAWDOWN_HALT_THRESHOLD

        max_bet = max(bet_sizes) if bet_sizes else 0
        min_bet = min(bet_sizes) if bet_sizes else 0
        avg_bet = sum(bet_sizes) / len(bet_sizes) if bet_sizes else 0

        scenario_name = f"${starting_balance:.0f} → {num_losses} losses"

        return StressTestResult(
            scenario_name=scenario_name,
            starting_balance=starting_balance,
            ending_balance=ending_balance,
            total_loss_usd=total_loss_usd,
            drawdown_pct=drawdown_pct,
            max_bet_size=max_bet,
            min_bet_size=min_bet,
            avg_bet_size=avg_bet,
            bet_sizes=bet_sizes,
            exceeds_halt_threshold=exceeds_halt
        )

    def run_stress_tests(self, balance_levels: List[float]) -> List[StressTestResult]:
        """
        Run stress tests at multiple balance levels.

        Args:
            balance_levels: List of starting balance values to test

        Returns:
            List of StressTestResult objects
        """
        results: List[StressTestResult] = []

        for balance in balance_levels:
            result = self.simulate_loss_streak(starting_balance=balance, num_losses=10)
            results.append(result)

        return results

    def generate_csv_report(self, results: List[StressTestResult], output_path: Path):
        """Generate CSV report with stress test results"""
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "Scenario",
                "Starting Balance",
                "Ending Balance",
                "Total Loss",
                "Drawdown %",
                "Max Bet",
                "Min Bet",
                "Avg Bet",
                "Exceeds 30% Halt",
                "Bet Sizes (sequence)"
            ])

            # Data rows
            for result in results:
                bet_sequence = " → ".join([f"${bet:.2f}" for bet in result.bet_sizes])

                writer.writerow([
                    result.scenario_name,
                    f"${result.starting_balance:.2f}",
                    f"${result.ending_balance:.2f}",
                    f"${result.total_loss_usd:.2f}",
                    f"{result.drawdown_pct * 100:.1f}%",
                    f"${result.max_bet_size:.2f}",
                    f"${result.min_bet_size:.2f}",
                    f"${result.avg_bet_size:.2f}",
                    "❌ YES" if result.exceeds_halt_threshold else "✅ NO",
                    bet_sequence
                ])

    def generate_markdown_report(self, results: List[StressTestResult], output_path: Path):
        """Generate detailed markdown report"""
        with open(output_path, 'w') as f:
            f.write("# Position Sizing Stress Test Report\n\n")
            f.write("**Persona:** Colonel Rita 'The Guardian' Stevens (Risk Management Architect)\n\n")
            f.write("**Date:** 2026-01-16\n\n")
            f.write("**Objective:** Validate that tiered position sizing protects against catastrophic loss during 10-loss streaks.\n\n")

            f.write("---\n\n")
            f.write("## Executive Summary\n\n")

            # Count scenarios that exceed halt threshold
            critical_scenarios = [r for r in results if r.exceeds_halt_threshold]
            safe_scenarios = [r for r in results if not r.exceeds_halt_threshold]

            if critical_scenarios:
                f.write("**Status:** ⚠️ **CRITICAL RISK DETECTED**\n\n")
                f.write(f"- {len(critical_scenarios)}/{len(results)} scenarios exceed 30% drawdown halt threshold\n")
                f.write(f"- Tiered sizing DOES NOT provide adequate protection at low balance levels\n")
                f.write(f"- Worst case: {max(r.drawdown_pct for r in results) * 100:.1f}% drawdown\n\n")
            else:
                f.write("**Status:** ✅ **POSITION SIZING ADEQUATE**\n\n")
                f.write(f"- All {len(results)} scenarios remain within 30% drawdown threshold\n")
                f.write(f"- Tiered sizing successfully protects against 10-loss streaks\n")
                f.write(f"- Worst case: {max(r.drawdown_pct for r in results) * 100:.1f}% drawdown\n\n")

            f.write("---\n\n")
            f.write("## Stress Test Configuration\n\n")
            f.write("**Position Sizing Tiers:**\n")
            f.write("- Balance < $30: 15% per trade\n")
            f.write("- Balance $30-75: 10% per trade\n")
            f.write("- Balance $75-150: 7% per trade\n")
            f.write("- Balance > $150: 5% per trade\n\n")
            f.write(f"**Constraints:**\n")
            f.write(f"- Minimum bet: ${self.MIN_BET_USD:.2f}\n")
            f.write(f"- Maximum bet: ${self.MAX_POSITION_USD:.2f}\n")
            f.write(f"- Halt threshold: {self.DRAWDOWN_HALT_THRESHOLD * 100:.0f}% drawdown\n\n")
            f.write("**Scenario:** 10 consecutive losses (worst case: all bets finish at $0.00)\n\n")

            f.write("---\n\n")
            f.write("## Detailed Results\n\n")

            for result in results:
                # Emoji based on threshold
                status_emoji = "❌" if result.exceeds_halt_threshold else "✅"

                f.write(f"### {status_emoji} {result.scenario_name}\n\n")
                f.write(f"| Metric | Value |\n")
                f.write(f"|--------|-------|\n")
                f.write(f"| Starting Balance | ${result.starting_balance:.2f} |\n")
                f.write(f"| Ending Balance | ${result.ending_balance:.2f} |\n")
                f.write(f"| Total Loss | ${result.total_loss_usd:.2f} |\n")
                f.write(f"| Drawdown | {result.drawdown_pct * 100:.1f}% |\n")
                f.write(f"| Max Bet Size | ${result.max_bet_size:.2f} |\n")
                f.write(f"| Min Bet Size | ${result.min_bet_size:.2f} |\n")
                f.write(f"| Avg Bet Size | ${result.avg_bet_size:.2f} |\n")
                f.write(f"| Exceeds 30% Halt | {'YES ❌' if result.exceeds_halt_threshold else 'NO ✅'} |\n\n")

                # Bet sequence visualization
                f.write("**Bet Size Evolution:**\n\n")
                for i, bet in enumerate(result.bet_sizes, 1):
                    balance_after = result.starting_balance - sum(result.bet_sizes[:i])
                    f.write(f"- Loss {i}: ${bet:.2f} bet → Balance: ${balance_after:.2f}\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("## Analysis\n\n")

            # Tiered effectiveness analysis
            f.write("### Tiered Sizing Effectiveness\n\n")

            # Calculate reduction in bet sizes over streak
            for result in results:
                if len(result.bet_sizes) >= 2:
                    reduction_pct = ((result.bet_sizes[0] - result.bet_sizes[-1]) / result.bet_sizes[0]) * 100
                    f.write(f"**{result.scenario_name}:**\n")
                    f.write(f"- First bet: ${result.bet_sizes[0]:.2f}\n")
                    f.write(f"- Last bet: ${result.bet_sizes[-1]:.2f}\n")
                    f.write(f"- Reduction: {reduction_pct:.1f}%\n")
                    f.write(f"- Assessment: {'Adaptive sizing working' if reduction_pct > 10 else 'Limited adaptation'}\n\n")

            # Critical threshold analysis
            f.write("### 30% Drawdown Threshold Analysis\n\n")

            closest_call = min(results, key=lambda r: abs(r.drawdown_pct - self.DRAWDOWN_HALT_THRESHOLD))
            f.write(f"**Closest call:** {closest_call.scenario_name}\n")
            f.write(f"- Drawdown: {closest_call.drawdown_pct * 100:.1f}%\n")
            f.write(f"- Margin from halt: {abs(closest_call.drawdown_pct - self.DRAWDOWN_HALT_THRESHOLD) * 100:.1f} percentage points\n\n")

            if closest_call.drawdown_pct < self.DRAWDOWN_HALT_THRESHOLD:
                margin = (self.DRAWDOWN_HALT_THRESHOLD - closest_call.drawdown_pct) * 100
                f.write(f"✅ Safety margin: {margin:.1f}% below halt threshold\n\n")
            else:
                excess = (closest_call.drawdown_pct - self.DRAWDOWN_HALT_THRESHOLD) * 100
                f.write(f"❌ Exceeds halt threshold by: {excess:.1f}%\n\n")

            f.write("---\n\n")
            f.write("## Recommendations\n\n")

            if critical_scenarios:
                f.write("### CRITICAL: Position Sizing Insufficient\n\n")
                f.write("**Problem:** Tiered sizing does not protect against 10-loss streaks at low balance levels.\n\n")
                f.write("**Recommendations:**\n")
                f.write("1. **Increase minimum tier:** Change <$30 tier from 15% → 10% per trade\n")
                f.write("2. **Add loss streak protection:** After 5 consecutive losses, reduce all tiers by 50%\n")
                f.write("3. **Lower minimum bet:** Consider $0.75 minimum (if CLOB allows) for more gradual scaling\n")
                f.write("4. **Add circuit breaker:** Halt trading after 7 consecutive losses (before hitting 30% drawdown)\n\n")
            else:
                f.write("### Position Sizing Validated ✅\n\n")
                f.write("**Finding:** Tiered sizing successfully protects against 10-loss streaks at tested balance levels.\n\n")
                f.write("**Recommendations:**\n")
                f.write("1. **Monitor in production:** Track actual loss streaks vs simulated scenarios\n")
                f.write("2. **Test extreme scenarios:** Simulate 15-loss and 20-loss streaks\n")
                f.write("3. **Add early warning:** Alert when 5+ consecutive losses occur (50% of tested scenario)\n")
                f.write("4. **Review quarterly:** Re-run stress tests after balance tier changes\n\n")

            # Balance tier recommendations
            f.write("### Balance-Specific Guidance\n\n")
            for result in results:
                risk_level = "HIGH RISK" if result.exceeds_halt_threshold else "ACCEPTABLE" if result.drawdown_pct > 0.20 else "LOW RISK"
                f.write(f"**{result.scenario_name}:** {risk_level}\n")
                f.write(f"- Max loss: ${result.total_loss_usd:.2f} ({result.drawdown_pct * 100:.1f}% drawdown)\n")

                if result.exceeds_halt_threshold:
                    f.write(f"- ❌ Would trigger halt at loss #{int(0.30 * result.starting_balance / result.avg_bet_size)}\n")
                elif result.drawdown_pct > 0.20:
                    f.write(f"- ⚠️ Uncomfortable drawdown (>20%)\n")
                else:
                    f.write(f"- ✅ Manageable drawdown (<20%)\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("## Conclusion\n\n")

            worst_drawdown = max(r.drawdown_pct for r in results)

            if worst_drawdown < 0.25:
                verdict = "PASS ✅"
                summary = "Tiered position sizing provides adequate protection against 10-loss streaks. The 30% halt threshold is not breached in any scenario."
            elif worst_drawdown < 0.30:
                verdict = "MARGINAL PASS ⚠️"
                summary = f"Tiered sizing barely protects against 10-loss streaks (worst case: {worst_drawdown * 100:.1f}%). Consider tightening sizing rules."
            else:
                verdict = "FAIL ❌"
                summary = f"Tiered sizing is INSUFFICIENT. Worst case drawdown ({worst_drawdown * 100:.1f}%) exceeds 30% halt threshold. Immediate action required."

            f.write(f"**Verdict:** {verdict}\n\n")
            f.write(f"{summary}\n\n")
            f.write("**Next Steps:**\n")
            if worst_drawdown >= 0.30:
                f.write("1. Implement recommended position sizing changes IMMEDIATELY\n")
                f.write("2. Add loss streak circuit breaker (halt after 7 consecutive losses)\n")
                f.write("3. Re-run stress tests after changes\n")
                f.write("4. Monitor first 50 live trades under new rules\n")
            else:
                f.write("1. Deploy current position sizing to production (validated)\n")
                f.write("2. Add loss streak monitoring alerts (5+ consecutive losses)\n")
                f.write("3. Review stress test results quarterly\n")
                f.write("4. Test extreme scenarios (15-20 loss streaks) for edge cases\n")

            f.write("\n---\n\n")
            f.write("**Generated by:** Ralph (Research Crew - Position Sizing Stress Test)\n")
            f.write("**Persona:** Colonel Rita 'The Guardian' Stevens\n")


def main():
    """Run stress tests and generate reports"""
    print("Position Sizing Stress Test")
    print("=" * 80)
    print("Persona: Colonel Rita 'The Guardian' Stevens")
    print("Objective: Validate position sizing protection during 10-loss streaks")
    print()

    # Initialize tester
    tester = PositionSizingStressTest()

    # Test scenarios (as specified in acceptance criteria)
    balance_levels = [50.0, 100.0, 200.0]

    print("Running stress tests...")
    results = tester.run_stress_tests(balance_levels)

    # Show summary
    print("\nStress Test Results:")
    print("-" * 80)
    for result in results:
        status = "❌ EXCEEDS HALT" if result.exceeds_halt_threshold else "✅ SAFE"
        print(f"{result.scenario_name:25} | Drawdown: {result.drawdown_pct * 100:5.1f}% | {status}")
    print()

    # Generate reports
    reports_dir = Path("reports/rita_stevens")
    reports_dir.mkdir(parents=True, exist_ok=True)

    csv_path = reports_dir / "stress_test_results.csv"
    md_path = reports_dir / "stress_test_results.md"

    print("Generating reports...")
    tester.generate_csv_report(results, csv_path)
    tester.generate_markdown_report(results, md_path)

    print(f"✅ CSV report: {csv_path}")
    print(f"✅ Markdown report: {md_path}")
    print()

    # Verdict
    worst_drawdown = max(r.drawdown_pct for r in results)
    critical_count = sum(1 for r in results if r.exceeds_halt_threshold)

    if critical_count > 0:
        print(f"⚠️  CRITICAL: {critical_count}/{len(results)} scenarios exceed 30% drawdown threshold")
        print(f"    Worst case: {worst_drawdown * 100:.1f}% drawdown")
        print(f"    ACTION REQUIRED: Review and adjust position sizing tiers")
        return 1
    else:
        print(f"✅ Position sizing validated: All scenarios remain within 30% threshold")
        print(f"    Worst case: {worst_drawdown * 100:.1f}% drawdown")
        print(f"    STATUS: Safe for production deployment")
        return 0


if __name__ == "__main__":
    exit(main())
