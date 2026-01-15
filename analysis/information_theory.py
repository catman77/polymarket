#!/usr/bin/env python3
"""
Information Theory Analysis of Market Predictability

Concepts:
- Shannon entropy: Measure of uncertainty/predictability
- Mutual information: How much does past predict future?
- Transfer entropy: Directional information flow
- Complexity measures: How structured is the market?
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import entropy
from itertools import product
from collections import Counter

DB_PATH = "analysis/epoch_history.db"

def load_data():
    """Load epoch data from SQLite"""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT crypto, epoch, direction, change_pct
        FROM epochs
        ORDER BY crypto, epoch
    """, conn)
    conn.close()

    df['epoch'] = pd.to_datetime(df['epoch'])
    df['direction_binary'] = (df['direction'] == 'Up').astype(int)
    return df

def shannon_entropy(series):
    """
    Calculate Shannon entropy

    H(X) = -Σ p(x) log2(p(x))

    For binary outcomes (Up/Down):
    - Max entropy = 1.0 (50/50 split, maximum uncertainty)
    - Min entropy = 0.0 (100% one direction, zero uncertainty)
    """
    value_counts = series.value_counts(normalize=True)
    return entropy(value_counts, base=2)

def conditional_entropy(series, lag=1):
    """
    Calculate conditional entropy H(X_t | X_{t-lag})

    Measures: How much uncertainty remains about current direction
              given we know direction 'lag' epochs ago?

    Lower conditional entropy = more predictable
    """
    if lag >= len(series):
        return None

    # Create lagged pairs
    current = series.values[lag:]
    lagged = series.values[:-lag]

    # Count joint occurrences
    joint_counts = Counter(zip(lagged, current))
    lagged_counts = Counter(lagged)

    # Calculate conditional probabilities and entropy
    h_conditional = 0.0
    n_total = len(current)

    for lag_val in lagged_counts:
        p_lag = lagged_counts[lag_val] / n_total

        # Conditional distribution: P(current | lagged = lag_val)
        conditional_dist = []
        for curr_val in [0, 1]:
            count = joint_counts.get((lag_val, curr_val), 0)
            if lagged_counts[lag_val] > 0:
                conditional_dist.append(count / lagged_counts[lag_val])
            else:
                conditional_dist.append(0)

        # Entropy of conditional distribution
        h_cond = entropy([p for p in conditional_dist if p > 0], base=2)
        h_conditional += p_lag * h_cond

    return h_conditional

def mutual_information(series, lag=1):
    """
    Calculate mutual information I(X_t ; X_{t-lag})

    I(X;Y) = H(X) - H(X|Y)

    Measures: How much information does past provide about future?
    - I = 0: Past and future independent (no predictability)
    - I > 0: Past provides information about future (predictable)
    """
    h_current = shannon_entropy(series)
    h_cond = conditional_entropy(series, lag)

    if h_cond is None:
        return None

    return h_current - h_cond

def transfer_entropy(source_series, target_series, lag=1):
    """
    Transfer entropy: T(X→Y) = I(Y_t ; X_{t-lag} | Y_{t-lag})

    Measures: Information flow from X to Y
    Does X's past help predict Y's future, beyond Y's own past?

    T > 0: X influences Y (causal information flow)
    """
    if lag >= min(len(source_series), len(target_series)):
        return None

    # Align series
    y_current = target_series.values[lag:]
    y_lagged = target_series.values[:-lag]
    x_lagged = source_series.values[:-lag]

    # Count triplets (x_lag, y_lag, y_current)
    triplet_counts = Counter(zip(x_lagged, y_lagged, y_current))
    y_pair_counts = Counter(zip(y_lagged, y_current))
    xy_lag_counts = Counter(zip(x_lagged, y_lagged))
    y_lag_counts = Counter(y_lagged)

    n_total = len(y_current)

    # Calculate transfer entropy
    te = 0.0

    for (x_lag, y_lag, y_curr), count in triplet_counts.items():
        p_triplet = count / n_total
        p_y_pair = y_pair_counts.get((y_lag, y_curr), 0) / n_total
        p_xy_lag = xy_lag_counts.get((x_lag, y_lag), 0) / n_total
        p_y_lag = y_lag_counts.get(y_lag, 0) / n_total

        if p_triplet > 0 and p_y_pair > 0 and p_xy_lag > 0 and p_y_lag > 0:
            te += p_triplet * np.log2((p_triplet * p_y_lag) / (p_y_pair * p_xy_lag))

    return te

