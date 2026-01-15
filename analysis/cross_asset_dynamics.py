#!/usr/bin/env python3
"""
Cross-Asset Correlation & Contagion Analysis

Econophysics concepts:
- Correlation networks (who moves together?)
- Lead-lag relationships (who leads, who follows?)
- Contagion effects (cascading directional changes)
- Systemic risk indicators
"""

import sqlite3
import pandas as pd
import numpy as np
from itertools import combinations
from scipy import stats
from scipy.stats import spearmanr
import networkx as nx

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

def synchronous_correlation(df):
    """
    Calculate pairwise correlations at same time (t=0)

    Measures: Do cryptos move together in the same epoch?
    """
    # Pivot to wide format
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    # Calculate correlation matrix
    corr_matrix = pivot.corr()

    # Extract pairwise correlations
    results = []
    cryptos = pivot.columns.tolist()

    for i, crypto1 in enumerate(cryptos):
        for j, crypto2 in enumerate(cryptos):
            if i < j:  # Avoid duplicates
                corr = corr_matrix.loc[crypto1, crypto2]
                n = pivot[[crypto1, crypto2]].dropna().shape[0]

                # Test significance
                if n > 2:
                    t_stat = corr * np.sqrt(n - 2) / np.sqrt(1 - corr**2)
                    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
                else:
                    p_value = 1.0

                results.append({
                    'crypto1': crypto1,
                    'crypto2': crypto2,
                    'correlation': corr,
                    'n_epochs': n,
                    'p_value': p_value,
                    'significant': p_value < 0.05
                })

    return pd.DataFrame(results)

def lead_lag_analysis(df, max_lag=4):
    """
    Identify lead-lag relationships between cryptos

    Question: Does BTC move first, then others follow?
    Method: Cross-correlation at different lags
    """
    # Pivot to wide format
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    results = []
    cryptos = pivot.columns.tolist()

    for crypto1, crypto2 in combinations(cryptos, 2):
        series1 = pivot[crypto1].dropna().values
        series2 = pivot[crypto2].dropna().values

        # Align series (use common epochs)
        common = pivot[[crypto1, crypto2]].dropna()
        s1 = common[crypto1].values
        s2 = common[crypto2].values

        if len(s1) < max_lag + 2:
            continue

        # Calculate cross-correlation at different lags
        max_corr = -1
        best_lag = 0

        for lag in range(-max_lag, max_lag + 1):
            if lag == 0:
                # Synchronous correlation
                corr = np.corrcoef(s1, s2)[0, 1]
            elif lag > 0:
                # crypto1 leads crypto2 by 'lag' epochs
                if len(s1) > lag:
                    corr = np.corrcoef(s1[:-lag], s2[lag:])[0, 1]
                else:
                    continue
            else:
                # crypto2 leads crypto1 by '|lag|' epochs
                lag_abs = abs(lag)
                if len(s2) > lag_abs:
                    corr = np.corrcoef(s1[lag_abs:], s2[:-lag_abs])[0, 1]
                else:
                    continue

            if abs(corr) > abs(max_corr):
                max_corr = corr
                best_lag = lag

        # Interpret lag
        if best_lag > 0:
            leader = crypto1
            follower = crypto2
            lag_epochs = best_lag
        elif best_lag < 0:
            leader = crypto2
            follower = crypto1
            lag_epochs = abs(best_lag)
        else:
            leader = 'Synchronous'
            follower = 'Synchronous'
            lag_epochs = 0

        results.append({
            'crypto1': crypto1,
            'crypto2': crypto2,
            'max_correlation': max_corr,
            'best_lag': best_lag,
            'lag_minutes': best_lag * 15,
            'leader': leader,
            'follower': follower
        })

    return pd.DataFrame(results)

