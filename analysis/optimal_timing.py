#!/usr/bin/env python3
"""
Optimal Entry Timing & Risk-Adjusted Strategy Analysis

Practical applications for trading:
- Best hours to trade (by crypto and day)
- Risk-adjusted performance metrics
- Kelly criterion position sizing
- Optimal holding periods
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime

DB_PATH = "analysis/epoch_history.db"

def load_data():
    """Load epoch data from SQLite"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT crypto, epoch, date, hour, direction,
               start_price, end_price, change_pct
        FROM epochs
        ORDER BY crypto, epoch
    """, conn)
    conn.close()

    df['epoch'] = pd.to_datetime(df['epoch'])
    df['direction_binary'] = (df['direction'] == 'Up').astype(int)
    df['day_of_week'] = df['epoch'].dt.dayofweek
    df['day_name'] = df['epoch'].dt.day_name()
    return df

def hourly_trading_performance(df, min_epochs=20):
    """
    Calculate performance metrics by hour

    For a binary outcome market strategy:
    - Assume we bet on the most common direction each hour
    - Calculate win rate, edge, Kelly fraction
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for hour in range(24):
            hour_df = crypto_df[crypto_df['hour'] == hour]

            if len(hour_df) < min_epochs:
                continue

            up_pct = hour_df['direction_binary'].mean()
            n = len(hour_df)

            # Determine predicted direction (bet on majority)
            if up_pct > 0.5:
                predicted_direction = 'Up'
                win_rate = up_pct
            else:
                predicted_direction = 'Down'
                win_rate = 1 - up_pct

            # Edge (advantage over 50/50)
            edge = win_rate - 0.5

            # Kelly criterion: f* = p - q = p - (1-p) = 2p - 1
            # For binary outcomes with 1:1 payoff
            kelly_fraction = 2 * win_rate - 1 if win_rate > 0.5 else 0

            # Statistical significance
            binom_test = stats.binomtest(
                int(up_pct * n),
                n,
                p=0.5,
                alternative='two-sided'
            )

            # Expected value per trade (assuming $1 risk, 1:1 payoff)
            ev_per_trade = win_rate * 1 - (1 - win_rate) * 1

            # Sharpe-like ratio: edge / std_dev
            # For binary outcomes: std_dev = sqrt(p*(1-p))
            std_dev = np.sqrt(win_rate * (1 - win_rate))
            sharpe = edge / std_dev if std_dev > 0 else 0

            # Confidence interval for win rate (95%)
            ci_low = stats.binom.ppf(0.025, n, win_rate) / n
            ci_high = stats.binom.ppf(0.975, n, win_rate) / n

            results.append({
                'crypto': crypto,
                'hour': hour,
                'n_epochs': n,
                'up_pct': up_pct,
                'predicted_direction': predicted_direction,
                'win_rate': win_rate,
                'edge': edge,
                'edge_pct': edge * 100,
                'kelly_fraction': kelly_fraction,
                'ev_per_trade': ev_per_trade,
                'sharpe_ratio': sharpe,
                'p_value': binom_test.pvalue,
                'significant': binom_test.pvalue < 0.05,
                'ci_95_low': ci_low,
                'ci_95_high': ci_high
            })

    return pd.DataFrame(results)

