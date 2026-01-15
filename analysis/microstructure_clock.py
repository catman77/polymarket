#!/usr/bin/env python3
"""
Market Microstructure Clock Analysis
Econophysics approach to identifying structural trading patterns
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from scipy import stats
from scipy.stats import entropy, chi2_contingency

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
    return df

def session_segmentation():
    """
    Divide 24-hour period into global trading sessions
    Based on major market centers and liquidity flows
    """
    return {
        'Asian': list(range(0, 8)),      # 00:00-08:00 UTC (Tokyo, Sydney, Hong Kong)
        'European': list(range(8, 16)),   # 08:00-16:00 UTC (London, Frankfurt)
        'US': list(range(16, 24))         # 16:00-24:00 UTC (NY, Chicago)
    }

def calculate_hourly_entropy(df):
    """
    Shannon entropy analysis by hour
    H = -Σ p(x) log2(p(x))

    Low entropy = predictable (strong directional bias)
    High entropy = unpredictable (near 50/50)
    Max entropy = 1.0 (perfect 50/50)
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for hour in range(24):
            hour_df = crypto_df[crypto_df['hour'] == hour]

            if len(hour_df) == 0:
                continue

            up_pct = hour_df['direction_binary'].mean()
            down_pct = 1 - up_pct

            # Shannon entropy
            if up_pct > 0 and down_pct > 0:
                h = -up_pct * np.log2(up_pct) - down_pct * np.log2(down_pct)
            else:
                h = 0  # Completely deterministic

            # Z-score test for bias significance
            n = len(hour_df)
            expected = 0.5
            std_err = np.sqrt(expected * (1 - expected) / n)
            z_score = (up_pct - expected) / std_err if std_err > 0 else 0
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

            results.append({
                'crypto': crypto,
                'hour': hour,
                'n_epochs': n,
                'up_pct': up_pct,
                'entropy': h,
                'edge': abs(up_pct - 0.5),  # Distance from 50%
                'z_score': z_score,
                'p_value': p_value,
                'significant': p_value < 0.05
            })

    return pd.DataFrame(results)

def session_analysis(df):
    """
    Analyze directional bias by trading session
    Tests if market behavior differs across global trading centers
    """
    sessions = session_segmentation()
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for session_name, hours in sessions.items():
            session_df = crypto_df[crypto_df['hour'].isin(hours)]

            if len(session_df) == 0:
                continue

            up_pct = session_df['direction_binary'].mean()
            n = len(session_df)

            # Binomial test: is this significantly different from 50%?
            binom_test = stats.binomtest(
                int(up_pct * n),
                n,
                p=0.5,
                alternative='two-sided'
            )

            results.append({
                'crypto': crypto,
                'session': session_name,
                'hours': f"{min(hours):02d}:00-{max(hours)+1:02d}:00",
                'n_epochs': n,
                'up_pct': up_pct,
                'edge': abs(up_pct - 0.5),
                'p_value': binom_test.pvalue,
                'significant': binom_test.pvalue < 0.05
            })

    return pd.DataFrame(results)

