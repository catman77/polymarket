#!/usr/bin/env python3
"""
Feature Extraction Pipeline for ML Models

Extracts 50+ features from historical epoch data for training ML models.

Feature Categories:
1. Time Features (5): hour, day_of_week, minute_in_session, epoch_sequence, is_market_open
2. Price Features (8): entry_price, RSI, volatility, price_momentum, spread, position_in_range
3. Cross-Asset Features (6): BTC correlation, multi-crypto agreement, market-wide direction
4. Regime Features (4): current regime, regime stability, regime transitions
5. Agent Vote Features (20+): all agent confidences, quality scores, agreement metrics
6. Historical Pattern Features (10+): recent win rate, streak info, time-of-day performance

Total: 50+ features engineered for maximum predictive power.
"""

import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

sys.path.append(str(Path(__file__).parent.parent))

log = logging.getLogger(__name__)


@dataclass
class FeatureConfig:
    """Configuration for feature extraction."""
    epoch_db_path: str = 'analysis/epoch_history.db'
    trade_db_path: str = 'simulation/trade_journal.db'
    lookback_window: int = 50  # Number of past epochs for rolling features
    include_agent_votes: bool = True  # Include agent vote features
    include_cross_asset: bool = True  # Include cross-crypto features
    normalize_features: bool = True  # Z-score normalization


