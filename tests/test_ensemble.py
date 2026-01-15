#!/usr/bin/env python3
"""
Tests for Ensemble Predictor

Tests ensemble voting methods, model loading, and predictions.
"""

import unittest
import numpy as np
import pickle
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ml.ensemble import EnsemblePredictor, EnsemblePrediction, ModelInfo


class TestModelInfo(unittest.TestCase):
    """Test ModelInfo dataclass"""

    def test_model_info_creation(self):
        """Test creating ModelInfo instance"""
        info = ModelInfo(
            name='xgboost',
            model_path='ml/models/xgboost_model.pkl',
            scaler_path=None,
            weight=0.95,
            accuracy=0.95,
            roc_auc=0.98
        )
        self.assertEqual(info.name, 'xgboost')
        self.assertEqual(info.weight, 0.95)
        self.assertIsNone(info.scaler_path)


class TestEnsemblePrediction(unittest.TestCase):
    """Test EnsemblePrediction dataclass"""

    def test_prediction_creation(self):
        """Test creating prediction result"""
        pred = EnsemblePrediction(
            direction='Up',
            probability=0.75,
            confidence=0.50,
            model_predictions={
                'xgboost': {'direction': 'Up', 'proba_up': 0.80},
                'random_forest': {'direction': 'Up', 'proba_up': 0.70}
            },
            voting_method='soft'
        )
        self.assertEqual(pred.direction, 'Up')
        self.assertEqual(pred.probability, 0.75)
        self.assertEqual(pred.voting_method, 'soft')
        self.assertEqual(len(pred.model_predictions), 2)