def lempel_ziv_complexity(series):
    """
    Lempel-Ziv complexity: Measure of randomness/structure

    Higher complexity = more random, less predictable
    Lower complexity = more structured, more predictable

    Normalized to [0, 1]
    """
    # Convert to string
    s = ''.join(map(str, series.astype(int).values))

    n = len(s)
    i = 0
    c = 1
    u = 1
    v = 1
    v_max = 1

    while u + v <= n:
        if s[i + v - 1] == s[u + v - 1]:
            v += 1
        else:
            v_max = max(v, v_max)
            i += 1
            if i == u:
                c += 1
                u += v_max
                v = 1
                i = 0
                v_max = 1
            else:
                v = 1

    if v != 1:
        c += 1

    # Normalize
    if n > 0:
        complexity = c / (n / np.log2(n))
    else:
        complexity = 0

    return complexity

def predictability_analysis(df):
    """
    Comprehensive predictability analysis for each crypto
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')
        series = crypto_df['direction_binary']

        if len(series) < 10:
            continue

        # Shannon entropy
        h = shannon_entropy(series)

        # Mutual information at different lags
        mi_lag1 = mutual_information(series, lag=1)
        mi_lag2 = mutual_information(series, lag=2)
        mi_lag4 = mutual_information(series, lag=4)

        # Conditional entropy
        h_cond_lag1 = conditional_entropy(series, lag=1)

        # Lempel-Ziv complexity
        lz_complexity = lempel_ziv_complexity(series)

        # Predictability score (0-1, higher = more predictable)
        # Based on: low entropy, high MI, low LZ complexity
        predictability = (
            (1 - h) * 0.4 +  # Low entropy = predictable
            (mi_lag1 if mi_lag1 else 0) * 0.4 +  # High MI = predictable
            (1 - lz_complexity) * 0.2  # Low complexity = predictable
        )

        results.append({
            'crypto': crypto,
            'n_epochs': len(series),
            'shannon_entropy': h,
            'conditional_entropy_lag1': h_cond_lag1,
            'mutual_information_lag1': mi_lag1,
            'mutual_information_lag2': mi_lag2,
            'mutual_information_lag4': mi_lag4,
            'lz_complexity': lz_complexity,
            'predictability_score': predictability
        })

    return pd.DataFrame(results)

def information_flow_network(df, lag=1):
    """
    Calculate transfer entropy between all crypto pairs
    Creates directed information flow network
    """
    results = []

    # Pivot to get aligned time series
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    cryptos = pivot.columns.tolist()

    for source in cryptos:
        for target in cryptos:
            if source == target:
                continue

            source_series = pivot[source].dropna()
            target_series = pivot[target].dropna()

            # Align on common epochs
            common_idx = source_series.index.intersection(target_series.index)
            if len(common_idx) < lag + 10:
                continue

            s = source_series.loc[common_idx]
            t = target_series.loc[common_idx]

            # Calculate transfer entropy
            te = transfer_entropy(s, t, lag=lag)

            if te is not None:
                results.append({
                    'source': source,
                    'target': target,
                    'transfer_entropy': te,
                    'n_epochs': len(common_idx)
                })

    return pd.DataFrame(results)

def temporal_entropy_evolution(df, window=24):
    """
    Calculate rolling entropy to see how predictability changes over time
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')

        if len(crypto_df) < window:
            continue

        for i in range(window, len(crypto_df)):
            window_data = crypto_df.iloc[i-window:i]
            h = shannon_entropy(window_data['direction_binary'])

            results.append({
                'crypto': crypto,
                'epoch': window_data.iloc[-1]['epoch'],
                'rolling_entropy': h,
                'predictability': 1 - h  # Invert entropy for intuitive interpretation
            })

    return pd.DataFrame(results)