def correlation_length_analysis(df):
    """
    Measure temporal auto-correlation of directional changes

    Correlation length = how many epochs does directional bias persist?
    Uses exponential decay model: C(t) = exp(-t/τ)
    τ = correlation length (in epochs)
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')
        directions = crypto_df['direction_binary'].values

        # Calculate auto-correlation at different lags
        max_lag = 20  # Up to 5 hours (20 * 15min)
        acf = []

        for lag in range(1, max_lag + 1):
            if lag >= len(directions):
                break

            # Pearson correlation between series and lagged series
            corr = np.corrcoef(directions[:-lag], directions[lag:])[0, 1]
            acf.append({
                'crypto': crypto,
                'lag_epochs': lag,
                'lag_minutes': lag * 15,
                'correlation': corr
            })

        results.extend(acf)

    acf_df = pd.DataFrame(results)

    # Estimate correlation length (where ACF drops to 1/e ≈ 0.37)
    tau_results = []
    for crypto in df['crypto'].unique():
        crypto_acf = acf_df[acf_df['crypto'] == crypto]

        # Find first lag where correlation drops below threshold
        threshold = 1/np.e
        below_threshold = crypto_acf[crypto_acf['correlation'] < threshold]

        if len(below_threshold) > 0:
            tau_epochs = below_threshold.iloc[0]['lag_epochs']
            tau_minutes = tau_epochs * 15
        else:
            tau_epochs = max_lag  # Longer than measured
            tau_minutes = tau_epochs * 15

        tau_results.append({
            'crypto': crypto,
            'correlation_length_epochs': tau_epochs,
            'correlation_length_minutes': tau_minutes,
            'correlation_length_hours': tau_minutes / 60
        })

    return acf_df, pd.DataFrame(tau_results)

def volatility_regime_analysis(df):
    """
    Classify epochs by volatility regime and test directional bias

    Volatility = |change_pct|
    Regimes: Low (<0.1%), Medium (0.1-0.3%), High (>0.3%)
    """
    df['volatility'] = df['change_pct'].abs()

    # Define regimes based on percentiles
    low_thresh = df['volatility'].quantile(0.33)
    high_thresh = df['volatility'].quantile(0.67)

    def classify_regime(vol):
        if vol < low_thresh:
            return 'Low'
        elif vol < high_thresh:
            return 'Medium'
        else:
            return 'High'

    df['regime'] = df['volatility'].apply(classify_regime)

    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for regime in ['Low', 'Medium', 'High']:
            regime_df = crypto_df[crypto_df['regime'] == regime]

            if len(regime_df) == 0:
                continue

            up_pct = regime_df['direction_binary'].mean()
            n = len(regime_df)

            # Test significance
            binom_test = stats.binomtest(
                int(up_pct * n),
                n,
                p=0.5,
                alternative='two-sided'
            )

            results.append({
                'crypto': crypto,
                'regime': regime,
                'n_epochs': n,
                'avg_volatility': regime_df['volatility'].mean(),
                'up_pct': up_pct,
                'edge': abs(up_pct - 0.5),
                'p_value': binom_test.pvalue
            })

    return pd.DataFrame(results), low_thresh, high_thresh

def momentum_mean_reversion_test(df):
    """
    Test for momentum vs mean reversion behavior

    Momentum: Up followed by Up (or Down by Down) > 50%
    Mean Reversion: Up followed by Down (or Down by Up) > 50%
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')
        directions = crypto_df['direction'].values

        # Count transitions
        same_direction = 0  # Momentum
        opposite_direction = 0  # Mean reversion

        for i in range(len(directions) - 1):
            if directions[i] == directions[i+1]:
                same_direction += 1
            else:
                opposite_direction += 1

        total = same_direction + opposite_direction
        momentum_pct = same_direction / total if total > 0 else 0

        # Chi-square test: is momentum% significantly different from 50%?
        chi2, p_value = stats.chisquare(
            [same_direction, opposite_direction],
            [total/2, total/2]
        )

        behavior = 'Momentum' if momentum_pct > 0.5 else 'Mean Reversion'
        strength = abs(momentum_pct - 0.5)

        results.append({
            'crypto': crypto,
            'n_transitions': total,
            'momentum_pct': momentum_pct,
            'mean_reversion_pct': 1 - momentum_pct,
            'behavior': behavior,
            'strength': strength,
            'chi2': chi2,
            'p_value': p_value,
            'significant': p_value < 0.05
        })

    return pd.DataFrame(results)

