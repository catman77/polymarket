#!/usr/bin/env python3
"""
Ensemble Learning and Model Stacking

Combines multiple models and signals:
- Voting classifiers (hard/soft voting)
- Stacking ensemble
- Blending models with time-of-day patterns
- Meta-learner approach
- Final production-ready predictor
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

from sklearn.ensemble import VotingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))

from ml_feature_engineering import FeatureEngineering
from ml_supervised_learning import EpochPredictor


class EnsemblePredictor:
    """Ensemble models for improved prediction accuracy."""

    def __init__(self, feature_matrix: pd.DataFrame = None):
        if feature_matrix is None:
            fe = FeatureEngineering()
            self.df = fe.build_feature_matrix()
        else:
            self.df = feature_matrix

        self.ensemble_models = {}
        self.scaler = None

    def prepare_data(self, crypto: str = None, test_size: float = 0.2) -> Tuple:
        """Prepare train/test split."""
        if crypto:
            df = self.df[self.df['crypto'] == crypto].copy()
        else:
            df = self.df.copy()

        df = df.sort_values('epoch')

        # Get features
        exclude_cols = [
            'crypto', 'epoch', 'date', 'datetime', 'direction',
            'start_price', 'end_price', 'change_pct', 'change_abs',
            'target', 'time_block', 'regime'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].values
        y = df['target'].values

        # Time-based split
        split_idx = int(len(X) * (1 - test_size))

        X_train = X[:split_idx]
        X_test = X[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]

        # Scale
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        self.scaler = scaler
        self.feature_names = feature_cols

        return X_train, X_test, y_train, y_test

    def train_voting_classifier(self, X_train, y_train, voting: str = 'soft') -> VotingClassifier:
        """
        Train voting ensemble.

        Args:
            voting: 'hard' (majority vote) or 'soft' (average probabilities)
        """
        print(f"Training Voting Classifier ({voting} voting)...")

        estimators = [
            ('lr', LogisticRegression(max_iter=1000, random_state=42)),
            ('rf', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1))
        ]

        if XGBOOST_AVAILABLE:
            estimators.append(('xgb', xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='logloss'
            )))

        voting_clf = VotingClassifier(
            estimators=estimators,
            voting=voting,
            n_jobs=-1
        )

        voting_clf.fit(X_train, y_train)
        self.ensemble_models['voting_' + voting] = voting_clf

        return voting_clf

    def train_stacking_classifier(self, X_train, y_train) -> StackingClassifier:
        """
        Train stacking ensemble.

        Base models: Logistic, Random Forest, XGBoost
        Meta-learner: Logistic Regression
        """
        print("Training Stacking Classifier...")

        estimators = [
            ('lr', LogisticRegression(max_iter=1000, random_state=42)),
            ('rf', RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1))
        ]

        if XGBOOST_AVAILABLE:
            estimators.append(('xgb', xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42,
                eval_metric='logloss'
            )))

        stacking_clf = StackingClassifier(
            estimators=estimators,
            final_estimator=LogisticRegression(max_iter=1000, random_state=42),
            cv=5,
            n_jobs=-1
        )

        stacking_clf.fit(X_train, y_train)
        self.ensemble_models['stacking'] = stacking_clf

        return stacking_clf

    def train_hourly_specialized_models(self, X_train, y_train,
                                       hourly_metadata: pd.Series) -> Dict:
        """
        Train separate models for different hours.

        Some hours may have very different patterns - specialize models.
        """
        print("Training Hourly Specialized Models...")

        hourly_models = {}

        # Group hours into blocks
        hour_blocks = {
            'night': list(range(0, 6)),
            'morning': list(range(6, 12)),
            'afternoon': list(range(12, 18)),
            'evening': list(range(18, 24))
        }

        for block_name, hours in hour_blocks.items():
            mask = hourly_metadata.isin(hours)
            X_block = X_train[mask]
            y_block = y_train[mask]

            if len(X_block) > 100:  # Minimum samples
                model = RandomForestClassifier(
                    n_estimators=100,
                    max_depth=8,
                    random_state=42,
                    n_jobs=-1
                )
                model.fit(X_block, y_block)
                hourly_models[block_name] = model

                print(f"  {block_name}: {len(X_block)} samples")

        self.ensemble_models['hourly_specialized'] = hourly_models

        return hourly_models

    def predict_with_hourly_models(self, X_test, hour_metadata: pd.Series) -> np.ndarray:
        """Make predictions using hourly specialized models."""
        if 'hourly_specialized' not in self.ensemble_models:
            print("Hourly models not trained.")
            return None

        hourly_models = self.ensemble_models['hourly_specialized']

        hour_blocks = {
            'night': list(range(0, 6)),
            'morning': list(range(6, 12)),
            'afternoon': list(range(12, 18)),
            'evening': list(range(18, 24))
        }

        y_pred = np.zeros(len(X_test))

        for block_name, hours in hour_blocks.items():
            if block_name not in hourly_models:
                continue

            mask = hour_metadata.isin(hours)
            if mask.sum() > 0:
                X_block = X_test[mask]
                y_pred[mask] = hourly_models[block_name].predict(X_block)

        return y_pred

    def blended_prediction(self, X_test, hour_metadata: pd.Series,
                          hourly_win_rates: pd.DataFrame) -> np.ndarray:
        """
        Blend ML predictions with historical hourly win rates.

        Uses weighted average:
        - 70% ML model prediction
        - 30% historical hourly bias
        """
        print("Creating blended predictions...")

        # Get ML predictions
        if 'voting_soft' in self.ensemble_models:
            ml_model = self.ensemble_models['voting_soft']
        elif 'stacking' in self.ensemble_models:
            ml_model = self.ensemble_models['stacking']
        else:
            print("No ensemble model available.")
            return None

        ml_proba = ml_model.predict_proba(X_test)[:, 1]

        # Get historical hourly biases
        hourly_bias = np.zeros(len(X_test))
        for i, hour in enumerate(hour_metadata):
            hour_data = hourly_win_rates[hourly_win_rates['hour'] == hour]
            if len(hour_data) > 0:
                hourly_bias[i] = hour_data.iloc[0]['win_rate'] / 100
            else:
                hourly_bias[i] = 0.5  # Default to 50%

        # Blend
        blended_proba = 0.7 * ml_proba + 0.3 * hourly_bias

        # Convert to binary predictions
        y_pred = (blended_proba >= 0.5).astype(int)

        return y_pred

    def evaluate_all_ensembles(self, X_test, y_test, hour_metadata: pd.Series = None):
        """Evaluate all ensemble models."""
        print()
        print("="*100)
        print("ENSEMBLE MODEL EVALUATION")
        print("="*100)
        print()

        results = {}

        for model_name, model in self.ensemble_models.items():
            if model_name == 'hourly_specialized':
                if hour_metadata is not None:
                    y_pred = self.predict_with_hourly_models(X_test, hour_metadata)
                    if y_pred is not None:
                        accuracy = accuracy_score(y_test, y_pred)
                        results[model_name] = accuracy
                        print(f"{model_name:<30} Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
            else:
                y_pred = model.predict(X_test)
                accuracy = accuracy_score(y_test, y_pred)
                results[model_name] = accuracy
                print(f"{model_name:<30} Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")

        print()

        return results


def main():
    """Main ensemble learning pipeline."""
    print("="*100)
    print("ENSEMBLE LEARNING - COMBINING MODELS")
    print("="*100)
    print()

    # Initialize
    ensemble = EnsemblePredictor()

    print(f"Total dataset: {len(ensemble.df)} epochs")
    print()

    # Prepare data
    X_train, X_test, y_train, y_test = ensemble.prepare_data(crypto=None, test_size=0.2)

    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print()

    # Get hour metadata for test set
    df_sorted = ensemble.df.sort_values('epoch')
    split_idx = int(len(df_sorted) * 0.8)
    test_hours = df_sorted.iloc[split_idx:]['hour'].reset_index(drop=True)

    # Train ensembles
    print("="*100)
    print("TRAINING ENSEMBLE MODELS")
    print("="*100)
    print()

    # 1. Voting classifier (hard)
    ensemble.train_voting_classifier(X_train, y_train, voting='hard')

    # 2. Voting classifier (soft)
    ensemble.train_voting_classifier(X_train, y_train, voting='soft')

    # 3. Stacking classifier
    ensemble.train_stacking_classifier(X_train, y_train)

    # 4. Hourly specialized models
    train_hours = df_sorted.iloc[:split_idx]['hour']
    ensemble.train_hourly_specialized_models(X_train, y_train, train_hours)

    print()

    # Evaluate all
    results = ensemble.evaluate_all_ensembles(X_test, y_test, hour_metadata=test_hours)

    # Find best model
    best_model = max(results.items(), key=lambda x: x[1])

    print()
    print("="*100)
    print("BEST MODEL")
    print("="*100)
    print()
    print(f"Model: {best_model[0]}")
    print(f"Accuracy: {best_model[1]:.4f} ({best_model[1]*100:.2f}%)")
    print()

    # Profitability analysis
    print("="*100)
    print("PROFITABILITY ANALYSIS")
    print("="*100)
    print()

    print("Break-even analysis:")
    print("-"*100)
    print("  Round-trip fees at 50% probability: ~6.3%")
    print("  Break-even win rate: ~53%")
    print()

    for model_name, accuracy in sorted(results.items(), key=lambda x: x[1], reverse=True):
        if accuracy > 0.53:
            edge = (accuracy - 0.53) * 100
            print(f"  {model_name:<30} Win rate: {accuracy*100:.2f}% | Edge: +{edge:.2f}% | PROFITABLE ✅")
        else:
            deficit = (0.53 - accuracy) * 100
            print(f"  {model_name:<30} Win rate: {accuracy*100:.2f}% | Deficit: -{deficit:.2f}% | UNPROFITABLE ❌")

    print()
    print("="*100)
    print("DEPLOYMENT RECOMMENDATIONS")
    print("="*100)
    print()

    print("1. MODEL SELECTION:")
    print(f"   - Deploy: {best_model[0]}")
    print(f"   - Expected win rate: {best_model[1]*100:.2f}%")
    print()

    print("2. INTEGRATION STRATEGY:")
    print("   - Use ensemble predictions as additional signal in bot")
    print("   - Combine with momentum/contrarian signals")
    print("   - Weight: 40% ML + 60% existing strategy")
    print()

    print("3. CONFIDENCE FILTERING:")
    print("   - Only trade when model confidence >70%")
    print("   - Use predict_proba() to get probability scores")
    print("   - Skip trades with uncertain predictions (45-55%)")
    print()

    print("4. CONTINUOUS LEARNING:")
    print("   - Retrain models weekly with new data")
    print("   - Monitor performance drift")
    print("   - A/B test new models before full deployment")
    print()

    print("5. RISK MANAGEMENT:")
    print("   - ML predictions can be wrong in regime changes")
    print("   - Don't override risk limits based on ML confidence")
    print("   - Use ML as filter, not as sole decision maker")
    print()


if __name__ == '__main__':
    main()