def pattern_frequency_analysis(df, pattern_length=3):
    """
    Analyze frequency of directional patterns

    Example patterns (length 3):
    - UUU (3 ups in a row)
    - UUD (up, up, down)
    - DDD (3 downs in a row)
    etc.
    """
    results = []

    for crypto in df['crypto'].unique():
        crypto_df = df[df['crypto'] == crypto].sort_values('epoch')
        directions = crypto_df['direction'].values

        if len(directions) < pattern_length:
            continue

        # Extract all patterns
        patterns = []
        for i in range(len(directions) - pattern_length + 1):
            pattern = ''.join(directions[i:i+pattern_length])
            patterns.append(pattern)

        # Count pattern frequencies
        pattern_counts = Counter(patterns)
        total_patterns = len(patterns)

        # Calculate entropy of pattern distribution
        pattern_probs = [count / total_patterns for count in pattern_counts.values()]
        pattern_entropy = entropy(pattern_probs, base=2)

        # Max entropy for patterns
        max_entropy = np.log2(2 ** pattern_length)  # All possible patterns

        # Normalized entropy (0-1)
        normalized_entropy = pattern_entropy / max_entropy if max_entropy > 0 else 0

        # Find most common patterns
        top_patterns = pattern_counts.most_common(5)

        results.append({
            'crypto': crypto,
            'pattern_length': pattern_length,
            'n_patterns': total_patterns,
            'unique_patterns': len(pattern_counts),
            'pattern_entropy': pattern_entropy,
            'normalized_pattern_entropy': normalized_entropy,
            'most_common_pattern': top_patterns[0][0] if top_patterns else None,
            'most_common_frequency': top_patterns[0][1] / total_patterns if top_patterns else 0
        })

    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("INFORMATION THEORY & PREDICTABILITY ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading epoch data...")
    df = load_data()
    print(f"Loaded {len(df)} epochs")
    print()

    # 1. Predictability Analysis
    print("=" * 80)
    print("1. PREDICTABILITY ANALYSIS")
    print("=" * 80)
    pred_df = predictability_analysis(df)
    print(pred_df.to_string(index=False))
    print()
    print("Interpretation:")
    print("  - Shannon Entropy: 0=predictable, 1=random")
    print("  - Mutual Information: 0=no predictability, higher=more predictable")
    print("  - LZ Complexity: 0=simple pattern, 1=random")
    print("  - Predictability Score: 0=unpredictable, 1=highly predictable")
    print()

    # 2. Information Flow Network
    print("=" * 80)
    print("2. INFORMATION FLOW NETWORK (Transfer Entropy)")
    print("=" * 80)
    print("Calculating directional information flow...")
    flow_df = information_flow_network(df, lag=1)

    if len(flow_df) > 0:
        print(flow_df.sort_values('transfer_entropy', ascending=False).to_string(index=False))
        print()

        # Identify information leaders
        outflow = flow_df.groupby('source')['transfer_entropy'].sum().sort_values(ascending=False)
        print("\nInformation Sources (highest outflow):")
        print(outflow)
    else:
        print("Not enough data for transfer entropy calculation")
    print()

    # 3. Temporal Entropy Evolution
    print("=" * 80)
    print("3. TEMPORAL ENTROPY EVOLUTION")
    print("=" * 80)
    temporal_df = temporal_entropy_evolution(df, window=24)
    print("Rolling entropy statistics:")
    print(temporal_df.groupby('crypto')['rolling_entropy'].describe())
    print()

    # 4. Pattern Frequency Analysis
    print("=" * 80)
    print("4. DIRECTIONAL PATTERN ANALYSIS")
    print("=" * 80)
    pattern_df = pattern_frequency_analysis(df, pattern_length=3)
    print(pattern_df.to_string(index=False))
    print()

    # Save results
    print("=" * 80)
    print("Saving results...")
    pred_df.to_csv('analysis/results_predictability.csv', index=False)
    if len(flow_df) > 0:
        flow_df.to_csv('analysis/results_information_flow.csv', index=False)
    temporal_df.to_csv('analysis/results_temporal_entropy.csv', index=False)
    pattern_df.to_csv('analysis/results_pattern_frequency.csv', index=False)
    print("Results saved to analysis/results_*.csv")
    print()

if __name__ == '__main__':
    main()
