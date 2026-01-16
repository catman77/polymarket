#!/usr/bin/env python3
"""
Agent Calibration Analysis - US-RC-028
Persona: Dr. Amara Johnson (Behavioral Finance Expert)

Purpose: Check if agent confidence predictions match actual win rates.
When an agent says 80% confidence, does it win 80% of the time?

Calibration Curve:
- Perfect calibration: y = x (predicted confidence = actual win rate)
- Overconfident: predicted > actual (agent thinks it knows more than it does)
- Underconfident: predicted < actual (agent is too cautious)

Approach:
1. Query agent_votes from shadow trading database
2. Join with outcomes to get actual results (win/loss)
3. Group votes by confidence buckets (0.5-0.6, 0.6-0.7, 0.7-0.8, etc.)
4. Calculate actual win rate per bucket
5. Generate calibration curve (predicted vs actual)
6. Identify overconfident/underconfident agents
"""

import sqlite3
import math
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "simulation" / "trade_journal.db"
REPORT_DIR = PROJECT_ROOT / "reports" / "amara_johnson"


def get_agent_votes_with_outcomes(db_path: Path) -> List[Tuple[str, str, float, bool]]:
    """
    Query agent votes with actual outcomes.

    Returns:
        List of (agent_name, direction, confidence, won) tuples
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query: Join agent_votes -> decisions -> outcomes
    # Match on strategy, crypto, epoch to link vote to outcome
    query = """
        SELECT
            av.agent_name,
            av.direction as predicted_direction,
            av.confidence,
            o.actual_direction,
            o.pnl
        FROM agent_votes av
        JOIN decisions d ON av.decision_id = d.id
        JOIN outcomes o ON (
            d.strategy = o.strategy
            AND d.crypto = o.crypto
            AND d.epoch = o.epoch
        )
        WHERE d.should_trade = 1
        AND d.direction IS NOT NULL
        ORDER BY av.agent_name, av.confidence
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Parse results
    votes_with_outcomes = []
    for agent_name, predicted_direction, confidence, actual_direction, pnl in rows:
        # Win = agent predicted direction matches actual direction
        won = (predicted_direction == actual_direction)
        votes_with_outcomes.append((agent_name, predicted_direction, confidence, won))

    return votes_with_outcomes


def bucket_confidence(confidence: float) -> str:
    """
    Assign confidence to bucket.

    Buckets: 0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0
    Returns bucket label (e.g., "0.60-0.70")
    """
    if confidence < 0.5:
        return "0.00-0.50"
    elif confidence < 0.6:
        return "0.50-0.60"
    elif confidence < 0.7:
        return "0.60-0.70"
    elif confidence < 0.8:
        return "0.70-0.80"
    elif confidence < 0.9:
        return "0.80-0.90"
    else:
        return "0.90-1.00"


def calculate_calibration_per_agent(votes: List[Tuple[str, str, float, bool]]) -> Dict[str, Dict[str, Tuple[float, int, int]]]:
    """
    Calculate calibration metrics per agent.

    Returns:
        {
            agent_name: {
                bucket: (actual_win_rate, wins, total),
                ...
            }
        }
    """
    # Group by agent and bucket
    agent_buckets = defaultdict(lambda: defaultdict(list))

    for agent_name, direction, confidence, won in votes:
        bucket = bucket_confidence(confidence)
        agent_buckets[agent_name][bucket].append(won)

    # Calculate win rate per bucket
    calibration_data = {}
    for agent_name, buckets in agent_buckets.items():
        agent_calibration = {}
        for bucket, outcomes in buckets.items():
            wins = sum(outcomes)
            total = len(outcomes)
            actual_win_rate = wins / total if total > 0 else 0.0
            agent_calibration[bucket] = (actual_win_rate, wins, total)
        calibration_data[agent_name] = agent_calibration

    return calibration_data


