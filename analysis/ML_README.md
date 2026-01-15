# Machine Learning Analysis Framework

**Comprehensive ML toolkit for discovering profitable trading patterns in 15-minute binary epoch data.**

---

## Overview

This framework provides end-to-end machine learning analysis for Polymarket AutoTrader, using 2,884+ historical epochs across BTC, ETH, SOL, and XRP to discover patterns and build predictive models.

### What's Included

1. **Feature Engineering** - Extract 50+ features from raw epoch data
2. **Supervised Learning** - Binary classification models (Logistic, RF, XGBoost, Neural Nets)
3. **Unsupervised Learning** - K-Means clustering, PCA, t-SNE visualization
4. **Time Segmentation** - Optimal time window discovery
5. **Pattern Mining** - Association rules, sequential patterns
6. **Ensemble Learning** - Model stacking, voting, blending

---

## Quick Start

### 1. Install Dependencies

```bash
pip install pandas numpy scikit-learn xgboost matplotlib seaborn
```

### 2. Ensure Dataset Exists

```bash
# Check if you have historical data
python3 analysis/historical_dataset.py --stats

# If needed, backfill data (7 days recommended)
python3 analysis/historical_dataset.py --backfill 7 --all
```

### 3. Run Complete Analysis

```bash
# This runs all 6 analysis modules (~5-10 minutes)
python3 analysis/ml_full_analysis.py
```

### 4. Review Results

- **Feature Matrix**: `analysis/feature_matrix.csv`
- **Cluster Visualizations**: `analysis/cluster_visualization_*.png`
- **Console Output**: Detailed insights printed to terminal

---

## Module Details

### 1. Feature Engineering (`ml_feature_engineering.py`)

**Purpose**: Transform raw epoch data into ML-ready features.

**Features Extracted**:

- **Temporal**: Hour, day-of-week, time blocks, cyclic encoding
- **Rolling Stats**: Momentum, volatility, streaks (windows: 1h, 2h, 4h, 8h)
- **Cross-Crypto**: Market consensus, divergence indicators
- **Lag Features**: Previous epoch outcomes (1, 2, 4, 8 epochs back)
- **Market Regimes**: Bullish/bearish/choppy classification
- **Hourly Stats**: Historical win rate by hour

**Usage**:

```python
from ml_feature_engineering import FeatureEngineering

fe = FeatureEngineering()
df = fe.build_feature_matrix()  # Returns DataFrame with all features

# Get feature column names
feature_cols = fe.get_feature_columns(df)
```

**Output**: DataFrame with ~50 features per epoch

---

### 2. Supervised Learning (`ml_supervised_learning.py`)

**Purpose**: Train binary classifiers to predict Up/Down outcomes.

**Models**:

- **Logistic Regression** (baseline)
- **Random Forest** (best performer)
- **XGBoost** (if installed)
- **Neural Network** (MLP)

**Evaluation**:

- Time-series cross-validation (walk-forward)
- Accuracy, precision, recall, F1, ROC-AUC
- Feature importance analysis

**Usage**:

```python
from ml_supervised_learning import EpochPredictor

predictor = EpochPredictor()
X_train, X_test, y_train, y_test = predictor.prepare_data(test_size=0.2)

predictor.train_all_models(X_train, y_train)

# Evaluate
for model_name in predictor.models.keys():
    predictor.evaluate_model(model_name, X_test, y_test)

predictor.print_results()
predictor.feature_importance('random_forest', top_n=20)
```

**Key Metrics**:

- **Break-even**: 53% win rate (accounting for 6.3% fees)
- **Profitable**: >60% win rate
- **Target**: 65%+ for consistent profits

---

### 3. Unsupervised Learning (`ml_unsupervised_learning.py`)

**Purpose**: Discover natural groupings and patterns without labels.

**Methods**:

- **K-Means Clustering** - Find similar epoch patterns
- **PCA** - Dimensionality reduction
- **t-SNE** - 2D visualization
- **Cluster Profiling** - Characterize discovered clusters

**Usage**:

```python
from ml_unsupervised_learning import EpochClusterer

clusterer = EpochClusterer()
X, metadata = clusterer.prepare_features()

# Find optimal k
results = clusterer.find_optimal_k(X, k_range=range(3, 11))

# Cluster
labels = clusterer.kmeans_clustering(X, n_clusters=5)

# Analyze
clusterer.analyze_clusters(metadata)
profiles = clusterer.cluster_profiling(metadata)

# Visualize
X_pca = clusterer.pca_analysis(X, n_components=10)
```

**Insights**:

- High win-rate clusters (>60%) = trade during these conditions
- Low win-rate clusters (<45%) = avoid trading
- Cluster features reveal what makes epochs profitable

---

### 4. Time Segmentation (`ml_time_segmentation.py`)

**Purpose**: Find optimal time windows for trading.

**Analyses**:

