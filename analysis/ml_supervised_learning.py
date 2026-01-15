#!/usr/bin/env python3
"""
Supervised Learning for Epoch Prediction

Trains binary classification models to predict Up/Down outcomes:
- Logistic Regression (baseline)
- Random Forest
- XGBoost
- Neural Network (MLP)

Includes walk-forward validation for time series.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
from datetime import datetime

# ML libraries
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from sklearn.neural_network import MLPClassifier
    MLP_AVAILABLE = True
except ImportError:
    MLP_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))

from ml_feature_engineering import FeatureEngineering


class EpochPredictor:
    """Supervised learning models for epoch outcome prediction."""

    def __init__(self, feature_matrix: pd.DataFrame = None):
        if feature_matrix is None:
            # Build feature matrix
            fe = FeatureEngineering()
            self.df = fe.build_feature_matrix()
        else:
            self.df = feature_matrix

        self.models = {}
        self.scalers = {}
        self.label_encoders = {}
        self.results = {}

    def prepare_data(self, crypto: str = None, test_size: float = 0.2) -> Tuple:
        """
        Prepare train/test split with proper time-based ordering.

        Args:
            crypto: If specified, train on single crypto. Otherwise, train on all.
            test_size: Proportion of data to use for testing (most recent data)

        Returns:
            X_train, X_test, y_train, y_test
        """
        if crypto:
            df = self.df[self.df['crypto'] == crypto].copy()
        else:
            df = self.df.copy()

        # Sort by time
        df = df.sort_values('epoch')

        # Encode categorical features
        if 'time_block' in df.columns:
            le_time_block = LabelEncoder()
            df['time_block_encoded'] = le_time_block.fit_transform(df['time_block'].astype(str))
            self.label_encoders['time_block'] = le_time_block

        if 'regime' in df.columns:
            le_regime = LabelEncoder()
            df['regime_encoded'] = le_regime.fit_transform(df['regime'].astype(str))
            self.label_encoders['regime'] = le_regime

        # Get feature columns
        exclude_cols = [
            'crypto', 'epoch', 'date', 'datetime', 'direction',
            'start_price', 'end_price', 'change_pct', 'change_abs',
            'target', 'time_block', 'regime'
        ]

        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].values
        y = df['target'].values

        # Time-based split (no shuffling!)
        split_idx = int(len(X) * (1 - test_size))

        X_train = X[:split_idx]
        X_test = X[split_idx:]
        y_train = y[:split_idx]
        y_test = y[split_idx:]

        # Scale features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        self.scalers['standard'] = scaler
        self.feature_names = feature_cols

        return X_train, X_test, y_train, y_test

    def train_logistic_regression(self, X_train, y_train, **kwargs) -> LogisticRegression:
        """Train logistic regression baseline."""
        print("Training Logistic Regression...")

        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            **kwargs
        )

        model.fit(X_train, y_train)
        self.models['logistic'] = model

        return model

    def train_random_forest(self, X_train, y_train, **kwargs) -> RandomForestClassifier:
        """Train random forest classifier."""
        print("Training Random Forest...")

        model = RandomForestClassifier(
            n_estimators=kwargs.get('n_estimators', 100),
            max_depth=kwargs.get('max_depth', 10),
            min_samples_split=kwargs.get('min_samples_split', 20),
            min_samples_leaf=kwargs.get('min_samples_leaf', 10),
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)
        self.models['random_forest'] = model

        return model

    def train_xgboost(self, X_train, y_train, **kwargs):
        """Train XGBoost classifier."""
        if not XGBOOST_AVAILABLE:
            print("XGBoost not installed. Skipping.")
            return None

        print("Training XGBoost...")

        model = xgb.XGBClassifier(
            n_estimators=kwargs.get('n_estimators', 100),
            max_depth=kwargs.get('max_depth', 6),
            learning_rate=kwargs.get('learning_rate', 0.1),
            subsample=kwargs.get('subsample', 0.8),
            colsample_bytree=kwargs.get('colsample_bytree', 0.8),
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss'
        )

        model.fit(X_train, y_train)
        self.models['xgboost'] = model

        return model

    def train_neural_network(self, X_train, y_train, **kwargs):
        """Train neural network (MLP)."""
        if not MLP_AVAILABLE:
            print("MLPClassifier not available. Skipping.")
            return None

        print("Training Neural Network...")

        model = MLPClassifier(
            hidden_layer_sizes=kwargs.get('hidden_layers', (100, 50)),
            activation=kwargs.get('activation', 'relu'),
            solver=kwargs.get('solver', 'adam'),
            alpha=kwargs.get('alpha', 0.0001),
            batch_size=kwargs.get('batch_size', 64),
            learning_rate=kwargs.get('learning_rate', 'adaptive'),
            max_iter=kwargs.get('max_iter', 500),
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=10
        )

        model.fit(X_train, y_train)
        self.models['neural_network'] = model

        return model

    def train_all_models(self, X_train, y_train):
        """Train all available models."""
        self.train_logistic_regression(X_train, y_train)
        self.train_random_forest(X_train, y_train)

        if XGBOOST_AVAILABLE:
            self.train_xgboost(X_train, y_train)

        if MLP_AVAILABLE:
            self.train_neural_network(X_train, y_train)

    def evaluate_model(self, model_name: str, X_test, y_test) -> Dict:
        """Evaluate a trained model."""
        if model_name not in self.models:
            print(f"Model {model_name} not found.")
            return {}

        model = self.models[model_name]
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None

        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0),
        }

        if y_pred_proba is not None:
            results['roc_auc'] = roc_auc_score(y_test, y_pred_proba)

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)
        results['confusion_matrix'] = cm

        # Trading metrics (win rate)
        results['win_rate'] = accuracy_score(y_test, y_pred) * 100

        self.results[model_name] = results

        return results

    def print_results(self):
        """Print formatted results for all models."""
        print("="*100)
        print("MODEL PERFORMANCE COMPARISON")
        print("="*100)
        print()

        print(f"{'Model':<20} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1':<12} {'ROC-AUC':<12} {'Win Rate':<12}")
        print("-"*100)

        for model_name, results in sorted(self.results.items()):
            print(f"{model_name:<20} "
                  f"{results['accuracy']:<12.4f} "
                  f"{results['precision']:<12.4f} "
                  f"{results['recall']:<12.4f} "
                  f"{results['f1']:<12.4f} "
                  f"{results.get('roc_auc', 0):<12.4f} "
                  f"{results['win_rate']:<11.2f}%")

        print()
        print("="*100)

    def feature_importance(self, model_name: str = 'random_forest', top_n: int = 20):
        """Print feature importance for tree-based models."""
        if model_name not in self.models:
            print(f"Model {model_name} not found.")
            return

        model = self.models[model_name]

        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:top_n]

            print()
            print(f"TOP {top_n} FEATURES - {model_name.upper()}")
            print("-"*60)

            for i, idx in enumerate(indices, 1):
                print(f"{i:2d}. {self.feature_names[idx]:<40} {importances[idx]:.6f}")

        elif model_name == 'logistic' and hasattr(model, 'coef_'):
            # For logistic regression, show coefficients
            coefs = np.abs(model.coef_[0])
            indices = np.argsort(coefs)[::-1][:top_n]

            print()
            print(f"TOP {top_n} FEATURES - LOGISTIC REGRESSION (abs coef)")
            print("-"*60)

            for i, idx in enumerate(indices, 1):
                print(f"{i:2d}. {self.feature_names[idx]:<40} {coefs[idx]:.6f}")

        else:
            print(f"Feature importance not available for {model_name}")

    def walk_forward_validation(self, n_splits: int = 5, crypto: str = None):
        """
        Perform walk-forward (time series) cross-validation.

        This is critical for time series data to avoid look-ahead bias.
        """
        print()
        print("="*100)
        print(f"WALK-FORWARD VALIDATION ({n_splits} splits)")
        print("="*100)
        print()

        if crypto:
            df = self.df[self.df['crypto'] == crypto].copy()
        else:
            df = self.df.copy()

        df = df.sort_values('epoch')

        # Prepare features
        exclude_cols = [
            'crypto', 'epoch', 'date', 'datetime', 'direction',
            'start_price', 'end_price', 'change_pct', 'change_abs',
            'target', 'time_block', 'regime'
        ]
        feature_cols = [col for col in df.columns if col not in exclude_cols]

        X = df[feature_cols].values
        y = df['target'].values

        # Time series split
        tscv = TimeSeriesSplit(n_splits=n_splits)

        cv_results = {model_name: [] for model_name in ['logistic', 'random_forest']}

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            print(f"Fold {fold}/{n_splits}")

            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Scale
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

            # Train models
            lr = LogisticRegression(max_iter=1000, random_state=42)
            lr.fit(X_train, y_train)
            lr_acc = accuracy_score(y_test, lr.predict(X_test))
            cv_results['logistic'].append(lr_acc)

            rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
            rf.fit(X_train, y_train)
            rf_acc = accuracy_score(y_test, rf.predict(X_test))
            cv_results['random_forest'].append(rf_acc)

            print(f"  Logistic: {lr_acc:.4f} | Random Forest: {rf_acc:.4f}")

        print()
        print("CROSS-VALIDATION SUMMARY")
        print("-"*60)

        for model_name, scores in cv_results.items():
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            print(f"{model_name:<20} {mean_score:.4f} ± {std_score:.4f}")

        print()

        return cv_results


def main():
    """Main training pipeline."""
    print("="*100)
    print("SUPERVISED LEARNING - EPOCH PREDICTION")
    print("="*100)
    print()

    # Initialize predictor
    predictor = EpochPredictor()

    print(f"Total dataset: {len(predictor.df)} epochs")
    print(f"Cryptos: {predictor.df['crypto'].unique()}")
    print()

    # Prepare data
    X_train, X_test, y_train, y_test = predictor.prepare_data(crypto=None, test_size=0.2)

    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Features: {len(predictor.feature_names)}")
    print()

    # Train all models
    predictor.train_all_models(X_train, y_train)

    # Evaluate all models
    print()
    print("Evaluating models on test set...")
    print()

    for model_name in predictor.models.keys():
        predictor.evaluate_model(model_name, X_test, y_test)

    # Print results
    predictor.print_results()

    # Feature importance
    predictor.feature_importance('random_forest', top_n=20)
    predictor.feature_importance('logistic', top_n=20)

    if XGBOOST_AVAILABLE and 'xgboost' in predictor.models:
        predictor.feature_importance('xgboost', top_n=20)

    # Walk-forward validation
    predictor.walk_forward_validation(n_splits=5)

    print()
    print("="*100)
    print("ANALYSIS COMPLETE")
    print("="*100)
    print()

    print("INTERPRETATION:")
    print("-"*100)
    print("1. Accuracy > 0.53: Better than random (accounting for 6.3% fees)")
    print("2. Win Rate > 60%: Profitable after fees")
    print("3. ROC-AUC > 0.60: Model has predictive power")
    print("4. Feature importance: Shows which patterns matter most")
    print()


if __name__ == '__main__':
    main()
