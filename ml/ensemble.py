#!/usr/bin/env python3
"""
Ensemble Predictor - Combines multiple ML models for improved predictions

Combines XGBoost, Random Forest, and Logistic Regression models using:
1. Soft voting (average predicted probabilities)
2. Weighted voting (weight models by validation performance)
3. Majority voting (simple vote count)

The ensemble approach reduces overfitting and improves generalization by
combining predictions from diverse models.
"""

import os
import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ModelInfo:
    """Information about a trained model"""
    name: str
    model_path: str
    scaler_path: Optional[str]  # Only for Logistic Regression
    weight: float  # Model weight based on validation accuracy
    accuracy: float
    roc_auc: float


@dataclass
class EnsemblePrediction:
    """Ensemble prediction with model breakdown"""
    direction: str  # "Up" or "Down"
    probability: float  # Ensemble probability (0-1)
    confidence: float  # Ensemble confidence (0-1)
    model_predictions: Dict[str, Dict]  # Per-model predictions
    voting_method: str  # "soft", "weighted", or "majority"


class EnsemblePredictor:
    """
    Ensemble predictor combining multiple ML models

    Supports three voting methods:
    1. Soft voting: Average predicted probabilities (recommended)
    2. Weighted voting: Weight models by validation accuracy
    3. Majority voting: Simple vote count (ties broken by soft voting)

    Example:
        ensemble = EnsemblePredictor()
        ensemble.load_models()
        prediction = ensemble.predict(features, method='soft')
        print(f"{prediction.direction} with {prediction.probability:.1%} probability")
    """

    def __init__(self, models_dir: str = 'ml/models'):
        """
        Initialize ensemble predictor

        Args:
            models_dir: Directory containing trained models
        """
        self.models_dir = Path(models_dir)
        self.models: Dict[str, any] = {}
        self.scalers: Dict[str, any] = {}
        self.model_info: Dict[str, ModelInfo] = {}

    def load_models(self) -> None:
        """
        Load all available models from models directory

        Looks for:
        - xgboost_model.pkl + xgboost_results.json
        - random_forest_model.pkl + random_forest_results.json
        - logistic_model.pkl + logistic_scaler.pkl + logistic_results.json

        Raises:
            FileNotFoundError: If models directory doesn't exist
            ValueError: If no models found
        """
        if not self.models_dir.exists():
            raise FileNotFoundError(f"Models directory not found: {self.models_dir}")

        # Try to load XGBoost
        self._load_model('xgboost', 'xgboost_model.pkl', 'xgboost_results.json')

        # Try to load Random Forest
        self._load_model('random_forest', 'random_forest_model.pkl', 'random_forest_results.json')

        # Try to load Logistic Regression (with scaler)
        self._load_model('logistic', 'logistic_model.pkl', 'logistic_results.json', 'logistic_scaler.pkl')

        if not self.models:
            raise ValueError("No models found - train models first with model_training.py")

        print(f"✅ Loaded {len(self.models)} models: {', '.join(self.models.keys())}")

    def _load_model(self, name: str, model_file: str, results_file: str, scaler_file: Optional[str] = None) -> None:
        """Load a single model with its metadata"""
        model_path = self.models_dir / model_file
        results_path = self.models_dir / results_file

        if not model_path.exists() or not results_path.exists():
            print(f"⚠️  Skipping {name}: files not found")
            return

        try:
            # Load model
            with open(model_path, 'rb') as f:
                model = pickle.load(f)

            # Load scaler if specified (Logistic Regression)
            scaler = None
            if scaler_file:
                scaler_path = self.models_dir / scaler_file
                if scaler_path.exists():
                    with open(scaler_path, 'rb') as f:
                        scaler = pickle.load(f)
                    self.scalers[name] = scaler

            # Load results metadata
            import json
            with open(results_path, 'r') as f:
                results = json.load(f)

            # Store model
            self.models[name] = model

            # Store model info
            self.model_info[name] = ModelInfo(
                name=name,
                model_path=str(model_path),
                scaler_path=str(self.models_dir / scaler_file) if scaler_file else None,
                weight=results.get('avg_accuracy', 0.5),  # Use accuracy as weight
                accuracy=results.get('avg_accuracy', 0.5),
                roc_auc=results.get('avg_roc_auc', 0.5)
            )

            print(f"  ✓ {name}: {results.get('avg_accuracy', 0)*100:.1f}% accuracy, {results.get('avg_roc_auc', 0):.3f} AUC")

        except Exception as e:
            print(f"⚠️  Failed to load {name}: {e}")

    def predict(
        self,
        features: np.ndarray,
        method: str = 'soft',
        min_confidence: float = 0.60
    ) -> EnsemblePrediction:
        """
        Make ensemble prediction from feature vector

        Args:
            features: Feature vector (numpy array, shape (14,) or (n, 14))
            method: Voting method ('soft', 'weighted', 'majority')
            min_confidence: Minimum confidence threshold (default 0.60)

        Returns:
            EnsemblePrediction with direction, probability, confidence, breakdown

        Example:
            features = np.array([...])  # 14 features
            pred = ensemble.predict(features, method='soft')
            if pred.confidence >= 0.60:
                print(f"Trade {pred.direction} with {pred.probability:.1%} probability")
        """
        if not self.models:
            raise ValueError("No models loaded - call load_models() first")

        # Ensure features is 2D (n_samples, n_features)
        if features.ndim == 1:
            features = features.reshape(1, -1)

        # Collect predictions from all models
        model_preds = {}

        for name, model in self.models.items():
            try:
                # Apply scaler if needed (Logistic Regression)
                X = features
                if name in self.scalers:
                    X = self.scalers[name].transform(features)

                # Get probability predictions
                proba = model.predict_proba(X)[0]  # [P(Down), P(Up)]
                pred_class = model.predict(X)[0]  # 0 or 1

                model_preds[name] = {
                    'proba_down': proba[0],
                    'proba_up': proba[1],
                    'prediction': int(pred_class),
                    'direction': 'Up' if pred_class == 1 else 'Down',
                    'confidence': max(proba),  # Confidence = max probability
                    'weight': self.model_info[name].weight
                }
            except Exception as e:
                print(f"⚠️  Model {name} prediction failed: {e}")
                # Skip failed model
                continue

        if not model_preds:
            raise ValueError("All models failed to predict")

        # Ensemble voting
        if method == 'soft':
            direction, probability = self._soft_voting(model_preds)
        elif method == 'weighted':
            direction, probability = self._weighted_voting(model_preds)
        elif method == 'majority':
            direction, probability = self._majority_voting(model_preds)
        else:
            raise ValueError(f"Unknown voting method: {method}")

        # Calculate ensemble confidence
        confidence = abs(probability - 0.5) * 2  # Scale [0.5, 1.0] -> [0, 1]

        return EnsemblePrediction(
            direction=direction,
            probability=probability,
            confidence=confidence,
            model_predictions=model_preds,
            voting_method=method
        )

    def _soft_voting(self, model_preds: Dict) -> Tuple[str, float]:
        """
        Soft voting: Average predicted probabilities

        Most robust method - uses full probability distribution
        """
        avg_up_prob = np.mean([p['proba_up'] for p in model_preds.values()])
        avg_down_prob = 1 - avg_up_prob

        direction = 'Up' if avg_up_prob > 0.5 else 'Down'
        probability = max(avg_up_prob, avg_down_prob)

        return direction, probability

    def _weighted_voting(self, model_preds: Dict) -> Tuple[str, float]:
        """
        Weighted voting: Weight models by validation accuracy

        Gives more influence to better-performing models
        """
        total_weight = sum(p['weight'] for p in model_preds.values())

        weighted_up_prob = sum(
            p['proba_up'] * p['weight']
            for p in model_preds.values()
        ) / total_weight

        weighted_down_prob = 1 - weighted_up_prob

        direction = 'Up' if weighted_up_prob > 0.5 else 'Down'
        probability = max(weighted_up_prob, weighted_down_prob)

        return direction, probability

    def _majority_voting(self, model_preds: Dict) -> Tuple[str, float]:
        """
        Majority voting: Simple vote count (ties broken by soft voting)

        Least sophisticated but interpretable
        """
        up_votes = sum(1 for p in model_preds.values() if p['direction'] == 'Up')
        down_votes = len(model_preds) - up_votes

        if up_votes > down_votes:
            direction = 'Up'
            probability = up_votes / len(model_preds)
        elif down_votes > up_votes:
            direction = 'Down'
            probability = down_votes / len(model_preds)
        else:
            # Tie: fall back to soft voting
            return self._soft_voting(model_preds)

        return direction, probability

    def predict_batch(
        self,
        features_batch: np.ndarray,
        method: str = 'soft'
    ) -> List[EnsemblePrediction]:
        """
        Make predictions for a batch of feature vectors

        Args:
            features_batch: Feature matrix (n_samples, n_features)
            method: Voting method

        Returns:
            List of EnsemblePrediction objects
        """
        predictions = []
        for features in features_batch:
            pred = self.predict(features, method=method)
            predictions.append(pred)
        return predictions

    def get_model_summary(self) -> Dict:
        """
        Get summary of loaded models

        Returns:
            Dictionary with model names, accuracies, weights
        """
        return {
            name: {
                'accuracy': info.accuracy,
                'roc_auc': info.roc_auc,
                'weight': info.weight
            }
            for name, info in self.model_info.items()
        }

    def compare_voting_methods(self, features: np.ndarray) -> Dict:
        """
        Compare all voting methods for a single prediction

        Args:
            features: Feature vector (14 features)

        Returns:
            Dictionary with predictions from each method
        """
        results = {}
        for method in ['soft', 'weighted', 'majority']:
            pred = self.predict(features, method=method)
            results[method] = {
                'direction': pred.direction,
                'probability': pred.probability,
                'confidence': pred.confidence
            }
        return results


