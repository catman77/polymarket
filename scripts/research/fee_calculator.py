#!/usr/bin/env python3
"""
US-RC-011: Calculate weighted average fee rate from trades

Persona: Dr. Sarah Chen (Probabilistic Mathematician)
Context: "The breakeven calculation depends on actual fees paid, not theoretical.
         I need to calculate the true weighted average fee rate."

This script calculates Polymarket fee rates based on actual entry prices,
then computes the weighted average to determine true breakeven win rate.
"""

import sys
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class FeeAnalysis:
    """Fee analysis results for a trade."""
    entry_price: float
    trade_size_usd: float
    fee_rate: float
    fee_amount_usd: float


class PolymarketFeeCalculator:
    """
    Calculate Polymarket fees based on entry price probability.

    Polymarket uses a maker-taker fee structure where fees depend on
    the probability of the outcome (represented by entry price).

    Fee formula (approximate):
    - At 50% probability (entry_price = $0.50): 3.15% taker fee
    - At extremes (entry_price near $0.01 or $0.99): fees approach 0%
    - Fee curve: fee_rate ≈ 3.15% × (1 - |2×price - 1|)

    This approximation models the fact that fees are lowest when
    probabilities are extreme (high certainty) and highest at 50/50.
    """

    BASE_FEE_RATE = 0.0315  # 3.15% at 50% probability

    @classmethod
    def calculate_fee_rate(cls, entry_price: float) -> float:
        """
        Calculate fee rate based on entry price probability.

        Args:
            entry_price: Entry price in USD (0.01 to 0.99)

        Returns:
            Fee rate as decimal (0.0315 = 3.15%)
        """
        # Validate entry price
        if entry_price < 0.01 or entry_price > 0.99:
            raise ValueError(f"Entry price must be between $0.01 and $0.99, got ${entry_price:.2f}")

        # Calculate distance from 50% probability
        # At 50%: distance = 0, fee = full 3.15%
        # At extremes: distance = 1, fee = 0%
        distance_from_50 = abs(2 * entry_price - 1)

        # Fee rate scales inversely with distance from 50%
        fee_rate = cls.BASE_FEE_RATE * (1 - distance_from_50)

        return fee_rate

    @classmethod
    def calculate_fee_amount(cls, entry_price: float, trade_size_usd: float) -> float:
        """
        Calculate fee amount in USD for a trade.

        Args:
            entry_price: Entry price in USD
            trade_size_usd: Trade size in USD

        Returns:
            Fee amount in USD
        """
        fee_rate = cls.calculate_fee_rate(entry_price)
        return fee_rate * trade_size_usd

    @classmethod
    def calculate_round_trip_fee_rate(cls, entry_price: float) -> float:
        """
        Calculate round-trip fee rate (entry + exit).

        For binary options that resolve to $1.00 or $0.00, the exit
        is typically at extreme probability (>99% or <1%), so exit
        fee is negligible. We approximate round-trip as 2× entry fee.

        Args:
            entry_price: Entry price in USD

        Returns:
            Round-trip fee rate as decimal
        """
        entry_fee = cls.calculate_fee_rate(entry_price)
        # Exit fee approximated as equal to entry (conservative)
        exit_fee = entry_fee
        return entry_fee + exit_fee


