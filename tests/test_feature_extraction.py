#!/usr/bin/env python3
"""
Unit tests for Feature Extraction Pipeline
"""

import unittest
import sqlite3
import tempfile
import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.feature_extraction import FeatureExtractor, FeatureConfig


class TestFeatureExtraction(unittest.TestCase):
    """Test cases for FeatureExtractor."""

    def setUp(self):
        """Create temporary database with test epoch data."""
        self.temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Create database schema
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE epoch_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crypto TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                date TEXT NOT NULL,
                hour INTEGER NOT NULL,
                direction TEXT NOT NULL,
                start_price REAL NOT NULL,
                end_price REAL NOT NULL,
                change_pct REAL NOT NULL,
                change_abs REAL NOT NULL,
                timestamp REAL NOT NULL,
                UNIQUE(crypto, epoch)
            )
        ''')

        # Insert test data (100 epochs across 4 cryptos)
        base_timestamp = datetime(2026, 1, 7, 8, 0, 0).timestamp()
        test_data = []

        for i in range(100):
            crypto = ['btc', 'eth', 'sol', 'xrp'][i % 4]
            ts = base_timestamp + (i * 900)  # 15-minute intervals
            dt = datetime.fromtimestamp(ts)
            date = dt.strftime('%Y-%m-%d')
            hour = dt.hour

            # Simulate prices with trend + noise
            base_prices = {'btc': 40000, 'eth': 3000, 'sol': 100, 'xrp': 0.5}
            base = base_prices[crypto]
            start_price = base + (i * 10) + np.random.randn() * 50
            change_pct = np.random.randn() * 0.5  # ±0.5%
            end_price = start_price * (1 + change_pct / 100)
            change_abs = end_price - start_price
            direction = 'Up' if change_pct > 0 else 'Down'

            test_data.append((
                crypto,
                int(ts),
                date,
                hour,
                direction,
                start_price,
                end_price,
                change_pct,
                change_abs,
                ts
            ))

        conn.executemany('''
            INSERT INTO epoch_outcomes
            (crypto, epoch, date, hour, direction, start_price, end_price, change_pct, change_abs, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', test_data)

        conn.commit()
        conn.close()

        # Create config
        self.config = FeatureConfig(
            epoch_db_path=self.db_path,
            include_cross_asset=True
        )

        self.extractor = FeatureExtractor(self.config)

    def tearDown(self):
        """Clean up temporary database."""
        self.extractor.close()
        os.unlink(self.db_path)

    def test_extract_all_epochs(self):
        """Test extracting all epochs from database."""
        df = self.extractor.extract_all_epochs()

        self.assertEqual(len(df), 100)
        self.assertIn('crypto', df.columns)
        self.assertIn('epoch', df.columns)
        self.assertIn('direction', df.columns)
        self.assertEqual(set(df['crypto'].unique()), {'btc', 'eth', 'sol', 'xrp'})

    def test_add_time_features(self):
        """Test time feature extraction."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_time_features(df)

        # Check features exist
        self.assertIn('hour', df.columns)
        self.assertIn('day_of_week', df.columns)
        self.assertIn('minute_in_session', df.columns)
        self.assertIn('epoch_sequence', df.columns)
        self.assertIn('is_market_open', df.columns)

        # Validate values
        self.assertTrue((df['hour'] >= 0).all() and (df['hour'] < 24).all())
        self.assertTrue((df['day_of_week'] >= 0).all() and (df['day_of_week'] <= 6).all())
        self.assertTrue((df['minute_in_session'] >= 0).all() and (df['minute_in_session'] < 1440).all())
        self.assertTrue((df['is_market_open'].isin([0, 1])).all())

    def test_add_price_features(self):
        """Test price feature extraction."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_time_features(df)
        df = self.extractor.add_price_features(df)

        # Check features exist
        self.assertIn('rsi', df.columns)
        self.assertIn('volatility', df.columns)
        self.assertIn('price_momentum', df.columns)
        self.assertIn('spread_proxy', df.columns)
        self.assertIn('position_in_range', df.columns)
        self.assertIn('price_z_score', df.columns)

        # Validate RSI range (0-100)
        rsi_valid = df['rsi'].dropna()
        self.assertTrue((rsi_valid >= 0).all() and (rsi_valid <= 100).all())

        # Validate position_in_range (0-1)
        pos_valid = df['position_in_range'].dropna()
        self.assertTrue((pos_valid >= 0).all() and (pos_valid <= 1).all())

    def test_add_cross_asset_features(self):
        """Test cross-asset feature extraction."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_time_features(df)
        df = self.extractor.add_price_features(df)
        df = self.extractor.add_cross_asset_features(df)

        # Check features exist
        self.assertIn('btc_correlation', df.columns)
        self.assertIn('multi_crypto_agreement', df.columns)
        self.assertIn('market_wide_direction', df.columns)

        # Validate correlation range (-1 to 1)
        corr_valid = df['btc_correlation'].dropna()
        self.assertTrue((corr_valid >= -1).all() and (corr_valid <= 1).all())

        # Validate agreement range (0-1)
        agreement_valid = df['multi_crypto_agreement'].dropna()
        self.assertTrue((agreement_valid >= 0).all() and (agreement_valid <= 1).all())

        # Validate market direction (-1, 0, 1)
        self.assertTrue(df['market_wide_direction'].isin([-1, 0, 1]).all())

    def test_add_target_label(self):
        """Test target label creation."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_target_label(df)

        self.assertIn('target', df.columns)
        self.assertTrue((df['target'].isin([0, 1])).all())

        # Check consistency with direction
        up_mask = df['direction'] == 'Up'
        self.assertTrue((df.loc[up_mask, 'target'] == 1).all())

        down_mask = df['direction'] == 'Down'
        self.assertTrue((df.loc[down_mask, 'target'] == 0).all())

    def test_create_train_val_test_split(self):
        """Test time-based data splitting."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_time_features(df)
        df = self.extractor.add_target_label(df)

        train, val, test = self.extractor.create_train_val_test_split(
            df, train_pct=0.70, val_pct=0.15, test_pct=0.15
        )

        # Check splits exist
        self.assertGreater(len(train), 0)
        self.assertGreater(len(val), 0)
        self.assertGreater(len(test), 0)

        # Check total equals original
        self.assertEqual(len(train) + len(val) + len(test), len(df))

        # Check time ordering (train < val < test)
        self.assertLess(train['timestamp'].max(), val['timestamp'].min())
        self.assertLess(val['timestamp'].max(), test['timestamp'].min())

    def test_get_feature_columns(self):
        """Test feature column extraction."""
        df = self.extractor.extract_all_epochs()
        df = self.extractor.add_time_features(df)
        df = self.extractor.add_price_features(df)
        df = self.extractor.add_target_label(df)

        features = self.extractor.get_feature_columns(df)

        # Check metadata is excluded
        metadata = ['id', 'crypto', 'epoch', 'date', 'direction', 'timestamp', 'target']
        for col in metadata:
            self.assertNotIn(col, features)

        # Check features are included
        expected_features = ['hour', 'rsi', 'volatility', 'price_momentum']
        for feat in expected_features:
            self.assertIn(feat, features)

    def test_full_pipeline(self):
        """Test end-to-end feature extraction pipeline."""
        df = self.extractor.extract_all_features()

        # Check output structure
        self.assertGreater(len(df), 0)
        self.assertIn('target', df.columns)

        # Check features
        features = self.extractor.get_feature_columns(df)
        self.assertGreater(len(features), 10)  # At least 10 features

        # Check no NaN in features (dropped during extraction)
        feature_data = df[features]
        self.assertEqual(feature_data.isna().sum().sum(), 0)

    def test_save_features(self):
        """Test saving features to CSV."""
        df = self.extractor.extract_all_features()

        # Create temp output file
        temp_csv = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv')
        temp_csv.close()

        try:
            self.extractor.save_features(df, temp_csv.name)

            # Check file exists
            self.assertTrue(Path(temp_csv.name).exists())

            # Load and verify
            loaded_df = pd.read_csv(temp_csv.name)
            self.assertEqual(len(loaded_df), len(df))
            self.assertEqual(set(loaded_df.columns), set(df.columns))

        finally:
            os.unlink(temp_csv.name)

    def test_no_cross_asset_features(self):
        """Test disabling cross-asset features."""
        config = FeatureConfig(
            epoch_db_path=self.db_path,
            include_cross_asset=False
        )
        extractor = FeatureExtractor(config)

        try:
            df = extractor.extract_all_epochs()
            df = extractor.add_time_features(df)
            df = extractor.add_price_features(df)
            df = extractor.add_cross_asset_features(df)

            # Cross-asset features should not be added
            self.assertNotIn('btc_correlation', df.columns)
            self.assertNotIn('multi_crypto_agreement', df.columns)

        finally:
            extractor.close()

    def test_feature_count(self):
        """Test that we extract at least 14+ features."""
        df = self.extractor.extract_all_features()
        features = self.extractor.get_feature_columns(df)

        # Should have at least 14 features (time + price + cross-asset)
        self.assertGreaterEqual(len(features), 14)


if __name__ == '__main__':
    unittest.main()
