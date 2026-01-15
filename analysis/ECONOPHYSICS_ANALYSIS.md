# Econophysics Analysis Suite

**Polymarket 15-Minute Binary Outcome Markets**

A comprehensive statistical physics and information theory approach to analyzing and predicting binary outcome market behavior.

---

## Overview

This analysis suite treats Polymarket's 15-minute Up/Down markets as a **complex adaptive system** and applies advanced econophysics methodologies to uncover:

- **Temporal patterns** (hourly, daily, session-based)
- **Phase transitions** (regime changes in market behavior)
- **Information flow** (which cryptos lead/follow)
- **Predictability limits** (entropy, complexity measures)
- **Optimal strategies** (Kelly criterion, risk-adjusted returns)

Dataset: **2,884 epochs** (7.5 days, Jan 7-15 2026) across BTC, ETH, SOL, XRP

---

## Theoretical Framework

### 1. Statistical Physics Analogies

| Financial Concept | Physics Analogy | Our Application |
|------------------|-----------------|-----------------|
| Market direction | Spin (+1/-1) | Up/Down outcome |
| Directional bias | Magnetization | Order parameter m |
| Volatility | Temperature | Regime classifier |
| Correlation | Coupling constant | Cross-asset sync |
| Regime change | Phase transition | Critical points |
| Predictability | Entropy | Shannon H(X) |

### 2. Key Metrics

#### Shannon Entropy
```
H(X) = -Σ p(x) log₂(p(x))
```
- **H = 0**: Perfectly predictable (100% one direction)
- **H = 1**: Maximum uncertainty (50/50 split)
- **H = 0.5-0.7**: Tradeable edge exists

#### Hurst Exponent
```
H = 0.5: Random walk (no memory)
H > 0.5: Persistent/momentum behavior
H < 0.5: Anti-persistent/mean reverting
```

#### Transfer Entropy
```
T(X→Y) = I(Y_t ; X_{t-1} | Y_{t-1})
```
Measures **causal information flow** from X to Y

#### Order Parameter (Magnetization)
```
m = (N_up - N_down) / N_total ∈ [-1, 1]
```
Analogous to magnetization in Ising model

---

## Analysis Modules

### **TIER 1: Foundation (Run First)**

#### 1. Microstructure Clock Analysis
**File**: `microstructure_clock.py`

**What it does:**
- Identifies hourly patterns in directional bias
- Calculates Shannon entropy by hour (predictability)
- Segments into global trading sessions (Asian/European/US)
- Classifies volatility regimes
- Tests momentum vs mean reversion
- Day-of-week calendar effects

**Key Outputs:**
- `results_hourly_entropy.csv` - Most predictable hours
- `results_trading_sessions.csv` - Session-based edges
- `results_volatility_regimes.csv` - Behavior by volatility
- `results_momentum_reversion.csv` - Momentum strength

**Expected Insights:**
- Which hours have lowest entropy (highest predictability)
- Time-of-day patterns linked to global trading flows
- Whether markets exhibit momentum or mean reversion

**Statistical Tests:**
- Z-score test for directional bias significance
- Binomial test for session patterns
- Chi-square test for momentum vs reversion

---

#### 2. Phase Transition Detection
**File**: `phase_transitions.py`

**What it does:**
- Calculates order parameter (directional magnetization)
- Detects susceptibility peaks (critical points)
- Computes Hurst exponent (memory/persistence)
- K-means clustering to identify regimes
- Markov transition matrix between states

**Key Outputs:**
- `results_order_parameter.csv` - Market state over time
- `results_phase_transitions.csv` - Regime change points
- `results_hurst_exponent.csv` - Persistence measure
- `results_regimes.csv` - Distinct market regimes
- `results_transition_matrix.csv` - State transition probabilities

**Expected Insights:**
- When markets undergo rapid regime changes
- Whether directional changes are persistent or random
- Probability of transitioning between bullish/bearish states

**Statistical Methods:**
- Rescaled range (R/S) analysis for Hurst exponent
- Peak detection on susceptibility (analogous to heat capacity)
- K-means clustering on [bias, volatility, momentum]

---

### **TIER 2: Advanced Analysis**

#### 3. Cross-Asset Dynamics
**File**: `cross_asset_dynamics.py`

