#!/usr/bin/env python3
"""
Quick ML Analysis Status

Provides a snapshot of:
- Dataset statistics
- Current best patterns
- Recommended next actions

Run this BEFORE the full analysis to see what data you have.
"""

import sys
from pathlib import Path
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(str(Path(__file__).parent.parent))


def check_dataset():
    """Check dataset status."""
    print("="*100)
    print("DATASET STATUS")
    print("="*100)
    print()

    db_path = Path('analysis/epoch_history.db')

    if not db_path.exists():
        print("❌ No dataset found!")
        print()
        print("To create dataset:")
        print("  python3 analysis/historical_dataset.py --backfill 7 --all")
        print()
        return False

    conn = sqlite3.connect(db_path)

    # Total records
    total = conn.execute("SELECT COUNT(*) FROM epoch_outcomes").fetchone()[0]

    # Date range
    result = conn.execute('''
        SELECT MIN(date) as earliest, MAX(date) as latest
        FROM epoch_outcomes
    ''').fetchone()

    earliest, latest = result

    # Per crypto
    crypto_stats = conn.execute('''
        SELECT crypto, COUNT(*) as count,
               SUM(CASE WHEN direction = 'Up' THEN 1 ELSE 0 END) as ups
        FROM epoch_outcomes
        GROUP BY crypto
    ''').fetchall()

    print(f"Total Epochs: {total:,}")
    print(f"Date Range: {earliest} to {latest}")

    # Calculate days
    date_diff = (datetime.strptime(latest, '%Y-%m-%d') -
                 datetime.strptime(earliest, '%Y-%m-%d')).days + 1

    print(f"Coverage: {date_diff} days ({total / 96:.1f} expected)")
    print()

    print("Per Crypto:")
    print("-"*60)
    print(f"{'Crypto':<8} {'Epochs':<10} {'Ups':<10} {'Downs':<10} {'Up %':<10}")
    print("-"*60)

    for crypto, count, ups in crypto_stats:
        downs = count - ups
        up_pct = (ups / count * 100) if count > 0 else 0
        print(f"{crypto.upper():<8} {count:<10} {ups:<10} {downs:<10} {up_pct:<9.1f}%")

    print()

    conn.close()

    return True


def quick_hourly_analysis():
    """Quick hourly win rate analysis."""
    print("="*100)
    print("QUICK HOURLY ANALYSIS")
    print("="*100)
    print()

    conn = sqlite3.connect('analysis/epoch_history.db')

    query = '''
        SELECT crypto, hour,
               COUNT(*) as total,
               SUM(CASE WHEN direction = 'Up' THEN 1 ELSE 0 END) as ups
        FROM epoch_outcomes
        GROUP BY crypto, hour
        HAVING total >= 10
    '''

    df = pd.read_sql_query(query, conn)
    conn.close()

    df['win_rate'] = (df['ups'] / df['total'] * 100)

    # Find best hours per crypto
    print("BEST HOURS (>60% win rate, min 10 epochs):")
    print("-"*100)

    best_found = False

    for crypto in ['btc', 'eth', 'sol', 'xrp']:
        crypto_df = df[df['crypto'] == crypto]
        best_hours = crypto_df[crypto_df['win_rate'] > 60].sort_values('win_rate', ascending=False)

        if len(best_hours) > 0:
            best_found = True
            hours_str = ', '.join([f"{row['hour']:02d}:00 ({row['win_rate']:.0f}%)"
                                  for _, row in best_hours.head(5).iterrows()])
            print(f"  {crypto.upper():<6} → {hours_str}")

    if not best_found:
        print("  No hours with >60% win rate found (need more data or patterns are weak)")

    print()


def check_feature_matrix():
    """Check if feature matrix exists."""
    print("="*100)
    print("FEATURE MATRIX STATUS")
    print("="*100)
    print()

    feature_path = Path('analysis/feature_matrix.csv')

    if feature_path.exists():
        df = pd.read_csv(feature_path, nrows=5)
        print(f"✅ Feature matrix exists")
        print(f"   Features: {len(df.columns)} columns")
        print(f"   Sample features: {', '.join(list(df.columns)[:10])}...")
        print()
    else:
        print("❌ Feature matrix not generated yet")
        print()
        print("To generate:")
        print("  python3 analysis/ml_feature_engineering.py")
        print()


def recommend_next_steps(has_data: bool):
    """Recommend next steps based on current state."""
    print("="*100)
    print("RECOMMENDED NEXT STEPS")
    print("="*100)
    print()

    if not has_data:
        print("1. ⚠️  COLLECT DATA FIRST:")
        print("   python3 analysis/historical_dataset.py --backfill 7 --all")
        print()
        print("   This will fetch 7 days of historical epochs (~2,600 epochs)")
        print()
        return

    print("1. 📦 INSTALL ML DEPENDENCIES:")
    print("   ./analysis/install_ml_dependencies.sh")
    print()

    print("2. 🚀 RUN FULL ML ANALYSIS:")
    print("   python3 analysis/ml_full_analysis.py")
    print()
    print("   This will run all 6 ML modules (~5-10 minutes)")
    print()

    print("3. 📊 REVIEW SPECIFIC ANALYSES:")
    print()
    print("   Feature Engineering:")
    print("     python3 analysis/ml_feature_engineering.py")
    print()
    print("   Supervised Learning:")
    print("     python3 analysis/ml_supervised_learning.py")
    print()
    print("   Time Segmentation:")
    print("     python3 analysis/ml_time_segmentation.py")
    print()
    print("   Pattern Mining:")
    print("     python3 analysis/ml_pattern_mining.py")
    print()

    print("4. 🔧 INTEGRATE FINDINGS:")
    print("   - Add profitable time filters to bot")
    print("   - Use ML predictions as signals")
    print("   - Apply discovered association rules")
    print()


def main():
    print()
    print("╔" + "="*98 + "╗")
    print("║" + " "*30 + "ML ANALYSIS QUICK STATUS" + " "*44 + "║")
    print("╚" + "="*98 + "╝")
    print()

    # Check dataset
    has_data = check_dataset()

    if has_data:
        # Quick analysis
        quick_hourly_analysis()

        # Check feature matrix
        check_feature_matrix()

    # Recommendations
    recommend_next_steps(has_data)

    print()


if __name__ == '__main__':
    main()
