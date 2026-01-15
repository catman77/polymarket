# Statistical Analysis Guide

## Overview

This guide covers comprehensive statistical analysis of 15-minute epoch binary outcome data for BTC, ETH, SOL, and XRP.

**Dataset:** 2,884 epochs over 7.5 days (Jan 7-14, 2026)

## Installation

```bash
cd /Volumes/TerraTitan/Development/polymarket-autotrader
pip install -r analysis/requirements_stats.txt
```

## Available Analyses

### 1. Chi-Square Tests for Hourly Bias

**Purpose:** Determine if certain hours have statistically significant directional bias.

**Hypothesis:**
- H0: Each hour has 50/50 up/down distribution (no bias)
- H1: Certain hours have significant directional bias

**Run:**
```bash
python3 analysis/statistical_analysis.py --test chi2

# For specific crypto
python3 analysis/statistical_analysis.py --test chi2 --crypto btc
```

**Output:**
- Chi-square statistic for each hour
- p-values (raw and Bonferroni-corrected)
- 95% confidence intervals for up%
- List of statistically significant hours

**Interpretation:**
- p-corrected < 0.05 → Hour has significant bias
- Cramér's V measures effect size (0.1=small, 0.3=medium, 0.5=large)
- Bonferroni correction prevents false positives from testing 24 hours

**Expected Results:**
- With 28-32 epochs per hour, need ~60pp bias (70%+ or 30%-) for significance
- Small sample sizes mean most hours won't reach significance
- Look for patterns across multiple adjacent hours

---

### 2. Sample Size Requirements

**Purpose:** Calculate how many epochs needed to detect various effect sizes.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test sample
```

**Output:**
- Required N for different effect sizes (5pp, 10pp, 15pp, 20pp, 25pp, 30pp)
- Days needed to accumulate sufficient data per hour
- Current sample sizes by hour

**Key Insights:**
- **5pp effect (55% vs 50%):** ~1571 epochs = 393 days per hour
- **10pp effect (60% vs 50%):** ~393 epochs = 98 days per hour
- **15pp effect (65% vs 50%):** ~175 epochs = 44 days per hour
- **20pp effect (70% vs 50%):** ~99 epochs = 25 days per hour
- **25pp effect (75% vs 50%):** ~64 epochs = 16 days per hour
- **30pp effect (80% vs 50%):** ~44 epochs = 11 days per hour

**Conclusion:** With 7.5 days of data, you can reliably detect 20pp+ effects, but not smaller patterns.

---

### 3. Time Series Analysis

**Purpose:** Test if outcomes are independent or have autocorrelation patterns.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test timeseries --crypto btc
```

**Tests Performed:**

#### 3a. Autocorrelation Function (ACF)
- Measures correlation between outcome at time t and time t-k
- **Positive ACF:** Momentum (Up follows Up)
- **Negative ACF:** Mean reversion (Up follows Down)
- **Near zero:** Independence (random walk)

#### 3b. Partial Autocorrelation (PACF)
- Direct correlation at each lag (removes indirect effects)
- Identifies true lag relationships

#### 3c. Ljung-Box Test
- H0: No autocorrelation up to lag k (data is random)
- H1: Significant autocorrelation exists
- **p < 0.05 → Reject H0 (not random)**

#### 3d. Runs Test
- Tests for clustering vs alternation
- **Fewer runs than expected:** Momentum/clustering
- **More runs than expected:** Mean reversion/alternation

#### 3e. Augmented Dickey-Fuller Test
- Tests stationarity (no trending over time)
- **p < 0.05 → Stationary (good for analysis)**

**Interpretation:**
- If ACF shows no significance → Outcomes are independent (efficient market)
- If ACF shows momentum → Can exploit trends
- If ACF shows mean reversion → Fade extremes

---

### 4. Multi-Factor ANOVA

**Purpose:** Identify which factors significantly affect outcomes.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test anova
```

**Factors Tested:**
- Hour of day (0-23)
- Day of week (0-6)
- Crypto (BTC/ETH/SOL/XRP)
- Time category (dawn/morning/midday/afternoon/evening/night)
- Is weekend (0/1)

**Output:**
- ANOVA table with F-statistics and p-values
- Effect sizes (η² - eta squared)
  - 0.01 = small effect
  - 0.06 = medium effect
  - 0.14 = large effect

**Interpretation:**
- **p < 0.05:** Factor has significant effect on outcomes
- **η² shows practical significance** (even if statistically significant)

---

### 5. Segmentation Analysis

**Purpose:** Find optimal time groupings for prediction.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test segment

# For specific crypto
python3 analysis/statistical_analysis.py --test segment --crypto btc
```

**Segmentations Compared:**
1. Hour (24 groups)
2. 2-Hour Blocks (12 groups)
3. 4-Hour Blocks (6 groups)
4. 6-Hour Blocks (4 groups)
5. 8-Hour Blocks (3 groups)
6. Time Category (dawn/morning/midday/afternoon/evening/night/late)
7. Day of Week (7 groups)
8. Weekend vs Weekday (2 groups)