def calculate_calibration_error(calibration_data: Dict[str, Dict[str, Tuple[float, int, int]]]) -> Dict[str, float]:
    """
    Calculate calibration error (ECE - Expected Calibration Error).

    ECE = sum(|predicted - actual| * n_samples) / total_samples

    Lower is better (perfect calibration = 0.0)
    """
    errors = {}

    for agent_name, buckets in calibration_data.items():
        total_samples = 0
        weighted_error_sum = 0.0

        for bucket, (actual_wr, wins, total) in buckets.items():
            # Bucket midpoint = predicted confidence
            bucket_lower = float(bucket.split("-")[0])
            bucket_upper = float(bucket.split("-")[1])
            predicted_confidence = (bucket_lower + bucket_upper) / 2

            # Error = |predicted - actual|
            error = abs(predicted_confidence - actual_wr)
            weighted_error_sum += error * total
            total_samples += total

        ece = weighted_error_sum / total_samples if total_samples > 0 else 0.0
        errors[agent_name] = ece

    return errors


def generate_ascii_calibration_plot(calibration_data: Dict[str, Dict[str, Tuple[float, int, int]]]) -> str:
    """
    Generate ASCII calibration curve (predicted vs actual).

    Format:
    1.0 |                     *
    0.9 |                 *
    0.8 |             *
    0.7 |         *
    0.6 |     *
    0.5 | *
        +------------------
        0.5  0.6  0.7  0.8  0.9  1.0
           Predicted Confidence
    """
    lines = []
    lines.append("📊 Calibration Curve (Predicted vs Actual Win Rate)")
    lines.append("")
    lines.append("Perfect calibration: Points on diagonal (y = x)")
    lines.append("Overconfident: Points below diagonal (predicted > actual)")
    lines.append("Underconfident: Points above diagonal (predicted < actual)")
    lines.append("")

    # Collect all data points
    all_points = []
    for agent_name, buckets in calibration_data.items():
        for bucket, (actual_wr, wins, total) in buckets.items():
            if total >= 3:  # Only plot buckets with enough samples
                bucket_lower = float(bucket.split("-")[0])
                bucket_upper = float(bucket.split("-")[1])
                predicted = (bucket_lower + bucket_upper) / 2
                all_points.append((predicted, actual_wr, agent_name, total))

    if not all_points:
        lines.append("⚠️ No data points with ≥3 samples per bucket")
        return "\n".join(lines)

    # ASCII plot (10 rows, 40 cols)
    rows = 10
    cols = 40
    grid = [[' ' for _ in range(cols)] for _ in range(rows)]

    # Plot diagonal (perfect calibration)
    for i in range(rows):
        for j in range(cols):
            x = j / (cols - 1)  # 0.0 to 1.0
            y = 1.0 - (i / (rows - 1))  # 1.0 to 0.0 (inverted)
            if abs(x - y) < 0.05:  # Within 5% of diagonal
                grid[i][j] = '·'

    # Plot data points
    for predicted, actual, agent_name, total in all_points:
        # Map to grid coordinates
        x = predicted  # 0.0 to 1.0
        y = actual     # 0.0 to 1.0

        col = int(x * (cols - 1))
        row = int((1.0 - y) * (rows - 1))  # Invert y-axis

        if 0 <= row < rows and 0 <= col < cols:
            # Symbol: * for overconfident (below diagonal), + for underconfident (above)
            if actual < predicted - 0.05:
                grid[row][col] = '*'  # Overconfident
            elif actual > predicted + 0.05:
                grid[row][col] = '+'  # Underconfident
            else:
                grid[row][col] = 'o'  # Well-calibrated

    # Render grid with axes
    lines.append("    1.0 |" + "".join(grid[0]))
    for i in range(1, rows):
        y_label = f"{1.0 - i / (rows - 1):.1f}"
        lines.append(f"    {y_label} |" + "".join(grid[i]))
    lines.append("    0.0 +" + "-" * cols)
    lines.append("        0.0" + " " * 15 + "0.5" + " " * 15 + "1.0")
    lines.append("             Predicted Confidence")
    lines.append("")
    lines.append("Legend: · = perfect calibration, * = overconfident, + = underconfident, o = well-calibrated")

    return "\n".join(lines)


