#!/usr/bin/env python3
"""
Visualization Suite for Econophysics Analysis Results

Creates publication-quality plots and heatmaps
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

RESULTS_DIR = Path('analysis')
PLOTS_DIR = Path('analysis/plots')
PLOTS_DIR.mkdir(exist_ok=True)

def plot_hourly_entropy_heatmap():
    """Heatmap: Entropy by crypto and hour"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_hourly_entropy.csv')

        pivot = df.pivot_table(
            index='crypto',
            columns='hour',
            values='entropy',
            aggfunc='mean'
        )

        fig, ax = plt.subplots(figsize=(16, 6))
        sns.heatmap(
            pivot,
            cmap='RdYlGn_r',  # Red=high entropy (random), Green=low entropy (predictable)
            annot=True,
            fmt='.3f',
            cbar_kws={'label': 'Shannon Entropy (0=predictable, 1=random)'},
            ax=ax
        )
        ax.set_title('Hourly Entropy by Cryptocurrency\n(Lower = More Predictable)', fontsize=14, fontweight='bold')
        ax.set_xlabel('Hour (UTC)', fontsize=12)
        ax.set_ylabel('Cryptocurrency', fontsize=12)

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'hourly_entropy_heatmap.png', dpi=300, bbox_inches='tight')
        print("✓ Created: hourly_entropy_heatmap.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_hourly_entropy.csv not found")

def plot_edge_by_hour():
    """Line plot: Trading edge by hour for each crypto"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_hourly_performance.csv')

        fig, ax = plt.subplots(figsize=(14, 7))

        for crypto in df['crypto'].unique():
            crypto_df = df[df['crypto'] == crypto].sort_values('hour')
            ax.plot(
                crypto_df['hour'],
                crypto_df['edge_pct'],
                marker='o',
                label=crypto,
                linewidth=2
            )

        ax.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Break-even')
        ax.axhline(y=10, color='green', linestyle=':', alpha=0.5, label='10% edge target')

        ax.set_xlabel('Hour (UTC)', fontsize=12)
        ax.set_ylabel('Edge (%)', fontsize=12)
        ax.set_title('Trading Edge by Hour\n(Assumes betting on majority direction)', fontsize=14, fontweight='bold')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'edge_by_hour.png', dpi=300, bbox_inches='tight')
        print("✓ Created: edge_by_hour.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_hourly_performance.csv not found")

def plot_day_hour_heatmap():
    """Heatmap: Edge by day of week and hour"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_day_hour_heatmap.csv')

        for crypto in df['crypto'].unique():
            crypto_df = df[df['crypto'] == crypto]

            pivot = crypto_df.pivot_table(
                index='day_of_week',
                columns='hour',
                values='edge',
                aggfunc='mean'
            )

            # Reorder days
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            pivot.index = pivot.index.map(lambda x: day_names[int(x)])

            fig, ax = plt.subplots(figsize=(16, 8))
            sns.heatmap(
                pivot,
                cmap='RdYlGn',
                center=0,
                annot=True,
                fmt='.2f',
                cbar_kws={'label': 'Edge (fraction)'},
                ax=ax,
                vmin=-0.2,
                vmax=0.2
            )
            ax.set_title(f'{crypto}: Trading Edge by Day and Hour\n(Green=positive edge, Red=negative edge)',
                        fontsize=14, fontweight='bold')
            ax.set_xlabel('Hour (UTC)', fontsize=12)
            ax.set_ylabel('Day of Week', fontsize=12)

            plt.tight_layout()
            plt.savefig(PLOTS_DIR / f'day_hour_{crypto.lower()}.png', dpi=300, bbox_inches='tight')
            print(f"✓ Created: day_hour_{crypto.lower()}.png")
            plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_day_hour_heatmap.csv not found")