**Output:**
- Chi-square test for each segmentation
- Cramér's V (effect size)
- Range of up% across groups (higher = more predictive)

**Best Segmentation:**
The one with:
- Highest Cramér's V
- Widest range of up%
- Statistically significant χ²

**Answers Your Questions:**
- "Are there better days for up vs down?" → Day of Week analysis
- "Morning vs afternoon?" → Time Category analysis
- "Early morning vs evening?" → 2-Hour or 4-Hour Blocks

---

### 6. Cross-Crypto Correlation

**Purpose:** Determine if cryptos move together or independently.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test correlation
```

**Tests Performed:**

#### 6a. Simultaneous Correlation
- Do BTC, ETH, SOL, XRP move together in same epoch?
- Correlation matrix with significance tests

#### 6b. Lead-Lag Analysis
- Does one crypto predict another?
- Tests lags 0-5 epochs (0-75 minutes)
- **Lag 0:** Simultaneous correlation
- **Lag 1+:** Leading indicator

**Expected Results:**
- **High correlation (>0.7):** Cryptos move together (risk concentration)
- **Low correlation (<0.3):** Independent (good for diversification)
- **Significant lag:** One crypto leads another (exploit for prediction)

**Use Cases:**
- If BTC leads XRP → Use BTC signal to predict XRP
- If high correlation → Don't bet same direction on all cryptos (avoid overexposure)

---

### 7. Predictive Power Analysis

**Purpose:** Build logistic regression model to predict direction.

**Run:**
```bash
python3 analysis/statistical_analysis.py --test predict
```

**Model:**
- **Features:** hour, day_of_week, is_weekend, crypto dummies
- **Target:** direction (Up=1, Down=0)
- **Method:** Logistic regression with train/test split (70/30)

**Output:**
- Classification report (precision, recall, F1-score)
- ROC AUC score
- Feature importance (coefficient magnitudes)
- Comparison to baseline (always predict majority class)

**Interpretation:**
- **AUC > 0.5:** Better than random
- **AUC > baseline:** Model has predictive power
- **AUC < baseline:** No predictive power (efficient market)
- **Feature coefficients:** Which factors matter most

**Benchmarks:**
- **AUC 0.50:** Random (no skill)
- **AUC 0.55-0.60:** Weak predictive power
- **AUC 0.60-0.70:** Moderate predictive power
- **AUC 0.70+:** Strong predictive power

---

### 8. Regime Detection

**Purpose:** Identify hidden market states (bull/bear/neutral).

**Run:**
```bash
# Simple rolling regime detection
python3 analysis/regime_detection.py --crypto btc --method simple --window 20

# Hidden Markov Model (3 states)
python3 analysis/regime_detection.py --crypto btc --method hmm --states 3

# Change point detection
python3 analysis/regime_detection.py --crypto btc --method changepoint

# Momentum regime classification
python3 analysis/regime_detection.py --crypto btc --method momentum

# Run all methods
python3 analysis/regime_detection.py --crypto btc --method all
```

#### 8a. Simple Regime Detection
- Uses rolling window (default 20 epochs = 5 hours)
- **Bull regime:** >60% ups in window
- **Bear regime:** <40% ups in window
- **Neutral regime:** 40-60% ups

**Output:**
- Regime statistics (count, up rate, avg change, volatility)
- Transition matrix (regime persistence)
- Average regime duration

#### 8b. Hidden Markov Model (HMM)
- Assumes hidden states generate observed outcomes
- Learns optimal states from data
- **Requires:** `pip install hmmlearn`

**Output:**
- State statistics (occurrences, up rate, avg change)
- Transition probabilities between states
- State parameters (means, covariances)

**Use Case:**
- If state persistence is high → Trade based on current regime
- If transitions are frequent → Regimes not useful

#### 8c. Change Point Detection
- Detects points where statistical properties change
- Uses PELT algorithm
- **Requires:** `pip install ruptures`

**Output:**
- Number of change points detected
- Segments with start/end times and up rates

**Use Case:**
- Identify when market shifts (volatility events, news, etc.)

#### 8d. Momentum Regime Classification
- Classifies based on recent momentum + volatility
- **Trending:** Strong momentum + low volatility
- **Choppy:** Weak momentum + high volatility
- **Weak trend:** Medium momentum

**Output:**
- Regime statistics
- Win rates if betting based on regime

---

## Complete Analysis Workflow

### Step 1: Run All Tests
```bash
python3 analysis/statistical_analysis.py --test all
```

This generates:
- All statistical tests
- Comprehensive report saved to `analysis/statistical_report.json`

### Step 2: Regime Analysis (per crypto)
```bash
for crypto in btc eth sol xrp; do
  python3 analysis/regime_detection.py --crypto $crypto --method all