def cascade_probability(df):
    """
    Calculate probability of directional cascade

    Cascade: If crypto1 goes Up, what's P(crypto2 also goes Up)?
    This measures contagion/spillover effects
    """
    # Pivot to wide format
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    results = []
    cryptos = pivot.columns.tolist()

    for crypto1, crypto2 in combinations(cryptos, 2):
        common = pivot[[crypto1, crypto2]].dropna()

        if len(common) == 0:
            continue

        # P(crypto2=Up | crypto1=Up)
        both_up = ((common[crypto1] == 1) & (common[crypto2] == 1)).sum()
        crypto1_up = (common[crypto1] == 1).sum()
        p_up_given_up = both_up / crypto1_up if crypto1_up > 0 else 0

        # P(crypto2=Down | crypto1=Down)
        both_down = ((common[crypto1] == 0) & (common[crypto2] == 0)).sum()
        crypto1_down = (common[crypto1] == 0).sum()
        p_down_given_down = both_down / crypto1_down if crypto1_down > 0 else 0

        # Overall contagion strength
        contagion = (p_up_given_up + p_down_given_down) / 2

        # Test if different from independence (0.5)
        n = len(common)
        z_score = (contagion - 0.5) / np.sqrt(0.25 / n) if n > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        results.append({
            'crypto1': crypto1,
            'crypto2': crypto2,
            'p_up_given_up': p_up_given_up,
            'p_down_given_down': p_down_given_down,
            'contagion_strength': contagion,
            'p_value': p_value,
            'significant': p_value < 0.05
        })

    return pd.DataFrame(results)

def systemic_risk_indicator(df, window=24):
    """
    Calculate systemic risk: How often do ALL cryptos move together?

    High systemic risk = market-wide moves (diversification fails)
    Low systemic risk = independent moves (diversification works)
    """
    # Pivot to wide format
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    # Calculate rolling percentage of epochs where all agree
    pivot['all_up'] = pivot.apply(lambda row: (row == 1).all(), axis=1).astype(int)
    pivot['all_down'] = pivot.apply(lambda row: (row == 0).all(), axis=1).astype(int)
    pivot['all_agree'] = pivot['all_up'] | pivot['all_down']

    # Rolling systemic risk
    pivot['systemic_risk'] = pivot['all_agree'].rolling(window).mean()

    results = []
    for idx, row in pivot.iterrows():
        results.append({
            'epoch': idx,
            'all_up': row['all_up'],
            'all_down': row['all_down'],
            'systemic_risk': row['systemic_risk']
        })

    return pd.DataFrame(results)

def correlation_network(corr_df, threshold=0.3):
    """
    Build correlation network graph

    Nodes: Cryptos
    Edges: Significant correlations above threshold
    """
    G = nx.Graph()

    # Add nodes
    cryptos = set(corr_df['crypto1'].unique()) | set(corr_df['crypto2'].unique())
    G.add_nodes_from(cryptos)

    # Add edges for significant correlations
    for _, row in corr_df.iterrows():
        if row['significant'] and abs(row['correlation']) >= threshold:
            G.add_edge(
                row['crypto1'],
                row['crypto2'],
                weight=abs(row['correlation'])
            )

    # Calculate network metrics
    metrics = {
        'n_nodes': G.number_of_nodes(),
        'n_edges': G.number_of_edges(),
        'density': nx.density(G),
        'avg_clustering': nx.average_clustering(G) if G.number_of_edges() > 0 else 0
    }

    # Node centrality
    if G.number_of_edges() > 0:
        degree_cent = nx.degree_centrality(G)
        betweenness_cent = nx.betweenness_centrality(G)

        node_metrics = []
        for node in G.nodes():
            node_metrics.append({
                'crypto': node,
                'degree_centrality': degree_cent[node],
                'betweenness_centrality': betweenness_cent[node]
            })

        node_df = pd.DataFrame(node_metrics)
    else:
        node_df = pd.DataFrame()

    return metrics, node_df

