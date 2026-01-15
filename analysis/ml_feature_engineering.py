#!/usr/bin/env python3
"""
Feature Engineering for Epoch Prediction

Extracts features from raw epoch data to feed into ML models:
- Temporal features (hour, day-of-week, time blocks)
- Rolling statistics (momentum, volatility)
- Cross-crypto correlations
- Market regime indicators
"""

import sys
from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

sys.path.append(str(Path(__file__).parent.parent))


class FeatureEngineering:
    """Extract ML features from epoch history."""

    def __init__(self, db_path: str = 'analysis/epoch_history.db'):
        self.db_path = db_path

    def load_raw_data(self, cryptos: List[str] = ['btc', 'eth', 'sol', 'xrp']) -> pd.DataFrame:
        """Load raw epoch data from database."""
        conn = sqlite3.connect(self.db_path)

        query = '''
            SELECT
                crypto,
                epoch,
                date,
                hour,
                direction,
                start_price,
                end_price,
                change_pct,
                change_abs
            FROM epoch_outcomes
            WHERE crypto IN ({})
            ORDER BY crypto, epoch
        '''.format(','.join(['?' for _ in cryptos]))

        df = pd.read_sql_query(query, conn, params=cryptos)
        conn.close()

        # Convert direction to binary (1 = Up, 0 = Down)
        df['target'] = (df['direction'] == 'Up').astype(int)

        # Add datetime column
        df['datetime'] = pd.to_datetime(df['epoch'], unit='s')
        df['date'] = pd.to_datetime(df['date'])

        return df

    def add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        df = df.copy()

        # Hour of day (already have this)
        # df['hour'] already exists

        # Day of week (0 = Monday, 6 = Sunday)
        df['day_of_week'] = df['datetime'].dt.dayofweek

        # Weekend flag
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

        # Time blocks (morning, afternoon, evening, night)
        df['time_block'] = pd.cut(
            df['hour'],
            bins=[0, 6, 12, 18, 24],
            labels=['night', 'morning', 'afternoon', 'evening'],
            include_lowest=True
        )

        # US trading hours (9:30 AM - 4:00 PM ET = 14:30 - 21:00 UTC)
        df['us_trading_hours'] = ((df['hour'] >= 14) & (df['hour'] < 21)).astype(int)

        # Asian trading hours (0:00 - 8:00 UTC)
        df['asian_trading_hours'] = (df['hour'] < 8).astype(int)

        # European trading hours (8:00 - 16:00 UTC)
        df['european_trading_hours'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)

        # Quarter hour within the day (0-95)
        df['quarter_of_day'] = df['hour'] * 4 + (df['epoch'] % 3600) // 900

        # Cyclic encoding of hour (to capture 23:00 close to 00:00)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

        # Cyclic encoding of day of week
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        return df

    def add_rolling_features(self, df: pd.DataFrame, windows: List[int] = [4, 8, 16, 32]) -> pd.DataFrame:
        """
        Add rolling statistics for each crypto.

        Args:
            windows: List of window sizes (in epochs). 4 = 1 hour, 8 = 2 hours, etc.
        """
        df = df.copy()

        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            crypto_df = df[mask].copy()

            for window in windows:
                # Rolling momentum (cumulative up direction)
                crypto_df[f'momentum_{window}'] = crypto_df['target'].rolling(window, min_periods=1).mean()

                # Rolling volatility (std of price changes)
                crypto_df[f'volatility_{window}'] = crypto_df['change_pct'].abs().rolling(window, min_periods=1).std()

                # Rolling average absolute change
                crypto_df[f'avg_abs_change_{window}'] = crypto_df['change_abs'].abs().rolling(window, min_periods=1).mean()

                # Rolling streak (consecutive ups or downs)
                # This is tricky - we'll use a custom function
                streak = []
                current_streak = 0
                for i, direction in enumerate(crypto_df['target']):
                    if i == 0:
                        current_streak = 1
                    elif direction == crypto_df['target'].iloc[i-1]:
                        current_streak += 1
                    else:
                        current_streak = 1
                    streak.append(current_streak)

                crypto_df[f'current_streak'] = streak
                crypto_df[f'avg_streak_{window}'] = crypto_df['current_streak'].rolling(window, min_periods=1).mean()

            # Update main dataframe
            df.loc[mask, crypto_df.columns] = crypto_df

        return df

    def add_cross_crypto_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features based on correlations between cryptos."""
        df = df.copy()

        # For each epoch, calculate how many cryptos went up
        epoch_summary = df.groupby('epoch').agg({
            'target': ['sum', 'mean'],
            'change_pct': ['mean', 'std']
        }).reset_index()

        epoch_summary.columns = ['epoch', 'num_ups', 'pct_ups', 'avg_change_pct', 'std_change_pct']

        # Merge back
        df = df.merge(epoch_summary, on='epoch', how='left')

        # Consensus direction (1 if 3+ cryptos went up, 0 otherwise)
        df['market_consensus_up'] = (df['num_ups'] >= 3).astype(int)

        # Market divergence (is this crypto going against the flow?)
        df['divergence'] = (df['target'] != df['market_consensus_up']).astype(int)

        return df

    def add_lag_features(self, df: pd.DataFrame, lags: List[int] = [1, 2, 4, 8]) -> pd.DataFrame:
        """
        Add lagged features (previous epoch outcomes).

        Args:
            lags: List of lag periods (in epochs)
        """
        df = df.copy()

        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            crypto_df = df[mask].copy()

            for lag in lags:
                # Previous direction
                crypto_df[f'prev_direction_{lag}'] = crypto_df['target'].shift(lag)

                # Previous change percent
                crypto_df[f'prev_change_pct_{lag}'] = crypto_df['change_pct'].shift(lag)

                # Previous absolute change
                crypto_df[f'prev_abs_change_{lag}'] = crypto_df['change_abs'].abs().shift(lag)

            # Update main dataframe
            df.loc[mask, crypto_df.columns] = crypto_df

        return df

    def add_market_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add market regime indicators (trending, choppy, volatile).
        """
        df = df.copy()

        for crypto in df['crypto'].unique():
            mask = df['crypto'] == crypto
            crypto_df = df[mask].copy()

            # 2-hour trend strength (16 epochs)
            window = 16
            crypto_df['trend_strength'] = crypto_df['target'].rolling(window, min_periods=1).mean()

            # Classify regime
            crypto_df['regime'] = 'neutral'
            crypto_df.loc[crypto_df['trend_strength'] > 0.65, 'regime'] = 'bullish'
            crypto_df.loc[crypto_df['trend_strength'] < 0.35, 'regime'] = 'bearish'

            # Volatility regime (high/low based on rolling std)
            vol_16 = crypto_df['change_pct'].abs().rolling(window, min_periods=1).std()
            vol_median = vol_16.median()

            crypto_df['high_volatility'] = (vol_16 > vol_median * 1.5).astype(int)
            crypto_df['low_volatility'] = (vol_16 < vol_median * 0.5).astype(int)

            # Choppy market (many direction changes)
            direction_changes = (crypto_df['target'].diff() != 0).rolling(window, min_periods=1).sum()
            crypto_df['choppy'] = (direction_changes > window * 0.6).astype(int)

            # Update main dataframe
            df.loc[mask, crypto_df.columns] = crypto_df

        return df

    def add_hourly_historical_stats(self, df: pd.DataFrame, lookback_days: int = 7) -> pd.DataFrame:
        """
        Add historical statistics for each hour (e.g., "hour 14 typically goes up 65% of time").
        """
        df = df.copy()

        for crypto in df['crypto'].unique():
            crypto_df = df[df['crypto'] == crypto].copy()

            # Calculate hourly up percentage for each hour across history
            hourly_stats = crypto_df.groupby('hour')['target'].agg(['mean', 'std', 'count']).reset_index()
            hourly_stats.columns = ['hour', 'hour_historical_up_pct', 'hour_historical_std', 'hour_count']

            # Merge back
            crypto_df = crypto_df.merge(hourly_stats, on='hour', how='left')

            # Update main dataframe
            df.loc[df['crypto'] == crypto, crypto_df.columns] = crypto_df

        return df

    def build_feature_matrix(self,
                            cryptos: List[str] = ['btc', 'eth', 'sol', 'xrp'],
                            include_rolling: bool = True,
                            include_cross_crypto: bool = True,
                            include_lags: bool = True,
                            include_regimes: bool = True,
                            include_hourly_stats: bool = True) -> pd.DataFrame:
        """
        Build complete feature matrix.

        Returns:
            DataFrame with all features and target variable.
        """
        print("Loading raw data...")
        df = self.load_raw_data(cryptos)
        print(f"  Loaded {len(df)} epochs across {len(cryptos)} cryptos")

        print("Adding temporal features...")
        df = self.add_temporal_features(df)

        if include_rolling:
            print("Adding rolling features...")
            df = self.add_rolling_features(df)

        if include_cross_crypto:
            print("Adding cross-crypto features...")
            df = self.add_cross_crypto_features(df)

        if include_lags:
            print("Adding lag features...")
            df = self.add_lag_features(df)

        if include_regimes:
            print("Adding market regime features...")
            df = self.add_market_regime_features(df)

        if include_hourly_stats:
            print("Adding hourly historical stats...")
            df = self.add_hourly_historical_stats(df)

        # Drop rows with NaN (from rolling/lag features)
        initial_len = len(df)
        df = df.dropna()
        print(f"Dropped {initial_len - len(df)} rows with missing values")

        print(f"Final feature matrix: {len(df)} rows × {len(df.columns)} columns")

        return df

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """
        Get list of feature columns (exclude metadata and target).
        """
        exclude_cols = [
            'crypto', 'epoch', 'date', 'datetime', 'direction',
            'start_price', 'end_price', 'change_pct', 'change_abs',
            'target', 'time_block', 'regime'  # categorical features to encode separately
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]
        return feature_cols


