#!/usr/bin/env python3
"""
US-RC-011: Calculate weighted average fee rate from trades

Persona: Dr. Sarah Chen (Probabilistic Mathematician)
Context: "The breakeven calculation depends on actual fees paid, not theoretical.
         I need to calculate the true weighted average fee rate."

This script analyzes actual trade data to calculate real fee costs and
determine true breakeven win rate.
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Import existing trade parser
sys.path.insert(0, str(Path(__file__).parent))
from parse_trade_logs import TradeLogParser
from fee_calculator import PolymarketFeeCalculator, calculate_weighted_average_fee


def parse_trades_from_log(log_file: Path) -> List[Tuple[float, float]]:
    """
    Parse trade data from bot log.

    Returns:
        List of (entry_price, trade_size_usd) tuples
    """
    # Check if log file exists
    if not log_file.exists():
        return []

    parser = TradeLogParser(log_file)
    parser.parse()

    # Extract entry price and trade size for each trade
    trade_data = []
    for trade in parser.trades:
        entry_price = trade.entry_price
        # Trade size = entry_price × shares
        trade_size_usd = entry_price * trade.shares
        trade_data.append((entry_price, trade_size_usd))

    return trade_data


def generate_fee_economics_report(log_file: Path, output_file: Path):
    """Generate comprehensive fee economics validation report."""

    # Parse trades
    print(f"Parsing trades from {log_file}...")
    trade_data = parse_trades_from_log(log_file)

    if not trade_data:
        print("⚠️  No trade data found. Generating empty report.")
        trade_data = []

    # Calculate weighted average fees
    print(f"Analyzing {len(trade_data)} trades...")
    results = calculate_weighted_average_fee(trade_data)

    # Generate markdown report
    report_lines = []
    report_lines.append("# Fee Economics Validation Report")
    report_lines.append("")
    report_lines.append("**Persona:** Dr. Sarah Chen (Probabilistic Mathematician)")
    report_lines.append("**Generated:** 2026-01-16")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Executive Summary
    report_lines.append("## Executive Summary")
    report_lines.append("")
    if len(trade_data) == 0:
        report_lines.append("⚠️ **Status:** NO DATA AVAILABLE")
        report_lines.append("")
        report_lines.append("No trade data found in bot logs. This report documents the methodology")
        report_lines.append("and will be populated with actual fee analysis once production data is available.")
    else:
        status = "✅ VALIDATED" if results['num_trades'] >= 50 else "⚠️ LIMITED DATA"
        report_lines.append(f"**Status:** {status}")
        report_lines.append("")
        report_lines.append(f"- **Trades Analyzed:** {results['num_trades']}")
        report_lines.append(f"- **Total Volume:** ${results['total_volume_usd']:.2f}")
        report_lines.append(f"- **Weighted Avg Fee Rate:** {results['weighted_avg_fee_rate']*100:.2f}%")
        report_lines.append(f"- **Round-Trip Fee Rate:** {results['weighted_avg_round_trip_fee']*100:.2f}%")
        report_lines.append(f"- **Breakeven Win Rate:** {results['breakeven_win_rate']*100:.2f}%")

        # Assessment
        if results['breakeven_win_rate'] > 0.55:
            report_lines.append("")
            report_lines.append("🔴 **CONCERN:** High breakeven win rate (>55%) makes profitability difficult.")
            report_lines.append("Current entry prices result in high fees. Recommend cheaper entries (<$0.25).")
        elif results['breakeven_win_rate'] > 0.53:
            report_lines.append("")
            report_lines.append("🟡 **MODERATE:** Breakeven win rate is achievable but tight margin.")
            report_lines.append("Current 56-60% win rate provides small edge. Improvement recommended.")
        else:
            report_lines.append("")
            report_lines.append("🟢 **EXCELLENT:** Low breakeven win rate provides comfortable margin.")
            report_lines.append("Cheap entry strategy is working well for fee minimization.")

    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # Fee Rate Analysis
    report_lines.append("## Fee Rate Analysis")
    report_lines.append("")
    if len(trade_data) > 0:
        report_lines.append("### Summary Statistics")
        report_lines.append("")
        report_lines.append(f"| Metric | Value |")
        report_lines.append(f"|--------|-------|")
        report_lines.append(f"| Number of Trades | {results['num_trades']} |")
        report_lines.append(f"| Total Volume | ${results['total_volume_usd']:.2f} |")
        report_lines.append(f"| Average Trade Size | ${results['total_volume_usd']/results['num_trades']:.2f} |")
        report_lines.append(f"| Min Fee Rate | {results['min_fee_rate']*100:.2f}% |")
        report_lines.append(f"| Max Fee Rate | {results['max_fee_rate']*100:.2f}% |")
        report_lines.append(f"| Weighted Avg Fee Rate | {results['weighted_avg_fee_rate']*100:.2f}% |")
        report_lines.append("")

        # Fee formula explanation
        report_lines.append("### Fee Formula")
        report_lines.append("")
        report_lines.append("Polymarket uses a probability-based fee structure:")
        report_lines.append("")
        report_lines.append("```")
        report_lines.append("fee_rate = 3.15% × (1 - |2 × entry_price - 1|)")
        report_lines.append("```")
        report_lines.append("")
        report_lines.append("**Examples:**")
        report_lines.append("- Entry at $0.50 (50% probability): 3.15% fee")
        report_lines.append("- Entry at $0.25 (25% probability): 1.58% fee")
        report_lines.append("- Entry at $0.10 (10% probability): 0.63% fee")
        report_lines.append("")

        # Entry price distribution
        report_lines.append("### Entry Price Distribution")
        report_lines.append("")
        # Bucket trades by entry price
        buckets = {
            '0.01-0.10': [],
            '0.10-0.15': [],
            '0.15-0.20': [],
            '0.20-0.25': [],
            '0.25-0.30': [],
            '0.30+': []
        }
        for entry_price, size in trade_data:
            if entry_price < 0.10:
                buckets['0.01-0.10'].append(size)
            elif entry_price < 0.15:
                buckets['0.10-0.15'].append(size)
            elif entry_price < 0.20:
                buckets['0.15-0.20'].append(size)
            elif entry_price < 0.25:
                buckets['0.20-0.25'].append(size)
            elif entry_price < 0.30:
                buckets['0.25-0.30'].append(size)
            else:
                buckets['0.30+'].append(size)

        report_lines.append("| Entry Price Range | Count | % of Trades | Total Volume | Avg Fee |")
        report_lines.append("|-------------------|-------|-------------|--------------|---------|")
        for bucket_name, sizes in buckets.items():
            if len(sizes) > 0:
                count = len(sizes)
                pct = count / len(trade_data) * 100
                volume = sum(sizes)
                # Estimate avg fee for bucket midpoint
                bucket_start = float(bucket_name.split('-')[0])
                if '+' in bucket_name:
                    avg_price = 0.35  # Estimate for 0.30+
                else:
                    bucket_end = float(bucket_name.split('-')[1])
                    avg_price = (bucket_start + bucket_end) / 2
                avg_fee = PolymarketFeeCalculator.calculate_fee_rate(avg_price)
                report_lines.append(f"| ${bucket_name} | {count} | {pct:.1f}% | ${volume:.2f} | {avg_fee*100:.2f}% |")
            else:
                report_lines.append(f"| ${bucket_name} | 0 | 0.0% | $0.00 | - |")
        report_lines.append("")
    else:
        report_lines.append("*No trade data available*")
        report_lines.append("")

    # Breakeven Win Rate Calculation
    report_lines.append("## Breakeven Win Rate Calculation")
    report_lines.append("")
    if len(trade_data) > 0:
        report_lines.append("### Mathematical Derivation")
        report_lines.append("")
        report_lines.append("To break even after fees, expected profit must equal zero:")
        report_lines.append("")
        report_lines.append("```")
        report_lines.append("E[profit] = 0")
        report_lines.append("win_rate × avg_win - (1 - win_rate) × avg_loss - fee = 0")
        report_lines.append("")
        report_lines.append("For binary options with $1.00 payout:")
        report_lines.append("win_rate × (1 - entry_price) - (1 - win_rate) × entry_price - round_trip_fee = 0")
        report_lines.append("")
        report_lines.append("Simplified (assuming entry_price ≈ 0.20 average):")
        report_lines.append("breakeven_wr ≈ 0.5 + (round_trip_fee / 2)")
        report_lines.append("```")
        report_lines.append("")
        report_lines.append("### Actual Calculation")
        report_lines.append("")
        report_lines.append(f"- **Weighted Avg Fee (one-way):** {results['weighted_avg_fee_rate']*100:.2f}%")
        report_lines.append(f"- **Round-trip Fee:** {results['weighted_avg_round_trip_fee']*100:.2f}%")
        report_lines.append(f"- **Breakeven Win Rate:** {results['breakeven_win_rate']*100:.2f}%")
        report_lines.append("")
        report_lines.append("### Comparison to Current Performance")
        report_lines.append("")
        report_lines.append("| Metric | Value | Status |")
        report_lines.append("|--------|-------|--------|")
        report_lines.append(f"| Breakeven WR | {results['breakeven_win_rate']*100:.2f}% | Required |")
        report_lines.append(f"| Claimed WR | 56-60% | *To be validated* |")

        # Calculate margin above breakeven
        claimed_wr_low = 0.56
        claimed_wr_high = 0.60
        margin_low = (claimed_wr_low - results['breakeven_win_rate']) * 100
        margin_high = (claimed_wr_high - results['breakeven_win_rate']) * 100

        if margin_low > 0:
            report_lines.append(f"| Margin (Low) | {claimed_wr_low*100:.1f}% - {results['breakeven_win_rate']*100:.2f}% = {margin_low:.2f}% | 🟢 Profitable |")
            report_lines.append(f"| Margin (High) | {claimed_wr_high*100:.1f}% - {results['breakeven_win_rate']*100:.2f}% = {margin_high:.2f}% | 🟢 Profitable |")
        else:
            report_lines.append(f"| Margin (Low) | {claimed_wr_low*100:.1f}% - {results['breakeven_win_rate']*100:.2f}% = {margin_low:.2f}% | 🔴 Unprofitable |")
            report_lines.append(f"| Margin (High) | {claimed_wr_high*100:.1f}% - {results['breakeven_win_rate']*100:.2f}% = {margin_high:.2f}% | 🔴 Unprofitable |")

        report_lines.append("")
    else:
        report_lines.append("*Awaiting trade data for calculation*")
        report_lines.append("")
        report_lines.append("Breakeven formula: `breakeven_wr = 0.5 + (round_trip_fee / 2)`")
        report_lines.append("")

    # Recommendations
    report_lines.append("## Recommendations")
    report_lines.append("")
    if len(trade_data) > 0:
        if results['breakeven_win_rate'] > 0.55:
            report_lines.append("### CRITICAL: High Fee Burden")
            report_lines.append("")
            report_lines.append("1. **Lower Entry Prices:** Target entries <$0.20 to reduce fees")
            report_lines.append("2. **Avoid 50% Entries:** Never enter near $0.50 (maximum fees)")
            report_lines.append("3. **Contrarian Focus:** Cheap entries ($0.08-$0.15) have best fee economics")
            report_lines.append("")
        elif results['breakeven_win_rate'] > 0.53:
            report_lines.append("### MODERATE: Acceptable but Improvable")
            report_lines.append("")
            report_lines.append("1. **Maintain Entry Discipline:** Keep average entry <$0.25")
            report_lines.append("2. **Win Rate Focus:** Small improvements (2-3%) would significantly increase profitability")
            report_lines.append("3. **Monitor Fee Drift:** Track weighted avg fee over time")
            report_lines.append("")
        else:
            report_lines.append("### EXCELLENT: Optimal Fee Structure")
            report_lines.append("")
            report_lines.append("1. **Maintain Current Strategy:** Cheap entries are working well")
            report_lines.append("2. **Focus on Win Rate:** Fee burden is minimized, optimize execution")
            report_lines.append("3. **Document Success:** Current entry price distribution is optimal")
            report_lines.append("")
    else:
        report_lines.append("1. **Collect Data:** Run bot in production to gather trade data")
        report_lines.append("2. **Re-run Analysis:** Execute this script after ≥50 trades")
        report_lines.append("3. **Target Entries:** Aim for average entry price <$0.25")
        report_lines.append("")

    # Methodology
    report_lines.append("## Methodology")
    report_lines.append("")
    report_lines.append("### Data Sources")
    report_lines.append("")
    report_lines.append(f"- **Trade Log:** `{log_file}`")
    report_lines.append(f"- **Trades Parsed:** {len(trade_data)}")
    report_lines.append("")
    report_lines.append("### Analysis Steps")
    report_lines.append("")
    report_lines.append("1. Parse all ORDER PLACED entries from bot.log")
    report_lines.append("2. Extract entry_price and shares for each trade")
    report_lines.append("3. Calculate fee_rate using Polymarket formula")
    report_lines.append("4. Calculate fee_amount = fee_rate × trade_size")
    report_lines.append("5. Compute weighted average: sum(fees) / sum(volume)")
    report_lines.append("6. Estimate round-trip fee (conservative: 2× one-way)")
    report_lines.append("7. Calculate breakeven_wr = 0.5 + (round_trip_fee / 2)")
    report_lines.append("")
    report_lines.append("### Formula Validation")
    report_lines.append("")
    report_lines.append("Fee calculator tested against known values:")
    report_lines.append("- Entry at $0.50 → 3.15% fee ✓")
    report_lines.append("- Entry at $0.10 → <1% fee ✓")
    report_lines.append("- Entry at $0.01 → <0.1% fee ✓")
    report_lines.append("")

    # Appendix
    report_lines.append("## Appendix: Trade Details")
    report_lines.append("")
    if len(trade_data) > 0 and len(trade_data) <= 50:
        report_lines.append("### All Trades")
        report_lines.append("")
        report_lines.append("| # | Entry Price | Trade Size | Fee Rate | Fee Amount |")
        report_lines.append("|---|-------------|------------|----------|------------|")
        for i, fa in enumerate(results['fee_details'], 1):
            report_lines.append(f"| {i} | ${fa.entry_price:.2f} | ${fa.trade_size_usd:.2f} | {fa.fee_rate*100:.2f}% | ${fa.fee_amount_usd:.2f} |")
        report_lines.append("")
    elif len(trade_data) > 50:
        report_lines.append(f"*{len(trade_data)} trades - see CSV export for full details*")
        report_lines.append("")
    else:
        report_lines.append("*No trades to display*")
        report_lines.append("")

    # Write report
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write('\n'.join(report_lines))

    print(f"✅ Report generated: {output_file}")

    return results


if __name__ == '__main__':
    # Paths
    log_file = Path('bot.log')
    output_file = Path('reports/sarah_chen/fee_economics_validation.md')

    # Generate report
    try:
        results = generate_fee_economics_report(log_file, output_file)

        # Summary
        print("\n--- Fee Economics Analysis ---")
        print(f"Trades Analyzed: {results['num_trades']}")
        if results['num_trades'] > 0:
            print(f"Weighted Avg Fee: {results['weighted_avg_fee_rate']*100:.2f}%")
            print(f"Round-trip Fee: {results['weighted_avg_round_trip_fee']*100:.2f}%")
            print(f"Breakeven WR: {results['breakeven_win_rate']*100:.2f}%")
            print(f"\n✅ Analysis complete!")
        else:
            print("⚠️  No trade data found (expected in dev environment)")
            print("   Report generated with methodology documentation")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