def generate_report(calibration_data: Dict[str, Dict[str, Tuple[float, int, int]]],
                   calibration_errors: Dict[str, float],
                   votes_count: int) -> str:
    """
    Generate markdown calibration report.
    """
    report = []
    report.append("# Agent Calibration Analysis")
    report.append("")
    report.append("**Researcher:** Dr. Amara Johnson (Behavioral Finance Expert)")
    report.append("**Date:** 2026-01-16")
    report.append("**Task:** US-RC-028")
    report.append("")
    report.append("## Executive Summary")
    report.append("")

    if not calibration_data:
        report.append("⚠️ **NO DATA AVAILABLE**")
        report.append("")
        report.append("The shadow trading database contains no resolved trades with agent votes.")
        report.append("Calibration analysis requires actual outcomes to compare against predicted confidence.")
        report.append("")
        report.append("**Next Steps:**")
        report.append("1. Wait for shadow strategies to accumulate resolved trades")
        report.append("2. Re-run this analysis after 50+ trades (for statistical significance)")
        report.append("3. Expected timeline: 2-3 days of live trading")
        return "\n".join(report)

    # Find most/least calibrated agents
    sorted_agents = sorted(calibration_errors.items(), key=lambda x: x[1])
    best_agent, best_ece = sorted_agents[0]
    worst_agent, worst_ece = sorted_agents[-1]

    report.append(f"**Total Agent Votes Analyzed:** {votes_count}")
    report.append(f"**Agents Evaluated:** {len(calibration_data)}")
    report.append("")
    report.append(f"🏆 **Best Calibrated:** {best_agent} (ECE = {best_ece:.3f})")
    report.append(f"⚠️ **Worst Calibrated:** {worst_agent} (ECE = {worst_ece:.3f})")
    report.append("")

    # Overall verdict
    avg_ece = sum(calibration_errors.values()) / len(calibration_errors)
    if avg_ece < 0.05:
        verdict = "✅ WELL-CALIBRATED"
        explanation = "Agents' confidence predictions closely match actual outcomes."
    elif avg_ece < 0.10:
        verdict = "⚠️ MODERATELY CALIBRATED"
        explanation = "Some discrepancies between predicted confidence and actual win rates."
    else:
        verdict = "❌ POORLY CALIBRATED"
        explanation = "Significant overconfidence or underconfidence detected."

    report.append(f"**Overall Verdict:** {verdict}")
    report.append(f"**Average Calibration Error:** {avg_ece:.3f}")
    report.append(f"**Interpretation:** {explanation}")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Methodology")
    report.append("")
    report.append("### What is Calibration?")
    report.append("")
    report.append("Calibration measures whether an agent's **predicted confidence** matches **actual outcomes**:")
    report.append("")
    report.append("- When an agent votes with 80% confidence → Does it win 80% of the time?")
    report.append("- **Perfect calibration:** Predicted confidence = Actual win rate")
    report.append("- **Overconfident:** Predicted > Actual (agent thinks it knows more than it does)")
    report.append("- **Underconfident:** Predicted < Actual (agent is too cautious)")
    report.append("")
    report.append("### Calibration Curve")
    report.append("")
    report.append("We plot **Predicted Confidence (x-axis)** vs **Actual Win Rate (y-axis)**:")
    report.append("")
    report.append("- **Diagonal line (y=x):** Perfect calibration")
    report.append("- **Below diagonal:** Overconfidence (claims higher confidence than deserved)")
    report.append("- **Above diagonal:** Underconfidence (claims lower confidence than deserved)")
    report.append("")
    report.append("### Expected Calibration Error (ECE)")
    report.append("")
    report.append("ECE = Average absolute difference between predicted and actual, weighted by sample size:")
    report.append("")
    report.append("```")
    report.append("ECE = Σ |predicted - actual| * n_samples / total_samples")
    report.append("```")
    report.append("")
    report.append("**Interpretation:**")
    report.append("- ECE < 0.05: Well-calibrated (excellent)")
    report.append("- ECE 0.05-0.10: Moderately calibrated (acceptable)")
    report.append("- ECE > 0.10: Poorly calibrated (needs improvement)")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Calibration Results by Agent")
    report.append("")

    for agent_name in sorted(calibration_data.keys()):
        buckets = calibration_data[agent_name]
        ece = calibration_errors[agent_name]

        report.append(f"### {agent_name}")
        report.append("")
        report.append(f"**Calibration Error (ECE):** {ece:.3f}")
        report.append("")
        report.append("| Confidence Bucket | Predicted | Actual WR | Wins | Total | Error | Verdict |")
        report.append("|------------------|-----------|-----------|------|-------|-------|---------|")

        for bucket in sorted(buckets.keys()):
            actual_wr, wins, total = buckets[bucket]
            bucket_lower = float(bucket.split("-")[0])
            bucket_upper = float(bucket.split("-")[1])
            predicted = (bucket_lower + bucket_upper) / 2
            error = abs(predicted - actual_wr)

            # Verdict
            if error < 0.05:
                verdict = "✅ Good"
            elif error < 0.10:
                verdict = "⚠️ Fair"
            else:
                if actual_wr < predicted:
                    verdict = "❌ Overconfident"
                else:
                    verdict = "❌ Underconfident"

            report.append(f"| {bucket} | {predicted:.2f} | {actual_wr:.2f} | {wins} | {total} | {error:.3f} | {verdict} |")

        report.append("")

        # Agent-specific recommendation
        if ece < 0.05:
            rec = f"✅ **Well-calibrated** - {agent_name}'s confidence predictions are reliable."
        elif ece < 0.10:
            rec = f"⚠️ **Moderately calibrated** - Minor adjustments may improve {agent_name}'s predictions."
        else:
            rec = f"❌ **Poorly calibrated** - {agent_name} needs recalibration or should be disabled."

        report.append(f"**Recommendation:** {rec}")
        report.append("")

    report.append("---")
    report.append("")
    report.append("## Calibration Curve")
    report.append("")

    # ASCII calibration plot
    plot = generate_ascii_calibration_plot(calibration_data)
    report.append("```")
    report.append(plot)
    report.append("```")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Overconfident Agents (Predicted > Actual)")
    report.append("")

    overconfident = []
    for agent_name, buckets in calibration_data.items():
        for bucket, (actual_wr, wins, total) in buckets.items():
            bucket_lower = float(bucket.split("-")[0])
            bucket_upper = float(bucket.split("-")[1])
            predicted = (bucket_lower + bucket_upper) / 2
            if predicted > actual_wr + 0.10 and total >= 5:  # Significant overconfidence
                overconfident.append((agent_name, bucket, predicted, actual_wr, total))

    if overconfident:
        report.append("⚠️ **Agents with significant overconfidence detected:**")
        report.append("")
        report.append("| Agent | Confidence Bucket | Predicted | Actual WR | Gap | Trades |")
        report.append("|-------|------------------|-----------|-----------|-----|--------|")
        for agent, bucket, pred, actual, total in sorted(overconfident, key=lambda x: x[2] - x[3], reverse=True):
            gap = pred - actual
            report.append(f"| {agent} | {bucket} | {pred:.2f} | {actual:.2f} | {gap:.2f} | {total} |")
        report.append("")
        report.append("**Implications:**")
        report.append("- Overconfident agents claim higher certainty than justified")
        report.append("- Risk: Inflates consensus confidence, leading to aggressive trades")
        report.append("- Fix: Apply confidence penalty (multiply by calibration factor)")
        report.append("- Or: Disable agent if consistently overconfident")
    else:
        report.append("✅ No agents show significant overconfidence.")

    report.append("")
    report.append("---")
    report.append("")
    report.append("## Underconfident Agents (Predicted < Actual)")
    report.append("")

    underconfident = []
    for agent_name, buckets in calibration_data.items():
        for bucket, (actual_wr, wins, total) in buckets.items():
            bucket_lower = float(bucket.split("-")[0])
            bucket_upper = float(bucket.split("-")[1])
            predicted = (bucket_lower + bucket_upper) / 2
            if actual_wr > predicted + 0.10 and total >= 5:  # Significant underconfidence
                underconfident.append((agent_name, bucket, predicted, actual_wr, total))

    if underconfident:
        report.append("⚠️ **Agents with significant underconfidence detected:**")
        report.append("")
        report.append("| Agent | Confidence Bucket | Predicted | Actual WR | Gap | Trades |")
        report.append("|-------|------------------|-----------|-----------|-----|--------|")
        for agent, bucket, pred, actual, total in sorted(underconfident, key=lambda x: x[3] - x[2], reverse=True):
            gap = actual - pred
            report.append(f"| {agent} | {bucket} | {pred:.2f} | {actual:.2f} | {gap:.2f} | {total} |")
        report.append("")
        report.append("**Implications:**")
        report.append("- Underconfident agents vote with lower confidence than justified")
        report.append("- Risk: Underweights good signals, reduces consensus confidence")
        report.append("- Fix: Apply confidence boost (multiply by calibration factor)")
        report.append("- Or: Retrain agent with updated confidence thresholds")
    else:
        report.append("✅ No agents show significant underconfidence.")

    report.append("")
    report.append("---")
    report.append("")
    report.append("## Recommendations")
    report.append("")

    # Prioritized recommendations
    report.append("### Immediate Actions")
    report.append("")

    # 1. Disable worst agents
    worst_agents = [name for name, ece in sorted_agents[-3:] if ece > 0.10]
    if worst_agents:
        report.append(f"1. **Disable poorly calibrated agents:** {', '.join(worst_agents)}")
        report.append(f"   - Calibration errors >0.10 indicate unreliable confidence predictions")
        report.append(f"   - Re-enable after recalibration or retraining")

    # 2. Apply calibration corrections
    needs_correction = [name for name, ece in sorted_agents if 0.05 < ece < 0.10]
    if needs_correction:
        report.append(f"2. **Apply confidence corrections:** {', '.join(needs_correction)}")
        report.append(f"   - Multiply confidence by calibration factor: factor = (actual_avg / predicted_avg)")
        report.append(f"   - Example: If agent claims 80% but wins 70%, apply factor = 0.875")

    # 3. Monitor well-calibrated agents
    well_calibrated = [name for name, ece in sorted_agents if ece < 0.05]
    if well_calibrated:
        report.append(f"3. **Maintain well-calibrated agents:** {', '.join(well_calibrated)}")
        report.append(f"   - These agents' confidence predictions are reliable")
        report.append(f"   - Continue monitoring for calibration drift over time")

    report.append("")
    report.append("### Long-Term Improvements")
    report.append("")
    report.append("1. **Periodic recalibration:** Re-run this analysis monthly")
    report.append("2. **Confidence thresholds:** Adjust MIN_CONFIDENCE based on calibration")
    report.append("3. **Agent retraining:** Use calibration feedback to improve ML models")
    report.append("4. **Ensemble reweighting:** Weight agents by inverse calibration error")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Behavioral Finance Perspective")
    report.append("")
    report.append("**Dr. Amara Johnson's Assessment:**")
    report.append("")
    report.append("> \"Calibration reveals the psychology of decision-making. Overconfidence is the most")
    report.append("> dangerous bias in trading—it leads to oversized positions, ignored warnings, and")
    report.append("> catastrophic losses. In this system, poorly calibrated agents amplify that risk.\"")
    report.append("")
    report.append("**Key Insights:**")
    report.append("")
    report.append("1. **Overconfidence Bias:** Humans (and ML models) tend to overestimate their accuracy")
    report.append("   - Dunning-Kruger effect: Unskilled agents don't know they're unskilled")
    report.append("   - Fix: External calibration validation (this analysis)")
    report.append("")
    report.append("2. **Confidence as a Signal:** Well-calibrated confidence is valuable information")
    report.append("   - High confidence from calibrated agent → Strong trade signal")
    report.append("   - High confidence from miscalibrated agent → False confidence")
    report.append("")
    report.append("3. **Calibration Drift:** Agents can become miscalibrated over time")
    report.append("   - Market regimes change, patterns shift")
    report.append("   - Solution: Continuous monitoring and recalibration")
    report.append("")
    report.append("4. **Ensemble Benefit:** Combining calibrated agents improves decisions")
    report.append("   - Diverse, well-calibrated agents → Wisdom of crowds")
    report.append("   - Redundant or miscalibrated agents → Groupthink, amplified errors")
    report.append("")

    report.append("---")
    report.append("")
    report.append("## Appendix: Statistical Notes")
    report.append("")
    report.append("### Sample Size Requirements")
    report.append("")
    report.append("Reliable calibration analysis requires sufficient samples per bucket:")
    report.append("")
    report.append("- **Minimum:** 5 votes per bucket (margin of error ~45%)")
    report.append("- **Good:** 20 votes per bucket (margin of error ~22%)")
    report.append("- **Excellent:** 50+ votes per bucket (margin of error ~14%)")
    report.append("")
    report.append("Current analysis includes only buckets with ≥3 samples (loose threshold).")
    report.append("For production decisions, wait for ≥20 samples per bucket.")
    report.append("")
    report.append("### Confidence Intervals")
    report.append("")
    report.append("Actual win rates have uncertainty (binomial confidence intervals):")
    report.append("")
    report.append("- 10 trades, 8 wins → 80% ± 25% (95% CI)")
    report.append("- 50 trades, 40 wins → 80% ± 11% (95% CI)")
    report.append("- 100 trades, 80 wins → 80% ± 8% (95% CI)")
    report.append("")
    report.append("Small sample sizes make calibration curves noisy. Interpret with caution.")
    report.append("")
    report.append("---")
    report.append("")
    report.append("**End of Report**")

    return "\n".join(report)


