#!/usr/bin/env python3
"""
Unsupervised Learning for Pattern Discovery

Uses clustering and dimensionality reduction to discover natural groupings:
- K-Means clustering
- PCA (Principal Component Analysis)
- t-SNE visualization
- Cluster analysis and profiling
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple

from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score, calinski_harabasz_score

try:
    from sklearn.manifold import TSNE
    TSNE_AVAILABLE = True
except ImportError:
    TSNE_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))

from ml_feature_engineering import FeatureEngineering


class EpochClusterer:
    """Unsupervised learning for epoch pattern discovery."""

    def __init__(self, feature_matrix: pd.DataFrame = None):
        if feature_matrix is None:
            fe = FeatureEngineering()
            self.df = fe.build_feature_matrix()
        else:
            self.df = feature_matrix

        self.clusters = None
        self.cluster_labels = None
        self.pca_model = None
        self.tsne_model = None

    def prepare_features(self, crypto: str = None) -> Tuple[np.ndarray, pd.DataFrame]:
        """Prepare feature matrix for clustering."""
        if crypto:
            df = self.df[self.df['crypto'] == crypto].copy()
        else:
            df = self.df.copy()

        # Get numeric features only
        exclude_cols = [
            'crypto', 'epoch', 'date', 'datetime', 'direction',
            'start_price', 'end_price', 'change_pct', 'change_abs',
            'target', 'time_block', 'regime'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].values
        metadata = df[['crypto', 'datetime', 'hour', 'day_of_week', 'target']].copy()

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        return X_scaled, metadata

    def find_optimal_k(self, X: np.ndarray, k_range: range = range(2, 11)) -> Dict:
        """
        Find optimal number of clusters using elbow method and silhouette score.

        Args:
            X: Scaled feature matrix
            k_range: Range of k values to test

        Returns:
            Dict with inertia and silhouette scores for each k
        """
        print("Finding optimal number of clusters...")
        print()

        inertias = []
        silhouette_scores = []
        ch_scores = []

        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(X)

            inertias.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(X, labels))
            ch_scores.append(calinski_harabasz_score(X, labels))

            print(f"k={k:2d} | Inertia: {kmeans.inertia_:10.2f} | "
                  f"Silhouette: {silhouette_scores[-1]:.4f} | "
                  f"CH Score: {ch_scores[-1]:.2f}")

        print()

        return {
            'k_values': list(k_range),
            'inertia': inertias,
            'silhouette': silhouette_scores,
            'calinski_harabasz': ch_scores
        }

    def kmeans_clustering(self, X: np.ndarray, n_clusters: int = 5, **kwargs):
        """Perform K-Means clustering."""
        print(f"Performing K-Means clustering with {n_clusters} clusters...")

        kmeans = KMeans(
            n_clusters=n_clusters,
            random_state=42,
            n_init=10,
            **kwargs
        )

        labels = kmeans.fit_predict(X)
        self.clusters = kmeans
        self.cluster_labels = labels

        # Metrics
        silhouette = silhouette_score(X, labels)
        ch_score = calinski_harabasz_score(X, labels)

        print(f"  Silhouette Score: {silhouette:.4f}")
        print(f"  Calinski-Harabasz Score: {ch_score:.2f}")
        print()

        return labels

    def analyze_clusters(self, metadata: pd.DataFrame):
        """Analyze cluster characteristics."""
        if self.cluster_labels is None:
            print("No clusters found. Run kmeans_clustering first.")
            return

        print("="*100)
        print("CLUSTER ANALYSIS")
        print("="*100)
        print()

        df_clusters = metadata.copy()
        df_clusters['cluster'] = self.cluster_labels

        for cluster_id in range(len(np.unique(self.cluster_labels))):
            cluster_data = df_clusters[df_clusters['cluster'] == cluster_id]

            print(f"CLUSTER {cluster_id}")
            print("-"*100)
            print(f"  Size: {len(cluster_data)} epochs ({len(cluster_data)/len(df_clusters)*100:.1f}%)")

            # Win rate
            win_rate = cluster_data['target'].mean() * 100
            print(f"  Win Rate (Up %): {win_rate:.1f}%")

            # Hourly distribution
            hour_dist = cluster_data['hour'].value_counts().sort_index()
            top_hours = hour_dist.nlargest(5)
            print(f"  Top Hours: {', '.join([f'{h}:00 ({c})' for h, c in top_hours.items()])}")

            # Day of week distribution
            dow_dist = cluster_data['day_of_week'].value_counts().sort_index()
            dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            dow_str = ', '.join([f'{dow_names[d]} ({c})' for d, c in dow_dist.items()])
            print(f"  Day Distribution: {dow_str}")

            # Crypto distribution
            crypto_dist = cluster_data['crypto'].value_counts()
            crypto_str = ', '.join([f'{c.upper()} ({cnt})' for c, cnt in crypto_dist.items()])
            print(f"  Crypto Distribution: {crypto_str}")

            print()

    def pca_analysis(self, X: np.ndarray, n_components: int = 10):
        """Perform PCA dimensionality reduction."""
        print(f"Performing PCA with {n_components} components...")

        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)

        self.pca_model = pca

        # Explained variance
        explained_var = pca.explained_variance_ratio_
        cumulative_var = np.cumsum(explained_var)

        print()
        print("EXPLAINED VARIANCE")
        print("-"*60)
        print(f"{'Component':<12} {'Variance':<15} {'Cumulative':<15}")
        print("-"*60)

        for i, (var, cum_var) in enumerate(zip(explained_var, cumulative_var), 1):
            print(f"PC{i:<11} {var:<14.4f} {cum_var:<14.4f}")

        print()
        print(f"Total variance explained by {n_components} components: {cumulative_var[-1]:.4f}")
        print()

        return X_pca

    def tsne_visualization(self, X: np.ndarray, perplexity: int = 30):
        """Perform t-SNE for 2D visualization."""
        if not TSNE_AVAILABLE:
            print("t-SNE not available.")
            return None

        print(f"Performing t-SNE (perplexity={perplexity})...")
        print("This may take a few minutes...")

        # Use PCA first to reduce dimensions (t-SNE is slow on high-dim data)
        if X.shape[1] > 50:
            pca = PCA(n_components=50)
            X = pca.fit_transform(X)

        tsne = TSNE(
            n_components=2,
            perplexity=perplexity,
            random_state=42,
            n_iter=1000
        )

        X_tsne = tsne.fit_transform(X)
        self.tsne_model = tsne

        print("t-SNE complete!")
        print()

        return X_tsne

    def plot_clusters_2d(self, X_reduced: np.ndarray, metadata: pd.DataFrame,
                        method: str = 'pca', save_path: str = None):
        """Plot clusters in 2D space."""
        if self.cluster_labels is None:
            print("No clusters to plot. Run kmeans_clustering first.")
            return

        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Plot 1: Clusters colored by cluster ID
        scatter1 = axes[0].scatter(
            X_reduced[:, 0],
            X_reduced[:, 1],
            c=self.cluster_labels,
            cmap='viridis',
            alpha=0.6,
            s=20
        )
        axes[0].set_xlabel(f'{method.upper()} Component 1')
        axes[0].set_ylabel(f'{method.upper()} Component 2')
        axes[0].set_title(f'Clusters ({method.upper()})')
        plt.colorbar(scatter1, ax=axes[0], label='Cluster')

        # Plot 2: Colored by target (Up/Down)
        scatter2 = axes[1].scatter(
            X_reduced[:, 0],
            X_reduced[:, 1],
            c=metadata['target'],
            cmap='RdYlGn',
            alpha=0.6,
            s=20
        )
        axes[1].set_xlabel(f'{method.upper()} Component 1')
        axes[1].set_ylabel(f'{method.upper()} Component 2')
        axes[1].set_title(f'Outcome (Red=Down, Green=Up)')
        plt.colorbar(scatter2, ax=axes[1], label='Outcome')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Plot saved to: {save_path}")

        plt.show()

    def cluster_profiling(self, metadata: pd.DataFrame) -> pd.DataFrame:
        """
        Create detailed cluster profiles.

        Returns:
            DataFrame with cluster statistics
        """
        if self.cluster_labels is None:
            print("No clusters found.")
            return pd.DataFrame()

        df_clusters = metadata.copy()
        df_clusters['cluster'] = self.cluster_labels

        profiles = []

        for cluster_id in range(len(np.unique(self.cluster_labels))):
            cluster_data = df_clusters[df_clusters['cluster'] == cluster_id]

            profile = {
                'cluster': cluster_id,
                'size': len(cluster_data),
                'pct_of_total': len(cluster_data) / len(df_clusters) * 100,
                'win_rate': cluster_data['target'].mean() * 100,
                'most_common_hour': cluster_data['hour'].mode()[0] if len(cluster_data) > 0 else -1,
                'most_common_dow': cluster_data['day_of_week'].mode()[0] if len(cluster_data) > 0 else -1,
                'most_common_crypto': cluster_data['crypto'].mode()[0] if len(cluster_data) > 0 else 'N/A',
            }

            profiles.append(profile)

        df_profiles = pd.DataFrame(profiles)

        return df_profiles


def main():
    """Main unsupervised learning pipeline."""
    print("="*100)
    print("UNSUPERVISED LEARNING - PATTERN DISCOVERY")
    print("="*100)
    print()

    # Initialize clusterer
    clusterer = EpochClusterer()

    print(f"Total dataset: {len(clusterer.df)} epochs")
    print(f"Cryptos: {clusterer.df['crypto'].unique()}")
    print()

    # Prepare features
    X, metadata = clusterer.prepare_features(crypto=None)
    print(f"Feature matrix: {X.shape[0]} samples × {X.shape[1]} features")
    print()

    # Find optimal k
    print("="*100)
    print("FINDING OPTIMAL NUMBER OF CLUSTERS")
    print("="*100)
    print()

    optimal_k_results = clusterer.find_optimal_k(X, k_range=range(3, 11))

    # Based on results, choose k (typically highest silhouette score or elbow point)
    best_k_idx = np.argmax(optimal_k_results['silhouette'])
    best_k = optimal_k_results['k_values'][best_k_idx]

    print(f"Recommended k: {best_k} (highest silhouette score: {optimal_k_results['silhouette'][best_k_idx]:.4f})")
    print()

    # Perform K-Means with optimal k
    print("="*100)
    print(f"K-MEANS CLUSTERING (k={best_k})")
    print("="*100)
    print()

    labels = clusterer.kmeans_clustering(X, n_clusters=best_k)

    # Analyze clusters
    clusterer.analyze_clusters(metadata)

    # Cluster profiling
    print("="*100)
    print("CLUSTER PROFILES")
    print("="*100)
    print()

    profiles = clusterer.cluster_profiling(metadata)
    print(profiles.to_string(index=False))
    print()

    # PCA analysis
    print("="*100)
    print("PCA DIMENSIONALITY REDUCTION")
    print("="*100)
    print()

    X_pca = clusterer.pca_analysis(X, n_components=10)

    # t-SNE visualization (optional - slow)
    if TSNE_AVAILABLE:
        print("="*100)
        print("t-SNE VISUALIZATION")
        print("="*100)
        print()

        X_tsne = clusterer.tsne_visualization(X, perplexity=30)

        if X_tsne is not None:
            # Plot
            output_path = Path('analysis/cluster_visualization_tsne.png')
            clusterer.plot_clusters_2d(X_tsne, metadata, method='tsne', save_path=str(output_path))

    # Plot PCA clusters
    X_pca_2d = X_pca[:, :2]  # First 2 components
    output_path_pca = Path('analysis/cluster_visualization_pca.png')
    clusterer.plot_clusters_2d(X_pca_2d, metadata, method='pca', save_path=str(output_path_pca))

    print()
    print("="*100)
    print("INSIGHTS & RECOMMENDATIONS")
    print("="*100)
    print()

    print("1. CLUSTER CHARACTERISTICS:")
    print("   - Look for clusters with >60% win rate (profitable after fees)")
    print("   - Identify time patterns (specific hours/days in high-performing clusters)")
    print("   - Note crypto-specific clusters (some cryptos may have unique patterns)")
    print()

    print("2. TRADING STRATEGY:")
    print("   - Focus trades on hours/conditions matching high win-rate clusters")
    print("   - Avoid trading during low win-rate cluster conditions")
    print("   - Use cluster features to filter entry signals")
    print()

    print("3. NEXT STEPS:")
    print("   - Combine cluster labels as features in supervised models")
    print("   - Create trading rules based on cluster membership")
    print("   - Monitor cluster drift over time (patterns may change)")
    print()


if __name__ == '__main__':
    main()
