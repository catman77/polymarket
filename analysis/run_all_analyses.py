#!/usr/bin/env python3
"""
Master Analysis Runner - Execute All Econophysics Analyses

Runs all analysis scripts in priority order and generates summary report
"""

import subprocess
import sys
import time
from datetime import datetime

ANALYSES = [
    {
        'name': 'Microstructure Clock Analysis',
        'script': 'microstructure_clock.py',
        'priority': 1,
        'description': 'Hourly patterns, entropy, sessions, volatility regimes'
    },
    {
        'name': 'Phase Transition Detection',
        'script': 'phase_transitions.py',
        'priority': 1,
        'description': 'Order parameters, Hurst exponent, regime clustering'
    },
    {
        'name': 'Cross-Asset Dynamics',
        'script': 'cross_asset_dynamics.py',
        'priority': 2,
        'description': 'Correlations, lead-lag, contagion, systemic risk'
    },
    {
        'name': 'Information Theory',
        'script': 'information_theory.py',
        'priority': 2,
        'description': 'Predictability, transfer entropy, pattern complexity'
    },
    {
        'name': 'Optimal Timing & Strategy',
        'script': 'optimal_timing.py',
        'priority': 3,
        'description': 'Best hours, Kelly criterion, risk-adjusted returns'
    }
]

def run_analysis(script_name):
    """Run a single analysis script"""
    try:
        result = subprocess.run(
            [sys.executable, f'analysis/{script_name}'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Analysis timed out (>5 minutes)"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 80)
    print("ECONOPHYSICS ANALYSIS SUITE")
    print("Polymarket 15-Minute Binary Outcome Markets")
    print("=" * 80)
    print(f"\nStart Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Analyses: {len(ANALYSES)}")
    print()

    results = []
    total_start = time.time()

    # Run by priority
    for priority in [1, 2, 3]:
        priority_analyses = [a for a in ANALYSES if a['priority'] == priority]

        if len(priority_analyses) == 0:
            continue

        print("=" * 80)
        print(f"TIER {priority} ANALYSES")
        print("=" * 80)
        print()

        for analysis in priority_analyses:
            print(f"Running: {analysis['name']}")
            print(f"  Description: {analysis['description']}")
            print(f"  Script: {analysis['script']}")
            print()

            start_time = time.time()
            success, output = run_analysis(analysis['script'])
            elapsed = time.time() - start_time

            if success:
                status = "✓ SUCCESS"
                print(f"{status} (completed in {elapsed:.1f}s)")
            else:
                status = "✗ FAILED"
                print(f"{status}")
                print(f"Error: {output}")

            print()

            results.append({
                'analysis': analysis['name'],
                'priority': priority,
                'status': status,
                'elapsed': elapsed,
                'output': output if not success else None
            })

    total_elapsed = time.time() - total_start

    # Summary Report
    print("=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print()

    successful = sum(1 for r in results if '✓' in r['status'])
    failed = sum(1 for r in results if '✗' in r['status'])

    print(f"Total Time: {total_elapsed:.1f}s")
    print(f"Successful: {successful}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print()

    if failed > 0:
        print("Failed Analyses:")
        for r in results:
            if '✗' in r['status']:
                print(f"  - {r['analysis']}")
                if r['output']:
                    print(f"    Error: {r['output'][:200]}")
        print()

    print("Output Files Generated:")
    print("  - analysis/results_*.csv (individual analysis results)")
    print()

    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("""
1. Review CSV results in analysis/ directory
2. Focus on:
   - results_best_opportunities.csv (immediate trading signals)
   - results_hourly_entropy.csv (most predictable hours)
   - results_predictability.csv (which cryptos are most predictable)
   - results_lead_lag.csv (which crypto leads others)

3. Integrate findings into bot:
   - Add hourly filters for high-edge periods
   - Adjust position sizing by volatility regime
   - Use correlation limits to prevent overexposure

4. Visualize results:
   - Create heatmaps of day-hour patterns
   - Plot rolling entropy over time
   - Graph correlation networks
    """)

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