**What it does:**
- Pairwise correlation analysis (do cryptos move together?)
- Lead-lag relationships (who moves first?)
- Cascade probability (contagion effects)
- Systemic risk indicator (all cryptos moving together)
- Correlation networks with centrality measures
- Time-varying correlation (rolling windows)

**Key Outputs:**
- `results_sync_correlation.csv` - Simultaneous correlations
- `results_lead_lag.csv` - Who leads, who follows
- `results_cascade_probability.csv` - Contagion strength
- `results_systemic_risk.csv` - Market-wide movement risk
- `results_network_centrality.csv` - Most connected cryptos

**Expected Insights:**
- Does BTC lead other cryptos? (likely yes)
- How strongly correlated are directional changes?
- During high volatility, do correlations increase?

**Statistical Tests:**
- Cross-correlation at different lags
- Conditional probability: P(Y up | X up)
- Network centrality (degree, betweenness)

---

#### 4. Information Theory & Predictability
**File**: `information_theory.py`

**What it does:**
- Shannon entropy analysis
- Mutual information (how much does past predict future?)
- Transfer entropy (directional information flow)
- Lempel-Ziv complexity (pattern structure)
- Pattern frequency analysis (common sequences)
- Temporal entropy evolution (changing predictability)

**Key Outputs:**
- `results_predictability.csv` - Overall predictability scores
- `results_information_flow.csv` - Causal influence network
- `results_temporal_entropy.csv` - Predictability over time
- `results_pattern_frequency.csv` - Common directional sequences

**Expected Insights:**
- Which crypto is most predictable?
- Is there directional causality (X influences Y)?
- What are the most common 3-epoch patterns (UUU, UUD, etc.)?

**Statistical Methods:**
- Conditional entropy: H(X_t | X_{t-1})
- Mutual information: I(X;Y) = H(X) - H(X|Y)
- Transfer entropy: T(X→Y) = I(Y_t ; X_{t-1} | Y_{t-1})
- Lempel-Ziv compression-based complexity

---

### **TIER 3: Trading Applications**

#### 5. Optimal Timing & Strategy
**File**: `optimal_timing.py`

