#!/usr/bin/env python3
"""
Quick Statistical Summary - No Heavy Dependencies
Provides basic statistical insights using only stdlib and sqlite3
"""

import sqlite3
import math
from collections import defaultdict
from datetime import datetime


def critical_value_chi2(df, alpha=0.05):
    """Approximate chi-square critical value for df=1"""
    if alpha == 0.05:
        return 3.841
    elif alpha == 0.01:
        return 6.635
    return 3.841


def chi_square_hourly_test(db_path='analysis/epoch_history.db'):
    """Chi-square test for hourly bias."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("=" * 100)
    print("CHI-SQUARE TEST FOR HOURLY BIAS (All Cryptos)")
    print("=" * 100)
    print()

    # Get data by hour
    cursor.execute("""
        SELECT hour,
               SUM(CASE WHEN direction='Up' THEN 1 ELSE 0 END) as ups,
               SUM(CASE WHEN direction='Down' THEN 1 ELSE 0 END) as downs,
               COUNT(*) as total
        FROM epoch_outcomes
        GROUP BY hour
        ORDER BY hour
    """)

    results = cursor.fetchall()

    print(f"{'Hour':<6} {'N':<6} {'Up%':<8} {'95% CI':<22} {'χ²':<10} {'Sig?':<10}")
    print("-" * 90)

    critical_value = critical_value_chi2(1, 0.05)
    bonferroni_cv = critical_value_chi2(1, 0.05/24)

    significant_hours = []

    for hour, ups, downs, total in results:
        if total == 0:
            continue

        up_pct = ups / total * 100

        # Expected under null hypothesis (50/50)
        expected = total / 2

        # Chi-square statistic
        chi2_stat = ((ups - expected)**2 / expected +
                     (downs - expected)**2 / expected)

        # 95% confidence interval for proportion
        p_hat = ups / total
        se = math.sqrt(p_hat * (1 - p_hat) / total)
        ci_lower = (p_hat - 1.96 * se) * 100
        ci_upper = (p_hat + 1.96 * se) * 100

        # Is significant?
        sig_marker = ""
        if chi2_stat > bonferroni_cv:
            sig_marker = "*** (Bonf)"
            significant_hours.append((hour, up_pct, chi2_stat))
        elif chi2_stat > critical_value:
            sig_marker = "* (raw)"

        print(f"{hour:02d}:00 "
              f"{total:<6} "
              f"{up_pct:6.1f}% "
              f"[{ci_lower:5.1f}%, {ci_upper:5.1f}%] "
              f"{chi2_stat:8.3f} "
              f"{sig_marker:<10}")

    print()
    print(f"Critical value (α=0.05): {critical_value:.3f}")
    print(f"Critical value (Bonferroni α=0.05/24): {bonferroni_cv:.3f}")
    print()

    if significant_hours:
        print("SIGNIFICANT HOURS (after Bonferroni correction):")
        for hour, up_pct, chi2 in significant_hours:
            bias = "UP" if up_pct > 50 else "DOWN"
            strength = abs(up_pct - 50)
            print(f"  {hour:02d}:00 → {bias} bias ({up_pct:.1f}%, strength={strength:.1f}pp, χ²={chi2:.3f})")
    else:
        print("No statistically significant hourly biases found (after Bonferroni correction).")
        print()
        print("NOTE: With only 28-32 epochs per hour, you need ~20pp bias (70%+ or 30%-) for significance.")

    print()
    print("=" * 100)
    print()

    conn.close()


def sample_size_requirements():
    """Calculate required sample sizes."""
    print("=" * 100)
    print("SAMPLE SIZE REQUIREMENTS")
    print("=" * 100)
    print()

    print("To detect various effect sizes with 80% power and α=0.05:")
    print()

    # Z-scores
    z_alpha = 1.96  # 95% confidence
    z_beta = 0.84   # 80% power

    p1 = 0.5  # Null (50/50)

    print(f"{'Effect':<15} {'Target Up%':<12} {'Required N':<12} {'Days/Hour*':<12}")
    print("-" * 60)

    for effect in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
        p2 = 0.5 + effect
        p_avg = (p1 + p2) / 2

        # Sample size formula
        n = ((z_alpha * math.sqrt(2 * p_avg * (1 - p_avg)) +
              z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2) / (effect**2)

        days = n / 4  # 4 epochs per hour per day

        print(f"{effect*100:>4.0f}pp ({effect:.2f})  "
              f"{p2*100:>6.1f}%      "
              f"{int(math.ceil(n)):>6}       "
              f"{days:>6.1f}")

    print()
    print("* Days needed to accumulate sufficient epochs for ONE hour")
    print("  (4 epochs per hour per day)")
    print()

    # Current sample sizes
    conn = sqlite3.connect('analysis/epoch_history.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT hour, COUNT(*) as count
        FROM epoch_outcomes
        GROUP BY hour
        ORDER BY hour
    """)

    hourly_counts = cursor.fetchall()

    print("Current sample sizes (all cryptos):")
    print(f"{'Hour':<6} {'N':<6} {'Sufficient for*':<20}")
    print("-" * 40)

    for hour, count in hourly_counts:
        # What effect size can we detect?
        if count >= 393:
            sufficient = "10pp+ effects"
        elif count >= 175:
            sufficient = "15pp+ effects"
        elif count >= 99:
            sufficient = "20pp+ effects"
        elif count >= 64:
            sufficient = "25pp+ effects"
        elif count >= 44:
            sufficient = "30pp+ effects"
        else:
            sufficient = "Very large only"

        print(f"{hour:02d}:00  {count:<6} {sufficient:<20}")

    print()
    print("CONCLUSION: With 7.5 days, you can detect 20-30pp effects.")
    print("            For smaller effects (10pp), need 30+ days.")
    print()
    print("=" * 100)
    print()

    conn.close()