def main():
    """Demo feature engineering."""
    fe = FeatureEngineering()

    print("="*100)
    print("FEATURE ENGINEERING DEMO")
    print("="*100)
    print()

    # Build feature matrix
    df = fe.build_feature_matrix()

    print()
    print("="*100)
    print("FEATURE SUMMARY")
    print("="*100)
    print()

    feature_cols = fe.get_feature_columns(df)
    print(f"Total features: {len(feature_cols)}")
    print()

    print("Temporal features:")
    temporal = [c for c in feature_cols if any(x in c for x in ['hour', 'day', 'dow', 'time', 'trading'])]
    for col in temporal:
        print(f"  - {col}")

    print()
    print("Rolling features:")
    rolling = [c for c in feature_cols if any(x in c for x in ['momentum', 'volatility', 'streak', 'avg_'])]
    for col in rolling[:10]:  # Just show first 10
        print(f"  - {col}")
    if len(rolling) > 10:
        print(f"  ... and {len(rolling) - 10} more")

    print()
    print("Cross-crypto features:")
    cross = [c for c in feature_cols if any(x in c for x in ['num_ups', 'pct_ups', 'consensus', 'divergence', 'market'])]
    for col in cross:
        print(f"  - {col}")

    print()
    print("Lag features:")
    lag = [c for c in feature_cols if 'prev_' in c]
    for col in lag[:10]:
        print(f"  - {col}")
    if len(lag) > 10:
        print(f"  ... and {len(lag) - 10} more")

    print()
    print("Regime features:")
    regime = [c for c in feature_cols if any(x in c for x in ['trend', 'volatility', 'choppy'])]
    for col in regime:
        print(f"  - {col}")

    print()
    print("="*100)
    print("SAMPLE DATA (first 5 rows)")
    print("="*100)
    print()
    print(df[['crypto', 'datetime', 'hour', 'target', 'momentum_16', 'volatility_16', 'market_consensus_up', 'hour_historical_up_pct']].head())

    print()
    print("="*100)
    print("TARGET DISTRIBUTION")
    print("="*100)
    print()
    print(df.groupby('crypto')['target'].agg(['sum', 'count', 'mean']))

    # Save to CSV for further analysis
    output_path = Path('analysis/feature_matrix.csv')
    df.to_csv(output_path, index=False)
    print()
    print(f"Feature matrix saved to: {output_path}")
    print()


if __name__ == '__main__':
    main()