def rolling_correlation(df, window=24):
    """
    Calculate rolling correlation to detect time-varying relationships

    Question: Does correlation increase during volatile periods?
    """
    # Pivot to wide format
    pivot = df.pivot_table(
        index='epoch',
        columns='crypto',
        values='direction_binary'
    )

    results = []
    cryptos = pivot.columns.tolist()

    for crypto1, crypto2 in combinations(cryptos, 2):
        common = pivot[[crypto1, crypto2]].dropna()

        if len(common) < window:
            continue

        # Rolling correlation
        rolling_corr = common[crypto1].rolling(window).corr(common[crypto2])

        for epoch, corr in rolling_corr.items():
            if not np.isnan(corr):
                results.append({
                    'epoch': epoch,
                    'crypto1': crypto1,
                    'crypto2': crypto2,
                    'rolling_correlation': corr
                })

    return pd.DataFrame(results)

def main():
    print("=" * 80)
    print("CROSS-ASSET CORRELATION & CONTAGION ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading epoch data...")
    df = load_data()
    print(f"Loaded {len(df)} epochs")
    print()

    # 1. Synchronous Correlation
    print("=" * 80)
    print("1. SYNCHRONOUS CORRELATION ANALYSIS")
    print("=" * 80)
    sync_corr = synchronous_correlation(df)
    print(sync_corr.to_string(index=False))
    print()

    # 2. Lead-Lag Analysis
    print("=" * 80)
    print("2. LEAD-LAG RELATIONSHIPS")
    print("=" * 80)
    lead_lag = lead_lag_analysis(df, max_lag=4)
    print("Best lag correlations:")
    print(lead_lag.to_string(index=False))
    print()

    # Identify leader
    if len(lead_lag) > 0:
        leader_counts = {}
        for _, row in lead_lag.iterrows():
            if row['leader'] != 'Synchronous':
                leader_counts[row['leader']] = leader_counts.get(row['leader'], 0) + 1

        if leader_counts:
            dominant_leader = max(leader_counts, key=leader_counts.get)
            print(f"\nDominant Leader: {dominant_leader} (leads in {leader_counts[dominant_leader]} pairs)")
            print()

    # 3. Cascade Probability
    print("=" * 80)
    print("3. DIRECTIONAL CASCADE ANALYSIS")
    print("=" * 80)
    cascade = cascade_probability(df)
    print(cascade.to_string(index=False))
    print()

    # 4. Systemic Risk
    print("=" * 80)
    print("4. SYSTEMIC RISK INDICATOR")
    print("=" * 80)
    systemic = systemic_risk_indicator(df, window=24)
    print("Systemic Risk Statistics:")
    print(systemic['systemic_risk'].describe())
    print()
    print(f"Epochs with all cryptos moving together: {systemic['all_agree'].sum()}/{len(systemic)} ({100*systemic['all_agree'].mean():.1f}%)")
    print()

    # 5. Correlation Network
    print("=" * 80)
    print("5. CORRELATION NETWORK ANALYSIS")
    print("=" * 80)
    network_metrics, node_metrics = correlation_network(sync_corr, threshold=0.3)
    print("Network Metrics:")
    for key, val in network_metrics.items():
        print(f"  {key}: {val:.3f}")
    print()

    if len(node_metrics) > 0:
        print("Node Centrality:")
        print(node_metrics.to_string(index=False))
        print()

    # 6. Rolling Correlation
    print("=" * 80)
    print("6. TIME-VARYING CORRELATION")
    print("=" * 80)
    rolling_corr = rolling_correlation(df, window=24)
    print("Rolling correlation statistics:")
    print(rolling_corr.groupby(['crypto1', 'crypto2'])['rolling_correlation'].describe())
    print()

    # Save results
    print("=" * 80)
    print("Saving results...")
    sync_corr.to_csv('analysis/results_sync_correlation.csv', index=False)
    lead_lag.to_csv('analysis/results_lead_lag.csv', index=False)
    cascade.to_csv('analysis/results_cascade_probability.csv', index=False)
    systemic.to_csv('analysis/results_systemic_risk.csv', index=False)
    if len(node_metrics) > 0:
        node_metrics.to_csv('analysis/results_network_centrality.csv', index=False)
    rolling_corr.to_csv('analysis/results_rolling_correlation.csv', index=False)
    print("Results saved to analysis/results_*.csv")
    print()

if __name__ == '__main__':
    main()