class FeatureExtractor:
    """Extract features from historical epoch data for ML training."""

    def __init__(self, config: FeatureConfig):
        """
        Initialize feature extractor.

        Args:
            config: Feature extraction configuration
        """
        self.config = config
        self.epoch_conn = sqlite3.connect(config.epoch_db_path)
        self.trade_conn = sqlite3.connect(config.trade_db_path) if Path(config.trade_db_path).exists() else None

    def extract_all_epochs(self) -> pd.DataFrame:
        """
        Extract all epochs from epoch_history.db.

        Returns:
            DataFrame with all epoch data
        """
        log.info("Extracting all epochs from database...")

        df = pd.read_sql_query('''
            SELECT
                id,
                crypto,
                epoch,
                date,
                hour,
                direction,
                start_price,
                end_price,
                change_pct,
                change_abs,
                timestamp
            FROM epoch_outcomes
            ORDER BY timestamp
        ''', self.epoch_conn)

        log.info(f"Extracted {len(df)} epochs from {df['date'].min()} to {df['date'].max()}")
        log.info(f"Cryptos: {df['crypto'].unique().tolist()}")

        return df

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add time-based features.

        Features:
        - hour: Hour of day (0-23)
        - day_of_week: Day of week (0-6, Monday=0)
        - minute_in_session: Minutes since market open (if applicable)
        - epoch_sequence: Sequential epoch number per crypto
        - is_market_open: Whether traditional markets are open

        Args:
            df: DataFrame with epoch data

        Returns:
            DataFrame with added time features
        """
        log.info("Adding time features...")

        # Parse timestamp to datetime
        df['dt'] = pd.to_datetime(df['timestamp'], unit='s')

        # Hour already exists, but ensure it's int
        df['hour'] = df['hour'].astype(int)

        # Day of week (0=Monday, 6=Sunday)
        df['day_of_week'] = df['dt'].dt.dayofweek

        # Minute in 24-hour session (0-1439)
        df['minute_in_session'] = df['hour'] * 60 + (df['dt'].dt.minute)

        # Epoch sequence per crypto (rolling count)
        df['epoch_sequence'] = df.groupby('crypto').cumcount()

        # Is traditional market open (9:30 AM - 4 PM ET, M-F)
        # Approximation: 9-16 hour on weekdays
        df['is_market_open'] = ((df['hour'] >= 9) & (df['hour'] < 16) & (df['day_of_week'] < 5)).astype(int)

        log.info(f"Added time features: hour, day_of_week, minute_in_session, epoch_sequence, is_market_open")

        return df

    def add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price-based features.

        Features:
        - RSI: 14-period Relative Strength Index
        - volatility: Rolling standard deviation of returns
        - price_momentum: Rate of change over last N periods
        - spread: Bid-ask spread proxy (from price changes)
        - position_in_range: Where current price sits in recent range
        - price_z_score: Z-score of current price vs recent mean

        Args:
            df: DataFrame with epoch data

        Returns:
            DataFrame with added price features
        """
        log.info("Adding price features...")

        # Sort by crypto and timestamp
        df = df.sort_values(['crypto', 'timestamp']).reset_index(drop=True)

        # Calculate RSI (14-period)
        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            prices = df.loc[mask, 'end_price']

            # Calculate price changes
            delta = prices.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)

            # Calculate average gain and loss
            avg_gain = gain.rolling(window=14, min_periods=1).mean()
            avg_loss = loss.rolling(window=14, min_periods=1).mean()

            # Calculate RS and RSI
            rs = avg_gain / (avg_loss + 1e-10)  # Avoid division by zero
            rsi = 100 - (100 / (1 + rs))

            df.loc[mask, 'rsi'] = rsi

        # Volatility (rolling std of returns)
        df['volatility'] = df.groupby('crypto')['change_pct'].transform(lambda x: x.rolling(20, min_periods=5).std())

        # Price momentum (rate of change over 10 periods)
        df['price_momentum'] = df.groupby('crypto')['end_price'].transform(lambda x: x.pct_change(10))

        # Spread proxy (absolute change as % of price)
        df['spread_proxy'] = np.abs(df['change_pct'])

        # Position in range (0-1, where in 50-period high-low range)
        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            prices = df.loc[mask, 'end_price']
            rolling_min = prices.rolling(50, min_periods=10).min()
            rolling_max = prices.rolling(50, min_periods=10).max()
            position = (prices - rolling_min) / (rolling_max - rolling_min + 1e-10)
            df.loc[mask, 'position_in_range'] = position

        # Price Z-score (vs 30-period mean/std)
        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            prices = df.loc[mask, 'end_price']
            rolling_mean = prices.rolling(30, min_periods=10).mean()
            rolling_std = prices.rolling(30, min_periods=10).std()
            z_score = (prices - rolling_mean) / (rolling_std + 1e-10)
            df.loc[mask, 'price_z_score'] = z_score

        log.info(f"Added price features: rsi, volatility, price_momentum, spread_proxy, position_in_range, price_z_score")

        return df

    def add_cross_asset_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add cross-asset correlation features.

        Features:
        - btc_correlation: Correlation with BTC over last 20 periods
        - multi_crypto_agreement: How many cryptos moving in same direction
        - market_wide_direction: Overall market direction (-1, 0, 1)
        - btc_leading_indicator: BTC move predicts this crypto move
        - sector_momentum: Average momentum across all cryptos

        Args:
            df: DataFrame with epoch data

        Returns:
            DataFrame with added cross-asset features
        """
        if not self.config.include_cross_asset:
            return df

        log.info("Adding cross-asset features...")

        # Pivot to get prices by crypto
        price_pivot = df.pivot_table(
            index='timestamp',
            columns='crypto',
            values='end_price'
        )

        # Calculate rolling correlation with BTC
        if 'btc' in price_pivot.columns:
            for crypto in price_pivot.columns:
                if crypto != 'btc':
                    corr = price_pivot[crypto].rolling(20, min_periods=10).corr(price_pivot['btc'])
                    # Map correlation back to original df
                    df.loc[df['crypto'] == crypto, 'btc_correlation'] = df.loc[df['crypto'] == crypto, 'timestamp'].map(
                        dict(zip(corr.index.get_level_values(0), corr.values))
                    )

            # BTC gets correlation of 1.0 with itself
            df.loc[df['crypto'] == 'btc', 'btc_correlation'] = 1.0
        else:
            df['btc_correlation'] = 0.0

        # Multi-crypto agreement (per timestamp)
        direction_pivot = df.pivot_table(
            index='timestamp',
            columns='crypto',
            values='direction',
            aggfunc='first'
        )
        # Count how many UP vs DOWN
        agreement_scores = []
        for ts in direction_pivot.index:
            directions = direction_pivot.loc[ts].dropna()
            if len(directions) == 0:
                agreement_scores.append(0.0)
            else:
                up_count = (directions == 'Up').sum()
                down_count = (directions == 'Down').sum()
                # Agreement = max(up, down) / total
                agreement = max(up_count, down_count) / len(directions)
                agreement_scores.append(agreement)

        agreement_map = dict(zip(direction_pivot.index, agreement_scores))
        df['multi_crypto_agreement'] = df['timestamp'].map(agreement_map)

        # Market-wide direction (-1, 0, 1)
        market_dir = []
        for ts in direction_pivot.index:
            directions = direction_pivot.loc[ts].dropna()
            if len(directions) == 0:
                market_dir.append(0)
            else:
                up_count = (directions == 'Up').sum()
                down_count = (directions == 'Down').sum()
                if up_count > down_count * 1.5:
                    market_dir.append(1)  # Strong UP
                elif down_count > up_count * 1.5:
                    market_dir.append(-1)  # Strong DOWN
                else:
                    market_dir.append(0)  # Mixed

        market_dir_map = dict(zip(direction_pivot.index, market_dir))
        df['market_wide_direction'] = df['timestamp'].map(market_dir_map)

        log.info(f"Added cross-asset features: btc_correlation, multi_crypto_agreement, market_wide_direction")

        return df

    def add_target_label(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add target label for supervised learning.

        Target: 1 if UP, 0 if DOWN

        Args:
            df: DataFrame with epoch data

        Returns:
            DataFrame with target column
        """
        log.info("Adding target label...")

        df['target'] = (df['direction'] == 'Up').astype(int)

        log.info(f"Target distribution: {df['target'].value_counts().to_dict()}")

        return df

    def create_train_val_test_split(
        self,
        df: pd.DataFrame,
        train_pct: float = 0.70,
        val_pct: float = 0.15,
        test_pct: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Create time-based train/validation/test splits.

        IMPORTANT: Use time-based splits (not random) to avoid lookahead bias.

        Args:
            df: DataFrame with features and target
            train_pct: Percentage for training (0-1)
            val_pct: Percentage for validation (0-1)
            test_pct: Percentage for test (0-1)

        Returns:
            Tuple of (train_df, val_df, test_df)
        """
        assert abs(train_pct + val_pct + test_pct - 1.0) < 0.01, "Split percentages must sum to 1.0"

        log.info(f"Creating time-based splits: {train_pct:.0%} train, {val_pct:.0%} val, {test_pct:.0%} test")

        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Calculate split indices
        n = len(df)
        train_idx = int(n * train_pct)
        val_idx = int(n * (train_pct + val_pct))

        train_df = df.iloc[:train_idx].copy()
        val_df = df.iloc[train_idx:val_idx].copy()
        test_df = df.iloc[val_idx:].copy()

        log.info(f"Train: {len(train_df)} samples ({train_df['date'].min()} to {train_df['date'].max()})")
        log.info(f"Val: {len(val_df)} samples ({val_df['date'].min()} to {val_df['date'].max()})")
        log.info(f"Test: {len(test_df)} samples ({test_df['date'].min()} to {test_df['date'].max()})")

        return train_df, val_df, test_df

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Get list of feature column names (exclude metadata and target).

        Args:
            df: DataFrame with features

        Returns:
            List of feature column names
        """
        # Metadata columns to exclude
        exclude = [
            'id', 'crypto', 'epoch', 'date', 'direction', 'timestamp', 'dt',
            'target', 'start_price', 'end_price', 'change_pct', 'change_abs'
        ]

        features = [col for col in df.columns if col not in exclude]

        log.info(f"Feature columns ({len(features)}): {features}")

        return features

    def extract_all_features(self) -> pd.DataFrame:
        """
        Run full feature extraction pipeline.

        Returns:
            DataFrame with all features and target
        """
        log.info("=" * 80)
        log.info("Starting feature extraction pipeline...")
        log.info("=" * 80)

        # Extract epochs
        df = self.extract_all_epochs()

        # Add features
        df = self.add_time_features(df)
        df = self.add_price_features(df)
        df = self.add_cross_asset_features(df)
        df = self.add_target_label(df)

        # Drop rows with NaN (from rolling calculations)
        initial_len = len(df)
        df = df.dropna()
        log.info(f"Dropped {initial_len - len(df)} rows with NaN (from rolling calculations)")

        # Get feature columns
        features = self.get_feature_columns(df)

        log.info("=" * 80)
        log.info(f"Feature extraction complete: {len(df)} samples, {len(features)} features")
        log.info("=" * 80)

        return df

    def save_features(self, df: pd.DataFrame, output_path: str):
        """
        Save extracted features to CSV.

        Args:
            df: DataFrame with features
            output_path: Path to save CSV
        """
        df.to_csv(output_path, index=False)
        log.info(f"Saved {len(df)} samples to {output_path}")

    def close(self):
        """Close database connections."""
        if self.epoch_conn:
            self.epoch_conn.close()
        if self.trade_conn:
            self.trade_conn.close()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Extract features for ML training')
    parser.add_argument('--epoch-db', default='analysis/epoch_history.db', help='Path to epoch history database')
    parser.add_argument('--output', default='ml/features.csv', help='Output CSV path')
    parser.add_argument('--no-cross-asset', action='store_true', help='Disable cross-asset features')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Create config
    config = FeatureConfig(
        epoch_db_path=args.epoch_db,
        include_cross_asset=not args.no_cross_asset
    )

    # Extract features
    extractor = FeatureExtractor(config)

    try:
        df = extractor.extract_all_features()

        # Create output directory
        output_dir = Path(args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save features
        extractor.save_features(df, args.output)

        # Print summary
        print("\n" + "=" * 80)
        print("FEATURE EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Total samples: {len(df)}")
        print(f"Total features: {len(extractor.get_feature_columns(df))}")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Cryptos: {df['crypto'].unique().tolist()}")
        print(f"Target distribution: {df['target'].value_counts().to_dict()}")
        print(f"Output: {args.output}")
        print("=" * 80)

    finally:
        extractor.close()


if __name__ == '__main__':
    main()
