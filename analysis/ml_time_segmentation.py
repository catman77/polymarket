#!/usr/bin/env python3
"""
Time Segmentation Optimization

Finds optimal time blocks and segmentation strategies:
- Morning/Afternoon/Evening/Night analysis
- Day-of-week patterns
- Best time windows per crypto
- Optimal time block sizes
- Natural breakpoints detection
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
import itertools

sys.path.append(str(Path(__file__).parent.parent))


class TimeSegmentationOptimizer:
    """Optimize time-based trading windows."""

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
            ORDER BY crypto, epoch
        '''

        self.df = pd.read_sql_query(query, conn)
        conn.close()

        self.df['target'] = (self.df['direction'] == 'Up').astype(int)
        self.df['datetime'] = pd.to_datetime(self.df['epoch'], unit='s')
        self.df['day_of_week'] = self.df['datetime'].dt.dayofweek

    def analyze_time_blocks(self, block_definitions: Dict[str, Tuple[int, int]]) -> pd.DataFrame:
        """
        Analyze performance for predefined time blocks.

        Args:
            block_definitions: Dict mapping block name to (start_hour, end_hour)

        Returns:
            DataFrame with win rates per block
        """
        results = []

        for crypto in self.df['crypto'].unique():
            crypto_df = self.df[self.df['crypto'] == crypto]

            for block_name, (start_hour, end_hour) in block_definitions.items():
                if end_hour > start_hour:
                    mask = (crypto_df['hour'] >= start_hour) & (crypto_df['hour'] < end_hour)
                else:
                    # Wrap around midnight
                    mask = (crypto_df['hour'] >= start_hour) | (crypto_df['hour'] < end_hour)

                block_data = crypto_df[mask]

                if len(block_data) > 0:
                    win_rate = block_data['target'].mean() * 100
                    total_epochs = len(block_data)
                    ups = block_data['target'].sum()
                    downs = total_epochs - ups

                    results.append({
                        'crypto': crypto,
                        'block': block_name,
                        'start_hour': start_hour,
                        'end_hour': end_hour,
                        'total_epochs': total_epochs,
                        'ups': ups,
                        'downs': downs,
                        'win_rate': win_rate
                    })

        return pd.DataFrame(results)

    def find_optimal_hour_windows(self, crypto: str, min_window_size: int = 1,
                                  max_window_size: int = 8) -> pd.DataFrame:
        """
        Find all possible hour windows and their win rates.

        Args:
            crypto: Crypto to analyze
            min_window_size: Minimum window size in hours
            max_window_size: Maximum window size in hours

        Returns:
            DataFrame with all windows sorted by win rate
        """
        crypto_df = self.df[self.df['crypto'] == crypto]
        results = []

        for window_size in range(min_window_size, max_window_size + 1):
            for start_hour in range(24):
                end_hour = (start_hour + window_size) % 24

                if end_hour > start_hour:
                    mask = (crypto_df['hour'] >= start_hour) & (crypto_df['hour'] < end_hour)
                else:
                    mask = (crypto_df['hour'] >= start_hour) | (crypto_df['hour'] < end_hour)

                window_data = crypto_df[mask]

                if len(window_data) > 0:
                    win_rate = window_data['target'].mean() * 100
                    total = len(window_data)

                    results.append({
                        'start_hour': start_hour,
                        'end_hour': end_hour,
                        'window_size': window_size,
                        'total_epochs': total,
                        'win_rate': win_rate
                    })

        df_windows = pd.DataFrame(results)
        return df_windows.sort_values('win_rate', ascending=False)

    def day_of_week_analysis(self) -> pd.DataFrame:
        """Analyze win rates by day of week."""
        dow_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        results = []

        for crypto in self.df['crypto'].unique():
            crypto_df = self.df[self.df['crypto'] == crypto]

            for dow in range(7):
                dow_data = crypto_df[crypto_df['day_of_week'] == dow]

                if len(dow_data) > 0:
                    win_rate = dow_data['target'].mean() * 100
                    total = len(dow_data)
                    ups = dow_data['target'].sum()

                    results.append({
                        'crypto': crypto,
                        'day_of_week': dow,
                        'day_name': dow_names[dow],
                        'total_epochs': total,
                        'ups': ups,
                        'downs': total - ups,
                        'win_rate': win_rate
                    })

        return pd.DataFrame(results)

    def cross_segment_analysis(self, segment_type: str = 'time_of_day') -> pd.DataFrame:
        """
        Analyze performance across multiple segment dimensions.

        Args:
            segment_type: 'time_of_day', 'day_of_week', or 'combined'
        """
        if segment_type == 'time_of_day':
            # Standard time blocks
            blocks = {
                'Early Morning (0-6)': (0, 6),
                'Morning (6-12)': (6, 12),
                'Afternoon (12-18)': (12, 18),
                'Evening (18-24)': (18, 24)
            }
            return self.analyze_time_blocks(blocks)

        elif segment_type == 'day_of_week':
            return self.day_of_week_analysis()

        elif segment_type == 'combined':
            # Combined time block + day of week
            results = []

            blocks = {
                'night': (0, 6),
                'morning': (6, 12),
                'afternoon': (12, 18),
                'evening': (18, 24)
            }

            dow_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

            for crypto in self.df['crypto'].unique():
                crypto_df = self.df[self.df['crypto'] == crypto]

                for block_name, (start_hour, end_hour) in blocks.items():
                    for dow in range(7):
                        hour_mask = (crypto_df['hour'] >= start_hour) & (crypto_df['hour'] < end_hour)
                        dow_mask = crypto_df['day_of_week'] == dow

                        segment_data = crypto_df[hour_mask & dow_mask]

                        if len(segment_data) > 0:
                            win_rate = segment_data['target'].mean() * 100
                            total = len(segment_data)

                            results.append({
                                'crypto': crypto,
                                'time_block': block_name,
                                'day': dow_names[dow],
                                'total_epochs': total,
                                'win_rate': win_rate
                            })

            return pd.DataFrame(results)

    def find_breakpoints(self, crypto: str, threshold_delta: float = 5.0) -> List[int]:
        """
        Find natural breakpoints in the day where win rate changes significantly.

        Args:
            crypto: Crypto to analyze
            threshold_delta: Minimum change in win rate to consider a breakpoint (%)

        Returns:
            List of hours where breakpoints occur
        """
        crypto_df = self.df[self.df['crypto'] == crypto]

        hourly_win_rates = []
        for hour in range(24):
            hour_data = crypto_df[crypto_df['hour'] == hour]
            if len(hour_data) > 0:
                win_rate = hour_data['target'].mean() * 100
                hourly_win_rates.append(win_rate)
            else:
                hourly_win_rates.append(50.0)  # Default to 50%

        breakpoints = []
        for i in range(1, 24):
            delta = abs(hourly_win_rates[i] - hourly_win_rates[i-1])
            if delta >= threshold_delta:
                breakpoints.append(i)

        return breakpoints

    def adaptive_block_optimization(self, crypto: str, target_num_blocks: int = 4) -> Dict:
        """
        Find optimal time blocks adaptively based on performance changes.

        Args:
            crypto: Crypto to analyze
            target_num_blocks: Desired number of blocks

        Returns:
            Dict with optimized block definitions
        """
        # Find natural breakpoints
        breakpoints = self.find_breakpoints(crypto, threshold_delta=3.0)

        if len(breakpoints) < target_num_blocks - 1:
            # Not enough natural breakpoints, use equal splits
            block_size = 24 // target_num_blocks
            breakpoints = [i * block_size for i in range(1, target_num_blocks)]

        # Select top breakpoints
        breakpoints = sorted(breakpoints)[:target_num_blocks - 1]
        breakpoints = [0] + breakpoints + [24]

        # Create block definitions
        blocks = {}
        for i in range(len(breakpoints) - 1):
            start = breakpoints[i]
            end = breakpoints[i + 1]
            blocks[f'Block_{i+1}_{start}h-{end}h'] = (start, end)

        # Analyze these blocks
        crypto_df = self.df[self.df['crypto'] == crypto]
        block_stats = []

        for block_name, (start, end) in blocks.items():
            mask = (crypto_df['hour'] >= start) & (crypto_df['hour'] < end)
            block_data = crypto_df[mask]

            if len(block_data) > 0:
                win_rate = block_data['target'].mean() * 100
                block_stats.append({
                    'block': block_name,
                    'start': start,
                    'end': end,
                    'total': len(block_data),
                    'win_rate': win_rate
                })

        return {
            'crypto': crypto,
            'blocks': blocks,
            'stats': pd.DataFrame(block_stats)
        }


def main():
    """Main time segmentation analysis."""
    print("="*100)
    print("TIME SEGMENTATION OPTIMIZATION")
    print("="*100)
    print()

    optimizer = TimeSegmentationOptimizer()

    print(f"Total epochs: {len(optimizer.df)}")
    print(f"Cryptos: {optimizer.df['crypto'].unique()}")
    print()

    # 1. Standard time blocks
    print("="*100)
    print("1. STANDARD TIME BLOCKS (Morning/Afternoon/Evening/Night)")
    print("="*100)
    print()

    time_blocks = optimizer.cross_segment_analysis('time_of_day')
    print(time_blocks.to_string(index=False))
    print()

    # Find best blocks
    best_blocks = time_blocks[time_blocks['win_rate'] > 60].sort_values('win_rate', ascending=False)
    if len(best_blocks) > 0:
        print("PROFITABLE TIME BLOCKS (>60% win rate):")
        print("-"*100)
        print(best_blocks[['crypto', 'block', 'total_epochs', 'win_rate']].to_string(index=False))
    else:
        print("No time blocks with >60% win rate found.")
    print()

    # 2. Day of week analysis
    print("="*100)
    print("2. DAY-OF-WEEK ANALYSIS")
    print("="*100)
    print()

    dow_analysis = optimizer.day_of_week_analysis()
    print(dow_analysis.to_string(index=False))
    print()

    # Best days
    best_days = dow_analysis[dow_analysis['win_rate'] > 60].sort_values('win_rate', ascending=False)
    if len(best_days) > 0:
        print("BEST DAYS (>60% win rate):")
        print("-"*100)
        print(best_days[['crypto', 'day_name', 'total_epochs', 'win_rate']].to_string(index=False))
    else:
        print("No days with >60% win rate found.")
    print()

    # 3. Optimal hour windows per crypto
    print("="*100)
    print("3. OPTIMAL HOUR WINDOWS (Top 10 per crypto)")
    print("="*100)
    print()

    for crypto in optimizer.df['crypto'].unique():
        print(f"\n{crypto.upper()}:")
        print("-"*100)

        windows = optimizer.find_optimal_hour_windows(crypto, min_window_size=2, max_window_size=6)
        top_windows = windows.head(10)

        print(f"{'Start':<8} {'End':<8} {'Size (h)':<10} {'Epochs':<10} {'Win Rate':<10}")
        print("-"*60)

        for _, row in top_windows.iterrows():
            print(f"{row['start_hour']:02d}:00    {row['end_hour']:02d}:00    "
                  f"{row['window_size']:<10} {row['total_epochs']:<10} {row['win_rate']:<9.1f}%")

    print()

    # 4. Combined analysis (time block + day of week)
    print("="*100)
    print("4. COMBINED ANALYSIS (Time Block × Day of Week)")
    print("="*100)
    print()

    combined = optimizer.cross_segment_analysis('combined')
    best_combined = combined[combined['win_rate'] > 60].sort_values('win_rate', ascending=False)

    if len(best_combined) > 0:
        print("HIGH WIN RATE COMBINATIONS (>60%):")
        print("-"*100)
        print(best_combined[['crypto', 'time_block', 'day', 'total_epochs', 'win_rate']].head(20).to_string(index=False))
    else:
        print("No combinations with >60% win rate found.")

    print()

    # 5. Adaptive block optimization
    print("="*100)
    print("5. ADAPTIVE BLOCK OPTIMIZATION (Natural Breakpoints)")
    print("="*100)
    print()

    for crypto in optimizer.df['crypto'].unique():
        result = optimizer.adaptive_block_optimization(crypto, target_num_blocks=4)

        print(f"\n{crypto.upper()}:")
        print("-"*100)
        print(result['stats'].to_string(index=False))
        print()

    # 6. Recommendations
    print("="*100)
    print("TRADING RECOMMENDATIONS")
    print("="*100)
    print()

    print("1. TIME-OF-DAY STRATEGY:")
    print("   - Identify your best time blocks per crypto")
    print("   - Only trade during blocks with >60% historical win rate")
    print("   - Avoid blocks with <45% win rate")
    print()

    print("2. DAY-OF-WEEK STRATEGY:")
    print("   - Some days may be consistently better for Up vs Down")
    print("   - Consider day-of-week bias when selecting direction")
    print("   - Weekends may have different patterns than weekdays")
    print()

    print("3. COMBINED STRATEGY:")
    print("   - Use both time block AND day of week for filtering")
    print("   - Example: 'Only bet BTC Up on Tuesday afternoons (12-18h)'")
    print("   - This gives more precision than time alone")
    print()

    print("4. WINDOW SIZE:")
    print("   - Larger windows (4-6h) = more stable but less precision")
    print("   - Smaller windows (1-2h) = higher variance but stronger signals")
    print("   - Optimal size depends on sample size and consistency")
    print()


if __name__ == '__main__':
    main()
