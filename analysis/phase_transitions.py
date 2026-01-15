#!/usr/bin/env python3
"""
Phase Transition Detection in Market Behavior
Statistical physics approach to identifying regime changes

Concepts:
- Order parameter: Directional bias strength
- Susceptibility: Variance of order parameter
- Critical points: Where market behavior changes abruptly
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import timedelta
import matplotlib.pyplot as plt
from scipy import stats
from scipy.signal import find_peaks
from sklearn.cluster import KMeans

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

def rolling_order_parameter(df, window=24):
    """
    Calculate order parameter over rolling window

    Order Parameter (OP): m = (N_up - N_down) / N_total
    m ∈ [-1, 1]
    m = +1: Perfect upward bias
    m = -1: Perfect downward bias
    m = 0: No bias (disordered)

    This is analogous to magnetization in Ising model
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch').copy()

        # Rolling calculation
        crypto_df['up_count'] = crypto_df['direction_binary'].rolling(window).sum()
        crypto_df['down_count'] = window - crypto_df['up_count']
        crypto_df['order_parameter'] = (crypto_df['up_count'] - crypto_df['down_count']) / window

        # Susceptibility (variance of order parameter)
        crypto_df['susceptibility'] = crypto_df['order_parameter'].rolling(window).var()

        # Drop NaN from rolling window
        crypto_df = crypto_df.dropna()

        crypto_df['crypto'] = crypto
        results.append(crypto_df[['crypto', 'epoch', 'order_parameter', 'susceptibility']])

    return pd.concat(results, ignore_index=True)

def detect_phase_transitions(op_df, threshold=2.0):
    """
    Detect phase transitions using susceptibility peaks

    High susceptibility = critical point = phase transition
    (analogous to heat capacity peaks at phase transitions)
    """
    results = []

    for crypto in op_df['crypto'].unique():
        crypto_df = op_df[op_df['crypto'] == crypto].sort_values('epoch')

        # Normalize susceptibility to find peaks
        susc = crypto_df['susceptibility'].values
        susc_normalized = (susc - susc.mean()) / susc.std()

        # Find peaks above threshold
        peaks, properties = find_peaks(susc_normalized, height=threshold, distance=10)

        for peak_idx in peaks:
            results.append({
                'crypto': crypto,
                'epoch': crypto_df.iloc[peak_idx]['epoch'],
                'order_parameter': crypto_df.iloc[peak_idx]['order_parameter'],
                'susceptibility': crypto_df.iloc[peak_idx]['susceptibility'],
                'susceptibility_z': susc_normalized[peak_idx]
            })

    return pd.DataFrame(results)

def hurst_exponent(series, max_lag=20):
    """
    Calculate Hurst exponent (H) to detect persistence vs anti-persistence

    H > 0.5: Persistent (trending, momentum)
    H = 0.5: Random walk (efficient market)
    H < 0.5: Anti-persistent (mean reverting)

    Uses rescaled range (R/S) analysis
    """
    lags = range(2, max_lag)
    tau = []

    for lag in lags:
        # Split series into chunks of size 'lag'
        chunks = [series[i:i+lag] for i in range(0, len(series), lag) if len(series[i:i+lag]) == lag]

        if len(chunks) == 0:
            continue

        rs_values = []
        for chunk in chunks:
            # Mean-adjusted series
            mean_chunk = np.mean(chunk)
            y = np.cumsum(chunk - mean_chunk)

            # Range
            r = np.max(y) - np.min(y)

            # Standard deviation
            s = np.std(chunk)

            if s > 0:
                rs_values.append(r / s)

        if len(rs_values) > 0:
            tau.append(np.mean(rs_values))

    # Fit log(R/S) = H * log(lag) + c
    if len(tau) > 0:
        log_lags = np.log(list(lags[:len(tau)]))
        log_tau = np.log(tau)

        # Linear regression
        slope, intercept = np.polyfit(log_lags, log_tau, 1)
        return slope  # Slope = Hurst exponent
    else:
        return 0.5  # Default to random walk

def hurst_analysis(df):
    """
    Calculate Hurst exponent for each crypto
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')

        # Use directional changes as series
        series = crypto_df['direction_binary'].values

        h = hurst_exponent(series)

        if h > 0.5:
            behavior = 'Persistent/Momentum'
        elif h < 0.5:
            behavior = 'Anti-persistent/Mean Reverting'
        else:
            behavior = 'Random Walk'

        results.append({
            'crypto': crypto,
            'hurst_exponent': h,
            'behavior': behavior,
            'deviation_from_random': abs(h - 0.5)
        })

    return pd.DataFrame(results)

def cluster_regimes(df, n_regimes=3):
    """
    Use K-means to identify distinct market regimes

    Features:
    - Directional bias (rolling mean)
    - Volatility (rolling std)
    - Momentum (autocorrelation)
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch').copy()

        # Feature engineering
        window = 24  # 6 hours
        crypto_df['rolling_bias'] = crypto_df['direction_binary'].rolling(window).mean()
        crypto_df['rolling_volatility'] = crypto_df['change_pct'].abs().rolling(window).std()

        # Momentum: correlation with lagged values
        crypto_df['momentum'] = crypto_df['direction_binary'].rolling(window).apply(
            lambda x: np.corrcoef(x[:-1], x[1:])[0, 1] if len(x) > 1 else 0
        )

        # Drop NaN
        crypto_df = crypto_df.dropna()

        if len(crypto_df) < n_regimes * 10:  # Need enough data
            continue

        # Feature matrix
        X = crypto_df[['rolling_bias', 'rolling_volatility', 'momentum']].values

        # K-means clustering
        kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        crypto_df['regime'] = kmeans.fit_predict(X)

        # Characterize each regime
        for regime_id in range(n_regimes):
            regime_df = crypto_df[crypto_df['regime'] == regime_id]

            results.append({
                'crypto': crypto,
                'regime': regime_id,
                'n_epochs': len(regime_df),
                'avg_bias': regime_df['rolling_bias'].mean(),
                'avg_volatility': regime_df['rolling_volatility'].mean(),
                'avg_momentum': regime_df['momentum'].mean(),
                'up_pct': regime_df['direction_binary'].mean()
            })

    return pd.DataFrame(results)