def main():
    """Main execution."""
    print("=" * 80)
    print("Agent Calibration Analysis - US-RC-028")
    print("Persona: Dr. Amara Johnson (Behavioral Finance Expert)")
    print("=" * 80)
    print()

    # Check database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        print("   Expected shadow trading database with agent votes and outcomes")
        print("   Run bot with shadow trading enabled to generate data")
        return 1

    print(f"📂 Database: {DB_PATH}")
    print()

    # Query data
    print("🔍 Querying agent votes with outcomes...")
    votes_with_outcomes = get_agent_votes_with_outcomes(DB_PATH)
    print(f"   Found {len(votes_with_outcomes)} agent votes with resolved outcomes")
    print()

    if len(votes_with_outcomes) == 0:
        print("⚠️  No data available for calibration analysis")
        print("   Shadow trading database contains no resolved trades with agent votes")
        print()
        print("📝 Generating report with 'no data' message...")

        # Generate empty report
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / "calibration_analysis.md"

        report = generate_report({}, {}, 0)
        report_path.write_text(report)

        print(f"✅ Report generated: {report_path}")
        print()
        print("🔄 Next Steps:")
        print("   1. Wait for shadow strategies to accumulate resolved trades")
        print("   2. Re-run analysis after 50+ trades (for statistical significance)")
        print("   3. Expected timeline: 2-3 days of live trading on VPS")
        return 0

    # Calculate calibration
    print("📊 Calculating calibration per agent...")
    calibration_data = calculate_calibration_per_agent(votes_with_outcomes)
    print(f"   Analyzed {len(calibration_data)} agents")
    print()

    # Calculate errors
    print("🧮 Calculating calibration errors (ECE)...")
    calibration_errors = calculate_calibration_error(calibration_data)

    for agent, ece in sorted(calibration_errors.items(), key=lambda x: x[1]):
        if ece < 0.05:
            verdict = "✅ Well-calibrated"
        elif ece < 0.10:
            verdict = "⚠️ Moderate"
        else:
            verdict = "❌ Poor"
        print(f"   {agent}: ECE = {ece:.3f} {verdict}")
    print()

    # Generate report
    print("📝 Generating calibration report...")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "calibration_analysis.md"

    report = generate_report(calibration_data, calibration_errors, len(votes_with_outcomes))
    report_path.write_text(report)

    print(f"✅ Report generated: {report_path}")
    print()

    # Summary
    avg_ece = sum(calibration_errors.values()) / len(calibration_errors) if calibration_errors else 0.0
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Agents Analyzed: {len(calibration_data)}")
    print(f"Total Votes: {len(votes_with_outcomes)}")
    print(f"Average ECE: {avg_ece:.3f}")
    print()

    if avg_ece < 0.05:
        print("✅ Overall Verdict: WELL-CALIBRATED")
        print("   Agents' confidence predictions are reliable")
    elif avg_ece < 0.10:
        print("⚠️ Overall Verdict: MODERATELY CALIBRATED")
        print("   Some adjustments recommended")
    else:
        print("❌ Overall Verdict: POORLY CALIBRATED")
        print("   Significant improvements needed")

    print()
    print("📊 See full report for detailed recommendations")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