done
```

### Step 3: Review Results

**Look for:**
1. **Significant hourly patterns** (chi-square test)
2. **Optimal time segmentation** (segmentation analysis)
3. **Cross-crypto relationships** (correlation analysis)
4. **Predictive factors** (logistic regression)
5. **Regime persistence** (HMM/regime detection)

---

## Statistical Interpretation Guidelines

### P-values
- **p < 0.001:** Very strong evidence (***)
- **p < 0.01:** Strong evidence (**)
- **p < 0.05:** Significant evidence (*)
- **p ≥ 0.05:** Insufficient evidence (fail to reject H0)

### Effect Sizes
- **Cramér's V:** 0.1 (small), 0.3 (medium), 0.5 (large)
- **η² (eta-squared):** 0.01 (small), 0.06 (medium), 0.14 (large)
- **Cohen's d:** 0.2 (small), 0.5 (medium), 0.8 (large)

### Confidence Intervals
- **95% CI:** Range where true value lies with 95% confidence
- **Narrow CI:** High precision (large sample)
- **Wide CI:** Low precision (small sample)
- **CI excludes 50%:** Significant bias

### Sample Size Reality Check
With 7.5 days of data:
- ✅ Can detect large effects (20pp+)
- ⚠️ Limited power for medium effects (10-15pp)
- ❌ Cannot reliably detect small effects (<10pp)

**Recommendation:** Collect 30+ days for robust patterns.

---

## Practical Application

### If Hourly Patterns Found
```python
# Example: XRP 09:00 has 75% up rate (significant)
# Trade: Bet UP on XRP at 09:00 with higher confidence

# Check:
# 1. Sample size (N ≥ 30?)
# 2. Bonferroni-corrected p-value < 0.05?
# 3. 95% CI excludes 50%?
# 4. Effect size (Cramér's V > 0.2)?
```

### If Time Segments Found
```python
# Example: Morning (09:00-12:00) = 62% up for BTC
# Trade: Increase position size during morning hours

# Check:
# 1. Chi-square test significant?
# 2. Range across segments > 10pp?
# 3. Consistent across multiple days?
```

### If Regimes Detected
```python
# Example: HMM finds 3 states with high persistence
# Trade: Identify current regime, bet accordingly

# Bull regime (70% up) → Bet UP
# Bear regime (30% up) → Bet DOWN
# Neutral regime (50% up) → Skip or use other signals
```

### If High Crypto Correlation
```python
# Example: BTC/ETH correlation = 0.85
# Risk management: Don't bet same direction on both

# If already UP on BTC → Skip ETH UP
# Diversify: BTC UP + SOL DOWN (lower correlation)
```

---

## Common Pitfalls

### 1. Multiple Comparisons Problem
**Issue:** Testing 24 hours increases false positive rate.
**Solution:** Use Bonferroni correction (α/24).

### 2. Small Sample Size
**Issue:** 7.5 days = only ~30 epochs per hour.
**Solution:** Focus on large effects, collect more data, or combine adjacent hours.

### 3. Overfitting
**Issue:** Finding patterns that don't generalize.
**Solution:** Out-of-sample validation, cross-validation, conservative thresholds.

### 4. Data Snooping Bias
**Issue:** Testing many hypotheses until finding significance.
**Solution:** Pre-register hypotheses, hold out test set.

### 5. Ignoring Transaction Costs
**Issue:** Small edge gets eaten by fees.
**Solution:** Account for 6.3% round-trip fees at 50% probability.

---

## Next Steps

1. **Collect more data:** 30+ days for robust patterns
2. **Forward testing:** Test patterns on new data (Jan 15+)
3. **Combine signals:** Use multiple factors (hour + regime + momentum)
4. **Backtest strategies:** Simulate trading based on findings
5. **Monitor pattern degradation:** Markets adapt, patterns fade

---

## Statistical Software Alternatives

If you prefer other tools:

### R
```r
# Chi-square test
chisq.test(table(df$hour, df$direction))

# Time series
library(forecast)
acf(df$direction_binary)

# Regime switching
library(MSwM)
```

### MATLAB
```matlab
% Chi-square
[h,p,stats] = chi2gof(data);

% HMM
[trans, emis] = hmmestimate(seq, states);
```

### Stata
```stata
* ANOVA
anova direction_binary hour day_of_week crypto

* Logistic regression
logit direction_binary i.hour i.day_of_week i.crypto
```

---

## References

1. **Chi-square test:** Pearson (1900), "On the criterion..."
2. **Bonferroni correction:** Dunn (1961), "Multiple comparisons..."
3. **Ljung-Box test:** Ljung & Box (1978), "On a measure..."
4. **Hidden Markov Models:** Rabiner (1989), "A tutorial on HMMs..."
5. **Change point detection:** Killick et al. (2012), "Optimal detection..."

---

## Support

Questions or issues? Check:
- Script comments and docstrings
- Python `--help` flags
- Statistical textbooks (recommend: "All of Statistics" by Wasserman)
- Stack Overflow for implementation questions

---

**Last Updated:** 2026-01-14
**Author:** Statistical Analysis Module
**Version:** 1.0