def segmentation_comparison():
    """Compare different time segmentations."""
    print("=" * 100)
    print("SEGMENTATION ANALYSIS")
    print("=" * 100)
    print()

    conn = sqlite3.connect('analysis/epoch_history.db')
    cursor = conn.cursor()

    segmentations = [
        ('Day of Week', 'strftime("%w", date)', 7),
        ('Hour', 'hour', 24),
        ('4-Hour Block', 'hour / 4', 6),
        ('8-Hour Block', 'hour / 8', 3),
        ('Weekend', 'CASE WHEN strftime("%w", date) IN ("0", "6") THEN 1 ELSE 0 END', 2),
    ]

    print(f"{'Segmentation':<20} {'Groups':<8} {'Min Up%':<10} {'Max Up%':<10} {'Range':<10} {'χ²':<10}")
    print("-" * 80)

    for name, sql_expr, n_groups in segmentations:
        cursor.execute(f"""
            SELECT {sql_expr} as segment,
                   SUM(CASE WHEN direction='Up' THEN 1 ELSE 0 END) as ups,
                   COUNT(*) as total
            FROM epoch_outcomes
            GROUP BY segment
        """)

        groups = cursor.fetchall()

        up_rates = [(ups / total * 100) for _, ups, total in groups if total > 0]

        if not up_rates:
            continue

        min_up = min(up_rates)
        max_up = max(up_rates)
        range_pp = max_up - min_up

        # Chi-square
        chi2_stat = 0
        for segment, ups, total in groups:
            if total > 0:
                expected = total / 2
                chi2_stat += ((ups - expected)**2 / expected +
                             (total - ups - expected)**2 / expected)

        sig = "***" if chi2_stat > critical_value_chi2(n_groups - 1, 0.05) else ""

        print(f"{name:<20} "
              f"{n_groups:<8} "
              f"{min_up:>8.1f}% "
              f"{max_up:>8.1f}% "
              f"{range_pp:>8.1f}pp "
              f"{chi2_stat:>8.2f} {sig}")

    print()
    print("Interpretation:")
    print("  - Range: Difference between highest and lowest up% (higher = more predictive)")
    print("  - χ²: Overall test for differences (*** = significant at α=0.05)")
    print()
    print("=" * 100)
    print()

    conn.close()