class TestEnsemblePredictor(unittest.TestCase):
    """Test EnsemblePredictor class"""

    def setUp(self):
        """Set up test fixtures"""
        self.models_dir = Path('tests/fixtures/models')
        self.ensemble = EnsemblePredictor(models_dir=str(self.models_dir))

    def test_init(self):
        """Test ensemble initialization"""
        self.assertEqual(self.ensemble.models_dir, self.models_dir)
        self.assertEqual(len(self.ensemble.models), 0)
        self.assertEqual(len(self.ensemble.scalers), 0)
        self.assertEqual(len(self.ensemble.model_info), 0)

    def test_load_models_missing_directory(self):
        """Test loading models from non-existent directory"""
        ensemble = EnsemblePredictor(models_dir='nonexistent')
        with self.assertRaises(FileNotFoundError):
            ensemble.load_models()

    @patch('ml.ensemble.Path.exists')
    @patch('builtins.open')
    @patch('pickle.load')
    def test_load_single_model(self, mock_pickle, mock_open, mock_exists):
        """Test loading a single model"""
        # Mock file existence
        mock_exists.return_value = True

        # Mock model
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.4, 0.6]]))
        mock_model.predict = Mock(return_value=np.array([1]))

        # Mock results
        mock_results = {
            'avg_accuracy': 0.95,
            'avg_roc_auc': 0.98
        }

        # Setup pickle.load to return model and results
        def pickle_side_effect(*args, **kwargs):
            return mock_model

        mock_pickle.side_effect = pickle_side_effect

        # Setup json.load
        with patch('json.load', return_value=mock_results):
            # Create mock file handle
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            # Load model
            self.ensemble._load_model('xgboost', 'xgboost_model.pkl', 'xgboost_results.json')

            # Verify model loaded
            self.assertIn('xgboost', self.ensemble.models)
            self.assertIn('xgboost', self.ensemble.model_info)
            self.assertEqual(self.ensemble.model_info['xgboost'].accuracy, 0.95)

    def test_soft_voting(self):
        """Test soft voting method"""
        model_preds = {
            'xgboost': {'proba_up': 0.80, 'proba_down': 0.20, 'weight': 0.95},
            'random_forest': {'proba_up': 0.70, 'proba_down': 0.30, 'weight': 0.90},
            'logistic': {'proba_up': 0.60, 'proba_down': 0.40, 'weight': 0.85}
        }

        direction, probability = self.ensemble._soft_voting(model_preds)

        # Average Up probability: (0.80 + 0.70 + 0.60) / 3 = 0.70
        self.assertEqual(direction, 'Up')
        self.assertAlmostEqual(probability, 0.70, places=2)

    def test_soft_voting_down(self):
        """Test soft voting with Down prediction"""
        model_preds = {
            'xgboost': {'proba_up': 0.30, 'proba_down': 0.70, 'weight': 0.95},
            'random_forest': {'proba_up': 0.40, 'proba_down': 0.60, 'weight': 0.90},
            'logistic': {'proba_up': 0.35, 'proba_down': 0.65, 'weight': 0.85}
        }

        direction, probability = self.ensemble._soft_voting(model_preds)

        # Average Up probability: (0.30 + 0.40 + 0.35) / 3 = 0.35
        # Down probability: 1 - 0.35 = 0.65
        self.assertEqual(direction, 'Down')
        self.assertAlmostEqual(probability, 0.65, places=2)

    def test_weighted_voting(self):
        """Test weighted voting method"""
        model_preds = {
            'xgboost': {'proba_up': 0.80, 'proba_down': 0.20, 'weight': 1.0},  # Best model
            'random_forest': {'proba_up': 0.60, 'proba_down': 0.40, 'weight': 0.8},
            'logistic': {'proba_up': 0.50, 'proba_down': 0.50, 'weight': 0.5}  # Worst model
        }

        direction, probability = self.ensemble._weighted_voting(model_preds)

        # Weighted Up probability: (0.80*1.0 + 0.60*0.8 + 0.50*0.5) / (1.0+0.8+0.5)
        # = (0.80 + 0.48 + 0.25) / 2.3 = 1.53 / 2.3 ≈ 0.665
        self.assertEqual(direction, 'Up')
        self.assertAlmostEqual(probability, 0.665, places=2)

    def test_majority_voting_up(self):
        """Test majority voting with Up consensus"""
        model_preds = {
            'xgboost': {'direction': 'Up', 'proba_up': 0.80, 'weight': 0.95},
            'random_forest': {'direction': 'Up', 'proba_up': 0.70, 'weight': 0.90},
            'logistic': {'direction': 'Down', 'proba_up': 0.40, 'weight': 0.85}
        }

        direction, probability = self.ensemble._majority_voting(model_preds)

        # 2 Up votes, 1 Down vote → Up wins
        self.assertEqual(direction, 'Up')
        self.assertAlmostEqual(probability, 2/3, places=2)

    def test_majority_voting_down(self):
        """Test majority voting with Down consensus"""
        model_preds = {
            'xgboost': {'direction': 'Down', 'proba_up': 0.30, 'weight': 0.95},
            'random_forest': {'direction': 'Down', 'proba_up': 0.40, 'weight': 0.90},
            'logistic': {'direction': 'Up', 'proba_up': 0.60, 'weight': 0.85}
        }

        direction, probability = self.ensemble._majority_voting(model_preds)

        # 2 Down votes, 1 Up vote → Down wins
        self.assertEqual(direction, 'Down')
        self.assertAlmostEqual(probability, 2/3, places=2)

    def test_majority_voting_tie_fallback(self):
        """Test majority voting with tie (even number of models)"""
        model_preds = {
            'xgboost': {'direction': 'Up', 'proba_up': 0.80, 'weight': 0.95},
            'random_forest': {'direction': 'Down', 'proba_up': 0.30, 'weight': 0.90}
        }

        direction, probability = self.ensemble._majority_voting(model_preds)

        # Tie → fallback to soft voting
        # Avg Up: (0.80 + 0.30) / 2 = 0.55 → Up
        self.assertEqual(direction, 'Up')
        self.assertAlmostEqual(probability, 0.55, places=2)

    def test_predict_no_models(self):
        """Test prediction without loaded models"""
        features = np.random.rand(14)
        with self.assertRaises(ValueError):
            self.ensemble.predict(features)

    @patch.object(EnsemblePredictor, 'load_models')
    def test_predict_with_mocked_models(self, mock_load):
        """Test prediction with mocked models"""
        # Mock models
        mock_model_1 = Mock()
        mock_model_1.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))  # Up
        mock_model_1.predict = Mock(return_value=np.array([1]))

        mock_model_2 = Mock()
        mock_model_2.predict_proba = Mock(return_value=np.array([[0.4, 0.6]]))  # Up
        mock_model_2.predict = Mock(return_value=np.array([1]))

        self.ensemble.models = {
            'xgboost': mock_model_1,
            'random_forest': mock_model_2
        }

        self.ensemble.model_info = {
            'xgboost': ModelInfo('xgboost', '', None, 0.95, 0.95, 0.98),
            'random_forest': ModelInfo('random_forest', '', None, 0.90, 0.90, 0.95)
        }

        # Predict
        features = np.random.rand(14)
        pred = self.ensemble.predict(features, method='soft')

        # Verify prediction
        self.assertEqual(pred.direction, 'Up')
        self.assertEqual(pred.voting_method, 'soft')
        self.assertGreater(pred.probability, 0.5)  # Should be > 0.5 for Up
        self.assertGreater(pred.confidence, 0.0)
        self.assertEqual(len(pred.model_predictions), 2)

    def test_predict_1d_features(self):
        """Test prediction with 1D feature array"""
        # Mock models
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))
        mock_model.predict = Mock(return_value=np.array([1]))

        self.ensemble.models = {'xgboost': mock_model}
        self.ensemble.model_info = {'xgboost': ModelInfo('xgboost', '', None, 0.95, 0.95, 0.98)}

        # 1D features
        features = np.random.rand(14)
        pred = self.ensemble.predict(features)

        # Should handle 1D → 2D conversion
        self.assertEqual(pred.direction, 'Up')

    def test_predict_batch(self):
        """Test batch prediction"""
        # Mock model
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))
        mock_model.predict = Mock(return_value=np.array([1]))

        self.ensemble.models = {'xgboost': mock_model}
        self.ensemble.model_info = {'xgboost': ModelInfo('xgboost', '', None, 0.95, 0.95, 0.98)}

        # Batch features (3 samples, 14 features)
        features_batch = np.random.rand(3, 14)
        predictions = self.ensemble.predict_batch(features_batch, method='soft')

        # Verify batch
        self.assertEqual(len(predictions), 3)
        for pred in predictions:
            self.assertIsInstance(pred, EnsemblePrediction)

    def test_get_model_summary(self):
        """Test getting model summary"""
        self.ensemble.model_info = {
            'xgboost': ModelInfo('xgboost', '', None, 0.95, 0.95, 0.98),
            'random_forest': ModelInfo('random_forest', '', None, 0.90, 0.90, 0.95)
        }

        summary = self.ensemble.get_model_summary()

        self.assertEqual(len(summary), 2)
        self.assertIn('xgboost', summary)
        self.assertEqual(summary['xgboost']['accuracy'], 0.95)
        self.assertEqual(summary['xgboost']['roc_auc'], 0.98)

    def test_compare_voting_methods(self):
        """Test comparing all voting methods"""
        # Mock model
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.7]]))
        mock_model.predict = Mock(return_value=np.array([1]))

        self.ensemble.models = {'xgboost': mock_model}
        self.ensemble.model_info = {'xgboost': ModelInfo('xgboost', '', None, 0.95, 0.95, 0.98)}

        features = np.random.rand(14)
        results = self.ensemble.compare_voting_methods(features)

        # Should have results for all 3 methods
        self.assertIn('soft', results)
        self.assertIn('weighted', results)
        self.assertIn('majority', results)

        # All should predict Up
        self.assertEqual(results['soft']['direction'], 'Up')
        self.assertEqual(results['weighted']['direction'], 'Up')
        self.assertEqual(results['majority']['direction'], 'Up')

    def test_confidence_calculation(self):
        """Test confidence scaling from probability"""
        # Mock model with 100% confidence (1.0 probability)
        mock_model = Mock()
        mock_model.predict_proba = Mock(return_value=np.array([[0.0, 1.0]]))
        mock_model.predict = Mock(return_value=np.array([1]))

        self.ensemble.models = {'xgboost': mock_model}
        self.ensemble.model_info = {'xgboost': ModelInfo('xgboost', '', None, 1.0, 1.0, 1.0)}

        features = np.random.rand(14)
        pred = self.ensemble.predict(features)

        # Probability 1.0 → confidence = (1.0 - 0.5) * 2 = 1.0
        self.assertAlmostEqual(pred.confidence, 1.0, places=2)

        # Test 50/50 probability (low confidence)
        mock_model.predict_proba = Mock(return_value=np.array([[0.5, 0.5]]))
        pred = self.ensemble.predict(features)

        # Probability 0.5 → confidence = (0.5 - 0.5) * 2 = 0.0
        self.assertAlmostEqual(pred.confidence, 0.0, places=2)


if __name__ == '__main__':
    unittest.main()