def day_hour_heatmap(df, min_epochs=10):
    """
    Create day-of-week × hour heatmap data

    Shows which specific day+hour combinations are most predictable
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for day in range(7):
            day_df = crypto_df[crypto_df['day_of_week'] == day]

            for hour in range(24):
                hour_df = day_df[day_df['hour'] == hour]

                if len(hour_df) < min_epochs:
                    continue

                up_pct = hour_df['direction_binary'].mean()
                n = len(hour_df)

                # Edge calculation
                if up_pct > 0.5:
                    win_rate = up_pct
                else:
                    win_rate = 1 - up_pct

                edge = win_rate - 0.5

                # Significance test
                binom_test = stats.binomtest(
                    int(up_pct * n),
                    n,
                    p=0.5,
                    alternative='two-sided'
                )

                results.append({
                    'crypto': crypto,
                    'day_of_week': day,
                    'day_name': hour_df.iloc[0]['day_name'],
                    'hour': hour,
                    'n_epochs': n,
                    'up_pct': up_pct,
                    'edge': edge,
                    'p_value': binom_test.pvalue,
                    'significant': binom_test.pvalue < 0.05
                })

    return pd.DataFrame(results)

def streak_analysis(df):
    """
    Analyze winning/losing streaks

    Question: After N consecutive Ups, what's probability of another Up?
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')
        directions = crypto_df['direction'].values

        # Track streaks
        max_streak_length = 5
        streak_outcomes = {i: {'Up': 0, 'Down': 0} for i in range(1, max_streak_length + 1)}

        current_streak = 1
        current_direction = directions[0]

        for i in range(1, len(directions)):
            if directions[i] == current_direction:
                current_streak += 1
            else:
                # Streak ended
                # Record what happened after streaks of length 1, 2, 3, etc.
                for length in range(1, min(current_streak, max_streak_length) + 1):
                    streak_outcomes[length][directions[i]] += 1

                current_streak = 1
                current_direction = directions[i]

        # Calculate probabilities
        for length in range(1, max_streak_length + 1):
            total = streak_outcomes[length]['Up'] + streak_outcomes[length]['Down']

            if total == 0:
                continue

            # P(Up | previous N were Up)
            up_count = sum(1 for j in range(length, len(directions)) if
                          all(directions[j-k] == 'Up' for k in range(1, length + 1)))
            up_then_up = sum(1 for j in range(length, len(directions)) if
                            all(directions[j-k] == 'Up' for k in range(1, length + 1)) and
                            directions[j] == 'Up')

            p_continue_up = up_then_up / up_count if up_count > 0 else 0

            # P(Down | previous N were Down)
            down_count = sum(1 for j in range(length, len(directions)) if
                            all(directions[j-k] == 'Down' for k in range(1, length + 1)))
            down_then_down = sum(1 for j in range(length, len(directions)) if
                                all(directions[j-k] == 'Down' for k in range(1, length + 1)) and
                                directions[j] == 'Down')

            p_continue_down = down_then_down / down_count if down_count > 0 else 0

            # Momentum indicator: avg probability of continuation
            momentum_strength = (p_continue_up + p_continue_down) / 2

            results.append({
                'crypto': crypto,
                'streak_length': length,
                'n_up_streaks': up_count,
                'n_down_streaks': down_count,
                'p_continue_up': p_continue_up,
                'p_continue_down': p_continue_down,
                'momentum_strength': momentum_strength,
                'behavior': 'Momentum' if momentum_strength > 0.5 else 'Mean Reversion'
            })

    return pd.DataFrame(results)

def session_performance(df):
    """
    Compare performance across global trading sessions

    Asian: 00-08 UTC
    European: 08-16 UTC
    US: 16-24 UTC
    """
    sessions = {
        'Asian': list(range(0, 8)),
        'European': list(range(8, 16)),
        'US': list(range(16, 24))
    }

    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for session_name, hours in sessions.items():
            session_df = crypto_df[crypto_df['hour'].isin(hours)]

            if len(session_df) == 0:
                continue

            up_pct = session_df['direction_binary'].mean()
            n = len(session_df)

            # Determine win rate
            if up_pct > 0.5:
                win_rate = up_pct
                predicted = 'Up'
            else:
                win_rate = 1 - up_pct
                predicted = 'Down'

            edge = win_rate - 0.5
            kelly_fraction = 2 * win_rate - 1 if win_rate > 0.5 else 0

            # Volatility (proxy: average absolute change)
            avg_volatility = session_df['change_pct'].abs().mean()

            # Risk-adjusted edge
            risk_adjusted_edge = edge / avg_volatility if avg_volatility > 0 else 0

            results.append({
                'crypto': crypto,
                'session': session_name,
                'hours': f"{min(hours):02d}-{max(hours)+1:02d} UTC",
                'n_epochs': n,
                'predicted_direction': predicted,
                'win_rate': win_rate,
                'edge_pct': edge * 100,
                'kelly_fraction': kelly_fraction,
                'avg_volatility': avg_volatility,
                'risk_adjusted_edge': risk_adjusted_edge
            })

    return pd.DataFrame(results)

def best_opportunities(hourly_df, min_edge=0.10, min_sample=20):
    """
    Filter for best trading opportunities

    Criteria:
    - Edge > 10%
    - Sample size > 20
    - Statistically significant
    """
    best = hourly_df[
        (hourly_df['edge'] >= min_edge) &
        (hourly_df['n_epochs'] >= min_sample) &
        (hourly_df['significant'])
    ].sort_values('edge', ascending=False)

    return best