def main():
    """
    CLI tool for testing ensemble predictor

    Usage:
        python3 ml/ensemble.py
        python3 ml/ensemble.py --test-features ml/features.csv
    """
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser(description='Ensemble Predictor')
    parser.add_argument('--models-dir', default='ml/models', help='Models directory')
    parser.add_argument('--test-features', help='Test features CSV (optional)')
    parser.add_argument('--method', default='soft', choices=['soft', 'weighted', 'majority'], help='Voting method')

    args = parser.parse_args()

    # Initialize ensemble
    print("🚀 Initializing Ensemble Predictor...")
    ensemble = EnsemblePredictor(models_dir=args.models_dir)
    ensemble.load_models()

    print("\n📊 Model Summary:")
    summary = ensemble.get_model_summary()
    for name, info in summary.items():
        print(f"  {name}:")
        print(f"    Accuracy: {info['accuracy']*100:.2f}%")
        print(f"    ROC AUC: {info['roc_auc']:.3f}")
        print(f"    Weight: {info['weight']:.3f}")

    # Test predictions if CSV provided
    if args.test_features:
        print(f"\n🔍 Testing on {args.test_features}...")
        df = pd.read_csv(args.test_features)

        # Extract features (exclude metadata)
        exclude_cols = ['id', 'crypto', 'epoch', 'date', 'direction', 'target',
                       'timestamp', 'dt', 'start_price', 'end_price', 'change_pct', 'change_abs']
        feature_cols = [c for c in df.columns if c not in exclude_cols]

        X_test = df[feature_cols].values
        y_test = df['target'].values if 'target' in df.columns else None

        # Predict first 5 samples
        print(f"\n📈 Sample Predictions (method={args.method}):")
        for i in range(min(5, len(X_test))):
            pred = ensemble.predict(X_test[i], method=args.method)
            actual = f"(Actual: {'Up' if y_test[i] == 1 else 'Down'})" if y_test is not None else ""
            print(f"\n  Sample {i+1}: {pred.direction} @ {pred.probability:.1%} confidence {actual}")
            for model, info in pred.model_predictions.items():
                print(f"    {model}: {info['direction']} ({info['proba_up']:.1%} Up, {info['proba_down']:.1%} Down)")

        # Batch prediction accuracy
        if y_test is not None:
            predictions = ensemble.predict_batch(X_test, method=args.method)
            y_pred = np.array([1 if p.direction == 'Up' else 0 for p in predictions])
            accuracy = (y_pred == y_test).mean()
            print(f"\n✅ Ensemble Accuracy ({args.method} voting): {accuracy*100:.2f}%")

    else:
        print("\n💡 To test predictions, provide --test-features ml/features.csv")


if __name__ == '__main__':
    main()
