#!/usr/bin/env python3
"""
Intra-Epoch Pattern Analysis

Hypothesis: Do 1-minute or 5-minute streaks WITHIN a 15-minute epoch
predict the final outcome? Can we use early momentum/mean-reversion
signals to trade mid-epoch?

Analysis:
1. For each completed 15-minute epoch, fetch the 15 one-minute candles
2. Look at early patterns (first 3-5 minutes)
3. Check if those patterns predict the final 15-minute outcome
"""

import requests
import time
from datetime import datetime, timezone
from collections import defaultdict
import statistics

CRYPTOS = ['BTC', 'ETH', 'SOL', 'XRP']
LOOKBACK_DAYS = 7  # Analyze 7 days of data


def get_epoch_with_minutes(symbol: str, epoch_start_ms: int) -> dict:
    """
    Fetch 1-minute candles for a specific 15-minute epoch.

    Returns dict with:
    - minutes: list of 15 one-minute outcomes (Up/Down)
    - epoch_outcome: final 15-minute outcome (Up/Down)
    - open_price: epoch open price
    - close_price: epoch close price
    """
    url = "https://api.binance.com/api/v3/klines"

    params = {
        'symbol': symbol,
        'interval': '1m',
        'startTime': epoch_start_ms,
        'limit': 15  # Exactly 15 minutes
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return None

        klines = resp.json()
        if len(klines) < 15:
            return None

        # Get minute-by-minute outcomes
        minutes = []
        for k in klines:
            open_p = float(k[1])
            close_p = float(k[4])
            minutes.append("Up" if close_p > open_p else "Down")

        # Get overall epoch outcome
        epoch_open = float(klines[0][1])
        epoch_close = float(klines[-1][4])
        epoch_outcome = "Up" if epoch_close > epoch_open else "Down"

        return {
            'minutes': minutes,
            'epoch_outcome': epoch_outcome,
            'open_price': epoch_open,
            'close_price': epoch_close,
            'price_change_pct': (epoch_close - epoch_open) / epoch_open * 100
        }

    except Exception as e:
        return None


def count_streak(outcomes: list, from_end: bool = True) -> tuple:
    """Count consecutive same-direction outcomes."""
    if not outcomes:
        return ("None", 0)

    if from_end:
        outcomes = list(reversed(outcomes))

    last = outcomes[0]
    count = 0
    for o in outcomes:
        if o == last:
            count += 1
        else:
            break

    return (last, count)


def analyze_early_patterns(epochs_data: list) -> dict:
    """
    Analyze patterns from first N minutes and their predictive power.
    """
    results = {
        'early_3min_streak': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'early_5min_streak': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'early_5min_momentum': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'early_3min_momentum': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'minute_5_streak': defaultdict(lambda: {'correct': 0, 'total': 0}),
    }

    for data in epochs_data:
        minutes = data['minutes']
        outcome = data['epoch_outcome']

        # === Pattern 1: Streak in first 3 minutes ===
        first_3 = minutes[:3]
        streak_dir, streak_len = count_streak(first_3, from_end=True)

        if streak_len >= 2:  # At least 2 consecutive
            key = f"{streak_len}_{streak_dir}"
            results['early_3min_streak'][key]['total'] += 1

            # Mean reversion hypothesis: opposite direction wins
            predicted = "Down" if streak_dir == "Up" else "Up"
            if predicted == outcome:
                results['early_3min_streak'][key]['correct'] += 1

        # === Pattern 2: Streak in first 5 minutes ===
        first_5 = minutes[:5]
        streak_dir, streak_len = count_streak(first_5, from_end=True)

        if streak_len >= 3:  # At least 3 consecutive
            key = f"{streak_len}_{streak_dir}"
            results['early_5min_streak'][key]['total'] += 1

            # Mean reversion hypothesis
            predicted = "Down" if streak_dir == "Up" else "Up"
            if predicted == outcome:
                results['early_5min_streak'][key]['correct'] += 1

        # === Pattern 3: Early momentum (first 5 min net direction) ===
        ups_5 = sum(1 for m in first_5 if m == "Up")
        downs_5 = 5 - ups_5

        if ups_5 >= 4:  # Strong UP momentum
            results['early_5min_momentum']['4+_Up']['total'] += 1
            # Test: Does momentum continue or reverse?
            if outcome == "Up":
                results['early_5min_momentum']['4+_Up']['correct'] += 1
        elif downs_5 >= 4:  # Strong DOWN momentum
            results['early_5min_momentum']['4+_Down']['total'] += 1
            if outcome == "Down":
                results['early_5min_momentum']['4+_Down']['correct'] += 1

        # === Pattern 4: Early momentum (first 3 min net direction) ===
        ups_3 = sum(1 for m in first_3 if m == "Up")
        downs_3 = 3 - ups_3

        if ups_3 == 3:  # All 3 Up
            results['early_3min_momentum']['3_Up']['total'] += 1
            if outcome == "Up":
                results['early_3min_momentum']['3_Up']['correct'] += 1
        elif downs_3 == 3:  # All 3 Down
            results['early_3min_momentum']['3_Down']['total'] += 1
            if outcome == "Down":
                results['early_3min_momentum']['3_Down']['correct'] += 1

        # === Pattern 5: Streak ending at minute 5 ===
        at_min_5 = minutes[:5]
        streak_dir, streak_len = count_streak(at_min_5, from_end=True)

        if streak_len >= 3:
            key = f"streak_{streak_len}_{streak_dir}_at_min5"
            results['minute_5_streak'][key]['total'] += 1

            # Test mean reversion
            predicted = "Down" if streak_dir == "Up" else "Up"
            if predicted == outcome:
                results['minute_5_streak'][key]['correct'] += 1

    return results


def main():
    print("\n" + "=" * 70)
    print("  INTRA-EPOCH PATTERN ANALYSIS")
    print("  Do 1-minute streaks within an epoch predict the final outcome?")
    print("=" * 70)

    # Generate epoch timestamps for last N days
    now = datetime.now(timezone.utc)
    current_epoch = int(now.timestamp()) // 900 * 900

    epochs_per_day = 96  # 24 * 4
    total_epochs = epochs_per_day * LOOKBACK_DAYS

    epoch_starts = []
    for i in range(total_epochs):
        epoch_ts = current_epoch - (i + 1) * 900  # Go back in time
        epoch_starts.append(epoch_ts)

    print(f"\n  Analyzing {total_epochs} epochs ({LOOKBACK_DAYS} days)")
    print(f"  Fetching 1-minute data for each epoch...")

    all_epochs_data = []

    for crypto in CRYPTOS:
        symbol = f"{crypto}USDT"
        print(f"\n  Processing {crypto}...")

        crypto_count = 0
        for i, epoch_ts in enumerate(epoch_starts):
            if i % 50 == 0:
                print(f"    Progress: {i}/{len(epoch_starts)} epochs")

            data = get_epoch_with_minutes(symbol, epoch_ts * 1000)
            if data:
                data['crypto'] = crypto
                data['epoch_ts'] = epoch_ts
                all_epochs_data.append(data)
                crypto_count += 1

            time.sleep(0.05)  # Rate limiting

        print(f"    {crypto}: {crypto_count} epochs collected")

    print(f"\n  Total epochs with minute data: {len(all_epochs_data)}")

    # Analyze patterns
    print("\n" + "=" * 70)
    print("  ANALYSIS RESULTS")
    print("=" * 70)

    results = analyze_early_patterns(all_epochs_data)

    # === Report: Early 3-minute streak (mean reversion) ===
    print("\n  [1] FIRST 3 MINUTES - Streak Mean Reversion")
    print("  " + "-" * 60)
    print("  Pattern: If first 3 mins have N consecutive Up/Down,")
    print("           predict OPPOSITE for final epoch outcome")
    print()

    for key, data in sorted(results['early_3min_streak'].items()):
        if data['total'] >= 20:  # Minimum sample size
            accuracy = data['correct'] / data['total'] * 100
            edge = accuracy - 50
            streak_len, direction = key.split('_')
            predicted = "Down" if direction == "Up" else "Up"
            print(f"    {streak_len} consecutive {direction}s → Predict {predicted}")
            print(f"      Accuracy: {accuracy:.1f}% | Samples: {data['total']} | Edge: {edge:+.1f}%")
            print()

    # === Report: Early 5-minute streak (mean reversion) ===
    print("\n  [2] FIRST 5 MINUTES - Streak Mean Reversion")
    print("  " + "-" * 60)
    print("  Pattern: If first 5 mins have N consecutive Up/Down,")
    print("           predict OPPOSITE for final epoch outcome")
    print()

    for key, data in sorted(results['early_5min_streak'].items()):
        if data['total'] >= 10:
            accuracy = data['correct'] / data['total'] * 100
            edge = accuracy - 50
            streak_len, direction = key.split('_')
            predicted = "Down" if direction == "Up" else "Up"
            print(f"    {streak_len} consecutive {direction}s → Predict {predicted}")
            print(f"      Accuracy: {accuracy:.1f}% | Samples: {data['total']} | Edge: {edge:+.1f}%")
            print()

    # === Report: Early momentum continuation ===
    print("\n  [3] FIRST 5 MINUTES - Momentum Continuation")
    print("  " + "-" * 60)
    print("  Pattern: If 4+ of first 5 minutes go same direction,")
    print("           predict SAME direction for final outcome (momentum)")
    print()

    for key, data in sorted(results['early_5min_momentum'].items()):
        if data['total'] >= 10:
            accuracy = data['correct'] / data['total'] * 100
            edge = accuracy - 50
            count, direction = key.split('_')
            print(f"    {count} of 5 minutes {direction} → Predict {direction}")
            print(f"      Accuracy: {accuracy:.1f}% | Samples: {data['total']} | Edge: {edge:+.1f}%")
            print()

    # === Report: First 3 minutes all same ===
    print("\n  [4] FIRST 3 MINUTES - All Same Direction (Momentum)")
    print("  " + "-" * 60)
    print("  Pattern: If all 3 first minutes same direction,")
    print("           predict SAME direction for final outcome")
    print()

    for key, data in sorted(results['early_3min_momentum'].items()):
        if data['total'] >= 10:
            accuracy = data['correct'] / data['total'] * 100
            edge = accuracy - 50
            count, direction = key.split('_')
            print(f"    All 3 minutes {direction} → Predict {direction}")
            print(f"      Accuracy: {accuracy:.1f}% | Samples: {data['total']} | Edge: {edge:+.1f}%")
            print()

    # === Summary ===
    print("\n" + "=" * 70)
    print("  SUMMARY: INTRA-EPOCH PATTERNS")
    print("=" * 70)

    # Find best patterns
    all_patterns = []

    for pattern_type, patterns in results.items():
        for key, data in patterns.items():
            if data['total'] >= 20:
                accuracy = data['correct'] / data['total'] * 100
                all_patterns.append({
                    'type': pattern_type,
                    'key': key,
                    'accuracy': accuracy,
                    'samples': data['total'],
                    'edge': accuracy - 50
                })

    # Sort by edge
    all_patterns.sort(key=lambda x: x['edge'], reverse=True)

    print("\n  Top Intra-Epoch Patterns (by edge):")
    print()

    for i, p in enumerate(all_patterns[:10], 1):
        print(f"    {i}. {p['type']}: {p['key']}")
        print(f"       Accuracy: {p['accuracy']:.1f}% | Samples: {p['samples']} | Edge: {p['edge']:+.1f}%")
        print()

    # Key insight
    print("\n  KEY INSIGHT:")
    print("  " + "-" * 60)

    # Check if mean reversion or momentum wins
    mean_reversion_edges = [p['edge'] for p in all_patterns if 'streak' in p['type']]
    momentum_edges = [p['edge'] for p in all_patterns if 'momentum' in p['type']]

    if mean_reversion_edges and momentum_edges:
        avg_mr = statistics.mean(mean_reversion_edges)
        avg_mom = statistics.mean(momentum_edges)

        if avg_mr > avg_mom:
            print(f"  Mean Reversion patterns avg edge: {avg_mr:+.1f}%")
            print(f"  Momentum continuation avg edge: {avg_mom:+.1f}%")
            print("  → MEAN REVERSION is stronger within epochs")
        else:
            print(f"  Momentum continuation avg edge: {avg_mom:+.1f}%")
            print(f"  Mean Reversion patterns avg edge: {avg_mr:+.1f}%")
            print("  → MOMENTUM CONTINUATION is stronger within epochs")

    print("\n" + "=" * 70)
    print("  Analysis complete!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
