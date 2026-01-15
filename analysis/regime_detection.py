#!/usr/bin/env python3
"""
Regime Detection using Hidden Markov Models

Detects hidden market regimes (states) that influence outcome probabilities.

Potential regimes:
- Bull regime (high up probability)
- Bear regime (high down probability)
- Choppy/neutral regime (50/50)
- Volatile regime (rapid switching)
"""

import sqlite3
import numpy as np
import pandas as pd
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')


class RegimeDetector:
    """Detect market regimes using HMM and change point detection."""

    def __init__(self, db_path: str = 'analysis/epoch_history.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.df = None
        self.load_data()

    def load_data(self):
        """Load epoch data."""
        query = """
            SELECT
                crypto,
                epoch,
                date,
                hour,
                direction,
                change_pct,
                timestamp
            FROM epoch_outcomes
            ORDER BY timestamp
        """
        self.df = pd.read_sql_query(query, self.conn)
        self.df['direction_binary'] = (self.df['direction'] == 'Up').astype(int)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='s')

    def simple_regime_detection(self, crypto: str, window: int = 20) -> pd.DataFrame:
        """
        Simple regime detection using rolling statistics.

        Classifies regimes based on recent win rates:
        - Bull: >60% ups in rolling window
        - Bear: <40% ups in rolling window
        - Neutral: 40-60% ups
        """
        print("=" * 100)
        print(f"SIMPLE REGIME DETECTION - {crypto.upper()}")
        print("=" * 100)
        print()

        data = self.df[self.df['crypto'] == crypto].copy()

        # Rolling win rate
        data['rolling_up_rate'] = data['direction_binary'].rolling(
            window=window, min_periods=window//2
        ).mean()

        # Classify regime
        def classify_regime(up_rate):
            if pd.isna(up_rate):
                return 'unknown'
            elif up_rate > 0.60:
                return 'bull'
            elif up_rate < 0.40:
                return 'bear'
            else:
                return 'neutral'

        data['regime'] = data['rolling_up_rate'].apply(classify_regime)

        print(f"Window size: {window} epochs ({window * 15} minutes)")
        print()

        # Regime statistics
        regime_stats = data.groupby('regime').agg({
            'direction_binary': ['count', 'mean'],
            'change_pct': ['mean', 'std']
        })

        regime_stats.columns = ['count', 'up_rate', 'avg_change', 'volatility']

        print("REGIME STATISTICS")
        print("-" * 80)
        print(regime_stats)
        print()

        # Transition matrix
        print("REGIME TRANSITION MATRIX")
        print("-" * 80)

        transitions = pd.crosstab(
            data['regime'].shift(1),
            data['regime'],
            normalize='index'
        ) * 100

        print(transitions)
        print()

        # Regime persistence
        print("REGIME PERSISTENCE")
        print("-" * 80)

        for regime in ['bull', 'bear', 'neutral']:
            regime_data = data[data['regime'] == regime]
            if len(regime_data) > 0:
                # How long does regime last?
                regime_lengths = []
                current_length = 0

                for idx, row in data.iterrows():
                    if row['regime'] == regime:
                        current_length += 1
                    elif current_length > 0:
                        regime_lengths.append(current_length)
                        current_length = 0

                if current_length > 0:
                    regime_lengths.append(current_length)

                if regime_lengths:
                    avg_length = np.mean(regime_lengths)
                    max_length = np.max(regime_lengths)
                    print(f"{regime.upper():<10} "
                          f"Avg duration: {avg_length:.1f} epochs ({avg_length*15:.0f} min), "
                          f"Max: {max_length} epochs ({max_length*15:.0f} min)")

        print()
        print("=" * 100)
        print()

        return data

    def hmm_regime_detection(self, crypto: str, n_states: int = 3):
        """
        Hidden Markov Model regime detection.

        Requires hmmlearn package.
        """
        print("=" * 100)
        print(f"HIDDEN MARKOV MODEL - {crypto.upper()}")
        print("=" * 100)
        print()

        try:
            from hmmlearn import hmm as hmm_lib

            data = self.df[self.df['crypto'] == crypto].copy()

            # Features: direction (0/1) and change magnitude
            X = data[['direction_binary', 'change_pct']].values

            # Fit HMM
            print(f"Fitting {n_states}-state Hidden Markov Model...")
            model = hmm_lib.GaussianHMM(
                n_components=n_states,
                covariance_type='full',
                n_iter=100,
                random_state=42
            )

            model.fit(X)

            # Predict states
            states = model.predict(X)
            data['hmm_state'] = states

            print(f"Model converged: {model.monitor_.converged}")
            print()

            # State statistics
            print("STATE STATISTICS")
            print("-" * 80)

            for state in range(n_states):
                state_data = data[data['hmm_state'] == state]
                up_rate = state_data['direction_binary'].mean()
                avg_change = state_data['change_pct'].mean()
                count = len(state_data)

                # Classify state
                if up_rate > 0.60:
                    label = "BULL"
                elif up_rate < 0.40:
                    label = "BEAR"
                else:
                    label = "NEUTRAL"

                print(f"State {state} ({label}):")
                print(f"  Occurrences: {count} ({count/len(data)*100:.1f}%)")
                print(f"  Up rate: {up_rate*100:.1f}%")
                print(f"  Avg change: {avg_change:+.3f}%")
                print()

            # Transition matrix
            print("TRANSITION MATRIX")
            print("-" * 80)
            print("Probability of moving from state i (row) to state j (column)")
            print()

            trans_matrix = pd.DataFrame(
                model.transmat_,
                index=[f"State {i}" for i in range(n_states)],
                columns=[f"State {i}" for i in range(n_states)]
            )
            print(trans_matrix)
            print()

            # State means and covariances
            print("STATE PARAMETERS")
            print("-" * 80)
            for state in range(n_states):
                print(f"State {state}:")
                print(f"  Mean: {model.means_[state]}")
                print(f"  Covariance:\n{model.covars_[state]}")
                print()

            print("=" * 100)
            print()

            return data

        except ImportError:
            print("hmmlearn not available.")
            print("Install with: pip install hmmlearn")
            print()
            print("=" * 100)
            print()
            return None

    def change_point_detection(self, crypto: str, min_size: int = 30):
        """
        Change point detection using PELT algorithm.

        Detects points where statistical properties change.
        """
        print("=" * 100)
        print(f"CHANGE POINT DETECTION - {crypto.upper()}")
        print("=" * 100)
        print()

        try:
            import ruptures as rpt

            data = self.df[self.df['crypto'] == crypto].copy()
            signal = data['direction_binary'].values.reshape(-1, 1)

            # PELT algorithm
            print("Running PELT change point detection...")
            model = "l2"  # Cost function
            algo = rpt.Pelt(model=model, min_size=min_size).fit(signal)

            # Detect change points
            result = algo.predict(pen=3)  # Penalty parameter

            print(f"Detected {len(result)-1} change points")
            print()

            # Analyze segments
            print("SEGMENTS")
            print("-" * 80)
            print(f"{'Segment':<10} {'Start':<20} {'End':<20} {'Duration':<12} {'Up Rate':<10}")
            print("-" * 80)

            change_points = [0] + result[:-1] + [len(data)]

            for i in range(len(change_points) - 1):
                start_idx = change_points[i]
                end_idx = change_points[i + 1]

                segment = data.iloc[start_idx:end_idx]

                start_time = segment['timestamp'].iloc[0]
                end_time = segment['timestamp'].iloc[-1]
                duration = len(segment)
                up_rate = segment['direction_binary'].mean()

                print(f"{i+1:<10} "
                      f"{start_time.strftime('%m-%d %H:%M'):<20} "
                      f"{end_time.strftime('%m-%d %H:%M'):<20} "
                      f"{duration:<12} "
                      f"{up_rate*100:>7.1f}%")

            print()
            print("=" * 100)
            print()

        except ImportError:
            print("ruptures not available.")
            print("Install with: pip install ruptures")
            print()
            print("=" * 100)
            print()

    def momentum_regime_classification(self, crypto: str, lookback: int = 10):
        """
        Classify regimes based on momentum patterns.

        Uses recent sequence of outcomes to classify regime.
        """
        print("=" * 100)
        print(f"MOMENTUM REGIME CLASSIFICATION - {crypto.upper()}")
        print("=" * 100)
        print()

        data = self.df[self.df['crypto'] == crypto].copy()

        # Calculate momentum features
        data['up_streak'] = 0
        data['down_streak'] = 0

        up_streak = 0
        down_streak = 0

        for idx, row in data.iterrows():
            if row['direction'] == 'Up':
                up_streak += 1
                down_streak = 0
            else:
                down_streak += 1
                up_streak = 0

            data.at[idx, 'up_streak'] = up_streak
            data.at[idx, 'down_streak'] = down_streak

        # Rolling momentum
        data['momentum'] = data['direction_binary'].rolling(
            window=lookback
        ).mean() - 0.5  # Centered at 0

        # Volatility (how much switching?)
        data['volatility'] = data['direction_binary'].rolling(
            window=lookback
        ).std()

        # Classify regime
        def classify_momentum_regime(row):
            if pd.isna(row['momentum']) or pd.isna(row['volatility']):
                return 'unknown'

            momentum = row['momentum']
            volatility = row['volatility']

            # Strong momentum + low volatility = trending
            if abs(momentum) > 0.15 and volatility < 0.45:
                return 'trending_bull' if momentum > 0 else 'trending_bear'

            # Weak momentum + high volatility = choppy
            elif abs(momentum) < 0.10 and volatility > 0.45:
                return 'choppy'

            # Medium momentum = weak trend
            elif momentum > 0.10:
                return 'weak_bull'
            elif momentum < -0.10:
                return 'weak_bear'
            else:
                return 'neutral'

        data['momentum_regime'] = data.apply(classify_momentum_regime, axis=1)

        # Statistics by regime
        print("MOMENTUM REGIME STATISTICS")
        print("-" * 80)

        regime_stats = data.groupby('momentum_regime').agg({
            'direction_binary': ['count', 'mean'],
            'change_pct': ['mean', 'std']
        })

        regime_stats.columns = ['count', 'up_rate', 'avg_change', 'volatility']
        regime_stats = regime_stats.sort_values('count', ascending=False)

        print(regime_stats)
        print()

        # Most profitable regimes
        print("REGIME PROFITABILITY (assuming bet on predicted direction)")
        print("-" * 80)

        for regime in data['momentum_regime'].unique():
            if regime == 'unknown':
                continue

            regime_data = data[data['momentum_regime'] == regime]

            # If bull regime, bet up; if bear, bet down
            if 'bull' in regime:
                correct = regime_data['direction_binary'].sum()
            elif 'bear' in regime:
                correct = (1 - regime_data['direction_binary']).sum()
            else:
                # For neutral/choppy, assume we don't bet
                correct = 0

            total = len(regime_data)
            win_rate = correct / total if total > 0 else 0

            print(f"{regime:<20} N={total:<6} Win rate: {win_rate*100:>6.1f}%")

        print()
        print("=" * 100)
        print()

        return data


def main():
    """Run regime detection analysis."""
    import argparse

    parser = argparse.ArgumentParser(description='Regime detection analysis')
    parser.add_argument('--crypto', type=str, default='btc', help='Crypto to analyze')
    parser.add_argument('--method', type=str, choices=[
        'simple', 'hmm', 'changepoint', 'momentum', 'all'
    ], default='all', help='Detection method')
    parser.add_argument('--window', type=int, default=20, help='Window size for rolling stats')
    parser.add_argument('--states', type=int, default=3, help='Number of HMM states')

    args = parser.parse_args()

    detector = RegimeDetector()

    if args.method in ['simple', 'all']:
        detector.simple_regime_detection(args.crypto, window=args.window)

    if args.method in ['hmm', 'all']:
        detector.hmm_regime_detection(args.crypto, n_states=args.states)

    if args.method in ['changepoint', 'all']:
        detector.change_point_detection(args.crypto)

    if args.method in ['momentum', 'all']:
        detector.momentum_regime_classification(args.crypto)


if __name__ == '__main__':
    main()