def transition_matrix(df, window=24):
    """
    Calculate state transition probabilities

    States: Bullish (up bias > 60%), Neutral (40-60%), Bearish (< 40%)
    Transition matrix P[i,j] = P(state j | state i)
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch').copy()

        # Define states based on rolling directional bias
        crypto_df['rolling_up_pct'] = crypto_df['direction_binary'].rolling(window).mean()
        crypto_df = crypto_df.dropna()

        def classify_state(up_pct):
            if up_pct > 0.6:
                return 'Bullish'
            elif up_pct < 0.4:
                return 'Bearish'
            else:
                return 'Neutral'

        crypto_df['state'] = crypto_df['rolling_up_pct'].apply(classify_state)

        # Count transitions
        states = crypto_df['state'].values
        transition_counts = {}

        for i in range(len(states) - 1):
            from_state = states[i]
            to_state = states[i + 1]
            key = (from_state, to_state)
            transition_counts[key] = transition_counts.get(key, 0) + 1

        # Calculate probabilities
        state_names = ['Bullish', 'Neutral', 'Bearish']
        for from_state in state_names:
            total = sum(count for (f, t), count in transition_counts.items() if f == from_state)

            if total == 0:
                continue

            for to_state in state_names:
                count = transition_counts.get((from_state, to_state), 0)
                prob = count / total if total > 0 else 0

                results.append({
                    'crypto': crypto,
                    'from_state': from_state,
                    'to_state': to_state,
                    'probability': prob,
                    'count': count
                })

    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("PHASE TRANSITION DETECTION")
    print("Statistical Physics Approach to Market Regime Changes")
    print("=" * 80)
    print()

    # Load data
    print("Loading epoch data...")
    df = load_data()
    print(f"Loaded {len(df)} epochs")
    print()

    # 1. Order Parameter Analysis
    print("=" * 80)
    print("1. ORDER PARAMETER & SUSCEPTIBILITY ANALYSIS")
    print("=" * 80)
    print("Calculating rolling order parameter (24-epoch window = 6 hours)...")
    op_df = rolling_order_parameter(df, window=24)

    print("\nOrder Parameter Statistics:")
    print(op_df.groupby('crypto')['order_parameter'].describe())
    print()

    # 2. Phase Transition Detection
    print("=" * 80)
    print("2. PHASE TRANSITION DETECTION")
    print("=" * 80)
    print("Detecting susceptibility peaks (critical points)...")
    transitions_df = detect_phase_transitions(op_df, threshold=2.0)

    if len(transitions_df) > 0:
        print(f"\nDetected {len(transitions_df)} potential phase transitions:")
        print(transitions_df.to_string(index=False))
    else:
        print("\nNo significant phase transitions detected (try lowering threshold)")
    print()

    # 3. Hurst Exponent Analysis
    print("=" * 80)
    print("3. HURST EXPONENT (Persistence Analysis)")
    print("=" * 80)
    hurst_df = hurst_analysis(df)
    print(hurst_df.to_string(index=False))
    print()
    print("Interpretation:")
    print("  H > 0.5: Momentum/Trending behavior")
    print("  H = 0.5: Random walk (efficient market)")
    print("  H < 0.5: Mean reversion behavior")
    print()

    # 4. Regime Clustering
    print("=" * 80)
    print("4. K-MEANS REGIME CLUSTERING")
    print("=" * 80)
    print("Identifying distinct market regimes (n=3)...")
    regime_df = cluster_regimes(df, n_regimes=3)
    print(regime_df.to_string(index=False))
    print()

    # 5. Transition Matrix
    print("=" * 80)
    print("5. STATE TRANSITION MATRIX")
    print("=" * 80)
    print("Calculating state transition probabilities...")
    transition_df = transition_matrix(df, window=24)

    for crypto in transition_df['crypto'].unique():
        print(f"\n{crypto}:")
        crypto_trans = transition_df[transition_df['crypto'] == crypto].pivot_table(
            index='from_state',
            columns='to_state',
            values='probability',
            fill_value=0
        )
        print(crypto_trans.round(3))
    print()

    # Save results
    print("=" * 80)
    print("Saving results...")
    op_df.to_csv('analysis/results_order_parameter.csv', index=False)
    transitions_df.to_csv('analysis/results_phase_transitions.csv', index=False)
    hurst_df.to_csv('analysis/results_hurst_exponent.csv', index=False)
    regime_df.to_csv('analysis/results_regimes.csv', index=False)
    transition_df.to_csv('analysis/results_transition_matrix.csv', index=False)
    print("Results saved to analysis/results_*.csv")
    print()

if __name__ == '__main__':
    main()
