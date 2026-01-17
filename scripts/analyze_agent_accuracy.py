#!/usr/bin/env python3
"""
US-TO-001: Analyze Agent Vote Accuracy

Parses shadow trading database to calculate per-agent accuracy.
When an agent votes UP, how often does the market actually go UP?

Usage:
    python3 scripts/analyze_agent_accuracy.py --source simulation/trade_journal.db --min-votes 20
"""

import argparse
import sqlite3
from collections import defaultdict
from typing import Dict, List, Tuple


class AgentAccuracyAnalyzer:
    """Analyzes per-agent vote accuracy from shadow trading database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to shadow trading database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            print(f"✅ Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            print(f"❌ Failed to connect to database: {e}")
            raise
    
    def get_agent_votes_with_outcomes(self) -> List[Dict]:
        """
        Get all agent votes with actual market outcomes.
        
        Returns list of:
        {
            'agent_name': 'RegimeAgent',
            'vote_direction': 'Up',
            'actual_outcome': 'WIN' or 'LOSS',
            'confidence': 0.75
        }
        """
        if not self.conn:
            raise RuntimeError("Not connected to database")
        
        # Query: Join agent_votes with outcomes through trades
        # Derive outcome from predicted_direction vs actual_direction
        query = """
        SELECT
            av.agent_name,
            av.direction as vote_direction,
            av.confidence,
            CASE
                WHEN o.predicted_direction = o.actual_direction THEN 'WIN'
                ELSE 'LOSS'
            END as outcome,
            t.direction as trade_direction,
            d.timestamp
        FROM agent_votes av
        JOIN decisions d ON av.decision_id = d.id
        JOIN trades t ON d.id = t.decision_id
        JOIN outcomes o ON t.id = o.trade_id
        WHERE o.actual_direction IS NOT NULL
        ORDER BY d.timestamp DESC
        """
        
        try:
            cursor = self.conn.execute(query)
            results = []
            
            for row in cursor:
                # Agent was "correct" if they voted same direction as trade AND trade won
                # OR voted opposite direction and trade lost (they were right to vote against it)
                agent_correct = (
                    (row['vote_direction'] == row['trade_direction'] and row['outcome'] == 'WIN') or
                    (row['vote_direction'] != row['trade_direction'] and row['outcome'] == 'LOSS')
                )
                
                results.append({
                    'agent_name': row['agent_name'],
                    'vote_direction': row['vote_direction'],
                    'trade_direction': row['trade_direction'],
                    'outcome': row['outcome'],
                    'confidence': row['confidence'],
                    'correct': agent_correct,
                    'timestamp': row['timestamp']
                })
            
            return results
            
        except sqlite3.Error as e:
            print(f"❌ Query failed: {e}")
            return []
    
    def calculate_agent_accuracy(self, votes: List[Dict], min_votes: int = 20) -> Dict:
        """Calculate accuracy metrics per agent"""
        
        agent_stats = defaultdict(lambda: {
            'total_votes': 0,
            'correct_votes': 0,
            'up_votes': 0,
            'down_votes': 0,
            'up_correct': 0,
            'down_correct': 0,
            'avg_confidence': []
        })
        
        for vote in votes:
            agent = vote['agent_name']
            stats = agent_stats[agent]
            
            stats['total_votes'] += 1
            stats['avg_confidence'].append(vote['confidence'])
            
            if vote['correct']:
                stats['correct_votes'] += 1
            
            if vote['vote_direction'] == 'Up':
                stats['up_votes'] += 1
                if vote['correct']:
                    stats['up_correct'] += 1
            else:
                stats['down_votes'] += 1
                if vote['correct']:
                    stats['down_correct'] += 1
        
        # Calculate final metrics
        results = {}
        for agent, stats in agent_stats.items():
            if stats['total_votes'] < min_votes:
                continue  # Skip agents with insufficient data
            
            accuracy = stats['correct_votes'] / stats['total_votes']
            up_accuracy = stats['up_correct'] / stats['up_votes'] if stats['up_votes'] > 0 else 0
            down_accuracy = stats['down_correct'] / stats['down_votes'] if stats['down_votes'] > 0 else 0
            avg_conf = sum(stats['avg_confidence']) / len(stats['avg_confidence'])
            
            results[agent] = {
                'total_votes': stats['total_votes'],
                'accuracy': accuracy,
                'up_accuracy': up_accuracy,
                'down_accuracy': down_accuracy,
                'avg_confidence': avg_conf,
                'up_votes': stats['up_votes'],
                'down_votes': stats['down_votes']
            }
        
        return results
    
    def print_accuracy_report(self, accuracy: Dict):
        """Print formatted accuracy report"""
        
        print("\n" + "="*80)
        print("AGENT VOTE ACCURACY REPORT")
        print("="*80)
        
        if not accuracy:
            print("\n❌ No agent vote data found in database")
            print("   Make sure shadow trading is enabled and trades have resolved")
            return
        
        # Sort by accuracy (descending)
        sorted_agents = sorted(accuracy.items(), key=lambda x: x[1]['accuracy'], reverse=True)
        
        print(f"\n{'Agent':<20} {'Votes':<8} {'Accuracy':<10} {'UP Acc':<10} {'DOWN Acc':<10} {'Avg Conf':<10}")
        print("-"*80)
        
        for agent, stats in sorted_agents:
            print(f"{agent:<20} {stats['total_votes']:<8} "
                  f"{stats['accuracy']:<10.1%} {stats['up_accuracy']:<10.1%} "
                  f"{stats['down_accuracy']:<10.1%} {stats['avg_confidence']:<10.1%}")
        
        print("\n" + "="*80)
        print("RECOMMENDED ACTIONS")
        print("="*80)
        
        # Recommendations
        high_performers = [(a, s) for a, s in sorted_agents if s['accuracy'] >= 0.70]
        medium_performers = [(a, s) for a, s in sorted_agents if 0.53 <= s['accuracy'] < 0.70]
        low_performers = [(a, s) for a, s in sorted_agents if s['accuracy'] < 0.53]
        
        if high_performers:
            print("\n🟢 HIGH PERFORMERS (≥70% accuracy) - BOOST WEIGHTS:")
            for agent, stats in high_performers:
                suggested_weight = round(1.0 + (stats['accuracy'] - 0.60) * 2.0, 1)
                print(f"   {agent}: {stats['accuracy']:.1%} → Weight: {suggested_weight}x "
                      f"(from 1.0x)")
        
        if medium_performers:
            print("\n🟡 MEDIUM PERFORMERS (53-70% accuracy) - KEEP BASELINE:")
            for agent, stats in medium_performers:
                print(f"   {agent}: {stats['accuracy']:.1%} → Weight: 1.0x (no change)")
        
        if low_performers:
            print("\n🔴 LOW PERFORMERS (<53% accuracy) - DISABLE:")
            for agent, stats in low_performers:
                print(f"   {agent}: {stats['accuracy']:.1%} → Weight: 0.0x (DISABLE)")
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("\n1. Update config/agent_config.py with recommended weights")
        print("2. Test with shadow trading for 24 hours")
        print("3. Compare consensus scores before/after reweighting")
        print("4. Monitor win rate for improvement")
    
    def export_to_csv(self, accuracy: Dict, output_file: str = "reports/agent_accuracy.csv"):
        """Export accuracy data to CSV"""
        import csv
        from pathlib import Path
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Agent', 'Total Votes', 'Accuracy', 'UP Accuracy', 
                             'DOWN Accuracy', 'Avg Confidence', 'Suggested Weight'])
            
            for agent, stats in sorted(accuracy.items(), key=lambda x: x[1]['accuracy'], reverse=True):
                suggested_weight = round(1.0 + (stats['accuracy'] - 0.60) * 2.0, 1)
                writer.writerow([
                    agent,
                    stats['total_votes'],
                    f"{stats['accuracy']:.1%}",
                    f"{stats['up_accuracy']:.1%}",
                    f"{stats['down_accuracy']:.1%}",
                    f"{stats['avg_confidence']:.1%}",
                    suggested_weight
                ])
        
        print(f"\n✅ Exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Analyze agent vote accuracy")
    parser.add_argument('--source', default='simulation/trade_journal.db',
                        help='Path to shadow trading database')
    parser.add_argument('--min-votes', type=int, default=20,
                        help='Minimum votes required per agent (default: 20)')
    parser.add_argument('--export', action='store_true',
                        help='Export results to CSV')
    
    args = parser.parse_args()
    
    print("="*80)
    print("US-TO-001: AGENT VOTE ACCURACY ANALYSIS")
    print("="*80)
    print(f"\nDatabase: {args.source}")
    print(f"Min votes: {args.min_votes}")
    
    analyzer = AgentAccuracyAnalyzer(args.source)
    analyzer.connect()
    
    # Get votes with outcomes
    print("\n📊 Fetching agent votes with resolved outcomes...")
    votes = analyzer.get_agent_votes_with_outcomes()
    
    if not votes:
        print("❌ No resolved trades found in database")
        print("\nPossible reasons:")
        print("- Shadow trading not enabled")
        print("- No trades have resolved yet (wait for epoch completion)")
        print("- Database path incorrect")
        return 1
    
    print(f"✅ Found {len(votes)} agent votes with outcomes")
    
    # Calculate accuracy
    print("\n📈 Calculating per-agent accuracy...")
    accuracy = analyzer.calculate_agent_accuracy(votes, min_votes=args.min_votes)
    
    # Print report
    analyzer.print_accuracy_report(accuracy)
    
    # Export if requested
    if args.export and accuracy:
        analyzer.export_to_csv(accuracy)
    
    return 0


if __name__ == '__main__':
    exit(main())