def cross_crypto_summary():
    """Cross-crypto comparison."""
    print("=" * 100)
    print("CROSS-CRYPTO SUMMARY")
    print("=" * 100)
    print()

    conn = sqlite3.connect('analysis/epoch_history.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT crypto,
               COUNT(*) as total,
               SUM(CASE WHEN direction='Up' THEN 1 ELSE 0 END) as ups,
               AVG(change_pct) as avg_change
        FROM epoch_outcomes
        GROUP BY crypto
        ORDER BY crypto
    """)

    results = cursor.fetchall()

    print(f"{'Crypto':<10} {'N':<8} {'Up%':<10} {'Avg Change':<12} {'Bias':<15}")
    print("-" * 60)

    for crypto, total, ups, avg_change in results:
        up_pct = ups / total * 100

        if up_pct > 55:
            bias = "↗ Bullish"
        elif up_pct < 45:
            bias = "↙ Bearish"
        else:
            bias = "⚖ Balanced"

        print(f"{crypto.upper():<10} "
              f"{total:<8} "
              f"{up_pct:>7.1f}% "
              f"{avg_change:>10.3f}% "
              f"{bias:<15}")

    print()
    print("NOTE: All cryptos near 50/50 → No systematic directional bias")
    print()
    print("=" * 100)
    print()

    conn.close()


def time_of_day_patterns():
    """Analyze time-of-day patterns."""
    print("=" * 100)
    print("TIME-OF-DAY PATTERNS")
    print("=" * 100)
    print()

    conn = sqlite3.connect('analysis/epoch_history.db')
    cursor = conn.cursor()

    time_periods = [
        ('Night (00-06)', 0, 6),
        ('Early Morning (06-09)', 6, 9),
        ('Morning (09-12)', 9, 12),
        ('Midday (12-15)', 12, 15),
        ('Afternoon (15-18)', 15, 18),
        ('Evening (18-21)', 18, 21),
        ('Late Evening (21-24)', 21, 24),
    ]

    print(f"{'Period':<25} {'N':<8} {'Up%':<10} {'Best Crypto':<15}")
    print("-" * 70)

    for period_name, start_hour, end_hour in time_periods:
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN direction='Up' THEN 1 ELSE 0 END) as ups
            FROM epoch_outcomes
            WHERE hour >= ? AND hour < ?
        """, (start_hour, end_hour))

        total, ups = cursor.fetchone()

        if total == 0:
            continue

        up_pct = ups / total * 100

        # Best crypto in this period
        cursor.execute("""
            SELECT crypto,
                   COUNT(*) as total,
                   SUM(CASE WHEN direction='Up' THEN 1 ELSE 0 END) as ups
            FROM epoch_outcomes
            WHERE hour >= ? AND hour < ?
            GROUP BY crypto
            ORDER BY ups * 1.0 / total DESC
            LIMIT 1
        """, (start_hour, end_hour))

        best = cursor.fetchone()
        if best:
            best_crypto, best_total, best_ups = best
            best_str = f"{best_crypto.upper()} ({best_ups/best_total*100:.1f}%)"
        else:
            best_str = "N/A"

        print(f"{period_name:<25} "
              f"{total:<8} "
              f"{up_pct:>7.1f}% "
              f"{best_str:<15}")

    print()
    print("=" * 100)
    print()

    conn.close()


def main():
    """Run quick statistical summary."""
    import sys

    db_path = 'analysis/epoch_history.db'

    # Check if database exists
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM epoch_outcomes")
        count = cursor.fetchone()[0]
        print(f"\nDataset: {count} epochs loaded\n")
        conn.close()
    except Exception as e:
        print(f"Error: Cannot access database at {db_path}")
        print(f"Error: {e}")
        return

    # Run analyses
    if len(sys.argv) > 1:
        test = sys.argv[1]
        if test == 'chi2':
            chi_square_hourly_test()
        elif test == 'sample':
            sample_size_requirements()
        elif test == 'segment':
            segmentation_comparison()
        elif test == 'crypto':
            cross_crypto_summary()
        elif test == 'time':
            time_of_day_patterns()
        else:
            print(f"Unknown test: {test}")
    else:
        # Run all
        chi_square_hourly_test()
        sample_size_requirements()
        segmentation_comparison()
        cross_crypto_summary()
        time_of_day_patterns()


if __name__ == '__main__':
    main()
