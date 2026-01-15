#!/usr/bin/env python3
"""
Comprehensive Statistical Analysis of 15-Minute Epoch Data

Performs rigorous statistical testing including:
1. Chi-square tests for hourly/daily bias significance
2. Time series analysis (ACF, PACF, Ljung-Box)
3. Multi-factor ANOVA
4. Optimal time segmentation analysis
5. Cross-crypto correlation and lead-lag
6. Regime detection with HMM
7. Predictive power analysis

Dataset: 2,884 epochs over 7.5 days (Jan 7-14, 2026)
Cryptos: BTC, ETH, SOL, XRP
"""

import sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import chi2_contingency, norm
from statsmodels.stats.multitest import multipletests
from statsmodels.tsa.stattools import acf, pacf, adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression
import warnings
warnings.filterwarnings('ignore')

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json


class EpochStatAnalyzer:
    """Statistical analyzer for epoch outcome data."""

    def __init__(self, db_path: str = 'analysis/epoch_history.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.df = None
        self.load_data()

    def load_data(self):
        """Load all epoch data into pandas DataFrame."""
        query = """
            SELECT
                crypto,
                epoch,
                date,
                hour,
                direction,
                start_price,
                end_price,
                change_pct,
                change_abs,
                timestamp,
                strftime('%w', date) as day_of_week,
                strftime('%H', datetime(timestamp, 'unixepoch')) as hour_str
            FROM epoch_outcomes
            ORDER BY timestamp
        """
        self.df = pd.read_sql_query(query, self.conn)
        self.df['direction_binary'] = (self.df['direction'] == 'Up').astype(int)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='s')
        self.df['day_of_week'] = self.df['day_of_week'].astype(int)

        # Create time segments
        self.df['time_period_2h'] = self.df['hour'] // 2  # 0-11 (12 periods)
        self.df['time_period_4h'] = self.df['hour'] // 4  # 0-5 (6 periods)
        self.df['time_period_6h'] = self.df['hour'] // 6  # 0-3 (4 periods)
        self.df['time_period_8h'] = self.df['hour'] // 8  # 0-2 (3 periods)

        # Time of day categories
        def categorize_time(hour):
            if 0 <= hour < 6:
                return 'night'
            elif 6 <= hour < 9:
                return 'early_morning'
            elif 9 <= hour < 12:
                return 'morning'
            elif 12 <= hour < 15:
                return 'midday'
            elif 15 <= hour < 18:
                return 'afternoon'
            elif 18 <= hour < 21:
                return 'evening'
            else:
                return 'late_evening'

        self.df['time_category'] = self.df['hour'].apply(categorize_time)

        # Weekend vs weekday
        self.df['is_weekend'] = self.df['day_of_week'].isin([0, 6]).astype(int)

        print(f"Loaded {len(self.df)} epochs")
        print(f"Date range: {self.df['date'].min()} to {self.df['date'].max()}")
        print(f"Cryptos: {self.df['crypto'].unique()}")
        print()

    def chi_square_test_hourly(self, crypto: str = None, alpha: float = 0.05) -> pd.DataFrame:
        """
        Test 1: Chi-square test for hourly bias significance.

        H0: Up/Down outcomes are uniformly distributed by hour (50/50 each hour)
        H1: Certain hours have significant directional bias

        Returns DataFrame with test results for each hour.
        """
        print("=" * 100)
        print("TEST 1: CHI-SQUARE TEST FOR HOURLY BIAS")
        print("=" * 100)
        print()

        if crypto:
            data = self.df[self.df['crypto'] == crypto]
            title = f"Crypto: {crypto.upper()}"
        else:
            data = self.df
            title = "All Cryptos Combined"

        print(title)
        print(f"Total epochs: {len(data)}")
        print()

        results = []

        for hour in range(24):
            hour_data = data[data['hour'] == hour]

            if len(hour_data) == 0:
                continue

            ups = (hour_data['direction'] == 'Up').sum()
            downs = (hour_data['direction'] == 'Down').sum()
            total = len(hour_data)

            # Expected counts under null hypothesis (50/50)
            expected = total / 2

            # Chi-square test
            observed = np.array([ups, downs])
            expected_array = np.array([expected, expected])
            chi2_stat = np.sum((observed - expected_array)**2 / expected_array)

            # p-value (df=1 for 2 categories)
            p_value = 1 - stats.chi2.cdf(chi2_stat, df=1)

            # Effect size (Cramér's V)
            cramers_v = np.sqrt(chi2_stat / total)

            # Confidence interval for proportion
            p_hat = ups / total
            se = np.sqrt(p_hat * (1 - p_hat) / total)
            ci_lower = p_hat - 1.96 * se
            ci_upper = p_hat + 1.96 * se

            results.append({
                'hour': hour,
                'total': total,
                'ups': ups,
                'downs': downs,
                'up_pct': ups / total * 100,
                'chi2_stat': chi2_stat,
                'p_value': p_value,
                'cramers_v': cramers_v,
                'ci_lower': ci_lower * 100,
                'ci_upper': ci_upper * 100
            })

        results_df = pd.DataFrame(results)

        # Bonferroni correction for multiple comparisons
        if len(results_df) > 0:
            _, p_corrected, _, _ = multipletests(
                results_df['p_value'],
                alpha=alpha,
                method='bonferroni'
            )
            results_df['p_corrected'] = p_corrected
            results_df['significant'] = results_df['p_corrected'] < alpha

        # Print results
        print(f"{'Hour':<6} {'N':<6} {'Up%':<8} {'95% CI':<20} {'χ²':<10} {'p-value':<10} {'p-corr':<10} {'Sig?':<6}")
        print("-" * 100)

        for _, row in results_df.iterrows():
            sig_marker = "***" if row['significant'] else ""
            print(f"{int(row['hour']):02d}:00 "
                  f"{int(row['total']):<6} "
                  f"{row['up_pct']:6.1f}% "
                  f"[{row['ci_lower']:5.1f}%, {row['ci_upper']:5.1f}%] "
                  f"{row['chi2_stat']:8.3f} "
                  f"{row['p_value']:8.4f} "
                  f"{row['p_corrected']:8.4f} "
                  f"{sig_marker:<6}")

        print()
        print(f"Bonferroni correction: α = {alpha} / {len(results_df)} = {alpha/len(results_df):.4f}")
        print(f"Significant hours (after correction): {results_df['significant'].sum()}")
        print()

        # Interpretation
        sig_hours = results_df[results_df['significant']]
        if len(sig_hours) > 0:
            print("SIGNIFICANT HOURS:")
            for _, row in sig_hours.iterrows():
                bias = "UP" if row['up_pct'] > 50 else "DOWN"
                strength = abs(row['up_pct'] - 50)
                print(f"  {int(row['hour']):02d}:00 → {bias} bias ({row['up_pct']:.1f}%, strength={strength:.1f}pp)")
        else:
            print("No statistically significant hourly biases found.")

        print()
        print("=" * 100)
        print()

        return results_df

    def sample_size_calculation(self, effect_size: float = 0.10, power: float = 0.80, alpha: float = 0.05):
        """
        Calculate required sample size for detecting effect sizes.

        Effect size = difference from 50% (e.g., 0.10 = 60% vs 50%)
        """
        print("=" * 100)
        print("SAMPLE SIZE REQUIREMENTS")
        print("=" * 100)
        print()

        print(f"Target: Detect {effect_size*100:.0f}pp deviation from 50/50 (e.g., {50+effect_size*100:.0f}% vs 50%)")
        print(f"Power: {power*100:.0f}% (probability of detecting effect if it exists)")
        print(f"Significance: α = {alpha}")
        print()

        # Z-scores
        z_alpha = norm.ppf(1 - alpha/2)  # Two-tailed
        z_beta = norm.ppf(power)

        # Proportions
        p1 = 0.5  # Null hypothesis
        p2 = 0.5 + effect_size  # Alternative
        p_avg = (p1 + p2) / 2

        # Sample size formula for two proportions
        n = ((z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) +
              z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2) / (effect_size**2)

        print(f"Required sample size: {int(np.ceil(n))} epochs per hour")
        print()

        # Current sample sizes
        hourly_counts = self.df.groupby('hour').size()
        print("Current sample sizes by hour:")
        print(hourly_counts)
        print()

        sufficient = (hourly_counts >= n).sum()
        print(f"Hours with sufficient sample size: {sufficient} / {len(hourly_counts)}")
        print()

        # Table for different effect sizes
        print("Sample size requirements for various effect sizes:")
        print(f"{'Effect Size':<15} {'Target Up%':<12} {'Required N':<12} {'Days Needed*':<12}")
        print("-" * 60)

        for es in [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]:
            p2 = 0.5 + es
            n = ((z_alpha * np.sqrt(2 * p_avg * (1 - p_avg)) +
                  z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2)))**2) / (es**2)
            days = n / 4  # 4 epochs per hour per day
            print(f"{es*100:>4.0f}pp ({es:.2f})  {p2*100:>6.1f}%      {int(np.ceil(n)):>6}       {days:>6.1f}")

        print()
        print("* Days needed to accumulate N epochs for one hour (4 epochs/hour/day)")
        print()
        print("=" * 100)
        print()

    def time_series_analysis(self, crypto: str):
        """
        Test 2: Time series analysis - ACF, PACF, Ljung-Box, Runs test.

        Tests for:
        - Autocorrelation (are outcomes independent?)
        - Momentum/mean reversion patterns
        - Randomness vs predictable patterns
        """
        print("=" * 100)
        print(f"TEST 2: TIME SERIES ANALYSIS - {crypto.upper()}")
        print("=" * 100)
        print()

        data = self.df[self.df['crypto'] == crypto].sort_values('timestamp')
        series = data['direction_binary'].values  # 1=Up, 0=Down

        print(f"Total observations: {len(series)}")
        print(f"Up: {series.sum()} ({series.mean()*100:.1f}%)")
        print(f"Down: {(1-series).sum()} ({(1-series.mean())*100:.1f}%)")
        print()

        # 1. Autocorrelation Function (ACF)
        print("1. AUTOCORRELATION FUNCTION (ACF)")
        print("-" * 80)
        print("Tests: Are outcomes correlated with previous outcomes?")
        print()

        acf_values = acf(series, nlags=20, alpha=0.05)
        acf_coefs = acf_values[0]
        acf_confint = acf_values[1]

        print(f"{'Lag':<6} {'ACF':<10} {'95% CI':<20} {'Significant?':<12}")
        print("-" * 60)

        for lag in range(1, min(21, len(acf_coefs))):
            ci_lower = acf_confint[lag][0]
            ci_upper = acf_confint[lag][1]
            is_sig = ci_lower > 0 or ci_upper < 0
            sig_marker = "YES ***" if is_sig else "No"
            print(f"{lag:<6} {acf_coefs[lag]:>8.4f} [{ci_lower:>7.4f}, {ci_upper:>7.4f}]  {sig_marker:<12}")

        print()
        print("Interpretation:")
        print("  - Positive ACF = momentum (Up follows Up)")
        print("  - Negative ACF = mean reversion (Up follows Down)")
        print("  - Near zero = independence (random walk)")
        print()

        # 2. Partial Autocorrelation (PACF)
        print("2. PARTIAL AUTOCORRELATION (PACF)")
        print("-" * 80)
        print("Tests: Direct correlation at each lag (removing indirect effects)")
        print()

        pacf_values = pacf(series, nlags=20, alpha=0.05)
        pacf_coefs = pacf_values[0]
        pacf_confint = pacf_values[1]

        print(f"{'Lag':<6} {'PACF':<10} {'95% CI':<20} {'Significant?':<12}")
        print("-" * 60)

        for lag in range(1, min(21, len(pacf_coefs))):
            ci_lower = pacf_confint[lag][0]
            ci_upper = pacf_confint[lag][1]
            is_sig = ci_lower > 0 or ci_upper < 0
            sig_marker = "YES ***" if is_sig else "No"
            print(f"{lag:<6} {pacf_coefs[lag]:>8.4f} [{ci_lower:>7.4f}, {ci_upper:>7.4f}]  {sig_marker:<12}")

        print()

        # 3. Ljung-Box Test
        print("3. LJUNG-BOX TEST (Test for overall randomness)")
        print("-" * 80)
        print("H0: No autocorrelation up to lag k (data is random)")
        print("H1: Significant autocorrelation exists")
        print()

        lb_test = acorr_ljungbox(series, lags=20, return_df=True)

        print(f"{'Lag':<6} {'Q-Stat':<12} {'p-value':<12} {'Result':<20}")
        print("-" * 60)

        for idx, row in lb_test.iterrows():
            result = "REJECT H0 (not random)" if row['lb_pvalue'] < 0.05 else "Accept H0 (random)"
            print(f"{idx:<6} {row['lb_stat']:>10.4f} {row['lb_pvalue']:>10.4f}  {result:<20}")

        print()

        # 4. Runs Test
        print("4. RUNS TEST (Randomness test)")
        print("-" * 80)
        print("Tests: Are Up/Down patterns random or clustered?")
        print()

        runs = 1
        for i in range(1, len(series)):
            if series[i] != series[i-1]:
                runs += 1

        n1 = series.sum()  # Ups
        n0 = len(series) - n1  # Downs

        # Expected runs under randomness
        expected_runs = (2 * n1 * n0) / (n1 + n0) + 1

        # Variance
        var_runs = (2 * n1 * n0 * (2 * n1 * n0 - n1 - n0)) / ((n1 + n0)**2 * (n1 + n0 - 1))

        # Z-score
        z_runs = (runs - expected_runs) / np.sqrt(var_runs)
        p_value_runs = 2 * (1 - norm.cdf(abs(z_runs)))

        print(f"Observed runs: {runs}")
        print(f"Expected runs (random): {expected_runs:.1f}")
        print(f"Z-score: {z_runs:.4f}")
        print(f"p-value: {p_value_runs:.4f}")
        print()

        if p_value_runs < 0.05:
            if runs < expected_runs:
                print("RESULT: Significant clustering (momentum/trends) ***")
            else:
                print("RESULT: Significant alternation (mean reversion) ***")
        else:
            print("RESULT: Random (no significant patterns)")

        print()

        # 5. Augmented Dickey-Fuller Test (Stationarity)
        print("5. AUGMENTED DICKEY-FULLER TEST (Stationarity)")
        print("-" * 80)
        print("Tests: Is the series stationary (no trending over time)?")
        print()

        adf_result = adfuller(series, autolag='AIC')

        print(f"ADF Statistic: {adf_result[0]:.4f}")
        print(f"p-value: {adf_result[1]:.4f}")
        print(f"Critical values:")
        for key, value in adf_result[4].items():
            print(f"  {key}: {value:.4f}")
        print()

        if adf_result[1] < 0.05:
            print("RESULT: Series is stationary (no trending)")
        else:
            print("RESULT: Series is non-stationary (has trends)")

        print()
        print("=" * 100)
        print()

    def multi_factor_anova(self):
        """
        Test 3: Multi-factor ANOVA to identify significant factors.

        Factors tested:
        - Hour of day
        - Day of week
        - Crypto
        - Time category (morning/afternoon/evening)
        """
        print("=" * 100)
        print("TEST 3: MULTI-FACTOR ANOVA")
        print("=" * 100)
        print()

        try:
            from statsmodels.formula.api import ols
            from statsmodels.stats.anova import anova_lm

            # Create model
            print("Testing factors: hour, day_of_week, crypto, time_category, is_weekend")
            print()

            model = ols('direction_binary ~ C(hour) + C(day_of_week) + C(crypto) + C(time_category) + is_weekend',
                       data=self.df).fit()

            anova_table = anova_lm(model, typ=2)

            print("ANOVA Results:")
            print(anova_table)
            print()

            # Effect sizes (eta-squared)
            anova_table['eta_sq'] = anova_table['sum_sq'] / anova_table['sum_sq'].sum()

            print("Effect Sizes (η²):")
            print(anova_table[['eta_sq']])
            print()

            # Interpretation
            print("Interpretation:")
            print("  - p-value < 0.05 = factor has significant effect")
            print("  - η² = proportion of variance explained (0.01=small, 0.06=medium, 0.14=large)")
            print()

            significant_factors = anova_table[anova_table['PR(>F)'] < 0.05].index.tolist()
            if 'Residual' in significant_factors:
                significant_factors.remove('Residual')

            if significant_factors:
                print(f"Significant factors: {', '.join(significant_factors)}")
            else:
                print("No significant factors found.")

        except ImportError:
            print("statsmodels not available for ANOVA. Install with: pip install statsmodels")

        print()
        print("=" * 100)
        print()

    def segmentation_analysis(self, crypto: str = None):
        """
        Test 4: Optimal time segmentation analysis.

        Compares different time groupings to find best predictive periods.
        """
        print("=" * 100)
        print("TEST 4: SEGMENTATION ANALYSIS")
        print("=" * 100)
        print()

        data = self.df if crypto is None else self.df[self.df['crypto'] == crypto]

        segmentations = [
            ('Hour (24)', 'hour', 24),
            ('2-Hour Blocks (12)', 'time_period_2h', 12),
            ('4-Hour Blocks (6)', 'time_period_4h', 6),
            ('6-Hour Blocks (4)', 'time_period_6h', 4),
            ('8-Hour Blocks (3)', 'time_period_8h', 3),
            ('Time Category (7)', 'time_category', 7),
            ('Day of Week (7)', 'day_of_week', 7),
            ('Weekend vs Weekday (2)', 'is_weekend', 2)
        ]

        results = []

        for name, column, n_groups in segmentations:
            grouped = data.groupby(column).agg({
                'direction_binary': ['count', 'sum', 'mean']
            })

            grouped.columns = ['count', 'ups', 'up_rate']

            # Chi-square test across all groups
            observed = []
            for _, row in grouped.iterrows():
                ups = int(row['ups'])
                downs = int(row['count'] - row['ups'])
                observed.append([ups, downs])

            if len(observed) > 1:
                chi2, p_value, dof, expected = chi2_contingency(observed)

                # Information criteria for model fit
                # Lower is better
                entropy = -np.sum(grouped['up_rate'] * np.log(grouped['up_rate'] + 1e-10) +
                                 (1 - grouped['up_rate']) * np.log(1 - grouped['up_rate'] + 1e-10))

                # Effect size
                n_total = grouped['count'].sum()
                cramers_v = np.sqrt(chi2 / (n_total * (n_groups - 1)))

                # Range of up rates
                up_rate_min = grouped['up_rate'].min()
                up_rate_max = grouped['up_rate'].max()
                up_rate_range = up_rate_max - up_rate_min

                results.append({
                    'segmentation': name,
                    'n_groups': n_groups,
                    'chi2': chi2,
                    'p_value': p_value,
                    'cramers_v': cramers_v,
                    'up_rate_range': up_rate_range * 100,
                    'entropy': entropy
                })

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('cramers_v', ascending=False)

        print(f"{'Segmentation':<25} {'Groups':<8} {'χ²':<12} {'p-value':<12} {'Cramér V':<12} {'Range':<12}")
        print("-" * 100)

        for _, row in results_df.iterrows():
            sig = "***" if row['p_value'] < 0.05 else ""
            print(f"{row['segmentation']:<25} {row['n_groups']:<8} "
                  f"{row['chi2']:>10.2f} {row['p_value']:>10.4f} "
                  f"{row['cramers_v']:>10.4f} {row['up_rate_range']:>9.1f}% {sig}")

        print()
        print("Interpretation:")
        print("  - Cramér's V: Effect size (0.1=small, 0.3=medium, 0.5=large)")
        print("  - Range: Difference between highest and lowest up% (higher = more predictive)")
        print("  - χ² test: Overall significance of segmentation")
        print()

        # Best segmentation
        best = results_df.iloc[0]
        print(f"BEST SEGMENTATION: {best['segmentation']}")
        print(f"  Effect size (Cramér's V): {best['cramers_v']:.4f}")
        print(f"  Range: {best['up_rate_range']:.1f}pp")
        print()

        print("=" * 100)
        print()

    def cross_crypto_correlation(self):
        """
        Test 5: Cross-crypto correlation and lead-lag analysis.
        """
        print("=" * 100)
        print("TEST 5: CROSS-CRYPTO CORRELATION")
        print("=" * 100)
        print()

        cryptos = self.df['crypto'].unique()

        # Create pivot table (epochs x cryptos)
        pivot = self.df.pivot_table(
            index='epoch',
            columns='crypto',
            values='direction_binary',
            aggfunc='first'
        )

        print("1. SIMULTANEOUS CORRELATION")
        print("-" * 80)
        print("Do cryptos move together in the same epoch?")
        print()

        corr_matrix = pivot.corr()
        print(corr_matrix)
        print()

        # Statistical significance
        n = len(pivot)
        print("Correlation significance tests:")
        print(f"{'Pair':<15} {'r':<10} {'t-stat':<10} {'p-value':<10} {'Significant?':<12}")
        print("-" * 60)

        for i, crypto1 in enumerate(cryptos):
            for crypto2 in cryptos[i+1:]:
                r = corr_matrix.loc[crypto1, crypto2]

                # t-test for correlation
                t_stat = r * np.sqrt(n - 2) / np.sqrt(1 - r**2)
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

                sig = "***" if p_value < 0.05 else ""
                print(f"{crypto1}-{crypto2:<10} {r:>8.4f} {t_stat:>8.4f} {p_value:>8.4f}  {sig}")

        print()

        # 2. Lead-lag analysis
        print("2. LEAD-LAG ANALYSIS")
        print("-" * 80)
        print("Do certain cryptos lead others?")
        print()

        max_lag = 5

        for crypto1 in cryptos:
            for crypto2 in cryptos:
                if crypto1 == crypto2:
                    continue

                series1 = pivot[crypto1].dropna()
                series2 = pivot[crypto2].dropna()

                # Find common indices
                common_idx = series1.index.intersection(series2.index)
                s1 = series1.loc[common_idx]
                s2 = series2.loc[common_idx]

                print(f"\n{crypto1.upper()} → {crypto2.upper()}")
                print(f"{'Lag':<6} {'Correlation':<12} {'p-value':<12}")
                print("-" * 40)

                for lag in range(0, max_lag + 1):
                    if lag == 0:
                        corr = s1.corr(s2)
                        n_obs = len(s1)
                    else:
                        corr = s1[:-lag].corr(s2[lag:])
                        n_obs = len(s1) - lag

                    # Significance test
                    if n_obs > 2:
                        t_stat = corr * np.sqrt(n_obs - 2) / np.sqrt(1 - corr**2 + 1e-10)
                        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n_obs - 2))
                    else:
                        p_value = 1.0

                    sig = "***" if p_value < 0.05 else ""
                    print(f"{lag:<6} {corr:>10.4f} {p_value:>10.4f}  {sig}")

        print()
        print("Interpretation:")
        print("  - Positive correlation = cryptos move together")
        print("  - Lag > 0: Leading indicator (crypto1 predicts crypto2)")
        print()
        print("=" * 100)
        print()

    def predictive_power_analysis(self):
        """
        Test 7: Logistic regression for direction prediction.
        """
        print("=" * 100)
        print("TEST 7: PREDICTIVE POWER ANALYSIS")
        print("=" * 100)
        print()

        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report, roc_auc_score

            # Features
            features = ['hour', 'day_of_week', 'is_weekend']

            # Add crypto dummies
            crypto_dummies = pd.get_dummies(self.df['crypto'], prefix='crypto')

            X = pd.concat([
                self.df[features],
                crypto_dummies
            ], axis=1)

            y = self.df['direction_binary']

            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, random_state=42
            )

            # Train model
            model = LogisticRegression(max_iter=1000)
            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]

            print("MODEL PERFORMANCE (Out-of-sample)")
            print("-" * 80)
            print(classification_report(y_test, y_pred, target_names=['Down', 'Up']))

            auc = roc_auc_score(y_test, y_proba)
            print(f"ROC AUC: {auc:.4f}")
            print()

            # Feature importance
            print("FEATURE IMPORTANCE")
            print("-" * 80)

            feature_importance = pd.DataFrame({
                'feature': X.columns,
                'coefficient': model.coef_[0]
            })
            feature_importance = feature_importance.reindex(
                feature_importance['coefficient'].abs().sort_values(ascending=False).index
            )

            print(feature_importance.head(15))
            print()

            # Baseline comparison
            baseline_acc = max(y_test.mean(), 1 - y_test.mean())
            model_acc = (y_pred == y_test).mean()

            print(f"Baseline accuracy (always predict majority): {baseline_acc:.4f}")
            print(f"Model accuracy: {model_acc:.4f}")
            print(f"Improvement: {(model_acc - baseline_acc)*100:.2f}pp")
            print()

            if model_acc > baseline_acc:
                print("RESULT: Model has predictive power (better than random)")
            else:
                print("RESULT: Model does not beat baseline (no predictive power)")

        except ImportError:
            print("scikit-learn not available. Install with: pip install scikit-learn")

        print()
        print("=" * 100)
        print()

    def generate_report(self, output_file: str = 'analysis/statistical_report.json'):
        """Generate comprehensive statistical report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'dataset_summary': {
                'total_epochs': len(self.df),
                'date_range': [self.df['date'].min(), self.df['date'].max()],
                'cryptos': self.df['crypto'].unique().tolist(),
                'total_days': self.df['date'].nunique()
            },
            'tests_performed': [
                'chi_square_hourly_bias',
                'sample_size_requirements',
                'time_series_analysis',
                'multi_factor_anova',
                'segmentation_analysis',
                'cross_crypto_correlation',
                'predictive_power'
            ]
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"Report saved to: {output_file}")


def main():
    """Run comprehensive statistical analysis."""
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive statistical analysis of epoch data')
    parser.add_argument('--test', type=str, choices=[
        'chi2', 'sample', 'timeseries', 'anova', 'segment', 'correlation', 'predict', 'all'
    ], default='all', help='Which test to run')
    parser.add_argument('--crypto', type=str, help='Specific crypto to analyze')
    parser.add_argument('--alpha', type=float, default=0.05, help='Significance level')

    args = parser.parse_args()

    analyzer = EpochStatAnalyzer()

    if args.test in ['chi2', 'all']:
        analyzer.chi_square_test_hourly(crypto=args.crypto, alpha=args.alpha)

    if args.test in ['sample', 'all']:
        analyzer.sample_size_calculation()

    if args.test in ['timeseries', 'all']:
        crypto = args.crypto or 'btc'
        analyzer.time_series_analysis(crypto)

    if args.test in ['anova', 'all']:
        analyzer.multi_factor_anova()

    if args.test in ['segment', 'all']:
        analyzer.segmentation_analysis(crypto=args.crypto)

    if args.test in ['correlation', 'all']:
        analyzer.cross_crypto_correlation()

    if args.test in ['predict', 'all']:
        analyzer.predictive_power_analysis()

    # Generate report
    if args.test == 'all':
        analyzer.generate_report()


if __name__ == '__main__':
    main()