**What it does:**
- Calculate win rate, edge, and Kelly fraction by hour
- Identify best trading opportunities (high edge + significant)
- Day-hour specific patterns (heatmap data)
- Streak analysis (after N ups, what's next?)
- Session-based performance comparison
- Volatility-adjusted position sizing

**Key Outputs:**
- `results_hourly_performance.csv` - Edge by hour
- `results_best_opportunities.csv` - Top trading opportunities
- `results_day_hour_heatmap.csv` - Day+hour combinations
- `results_streak_analysis.csv` - Momentum after streaks
- `results_session_performance.csv` - Asian/European/US edge
- `results_volatility_sizing.csv` - Position size adjustments

**Expected Insights:**
- Which specific hours have >10% edge?
- Should we increase bets after 2 ups in a row? (momentum)
- Which session is most profitable per crypto?

**Key Formulas:**
- **Win rate**: W = max(p_up, p_down)
- **Edge**: E = W - 0.5
- **Kelly fraction**: f* = 2W - 1
- **Expected value**: EV = W × 1 - (1-W) × 1
- **Sharpe ratio**: Edge / √(W(1-W))

---

## Running the Analysis

### Quick Start

```bash
# Run all analyses in sequence
python3 analysis/run_all_analyses.py

# Generate visualizations
python3 analysis/visualize_results.py
```

### Individual Modules

```bash
# Run specific analysis
python3 analysis/microstructure_clock.py
python3 analysis/phase_transitions.py
python3 analysis/cross_asset_dynamics.py
python3 analysis/information_theory.py
python3 analysis/optimal_timing.py
```

### Output Structure

```
analysis/
├── results_*.csv                    # CSV results
├── plots/                           # Visualizations
│   ├── hourly_entropy_heatmap.png
│   ├── edge_by_hour.png
│   ├── day_hour_*.png
│   ├── correlation_matrix.png
│   ├── predictability_scores.png
│   └── ...
└── ECONOPHYSICS_ANALYSIS.md         # This file
```

---

## Practical Trading Implications

### Immediate Actions

1. **Filter by High-Edge Hours**
   - Add to bot: Skip trading during low-entropy hours
   - Example: If XRP 09:00 UTC has 75% up bias and p<0.05, always bet Up

2. **Session-Based Strategy**
   - Different cryptos perform better in different sessions
   - BTC might have edge during US hours, ETH during European

3. **Volatility Regime Adjustment**
   - Reduce position size during high volatility regimes
   - Increase during low volatility (more predictable)

4. **Lead-Lag Exploitation**
   - If BTC leads ETH by 1 epoch, wait for BTC signal before trading ETH
   - Implement cross-crypto confirmation

5. **Momentum vs Mean Reversion**
   - If Hurst > 0.5: Add momentum filters (bet with recent direction)
   - If Hurst < 0.5: Add contrarian filters (fade recent direction)

### Position Sizing Example

```python
# From optimal_timing.py results
BASE_SIZE = 0.05  # 5% of balance

# Adjust by hour edge
if hour in HIGH_EDGE_HOURS:
    size_multiplier = 1.5
elif hour in LOW_EDGE_HOURS:
    size_multiplier = 0.5
else:
    size_multiplier = 1.0

# Adjust by volatility regime
if volatility_regime == 'High':
    size_multiplier *= 0.7
elif volatility_regime == 'Low':
    size_multiplier *= 1.2

# Adjust by Kelly criterion
kelly_fraction = 2 * win_rate - 1
size = BASE_SIZE * size_multiplier * kelly_fraction
```

---

## Interpretation Guide

### Entropy Values

| Entropy | Interpretation | Action |
|---------|---------------|---------|
| 0.0 - 0.3 | Highly predictable | **TRADE** - Strong edge |
| 0.3 - 0.5 | Moderate predictability | Trade with caution |
| 0.5 - 0.7 | Weak pattern | Avoid or reduce size |
| 0.7 - 1.0 | Near random | **DO NOT TRADE** |

### Edge Values

| Edge | Win Rate | Interpretation |
|------|----------|---------------|
| >20% | 70%+ | Excellent opportunity |
| 10-20% | 60-70% | Good opportunity |
| 5-10% | 55-60% | Marginal (watch fees) |
| <5% | 50-55% | Not worth trading |

### Statistical Significance

- **p < 0.01**: Highly significant (very confident)
- **p < 0.05**: Significant (confident)
- **p < 0.10**: Marginally significant (cautious)
- **p > 0.10**: Not significant (avoid)

**Important**: Always check sample size (n). Small n + low p-value could be luck.

---

## Advanced Interpretations

### Order Parameter Dynamics

```
m(t) = (N_up - N_down) / N_total

|m| → 1: Strong directional consensus (ordered state)
|m| → 0: No consensus (disordered state)
```

**Trading implication**: High |m| after low |m| suggests regime change.

### Susceptibility Peaks

```
χ = var(m)

Peak in χ → Critical point → Phase transition imminent
```

**Trading implication**: Reduce size near peaks (high uncertainty).

### Transfer Entropy Interpretation

```
T(BTC → ETH) = 0.05
T(ETH → BTC) = 0.01

Conclusion: BTC influences ETH more than vice versa
```

**Trading implication**: Wait for BTC signal before trading ETH.

---

## Validation & Robustness

### Bootstrap Confidence Intervals

For any metric with n epochs, bootstrap 95% CI:

```python
from scipy.stats import bootstrap

def metric_func(data):
    return data.mean()  # or any metric

result = bootstrap((data,), metric_func, n_resamples=10000)
ci_low, ci_high = result.confidence_interval
```

### Rolling Window Validation

Split data into train/test:
- Train: Jan 7-12 (first 5 days)
- Test: Jan 13-15 (last 2.5 days)

Check if patterns persist out-of-sample.

### Statistical Corrections

For multiple hypothesis testing (e.g., 24 hours × 4 cryptos = 96 tests):

**Bonferroni correction**: p_adj = p × n_tests
**FDR correction** (less conservative): Use `statsmodels.stats.multitest.fdrcorrection`

---

## Limitations & Caveats

### 1. Sample Size
- 7.5 days is relatively short
- Some day-hour combinations have n < 10 epochs
- Patterns may not persist long-term

### 2. Non-Stationarity
- Market behavior changes over time
- Profitable patterns attract capital → edges decay
- Need continuous re-calibration

### 3. Transaction Costs
- Polymarket fees: ~3-6% per round-trip
- Need >6% edge to be profitable after fees
- Many significant patterns may not be tradeable

### 4. Multiple Testing
- Testing 100+ patterns increases false positives
- Use FDR correction or hold out validation set

### 5. Market Impact
- This is a prediction market, not spot exchange
- Patterns reflect prediction market dynamics, not underlying crypto
- Betting volume affects prices

---

## References & Further Reading

### Econophysics
1. Mantegna & Stanley (2000) - "Introduction to Econophysics"
2. Bouchaud & Potters (2003) - "Theory of Financial Risk and Derivative Pricing"
3. Johnson et al. (2003) - "Application of multi-agent games to the prediction of financial time-series"

### Information Theory in Finance
1. Schreiber (2000) - "Measuring information transfer" (Transfer Entropy)
2. Marschinski & Kantz (2002) - "Analysing the information flow between financial time series"

### Statistical Methods
1. Hurst (1951) - "Long-term storage capacity of reservoirs" (Hurst exponent)
2. Lempel & Ziv (1976) - "On the complexity of finite sequences" (LZ complexity)

### Binary Outcome Markets
1. Wolfers & Zitzewitz (2004) - "Prediction markets"
2. Arrow et al. (2008) - "The promise of prediction markets"

---

## Future Enhancements

### Short-term
- [ ] Intraday analysis (within 15-minute windows)
- [ ] Order book depth analysis
- [ ] Price movement velocity (not just direction)
- [ ] Multi-timeframe confirmation (1h, 4h trends)

### Medium-term
- [ ] Machine learning regime classification
- [ ] Reinforcement learning for position sizing
- [ ] Network topology analysis (who influences whom)
- [ ] Wavelet analysis for multi-scale patterns

### Long-term
- [ ] Real-time dashboard with live signals
- [ ] Bayesian updating of pattern probabilities
- [ ] Agent-based model simulation
- [ ] Backtest framework with transaction costs

---

## Contact & Contributions

For questions, suggestions, or improvements:
- GitHub Issues: Report bugs or request features
- Pull Requests: Contribute new analyses

**Author**: Econophysics Analysis Framework
**Version**: 1.0
**Last Updated**: January 2026

---

## Appendix: Quick Reference

### Run Everything
```bash
cd /Volumes/TerraTitan/Development/polymarket-autotrader
python3 analysis/run_all_analyses.py
python3 analysis/visualize_results.py
```

### Best Opportunities
```bash
# View top trading opportunities
cat analysis/results_best_opportunities.csv | column -t -s,
```

### Most Predictable Hours
```bash
# Sort by lowest entropy (most predictable)
cat analysis/results_hourly_entropy.csv | sort -t, -k5 -n | head -10
```

### Kelly Fractions
```bash
# Hours with highest Kelly fractions
cat analysis/results_hourly_performance.csv | sort -t, -k9 -rn | head -10
```

### Integration into Bot
```python
# Example: Add hourly filter to bot

import pandas as pd

# Load results
hourly_perf = pd.read_csv('analysis/results_hourly_performance.csv')

# Filter for high-edge hours
high_edge = hourly_perf[
    (hourly_perf['edge'] > 0.10) &
    (hourly_perf['significant']) &
    (hourly_perf['n_epochs'] >= 20)
]

# Create lookup dict
TRADE_HOURS = {}
for _, row in high_edge.iterrows():
    crypto = row['crypto']
    hour = row['hour']
    direction = row['predicted_direction']

    if crypto not in TRADE_HOURS:
        TRADE_HOURS[crypto] = {}

    TRADE_HOURS[crypto][hour] = direction

# In bot's signal generation:
current_hour = datetime.utcnow().hour

if crypto in TRADE_HOURS and current_hour in TRADE_HOURS[crypto]:
    recommended_direction = TRADE_HOURS[crypto][current_hour]

    # Boost signal if it matches recommended direction
    if signal_direction == recommended_direction:
        signal_strength *= 1.5  # 50% boost
```

---

**End of Documentation**