def volatility_adjusted_sizing(df):
    """
    Calculate recommended position sizes based on volatility

    Higher volatility = smaller positions
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        # Overall stats
        avg_volatility = crypto_df['change_pct'].abs().mean()
        volatility_std = crypto_df['change_pct'].abs().std()

        # For each hour
        for hour in range(24):
            hour_df = crypto_df[crypto_df['hour'] == hour]

            if len(hour_df) < 10:
                continue

            hour_volatility = hour_df['change_pct'].abs().mean()

            # Normalized volatility score (0-1)
            if volatility_std > 0:
                vol_z_score = (hour_volatility - avg_volatility) / volatility_std
            else:
                vol_z_score = 0

            # Position size multiplier (inverse of volatility)
            # High vol = smaller multiplier
            position_multiplier = 1 / (1 + abs(vol_z_score))

            results.append({
                'crypto': crypto,
                'hour': hour,
                'avg_volatility': hour_volatility,
                'vol_z_score': vol_z_score,
                'volatility_regime': 'High' if vol_z_score > 1 else 'Normal' if vol_z_score > -1 else 'Low',
                'position_multiplier': position_multiplier
            })

    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("OPTIMAL ENTRY TIMING & RISK-ADJUSTED STRATEGY ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading epoch data...")
    df = load_data()
    print(f"Loaded {len(df)} epochs")
    print()

    # 1. Hourly Trading Performance
    print("=" * 80)
    print("1. HOURLY TRADING PERFORMANCE ANALYSIS")
    print("=" * 80)
    hourly_perf = hourly_trading_performance(df, min_epochs=20)

    print("Top hours by edge (min 20 epochs):")
    top_hours = hourly_perf.nlargest(10, 'edge')[
        ['crypto', 'hour', 'n_epochs', 'predicted_direction', 'win_rate',
         'edge_pct', 'kelly_fraction', 'sharpe_ratio', 'p_value']
    ]
    print(top_hours.to_string(index=False))
    print()

    # 2. Best Opportunities
    print("=" * 80)
    print("2. BEST TRADING OPPORTUNITIES (Edge > 10%, Significant)")
    print("=" * 80)
    best_ops = best_opportunities(hourly_perf, min_edge=0.10, min_sample=20)

    if len(best_ops) > 0:
        print(best_ops[
            ['crypto', 'hour', 'n_epochs', 'predicted_direction',
             'win_rate', 'edge_pct', 'kelly_fraction', 'p_value']
        ].to_string(index=False))
    else:
        print("No opportunities meet the criteria (try lowering thresholds)")
    print()

    # 3. Day-Hour Heatmap
    print("=" * 80)
    print("3. DAY-HOUR SPECIFIC PATTERNS")
    print("=" * 80)
    day_hour = day_hour_heatmap(df, min_epochs=5)

    # Show strongest patterns
    strongest = day_hour[day_hour['significant']].nlargest(10, 'edge')[
        ['crypto', 'day_name', 'hour', 'n_epochs', 'up_pct', 'edge', 'p_value']
    ]

    if len(strongest) > 0:
        print("Strongest day-hour combinations:")
        print(strongest.to_string(index=False))
    else:
        print("No significant day-hour patterns found")
    print()

    # 4. Streak Analysis
    print("=" * 80)
    print("4. STREAK ANALYSIS (Momentum vs Mean Reversion)")
    print("=" * 80)
    streaks = streak_analysis(df)
    print(streaks.to_string(index=False))
    print()

    # 5. Session Performance
    print("=" * 80)
    print("5. TRADING SESSION PERFORMANCE")
    print("=" * 80)
    session_perf = session_performance(df)
    print(session_perf.to_string(index=False))
    print()

    # 6. Volatility-Adjusted Sizing
    print("=" * 80)
    print("6. VOLATILITY-ADJUSTED POSITION SIZING")
    print("=" * 80)
    vol_sizing = volatility_adjusted_sizing(df)
    print("Sample (first 24 hours for BTC):")
    print(vol_sizing[vol_sizing['crypto'] == 'BTC'].head(24).to_string(index=False))
    print()

    # Summary Statistics
    print("=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"\nTotal analyzable hours: {len(hourly_perf)}")
    print(f"Significant patterns: {hourly_perf['significant'].sum()} ({100*hourly_perf['significant'].mean():.1f}%)")
    print(f"\nEdge distribution:")
    print(hourly_perf['edge_pct'].describe())
    print(f"\nBest crypto by average edge:")
    print(hourly_perf.groupby('crypto')['edge_pct'].mean().sort_values(ascending=False))
    print()

    # Save results
    print("=" * 80)
    print("Saving results...")
    hourly_perf.to_csv('analysis/results_hourly_performance.csv', index=False)
    best_ops.to_csv('analysis/results_best_opportunities.csv', index=False)
    day_hour.to_csv('analysis/results_day_hour_heatmap.csv', index=False)
    streaks.to_csv('analysis/results_streak_analysis.csv', index=False)
    session_perf.to_csv('analysis/results_session_performance.csv', index=False)
    vol_sizing.to_csv('analysis/results_volatility_sizing.csv', index=False)
    print("Results saved to analysis/results_*.csv")
    print()

if __name__ == '__main__':
    main()