def plot_correlation_matrix():
    """Correlation matrix between cryptos"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_sync_correlation.csv')

        # Build correlation matrix
        cryptos = sorted(set(df['crypto1'].unique()) | set(df['crypto2'].unique()))
        n = len(cryptos)
        corr_matrix = np.eye(n)

        crypto_to_idx = {c: i for i, c in enumerate(cryptos)}

        for _, row in df.iterrows():
            i = crypto_to_idx[row['crypto1']]
            j = crypto_to_idx[row['crypto2']]
            corr_matrix[i, j] = row['correlation']
            corr_matrix[j, i] = row['correlation']

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            corr_matrix,
            xticklabels=cryptos,
            yticklabels=cryptos,
            annot=True,
            fmt='.3f',
            cmap='coolwarm',
            center=0,
            vmin=-1,
            vmax=1,
            cbar_kws={'label': 'Correlation'},
            ax=ax
        )
        ax.set_title('Synchronous Directional Correlation\n(Do they move together?)', fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'correlation_matrix.png', dpi=300, bbox_inches='tight')
        print("✓ Created: correlation_matrix.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_sync_correlation.csv not found")

def plot_volatility_regimes():
    """Bar chart: Directional bias by volatility regime"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_volatility_regimes.csv')

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        for idx, crypto in enumerate(df['crypto'].unique()):
            crypto_df = df[df['crypto'] == crypto]

            ax = axes[idx]
            x = np.arange(len(crypto_df))
            width = 0.35

            bars1 = ax.bar(x - width/2, crypto_df['up_pct'], width, label='Up %')
            bars2 = ax.bar(x + width/2, 1 - crypto_df['up_pct'], width, label='Down %')

            ax.axhline(y=0.5, color='black', linestyle='--', alpha=0.5)
            ax.set_ylabel('Probability')
            ax.set_title(f'{crypto}: Directional Bias by Volatility Regime', fontweight='bold')
            ax.set_xticks(x)
            ax.set_xticklabels(crypto_df['regime'])
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'volatility_regimes.png', dpi=300, bbox_inches='tight')
        print("✓ Created: volatility_regimes.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_volatility_regimes.csv not found")

def plot_predictability_scores():
    """Bar chart: Overall predictability by crypto"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_predictability.csv')

        fig, ax = plt.subplots(figsize=(10, 6))

        cryptos = df['crypto'].values
        scores = df['predictability_score'].values

        colors = ['green' if s > 0.5 else 'orange' if s > 0.4 else 'red' for s in scores]

        bars = ax.barh(cryptos, scores, color=colors, alpha=0.7, edgecolor='black')

        ax.axvline(x=0.5, color='black', linestyle='--', alpha=0.5, label='Random walk threshold')
        ax.set_xlabel('Predictability Score (0=random, 1=highly predictable)', fontsize=12)
        ax.set_title('Market Predictability by Cryptocurrency\n(Based on entropy, mutual information, complexity)',
                    fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'predictability_scores.png', dpi=300, bbox_inches='tight')
        print("✓ Created: predictability_scores.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_predictability.csv not found")

def plot_hurst_exponents():
    """Bar chart: Hurst exponents (momentum vs mean reversion)"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_hurst_exponent.csv')

        fig, ax = plt.subplots(figsize=(10, 6))

        cryptos = df['crypto'].values
        hurst = df['hurst_exponent'].values

        colors = ['blue' if h > 0.5 else 'red' if h < 0.5 else 'gray' for h in hurst]

        bars = ax.barh(cryptos, hurst, color=colors, alpha=0.7, edgecolor='black')

        ax.axvline(x=0.5, color='black', linestyle='--', linewidth=2, label='Random walk (H=0.5)')
        ax.axvline(x=0.6, color='blue', linestyle=':', alpha=0.5)
        ax.axvline(x=0.4, color='red', linestyle=':', alpha=0.5)

        ax.set_xlabel('Hurst Exponent', fontsize=12)
        ax.set_title('Hurst Exponent by Cryptocurrency\n(Blue=Momentum/Persistent, Red=Mean Reversion, Gray=Random)',
                    fontsize=14, fontweight='bold')
        ax.set_xlim(0, 1)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        # Add text annotations
        ax.text(0.55, len(cryptos), 'Momentum →', fontsize=10, color='blue', style='italic')
        ax.text(0.35, len(cryptos), '← Mean Reversion', fontsize=10, color='red', style='italic')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'hurst_exponents.png', dpi=300, bbox_inches='tight')
        print("✓ Created: hurst_exponents.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_hurst_exponent.csv not found")