- **Time Blocks**: Morning/Afternoon/Evening/Night
- **Day-of-Week**: Monday-Sunday patterns
- **Hour Windows**: Best 1-8 hour windows per crypto
- **Combined**: Time block × Day of week
- **Adaptive Blocks**: Natural breakpoint detection

**Usage**:

```python
from ml_time_segmentation import TimeSegmentationOptimizer

optimizer = TimeSegmentationOptimizer()

# Time blocks
time_blocks = optimizer.cross_segment_analysis('time_of_day')

# Day of week
dow_analysis = optimizer.day_of_week_analysis()

# Best windows
windows = optimizer.find_optimal_hour_windows('btc', min_window_size=2, max_window_size=6)

# Combined analysis
combined = optimizer.cross_segment_analysis('combined')
```

**Example Insights**:

- "BTC: 14:00-18:00 has 68% up rate (42 epochs)"
- "ETH: Tuesday mornings favor Down (35% up rate)"
- "SOL: Weekends show neutral pattern (50/50)"

---

### 5. Pattern Mining (`ml_pattern_mining.py`)

**Purpose**: Discover association rules and sequential patterns.

**Methods**:

- **Apriori Algorithm** - Frequent itemsets
- **Association Rules** - If-then patterns (confidence, lift)
- **Sequential Patterns** - "3 ups → down?" type patterns
- **Cross-Crypto Correlations** - "If BTC up, then ETH up?"
- **Conditional Probabilities** - Hour-specific patterns

**Usage**:

```python
from ml_pattern_mining import PatternMiner

miner = PatternMiner()

# Create transactions
transactions = miner.create_epoch_transactions()

# Find frequent itemsets
itemsets = miner.apriori_frequent_itemsets(transactions, min_support=0.10)

# Generate rules
rules = miner.generate_association_rules(itemsets, min_confidence=0.65)

# Sequential patterns
patterns = miner.sequential_pattern_mining('btc', sequence_length=3)

# Cross-crypto
correlations = miner.crypto_correlation_patterns()
```

**Example Rules**:

- IF `hour_14, btc_up` THEN `eth_up` (confidence=0.72, lift=1.3)
- IF `↑↑↑` (3 ups) THEN `↓` next (confidence=0.65)
- IF `btc_up` THEN `eth_up` (70% of the time)

---

### 6. Ensemble Learning (`ml_ensemble.py`)

**Purpose**: Combine multiple models for better predictions.

**Methods**:

- **Voting Classifier** - Hard/soft voting across models
- **Stacking Classifier** - Meta-learner on top of base models
- **Hourly Specialized** - Different models for different hours
- **Blended Predictions** - ML + historical patterns

**Usage**:

```python
from ml_ensemble import EnsemblePredictor

ensemble = EnsemblePredictor()
X_train, X_test, y_train, y_test = ensemble.prepare_data(test_size=0.2)

# Train ensembles
ensemble.train_voting_classifier(X_train, y_train, voting='soft')
ensemble.train_stacking_classifier(X_train, y_train)

# Evaluate
results = ensemble.evaluate_all_ensembles(X_test, y_test)

# Find best
best_model = max(results.items(), key=lambda x: x[1])
```

**Why Ensemble?**:

- Reduces overfitting
- More robust predictions
- Combines strengths of different models
- Typically 2-5% accuracy improvement

---

## Interpreting Results

### Win Rate Thresholds

| Win Rate | Interpretation |
|----------|----------------|
| <50% | Losing strategy |
| 50-53% | Break-even (fees eat profit) |
| 53-60% | Marginal profit |
| 60-65% | Good profit |
| 65%+ | Excellent profit |

### Feature Importance

Top features reveal what drives outcomes:

- **High importance**: `hour_historical_up_pct`, `momentum_16`, `market_consensus_up`
- **Medium importance**: `volatility_16`, `trend_strength`, `dow_sin`
- **Low importance**: Individual lag features, specific hours

### Cluster Analysis

**Good clusters** (>60% win rate):
- Note their characteristics (hour, crypto, day)
- Create trading rules to match these conditions
- Example: "Cluster 3 = BTC, hour 14-16, high momentum → 68% up"

**Bad clusters** (<45% win rate):
- Avoid trading during these conditions
- Example: "Cluster 1 = choppy market, evening, low volume → 42% up"

### Association Rules

**Strong rules** (confidence >0.75, lift >1.2):
- Use as entry filters
- Example: IF `morning AND btc_up AND eth_up` THEN `sol_up` (78% confidence)

**Weak rules** (confidence <0.60):
- Ignore or inverse as contrarian signals

---

## Integration with Trading Bot

### Step 1: Add Time Filters

Based on time segmentation results:

