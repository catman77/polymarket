#!/usr/bin/env python3
"""
Complete ML Analysis Pipeline

Runs all machine learning analyses in sequence:
1. Feature engineering
2. Supervised learning
3. Unsupervised learning (clustering)
4. Time segmentation optimization
5. Pattern mining
6. Ensemble learning

Generates comprehensive report with actionable insights.
"""

import sys
from pathlib import Path
import time
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))


def print_section(title: str):
    """Print formatted section header."""
    print()
    print("="*100)
    print(f"{title.upper()}")
    print("="*100)
    print()


def main():
    start_time = time.time()

    print_section("POLYMARKET AUTOTRADER - COMPLETE ML ANALYSIS")

    print(f"Analysis started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This will run:")
    print("  1. Feature Engineering")
    print("  2. Supervised Learning (Classification)")
    print("  3. Unsupervised Learning (Clustering)")
    print("  4. Time Segmentation Optimization")
    print("  5. Pattern Mining & Association Rules")
    print("  6. Ensemble Learning")
    print()
    print("Estimated time: 5-10 minutes")
    print()

    input("Press Enter to start...")
    print()

    # 1. Feature Engineering
    print_section("Step 1/6: Feature Engineering")

    try:
        from ml_feature_engineering import FeatureEngineering

        fe = FeatureEngineering()
        df = fe.build_feature_matrix()

        print(f"✅ Feature matrix built: {len(df)} epochs × {len(df.columns)} features")
        print()

        # Save for later use
        output_path = Path('analysis/feature_matrix.csv')
        df.to_csv(output_path, index=False)
        print(f"💾 Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Error in feature engineering: {e}")
        return

    # 2. Supervised Learning
    print_section("Step 2/6: Supervised Learning")

    try:
        from ml_supervised_learning import EpochPredictor

        predictor = EpochPredictor(df)
        X_train, X_test, y_train, y_test = predictor.prepare_data(test_size=0.2)

        print("Training models...")
        predictor.train_all_models(X_train, y_train)

        print("Evaluating models...")
        for model_name in predictor.models.keys():
            predictor.evaluate_model(model_name, X_test, y_test)

        predictor.print_results()

        print("\n📊 Feature Importance (Random Forest):")
        predictor.feature_importance('random_forest', top_n=15)

        print("\n🔄 Walk-Forward Validation:")
        cv_results = predictor.walk_forward_validation(n_splits=5)

        print("✅ Supervised learning complete")

    except Exception as e:
        print(f"❌ Error in supervised learning: {e}")

    # 3. Unsupervised Learning
    print_section("Step 3/6: Unsupervised Learning (Clustering)")

    try:
        from ml_unsupervised_learning import EpochClusterer

        clusterer = EpochClusterer(df)
        X, metadata = clusterer.prepare_features()

        print("Finding optimal number of clusters...")
        optimal_k_results = clusterer.find_optimal_k(X, k_range=range(3, 9))

        best_k = optimal_k_results['k_values'][
            optimal_k_results['silhouette'].index(max(optimal_k_results['silhouette']))
        ]

        print(f"\nOptimal k: {best_k}")
        print()

        print("Performing K-Means clustering...")
        labels = clusterer.kmeans_clustering(X, n_clusters=best_k)

        print("Analyzing clusters...")
        clusterer.analyze_clusters(metadata)

        profiles = clusterer.cluster_profiling(metadata)
        print("\n📋 Cluster Profiles:")
        print(profiles.to_string(index=False))

        print("\n✅ Clustering complete")

    except Exception as e:
        print(f"❌ Error in unsupervised learning: {e}")

    # 4. Time Segmentation
    print_section("Step 4/6: Time Segmentation Optimization")

    try:
        from ml_time_segmentation import TimeSegmentationOptimizer

        optimizer = TimeSegmentationOptimizer()

        print("Analyzing time blocks...")
        time_blocks = optimizer.cross_segment_analysis('time_of_day')

        best_blocks = time_blocks[time_blocks['win_rate'] > 60].sort_values('win_rate', ascending=False)
        if len(best_blocks) > 0:
            print("\n🔥 Profitable Time Blocks (>60% win rate):")
            print(best_blocks[['crypto', 'block', 'total_epochs', 'win_rate']].to_string(index=False))
        else:
            print("\n⚠️  No time blocks with >60% win rate found")

        print("\nAnalyzing day-of-week patterns...")
        dow_analysis = optimizer.day_of_week_analysis()

        best_days = dow_analysis[dow_analysis['win_rate'] > 60].sort_values('win_rate', ascending=False)
        if len(best_days) > 0:
            print("\n📅 Best Days (>60% win rate):")
            print(best_days[['crypto', 'day_name', 'total_epochs', 'win_rate']].head(10).to_string(index=False))

        print("\n✅ Time segmentation complete")

    except Exception as e:
        print(f"❌ Error in time segmentation: {e}")

    # 5. Pattern Mining
    print_section("Step 5/6: Pattern Mining")

    try:
        from ml_pattern_mining import PatternMiner

        miner = PatternMiner()

        print("Creating epoch transactions...")
        transactions = miner.create_epoch_transactions()
        print(f"  {len(transactions)} transactions created")

        print("\nFinding frequent itemsets...")
        frequent_itemsets = miner.apriori_frequent_itemsets(transactions, min_support=0.10, max_length=3)
        print(f"  {len(frequent_itemsets)} frequent itemsets found")

        print("\nGenerating association rules...")
        rules = miner.generate_association_rules(frequent_itemsets, min_confidence=0.65)
        print(f"  {len(rules)} association rules found")

        if len(rules) > 0:
            print("\n🔍 Top 10 Association Rules:")
            for i, rule in enumerate(rules[:10], 1):
                ante_str = ', '.join(sorted(rule['antecedent']))
                cons_str = ', '.join(sorted(rule['consequent']))
                print(f"{i:2d}. IF {ante_str} THEN {cons_str} (conf={rule['confidence']:.2%})")

        print("\nAnalyzing sequential patterns...")
        for crypto in ['btc', 'eth']:
            patterns = miner.sequential_pattern_mining(crypto, sequence_length=3)
            strong_patterns = [p for p in patterns if p['total_occurrences'] >= 10 and
                             (p['prob_next_up'] > 65 or p['prob_next_up'] < 35)]

            if strong_patterns:
                print(f"\n  {crypto.upper()} - Strong Sequential Patterns:")
                for p in strong_patterns[:5]:
                    print(f"    {p['sequence_str']} → {p['prob_next_up']:.0f}% up ({p['total_occurrences']} times)")

        print("\n✅ Pattern mining complete")

    except Exception as e:
        print(f"❌ Error in pattern mining: {e}")

    # 6. Ensemble Learning
    print_section("Step 6/6: Ensemble Learning")

    try:
        from ml_ensemble import EnsemblePredictor

        ensemble = EnsemblePredictor(df)
        X_train, X_test, y_train, y_test = ensemble.prepare_data(test_size=0.2)

        print("Training ensemble models...")

        ensemble.train_voting_classifier(X_train, y_train, voting='soft')
        ensemble.train_stacking_classifier(X_train, y_train)

        # Get hour metadata
        df_sorted = ensemble.df.sort_values('epoch')
        split_idx = int(len(df_sorted) * 0.8)
        test_hours = df_sorted.iloc[split_idx:]['hour'].reset_index(drop=True)

        print("\nEvaluating ensembles...")
        results = ensemble.evaluate_all_ensembles(X_test, y_test, hour_metadata=test_hours)

        best_model = max(results.items(), key=lambda x: x[1])

        print(f"\n🏆 Best Model: {best_model[0]}")
        print(f"   Win Rate: {best_model[1]*100:.2f}%")

        if best_model[1] > 0.53:
            edge = (best_model[1] - 0.53) * 100
            print(f"   Edge over break-even: +{edge:.2f}%")
            print("   ✅ PROFITABLE (after 6.3% fees)")
        else:
            print("   ❌ Below break-even threshold (53%)")

        print("\n✅ Ensemble learning complete")

    except Exception as e:
        print(f"❌ Error in ensemble learning: {e}")

    # Final summary
    elapsed_time = time.time() - start_time

    print_section("Analysis Complete")

    print(f"Total time: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    print()

    print("📊 NEXT STEPS:")
    print("-"*100)
    print()

    print("1. REVIEW RESULTS:")
    print("   - Check feature_matrix.csv for feature data")
    print("   - Review model accuracies and win rates")
    print("   - Identify high-confidence patterns")
    print()

    print("2. INTEGRATE INTO BOT:")
    print("   - Add profitable time filters to bot/momentum_bot_v12.py")
    print("   - Use association rules for entry filtering")
    print("   - Implement ensemble predictions as secondary signal")
    print()

    print("3. BACKTEST:")
    print("   - Test discovered patterns on historical data")
    print("   - Validate win rates with real trading simulation")
    print("   - Measure P&L impact")
    print()

    print("4. DEPLOY & MONITOR:")
    print("   - A/B test new strategies")
    print("   - Track real-world performance")
    print("   - Retrain models weekly")
    print()

    print("5. ITERATE:")
    print("   - Collect more data")
    print("   - Re-run analysis monthly")
    print("   - Adapt to market regime changes")
    print()


if __name__ == '__main__':
    main()
