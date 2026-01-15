#!/usr/bin/env python3
"""
Pattern Mining and Association Rules

Discovers sequential patterns and association rules:
- Frequent itemsets (e.g., "if hour=14 and BTC up, then ETH up")
- Sequential patterns (e.g., "3 ups in a row → likely down next")
- Market basket analysis adapted to time series
- Conditional probabilities
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, List, Tuple, Set
from collections import defaultdict, Counter
from itertools import combinations

sys.path.append(str(Path(__file__).parent.parent))


class PatternMiner:
    """Mine frequent patterns and association rules from epoch data."""

    def __init__(self, db_path: str = 'analysis/epoch_history.db'):
        self.db_path = db_path
        self.load_data()

    def load_data(self):
        """Load data from database."""
        conn = sqlite3.connect(self.db_path)

        query = '''
            SELECT
                crypto,
                epoch,
                date,
                hour,
                direction,
                change_pct
            FROM epoch_outcomes
            ORDER BY epoch, crypto
        '''

        self.df = pd.read_sql_query(query, conn)
        conn.close()

        self.df['target'] = (self.df['direction'] == 'Up').astype(int)
        self.df['datetime'] = pd.to_datetime(self.df['epoch'], unit='s')
        self.df['day_of_week'] = self.df['datetime'].dt.dayofweek

    def create_epoch_transactions(self) -> List[Set[str]]:
        """
        Create 'transactions' for each epoch (like market basket).

        Each transaction contains items like:
        - 'btc_up', 'eth_down', 'hour_14', 'monday', etc.

        Returns:
            List of sets, where each set is an epoch's features
        """
        transactions = []

        # Group by epoch (all cryptos in same epoch = one transaction)
        for epoch, group in self.df.groupby('epoch'):
            items = set()

            # Add crypto directions
            for _, row in group.iterrows():
                crypto = row['crypto']
                direction = 'up' if row['target'] == 1 else 'down'
                items.add(f'{crypto}_{direction}')

            # Add temporal features (same for all cryptos in epoch)
            hour = group.iloc[0]['hour']
            dow = group.iloc[0]['day_of_week']

            items.add(f'hour_{hour}')
            items.add(f'dow_{dow}')

            # Add time blocks
            if 0 <= hour < 6:
                items.add('night')
            elif 6 <= hour < 12:
                items.add('morning')
            elif 12 <= hour < 18:
                items.add('afternoon')
            else:
                items.add('evening')

            transactions.append(items)

        return transactions

    def apriori_frequent_itemsets(self, transactions: List[Set[str]],
                                  min_support: float = 0.1,
                                  max_length: int = 3) -> Dict[frozenset, float]:
        """
        Find frequent itemsets using Apriori algorithm.

        Args:
            transactions: List of item sets
            min_support: Minimum support threshold (0-1)
            max_length: Maximum itemset length

        Returns:
            Dict mapping itemsets to their support
        """
        n_transactions = len(transactions)
        min_count = int(min_support * n_transactions)

        # Count 1-itemsets
        item_counts = defaultdict(int)
        for transaction in transactions:
            for item in transaction:
                item_counts[item] += 1

        # Filter by min support
        frequent_itemsets = {
            frozenset([item]): count / n_transactions
            for item, count in item_counts.items()
            if count >= min_count
        }

        # Generate larger itemsets
        for length in range(2, max_length + 1):
            # Generate candidates
            prev_itemsets = [itemset for itemset in frequent_itemsets.keys()
                           if len(itemset) == length - 1]

            candidates = set()
            for i, itemset1 in enumerate(prev_itemsets):
                for itemset2 in prev_itemsets[i+1:]:
                    union = itemset1 | itemset2
                    if len(union) == length:
                        candidates.add(union)

            # Count candidates
            candidate_counts = defaultdict(int)
            for transaction in transactions:
                for candidate in candidates:
                    if candidate.issubset(transaction):
                        candidate_counts[candidate] += 1

            # Add frequent candidates
            for candidate, count in candidate_counts.items():
                if count >= min_count:
                    frequent_itemsets[candidate] = count / n_transactions

        return frequent_itemsets

    def generate_association_rules(self, frequent_itemsets: Dict[frozenset, float],
                                   min_confidence: float = 0.65) -> List[Dict]:
        """
        Generate association rules from frequent itemsets.

        Rule format: antecedent -> consequent (confidence, lift)

        Args:
            frequent_itemsets: Dict of itemsets with their support
            min_confidence: Minimum confidence threshold

        Returns:
            List of rules as dicts
        """
        rules = []

        # Only generate rules from itemsets of size 2+
        for itemset, support in frequent_itemsets.items():
            if len(itemset) < 2:
                continue

            # Generate all possible splits
            for i in range(1, len(itemset)):
                for antecedent in combinations(itemset, i):
                    antecedent = frozenset(antecedent)
                    consequent = itemset - antecedent

                    # Calculate confidence
                    antecedent_support = frequent_itemsets.get(antecedent, 0)

                    if antecedent_support > 0:
                        confidence = support / antecedent_support

                        # Calculate lift
                        consequent_support = frequent_itemsets.get(consequent, 0)
                        if consequent_support > 0:
                            lift = confidence / consequent_support
                        else:
                            lift = 0

                        if confidence >= min_confidence:
                            rules.append({
                                'antecedent': set(antecedent),
                                'consequent': set(consequent),
                                'support': support,
                                'confidence': confidence,
                                'lift': lift
                            })

        # Sort by confidence
        rules.sort(key=lambda x: x['confidence'], reverse=True)

        return rules

    def sequential_pattern_mining(self, crypto: str, sequence_length: int = 3) -> Dict:
        """
        Find sequential patterns (e.g., "3 ups in a row -> down").

        Args:
            crypto: Crypto to analyze
            sequence_length: Length of sequences to analyze

        Returns:
            Dict with sequence patterns and their next-epoch probabilities
        """
        crypto_df = self.df[self.df['crypto'] == crypto].sort_values('epoch')
        directions = crypto_df['target'].values

        # Build sequences
        sequence_counts = defaultdict(lambda: {'next_up': 0, 'next_down': 0})

        for i in range(len(directions) - sequence_length):
            sequence = tuple(directions[i:i+sequence_length])
            next_direction = directions[i + sequence_length]

            if next_direction == 1:
                sequence_counts[sequence]['next_up'] += 1
            else:
                sequence_counts[sequence]['next_down'] += 1

        # Calculate probabilities
        patterns = []
        for sequence, counts in sequence_counts.items():
            total = counts['next_up'] + counts['next_down']
            if total >= 5:  # Minimum occurrences
                prob_up = counts['next_up'] / total * 100

                patterns.append({
                    'sequence': sequence,
                    'sequence_str': ''.join(['↑' if x == 1 else '↓' for x in sequence]),
                    'total_occurrences': total,
                    'prob_next_up': prob_up,
                    'prob_next_down': 100 - prob_up,
                    'next_ups': counts['next_up'],
                    'next_downs': counts['next_down']
                })

        # Sort by total occurrences
        patterns.sort(key=lambda x: x['total_occurrences'], reverse=True)

        return patterns

    def crypto_correlation_patterns(self) -> pd.DataFrame:
        """
        Find patterns of cross-crypto correlations.

        Example: "When BTC goes up, ETH goes up 70% of the time"
        """
        results = []

        # Group by epoch
        epoch_groups = self.df.groupby('epoch')

        for crypto1 in ['btc', 'eth', 'sol', 'xrp']:
            for crypto2 in ['btc', 'eth', 'sol', 'xrp']:
                if crypto1 >= crypto2:  # Avoid duplicates
                    continue

                co_occurrences = {
                    'both_up': 0,
                    'both_down': 0,
                    'c1_up_c2_down': 0,
                    'c1_down_c2_up': 0
                }

                for epoch, group in epoch_groups:
                    c1_data = group[group['crypto'] == crypto1]
                    c2_data = group[group['crypto'] == crypto2]

                    if len(c1_data) == 0 or len(c2_data) == 0:
                        continue

                    c1_up = c1_data.iloc[0]['target'] == 1
                    c2_up = c2_data.iloc[0]['target'] == 1

                    if c1_up and c2_up:
                        co_occurrences['both_up'] += 1
                    elif not c1_up and not c2_up:
                        co_occurrences['both_down'] += 1
                    elif c1_up and not c2_up:
                        co_occurrences['c1_up_c2_down'] += 1
                    else:
                        co_occurrences['c1_down_c2_up'] += 1

                total = sum(co_occurrences.values())

                if total > 0:
                    # Calculate conditional probabilities
                    c1_ups = co_occurrences['both_up'] + co_occurrences['c1_up_c2_down']
                    prob_c2_up_given_c1_up = (co_occurrences['both_up'] / c1_ups * 100) if c1_ups > 0 else 0

                    c1_downs = co_occurrences['both_down'] + co_occurrences['c1_down_c2_up']
                    prob_c2_up_given_c1_down = (co_occurrences['c1_down_c2_up'] / c1_downs * 100) if c1_downs > 0 else 0

                    results.append({
                        'crypto1': crypto1,
                        'crypto2': crypto2,
                        'total_epochs': total,
                        'prob_c2_up_if_c1_up': prob_c2_up_given_c1_up,
                        'prob_c2_up_if_c1_down': prob_c2_up_given_c1_down,
                        'correlation': 'positive' if prob_c2_up_given_c1_up > 60 else 'negative' if prob_c2_up_given_c1_up < 40 else 'neutral'
                    })

        return pd.DataFrame(results)

    def hourly_conditional_patterns(self, crypto: str) -> pd.DataFrame:
        """
        Find conditional patterns based on hour.

        Example: "At hour 14, if previous epoch was up, next epoch is up 65% of time"
        """
        crypto_df = self.df[self.df['crypto'] == crypto].sort_values('epoch')
        results = []

        for hour in range(24):
            hour_data = crypto_df[crypto_df['hour'] == hour].copy()

            if len(hour_data) < 10:
                continue

            # Add previous direction
            hour_data['prev_direction'] = hour_data['target'].shift(1)
            hour_data = hour_data.dropna()

            # Conditional probabilities
            prev_up = hour_data[hour_data['prev_direction'] == 1]
            prev_down = hour_data[hour_data['prev_direction'] == 0]

            if len(prev_up) > 0:
                prob_up_given_prev_up = prev_up['target'].mean() * 100
            else:
                prob_up_given_prev_up = 50

            if len(prev_down) > 0:
                prob_up_given_prev_down = prev_down['target'].mean() * 100
            else:
                prob_up_given_prev_down = 50

            results.append({
                'hour': hour,
                'total_epochs': len(hour_data),
                'prob_up_if_prev_up': prob_up_given_prev_up,
                'prob_up_if_prev_down': prob_up_given_prev_down,
                'mean_reversion': prob_up_given_prev_down > prob_up_given_prev_up,
                'momentum': prob_up_given_prev_up > prob_up_given_prev_down
            })

        return pd.DataFrame(results)


def main():
    """Main pattern mining pipeline."""
    print("="*100)
    print("PATTERN MINING & ASSOCIATION RULES")
    print("="*100)
    print()

    miner = PatternMiner()

    print(f"Total epochs: {len(miner.df)}")
    print()

    # 1. Create transactions
    print("="*100)
    print("1. CREATING EPOCH TRANSACTIONS")
    print("="*100)
    print()

    transactions = miner.create_epoch_transactions()
    print(f"Created {len(transactions)} transactions")
    print(f"Sample transaction: {list(transactions[0])}")
    print()

    # 2. Find frequent itemsets
    print("="*100)
    print("2. FREQUENT ITEMSETS (min_support=10%)")
    print("="*100)
    print()

    frequent_itemsets = miner.apriori_frequent_itemsets(transactions, min_support=0.10, max_length=3)

    # Show top itemsets by size
    for length in [1, 2, 3]:
        length_itemsets = [(itemset, support) for itemset, support in frequent_itemsets.items()
                          if len(itemset) == length]
        length_itemsets.sort(key=lambda x: x[1], reverse=True)

        print(f"\nTOP {length}-ITEMSETS:")
        print("-"*80)

        for itemset, support in length_itemsets[:10]:
            items_str = ', '.join(sorted(itemset))
            print(f"  {items_str:<60} Support: {support:.3f}")

    print()

    # 3. Association rules
    print("="*100)
    print("3. ASSOCIATION RULES (min_confidence=65%)")
    print("="*100)
    print()

    rules = miner.generate_association_rules(frequent_itemsets, min_confidence=0.65)

    print(f"Found {len(rules)} association rules")
    print()
    print("TOP 20 RULES (by confidence):")
    print("-"*100)

    for i, rule in enumerate(rules[:20], 1):
        ante_str = ', '.join(sorted(rule['antecedent']))
        cons_str = ', '.join(sorted(rule['consequent']))

        print(f"{i:2d}. IF {ante_str:<35} THEN {cons_str:<25} "
              f"(conf={rule['confidence']:.2%}, lift={rule['lift']:.2f})")

    print()

    # 4. Sequential patterns
    print("="*100)
    print("4. SEQUENTIAL PATTERNS (3-epoch sequences)")
    print("="*100)
    print()

    for crypto in ['btc', 'eth', 'sol', 'xrp']:
        patterns = miner.sequential_pattern_mining(crypto, sequence_length=3)

        print(f"\n{crypto.upper()}:")
        print("-"*80)
        print(f"{'Sequence':<15} {'Count':<10} {'Next Up %':<12} {'Next Down %':<12}")
        print("-"*80)

        for pattern in patterns[:10]:
            print(f"{pattern['sequence_str']:<15} "
                  f"{pattern['total_occurrences']:<10} "
                  f"{pattern['prob_next_up']:<11.1f}% "
                  f"{pattern['prob_next_down']:<11.1f}%")

    print()

    # 5. Cross-crypto correlations
    print("="*100)
    print("5. CROSS-CRYPTO CORRELATION PATTERNS")
    print("="*100)
    print()

    correlations = miner.crypto_correlation_patterns()
    print(correlations.to_string(index=False))

    print()
    print("INTERPRETATION:")
    print("-"*80)
    for _, row in correlations.iterrows():
        if row['correlation'] == 'positive':
            print(f"  {row['crypto1'].upper()} ↑ → {row['crypto2'].upper()} ↑ "
                  f"({row['prob_c2_up_if_c1_up']:.0f}% of the time)")

    print()

    # 6. Hourly conditional patterns
    print("="*100)
    print("6. HOURLY CONDITIONAL PATTERNS (Momentum vs Mean Reversion)")
    print("="*100)
    print()

    for crypto in ['btc', 'eth']:
        hourly_patterns = miner.hourly_conditional_patterns(crypto)

        print(f"\n{crypto.upper()}:")
        print("-"*100)

        # Show momentum hours
        momentum_hours = hourly_patterns[
            (hourly_patterns['momentum']) &
            (hourly_patterns['prob_up_if_prev_up'] > 60)
        ]

        if len(momentum_hours) > 0:
            print("\nMOMENTUM HOURS (up follows up):")
            for _, row in momentum_hours.iterrows():
                print(f"  Hour {row['hour']:02d}: {row['prob_up_if_prev_up']:.1f}% up if prev up")

        # Show mean reversion hours
        reversion_hours = hourly_patterns[
            (hourly_patterns['mean_reversion']) &
            (hourly_patterns['prob_up_if_prev_down'] > 60)
        ]

        if len(reversion_hours) > 0:
            print("\nMEAN REVERSION HOURS (down follows up):")
            for _, row in reversion_hours.iterrows():
                print(f"  Hour {row['hour']:02d}: {row['prob_up_if_prev_down']:.1f}% up if prev down")

    print()
    print("="*100)
    print("KEY INSIGHTS")
    print("="*100)
    print()

    print("1. ASSOCIATION RULES:")
    print("   - High confidence rules (>80%) are strong signals")
    print("   - Lift > 1.0 means positive correlation")
    print("   - Use rules to filter entry conditions")
    print()

    print("2. SEQUENTIAL PATTERNS:")
    print("   - Look for streaks with >65% next-direction probability")
    print("   - Some sequences strongly predict reversals")
    print("   - Combine with time-of-day for better accuracy")
    print()

    print("3. CROSS-CRYPTO PATTERNS:")
    print("   - Positive correlations = trade same direction")
    print("   - If BTC moves first, follow with correlated cryptos")
    print("   - Negative correlations = hedge opportunities")
    print()

    print("4. MOMENTUM VS MEAN REVERSION:")
    print("   - Identify which hours favor momentum vs reversion")
    print("   - Adjust strategy based on hour")
    print("   - Don't fight the prevailing pattern")
    print()


if __name__ == '__main__':
    main()