```python
# In bot/momentum_bot_v12.py

PROFITABLE_HOURS = {
    'btc': [14, 15, 16, 17],  # Example from analysis
    'eth': [10, 11, 12, 13],
    'sol': [18, 19, 20, 21],
    'xrp': [8, 9, 10]
}

def should_trade_now(crypto: str, hour: int) -> bool:
    """Only trade during profitable hours."""
    return hour in PROFITABLE_HOURS.get(crypto, [])
```

### Step 2: Use ML Predictions

Add ensemble model as signal:

```python
from analysis.ml_ensemble import EnsemblePredictor

# Load trained model
ensemble = EnsemblePredictor()
# ... load saved model weights ...

def get_ml_signal(crypto: str, features: dict) -> float:
    """Get ML prediction probability (0-1)."""
    X = prepare_features(features)  # Transform to feature vector
    proba = ensemble.models['voting_soft'].predict_proba(X)[0, 1]
    return proba

# In main trading loop:
ml_prob = get_ml_signal(crypto, current_features)

if ml_prob > 0.70:  # High confidence Up
    # Increase position size or trade with more confidence
    pass
elif ml_prob < 0.30:  # High confidence Down
    # Bet Down
    pass
else:
    # Skip (uncertain)
    pass
```

### Step 3: Apply Association Rules

```python
def check_association_rules(crypto: str, hour: int, market_state: dict) -> str:
    """Apply discovered association rules."""

    # Example rule: IF hour=14 AND btc_up THEN eth_up (confidence=0.72)
    if hour == 14 and market_state['btc'] == 'up' and crypto == 'eth':
        return 'UP'  # Strong signal

    # Add more rules from analysis
    return 'NEUTRAL'
```

---

## Advanced Usage

### Custom Feature Engineering

Add domain-specific features:

```python
# In ml_feature_engineering.py

def add_custom_features(self, df: pd.DataFrame) -> pd.DataFrame:
    """Add your own features."""
    df = df.copy()

    # Example: Polymarket-specific features
    df['epoch_progress'] = (df['epoch'] % 900) / 900  # Progress within epoch
    df['is_quarter_hour'] = (df['epoch'] % 900 == 0).astype(int)

    # Order book features (if you have this data)
    # df['bid_ask_spread'] = ...

    return df
```

### Hyperparameter Tuning

Use grid search for better models:

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15],
    'min_samples_split': [10, 20, 30]
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid,
    cv=TimeSeriesSplit(n_splits=5),
    scoring='accuracy',
    n_jobs=-1
)

grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
```

### Save/Load Models

```python
import joblib

# Save
joblib.dump(predictor.models['random_forest'], 'models/rf_model.pkl')

# Load
loaded_model = joblib.load('models/rf_model.pkl')
predictions = loaded_model.predict(X_test)
```

---

## Troubleshooting

### "No module named 'xgboost'"

XGBoost is optional. Install with:

```bash
pip install xgboost
```

Or skip XGBoost models (other models will still work).

### "Database is locked"

SQLite database is in use by another process. Wait or kill the process:

```bash
lsof analysis/epoch_history.db
kill -9 <PID>
```

### "Not enough data"

Need at least 3-5 days of data for meaningful analysis:

```bash
python3 analysis/historical_dataset.py --backfill 7 --all
```

### "Memory error"

Reduce dataset size or features:

```python
# Use fewer features
df = fe.build_feature_matrix(
    include_rolling=True,
    include_cross_crypto=False,  # Skip this
    include_lags=False  # Skip this
)
```

---

## Performance Benchmarks

**On MacBook Pro M1 (16GB RAM)**:

| Module | Time | Output |
|--------|------|--------|
| Feature Engineering | ~30s | 2,800 × 50 matrix |
| Supervised Learning | ~2min | 4 models trained |
| Unsupervised Learning | ~1min | Clusters + viz |
| Time Segmentation | ~30s | Reports |
| Pattern Mining | ~1min | Rules + patterns |
| Ensemble Learning | ~3min | Ensembles |
| **Total** | **~8min** | **Complete analysis** |

---

## Citation & References

**Algorithms**:

- Apriori: Agrawal & Srikant (1994)
- Random Forest: Breiman (2001)
- XGBoost: Chen & Guestrin (2016)
- t-SNE: van der Maaten & Hinton (2008)

**Implementation**:

- scikit-learn: [scikit-learn.org](https://scikit-learn.org)
- XGBoost: [xgboost.readthedocs.io](https://xgboost.readthedocs.io)

---

## Next Steps

1. **Run the analysis** - Execute `ml_full_analysis.py`
2. **Review insights** - Look for >60% win rate patterns
3. **Backtest** - Test patterns on historical trades
4. **Integrate** - Add profitable filters to bot
5. **Monitor** - Track real-world performance
6. **Iterate** - Re-run analysis weekly with new data

---

## Support

For issues or questions:

1. Check this README
2. Review console output and error messages
3. Inspect intermediate outputs (CSVs, plots)
4. Open GitHub issue with full error traceback

---

**Happy trading! 🚀📊**