def plot_session_performance():
    """Grouped bar chart: Performance by trading session"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_session_performance.csv')

        fig, ax = plt.subplots(figsize=(12, 6))

        sessions = df['session'].unique()
        cryptos = df['crypto'].unique()
        x = np.arange(len(cryptos))
        width = 0.25

        for idx, session in enumerate(sessions):
            session_df = df[df['session'] == session].set_index('crypto')
            values = [session_df.loc[c, 'edge_pct'] if c in session_df.index else 0 for c in cryptos]

            ax.bar(x + idx * width, values, width, label=session)

        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax.set_ylabel('Edge (%)', fontsize=12)
        ax.set_title('Trading Edge by Global Session\n(Asian: 00-08 UTC, European: 08-16 UTC, US: 16-24 UTC)',
                    fontsize=14, fontweight='bold')
        ax.set_xticks(x + width)
        ax.set_xticklabels(cryptos)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'session_performance.png', dpi=300, bbox_inches='tight')
        print("✓ Created: session_performance.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_session_performance.csv not found")

def plot_information_flow():
    """Network-style plot: Transfer entropy between cryptos"""
    try:
        df = pd.read_csv(RESULTS_DIR / 'results_information_flow.csv')

        # Create adjacency matrix
        cryptos = sorted(set(df['source'].unique()) | set(df['target'].unique()))
        n = len(cryptos)
        flow_matrix = np.zeros((n, n))

        crypto_to_idx = {c: i for i, c in enumerate(cryptos)}

        for _, row in df.iterrows():
            i = crypto_to_idx[row['source']]
            j = crypto_to_idx[row['target']]
            flow_matrix[i, j] = row['transfer_entropy']

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            flow_matrix,
            xticklabels=cryptos,
            yticklabels=cryptos,
            annot=True,
            fmt='.4f',
            cmap='YlOrRd',
            cbar_kws={'label': 'Transfer Entropy (information flow)'},
            ax=ax
        )
        ax.set_xlabel('Target (receives information)', fontsize=12)
        ax.set_ylabel('Source (sends information)', fontsize=12)
        ax.set_title('Directional Information Flow Network\n(Higher = stronger causal influence)',
                    fontsize=14, fontweight='bold')

        plt.tight_layout()
        plt.savefig(PLOTS_DIR / 'information_flow.png', dpi=300, bbox_inches='tight')
        print("✓ Created: information_flow.png")
        plt.close()

    except FileNotFoundError:
        print("✗ Skipped: results_information_flow.csv not found")

def main():
    print("=" * 80)
    print("VISUALIZATION SUITE")
    print("=" * 80)
    print()

    print(f"Reading results from: {RESULTS_DIR}")
    print(f"Saving plots to: {PLOTS_DIR}")
    print()

    visualizations = [
        ('Hourly Entropy Heatmap', plot_hourly_entropy_heatmap),
        ('Edge by Hour', plot_edge_by_hour),
        ('Day-Hour Heatmaps', plot_day_hour_heatmap),
        ('Correlation Matrix', plot_correlation_matrix),
        ('Volatility Regimes', plot_volatility_regimes),
        ('Predictability Scores', plot_predictability_scores),
        ('Hurst Exponents', plot_hurst_exponents),
        ('Session Performance', plot_session_performance),
        ('Information Flow', plot_information_flow),
    ]

    for name, func in visualizations:
        print(f"Generating: {name}")
        try:
            func()
        except Exception as e:
            print(f"✗ Error: {str(e)}")
        print()

    print("=" * 80)
    print("Visualization complete!")
    print(f"View plots in: {PLOTS_DIR}")
    print("=" * 80)

if __name__ == '__main__':
    main()