def calculate_weighted_average_fee(trades: List[Tuple[float, float]]) -> dict:
    """
    Calculate weighted average fee rate across all trades.

    Args:
        trades: List of (entry_price, trade_size_usd) tuples

    Returns:
        Dictionary with analysis results
    """
    if not trades:
        return {
            'num_trades': 0,
            'total_volume_usd': 0.0,
            'weighted_avg_fee_rate': 0.0,
            'weighted_avg_round_trip_fee': 0.0,
            'min_fee_rate': 0.0,
            'max_fee_rate': 0.0,
            'breakeven_win_rate': 0.5,
            'fee_details': []
        }

    # Calculate fees for each trade
    fee_analyses = []
    total_fees_paid = 0.0
    total_volume = 0.0

    for entry_price, trade_size in trades:
        fee_rate = PolymarketFeeCalculator.calculate_fee_rate(entry_price)
        fee_amount = fee_rate * trade_size

        fee_analyses.append(FeeAnalysis(
            entry_price=entry_price,
            trade_size_usd=trade_size,
            fee_rate=fee_rate,
            fee_amount_usd=fee_amount
        ))

        total_fees_paid += fee_amount
        total_volume += trade_size

    # Weighted average fee rate
    weighted_avg_fee_rate = total_fees_paid / total_volume if total_volume > 0 else 0.0

    # Round-trip fee (conservative estimate: 2× one-way)
    weighted_avg_round_trip = weighted_avg_fee_rate * 2

    # Breakeven win rate calculation
    # Need to win enough to cover round-trip fees
    # breakeven_wr = 0.5 + (round_trip_fee / 2)
    breakeven_win_rate = 0.5 + (weighted_avg_round_trip / 2)

    # Min/max fee rates
    fee_rates = [fa.fee_rate for fa in fee_analyses]
    min_fee_rate = min(fee_rates)
    max_fee_rate = max(fee_rates)

    return {
        'num_trades': len(trades),
        'total_volume_usd': total_volume,
        'weighted_avg_fee_rate': weighted_avg_fee_rate,
        'weighted_avg_round_trip_fee': weighted_avg_round_trip,
        'min_fee_rate': min_fee_rate,
        'max_fee_rate': max_fee_rate,
        'breakeven_win_rate': breakeven_win_rate,
        'fee_details': fee_analyses
    }


def test_fee_calculator():
    """Test fee calculator with known values."""
    calc = PolymarketFeeCalculator()

    # Test 1: Entry at $0.50 (50% probability) should return 3.15%
    fee_50 = calc.calculate_fee_rate(0.50)
    print(f"Test 1: Entry at $0.50 → {fee_50*100:.2f}% fee")
    assert abs(fee_50 - 0.0315) < 0.0001, f"Expected 3.15%, got {fee_50*100:.2f}%"

    # Test 2: Entry at $0.10 (cheap, far from 50%) should be <3.15%
    fee_10 = calc.calculate_fee_rate(0.10)
    print(f"Test 2: Entry at $0.10 → {fee_10*100:.2f}% fee")
    assert fee_10 < 0.01, f"Expected <1%, got {fee_10*100:.2f}%"

    # Test 3: Entry at $0.90 (expensive, far from 50%) should be <3.15%
    fee_90 = calc.calculate_fee_rate(0.90)
    print(f"Test 3: Entry at $0.90 → {fee_90*100:.2f}% fee")
    assert fee_90 < 0.01, f"Expected <1%, got {fee_90*100:.2f}%"

    # Test 4: Entry at $0.01 (extreme) should be very low
    fee_01 = calc.calculate_fee_rate(0.01)
    print(f"Test 4: Entry at $0.01 → {fee_01*100:.4f}% fee")
    assert fee_01 < 0.001, f"Expected <0.1%, got {fee_01*100:.4f}%"

    print("\n✅ All tests passed!")

    # Test weighted average
    print("\n--- Testing Weighted Average ---")
    test_trades = [
        (0.50, 10.0),  # $10 at 50% (high fee)
        (0.10, 5.0),   # $5 at 10% (low fee)
        (0.25, 15.0),  # $15 at 25% (medium fee)
    ]

    results = calculate_weighted_average_fee(test_trades)
    print(f"Trades: {len(test_trades)}")
    print(f"Total Volume: ${results['total_volume_usd']:.2f}")
    print(f"Weighted Avg Fee: {results['weighted_avg_fee_rate']*100:.2f}%")
    print(f"Round-trip Fee: {results['weighted_avg_round_trip_fee']*100:.2f}%")
    print(f"Breakeven WR: {results['breakeven_win_rate']*100:.2f}%")

    print("\nFee breakdown by trade:")
    for i, fa in enumerate(results['fee_details'], 1):
        print(f"  Trade {i}: Entry=${fa.entry_price:.2f}, Size=${fa.trade_size_usd:.2f}, "
              f"Fee={fa.fee_rate*100:.2f}% (${fa.fee_amount_usd:.2f})")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_fee_calculator()
    else:
        print("Fee Calculator Module")
        print("Usage: python3 fee_calculator.py test")
        print("\nImport this module to use PolymarketFeeCalculator class")
        print("Example:")
        print("  from fee_calculator import PolymarketFeeCalculator")
        print("  fee_rate = PolymarketFeeCalculator.calculate_fee_rate(0.15)")
        print("  print(f'Fee rate: {fee_rate*100:.2f}%')")