def day_of_week_analysis(df):
    """
    Test for calendar effects (day of week patterns)
    """
    df['day_of_week'] = df['epoch'].dt.dayofweek
    df['day_name'] = df['epoch'].dt.day_name()

    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto]

        for dow in range(7):
            dow_df = crypto_df[crypto_df['day_of_week'] == dow]

            if len(dow_df) == 0:
                continue

            up_pct = dow_df['direction_binary'].mean()
            n = len(dow_df)

            # Binomial test
            binom_test = stats.binomtest(
                int(up_pct * n),
                n,
                p=0.5,
                alternative='two-sided'
            )

            results.append({
                'crypto': crypto,
                'day_of_week': dow,
                'day_name': dow_df.iloc[0]['day_name'],
                'n_epochs': n,
                'up_pct': up_pct,
                'edge': abs(up_pct - 0.5),
                'p_value': binom_test.pvalue,
                'significant': binom_test.pvalue < 0.05
            })

    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("MARKET MICROSTRUCTURE CLOCK ANALYSIS")
    print("Econophysics Approach to 15-Minute Binary Outcome Markets")
    print("=" * 80)
    print()

    # Load data
    print("Loading epoch data...")
    df = load_data()
    print(f"Loaded {len(df)} epochs across {df['crypto'].nunique()} cryptocurrencies")
    print(f"Date range: {df['epoch'].min()} to {df['epoch'].max()}")
    print()

    # 1. Hourly Entropy Analysis
    print("=" * 80)
    print("1. HOURLY ENTROPY ANALYSIS")
    print("=" * 80)
    entropy_df = calculate_hourly_entropy(df)

    # Show most predictable hours (lowest entropy)
    print("\nMost Predictable Hours (Lowest Entropy = Strong Directional Bias):")
    print("-" * 80)
    top_predictable = entropy_df.nsmallest(10, 'entropy')[
        ['crypto', 'hour', 'n_epochs', 'up_pct', 'entropy', 'edge', 'p_value']
    ]
    print(top_predictable.to_string(index=False))

    # Show statistical significance
    significant = entropy_df[entropy_df['significant']]
    print(f"\nStatistically Significant Hourly Patterns (p < 0.05): {len(significant)}/{len(entropy_df)}")
    print()

    # 2. Trading Session Analysis
    print("=" * 80)
    print("2. GLOBAL TRADING SESSION ANALYSIS")
    print("=" * 80)
    session_df = session_analysis(df)
    print(session_df.to_string(index=False))
    print()

    # 3. Correlation Length
    print("=" * 80)
    print("3. TEMPORAL AUTO-CORRELATION ANALYSIS")
    print("=" * 80)
    acf_df, tau_df = correlation_length_analysis(df)
    print("Correlation Length (Directional Persistence):")
    print(tau_df.to_string(index=False))
    print()

    # 4. Volatility Regime Analysis
    print("=" * 80)
    print("4. VOLATILITY REGIME ANALYSIS")
    print("=" * 80)
    vol_df, low_t, high_t = volatility_regime_analysis(df)
    print(f"Low Volatility: < {low_t:.4f}%")
    print(f"High Volatility: > {high_t:.4f}%")
    print()
    print(vol_df.to_string(index=False))
    print()

    # 5. Momentum vs Mean Reversion
    print("=" * 80)
    print("5. MOMENTUM vs MEAN REVERSION TEST")
    print("=" * 80)
    momentum_df = momentum_mean_reversion_test(df)
    print(momentum_df.to_string(index=False))
    print()

    # 6. Day of Week Effects
    print("=" * 80)
    print("6. CALENDAR EFFECTS (Day of Week)")
    print("=" * 80)
    dow_df = day_of_week_analysis(df)

    # Show only significant patterns
    sig_dow = dow_df[dow_df['significant']]
    if len(sig_dow) > 0:
        print("Significant Day-of-Week Patterns:")
        print(sig_dow[['crypto', 'day_name', 'n_epochs', 'up_pct', 'edge', 'p_value']].to_string(index=False))
    else:
        print("No significant day-of-week patterns found (p < 0.05)")
    print()

    # Save results
    print("=" * 80)
    print("Saving results to CSV...")
    entropy_df.to_csv('analysis/results_hourly_entropy.csv', index=False)
    session_df.to_csv('analysis/results_trading_sessions.csv', index=False)
    tau_df.to_csv('analysis/results_correlation_length.csv', index=False)
    vol_df.to_csv('analysis/results_volatility_regimes.csv', index=False)
    momentum_df.to_csv('analysis/results_momentum_reversion.csv', index=False)
    dow_df.to_csv('analysis/results_day_of_week.csv', index=False)
    print("Results saved to analysis/results_*.csv")
    print()

if __name__ == '__main__':
    main()
