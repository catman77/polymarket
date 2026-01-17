#!/usr/bin/env python3
"""
Threshold Math Analysis for Vote Aggregation System

Mathematical analysis of the consensus threshold system to understand:
1. What conditions are required to reach various thresholds
2. What percentage of realistic scenarios pass each threshold
3. Optimal threshold recommendations

Formula: weighted_score = sum(confidence × quality × weight) / sum(weight)
"""

import random
import itertools
from dataclasses import dataclass
from typing import List, Tuple, Dict
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for a voting agent"""
    name: str
    weight: float
    confidence_range: Tuple[float, float]  # (min, max)
    quality_range: Tuple[float, float]      # (min, max)

    @property
    def max_contribution(self) -> float:
        """Maximum possible contribution to weighted score"""
        return self.confidence_range[1] * self.quality_range[1] * self.weight

    @property
    def min_contribution(self) -> float:
        """Minimum possible contribution to weighted score"""
        return self.confidence_range[0] * self.quality_range[0] * self.weight

    @property
    def typical_contribution(self) -> float:
        """Typical (midpoint) contribution"""
        mid_conf = (self.confidence_range[0] + self.confidence_range[1]) / 2
        mid_qual = (self.quality_range[0] + self.quality_range[1]) / 2
        return mid_conf * mid_qual * self.weight


# Current agent configurations
AGENTS = [
    AgentConfig(
        name="TimePatternAgent",
        weight=0.5,
        confidence_range=(0.40, 0.70),
        quality_range=(0.60, 0.90)
    ),
    AgentConfig(
        name="OrderBookAgent",
        weight=0.8,
        confidence_range=(0.30, 0.60),
        quality_range=(0.80, 1.00)
    ),
    AgentConfig(
        name="FundingRateAgent",
        weight=0.8,
        confidence_range=(0.30, 0.50),
        quality_range=(0.30, 0.70)
    ),
]

THRESHOLDS_TO_TEST = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


# ============================================================================
# CORE MATH FUNCTIONS
# ============================================================================

def calculate_weighted_score(votes: List[Tuple[float, float, float]]) -> float:
    """
    Calculate weighted score from agent votes.

    Args:
        votes: List of (confidence, quality, weight) tuples

    Returns:
        Weighted score between 0 and 1
    """
    total_weighted = sum(conf * qual * weight for conf, qual, weight in votes)
    total_weight = sum(weight for _, _, weight in votes)

    if total_weight == 0:
        return 0.0

    return total_weighted / total_weight


def theoretical_bounds(agents: List[AgentConfig]) -> Tuple[float, float]:
    """
    Calculate theoretical min/max weighted scores.

    Returns:
        (min_score, max_score) tuple
    """
    total_weight = sum(a.weight for a in agents)

    min_numerator = sum(a.min_contribution for a in agents)
    max_numerator = sum(a.max_contribution for a in agents)

    return min_numerator / total_weight, max_numerator / total_weight


# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def analyze_theoretical_bounds(agents: List[AgentConfig]) -> Dict:
    """Analyze the theoretical bounds of the voting system"""

    total_weight = sum(a.weight for a in agents)
    min_score, max_score = theoretical_bounds(agents)

    # Calculate each agent's contribution range
    agent_analysis = []
    for agent in agents:
        weight_fraction = agent.weight / total_weight
        min_contrib = agent.min_contribution / total_weight
        max_contrib = agent.max_contribution / total_weight
        typical_contrib = agent.typical_contribution / total_weight

        agent_analysis.append({
            'name': agent.name,
            'weight': agent.weight,
            'weight_fraction': weight_fraction,
            'min_contribution': min_contrib,
            'max_contribution': max_contrib,
            'typical_contribution': typical_contrib,
            'conf_range': agent.confidence_range,
            'qual_range': agent.quality_range,
        })

    return {
        'total_weight': total_weight,
        'min_score': min_score,
        'max_score': max_score,
        'agents': agent_analysis,
    }


def find_minimum_requirements(agents: List[AgentConfig], threshold: float) -> Dict:
    """
    Find the minimum requirements to reach a threshold.

    Uses algebraic analysis to determine what's needed.
    """
    total_weight = sum(a.weight for a in agents)
    required_numerator = threshold * total_weight

    # What if all agents vote at their maximum?
    max_numerator = sum(a.max_contribution for a in agents)

    # What if all agents vote at their typical values?
    typical_numerator = sum(a.typical_contribution for a in agents)

    # What's the shortfall at typical values?
    shortfall_at_typical = required_numerator - typical_numerator

    # For each agent, calculate how much "boost" they could provide above typical
    agent_boosts = []
    for agent in agents:
        max_boost = agent.max_contribution - agent.typical_contribution
        agent_boosts.append({
            'name': agent.name,
            'max_boost': max_boost / total_weight,
            'boost_potential': max_boost,
        })

    return {
        'threshold': threshold,
        'required_numerator': required_numerator,
        'max_achievable': max_numerator / total_weight,
        'typical_score': typical_numerator / total_weight,
        'shortfall_at_typical': shortfall_at_typical / total_weight,
        'can_reach_threshold': max_numerator >= required_numerator,
        'needs_all_max': typical_numerator < required_numerator,
        'agent_boosts': agent_boosts,
    }


def monte_carlo_simulation(agents: List[AgentConfig],
                          threshold: float,
                          n_simulations: int = 100000) -> Dict:
    """
    Run Monte Carlo simulation to estimate pass rate.

    Samples uniformly from each agent's confidence and quality ranges.
    """
    passes = 0
    scores = []
    passing_examples = []
    failing_examples = []

    for _ in range(n_simulations):
        votes = []
        vote_details = []

        for agent in agents:
            conf = random.uniform(*agent.confidence_range)
            qual = random.uniform(*agent.quality_range)
            votes.append((conf, qual, agent.weight))
            vote_details.append({
                'name': agent.name,
                'confidence': conf,
                'quality': qual,
                'contribution': conf * qual * agent.weight
            })

        score = calculate_weighted_score(votes)
        scores.append(score)

        if score >= threshold:
            passes += 1
            if len(passing_examples) < 5:
                passing_examples.append({'score': score, 'votes': vote_details})
        else:
            if len(failing_examples) < 3:
                failing_examples.append({'score': score, 'votes': vote_details})

    # Calculate distribution statistics
    scores_sorted = sorted(scores)
    percentiles = {
        'p5': scores_sorted[int(n_simulations * 0.05)],
        'p25': scores_sorted[int(n_simulations * 0.25)],
        'p50': scores_sorted[int(n_simulations * 0.50)],
        'p75': scores_sorted[int(n_simulations * 0.75)],
        'p95': scores_sorted[int(n_simulations * 0.95)],
    }

    return {
        'threshold': threshold,
        'n_simulations': n_simulations,
        'pass_count': passes,
        'pass_rate': passes / n_simulations,
        'mean_score': sum(scores) / n_simulations,
        'min_score': min(scores),
        'max_score': max(scores),
        'percentiles': percentiles,
        'passing_examples': passing_examples,
        'failing_examples': failing_examples,
    }


def sensitivity_analysis(agents: List[AgentConfig],
                        base_threshold: float = 0.50) -> Dict:
    """
    Analyze how changes to parameters affect pass rate.
    """
    results = {}

    # Baseline
    baseline = monte_carlo_simulation(agents, base_threshold, 10000)
    results['baseline'] = {
        'pass_rate': baseline['pass_rate'],
        'mean_score': baseline['mean_score'],
    }

    # Test weight changes
    weight_sensitivity = []
    for i, agent in enumerate(agents):
        for multiplier in [0.5, 0.75, 1.25, 1.5, 2.0]:
            modified_agents = [
                AgentConfig(
                    name=a.name,
                    weight=a.weight * multiplier if j == i else a.weight,
                    confidence_range=a.confidence_range,
                    quality_range=a.quality_range
                )
                for j, a in enumerate(agents)
            ]
            sim = monte_carlo_simulation(modified_agents, base_threshold, 5000)
            weight_sensitivity.append({
                'agent': agent.name,
                'multiplier': multiplier,
                'new_weight': agent.weight * multiplier,
                'pass_rate': sim['pass_rate'],
                'delta': sim['pass_rate'] - baseline['pass_rate'],
            })
    results['weight_sensitivity'] = weight_sensitivity

    # Test confidence range expansion
    confidence_sensitivity = []
    for i, agent in enumerate(agents):
        for expansion in [-0.1, -0.05, 0.05, 0.10, 0.15]:
            new_min = max(0, agent.confidence_range[0] + expansion)
            new_max = min(1, agent.confidence_range[1] + expansion)

            modified_agents = [
                AgentConfig(
                    name=a.name,
                    weight=a.weight,
                    confidence_range=(new_min, new_max) if j == i else a.confidence_range,
                    quality_range=a.quality_range
                )
                for j, a in enumerate(agents)
            ]
            sim = monte_carlo_simulation(modified_agents, base_threshold, 5000)
            confidence_sensitivity.append({
                'agent': agent.name,
                'shift': expansion,
                'new_range': (new_min, new_max),
                'pass_rate': sim['pass_rate'],
                'delta': sim['pass_rate'] - baseline['pass_rate'],
            })
    results['confidence_sensitivity'] = confidence_sensitivity

    return results


def find_optimal_threshold(agents: List[AgentConfig],
                          target_pass_rate: float = 0.25) -> Dict:
    """
    Binary search to find threshold that gives target pass rate.
    """
    low, high = 0.0, 1.0
    iterations = []

    for _ in range(20):  # Binary search iterations
        mid = (low + high) / 2
        sim = monte_carlo_simulation(agents, mid, 20000)

        iterations.append({
            'threshold': mid,
            'pass_rate': sim['pass_rate'],
        })

        if sim['pass_rate'] > target_pass_rate:
            low = mid
        else:
            high = mid

        if abs(sim['pass_rate'] - target_pass_rate) < 0.01:
            break

    # Final precise simulation
    final_threshold = (low + high) / 2
    final_sim = monte_carlo_simulation(agents, final_threshold, 50000)

    return {
        'target_pass_rate': target_pass_rate,
        'optimal_threshold': final_threshold,
        'actual_pass_rate': final_sim['pass_rate'],
        'iterations': iterations,
    }


def grid_search_all_combos(agents: List[AgentConfig],
                          threshold: float,
                          steps: int = 5) -> Dict:
    """
    Exhaustive grid search over discrete combinations.
    """
    combinations = []
    pass_count = 0
    total_count = 0

    # Generate grid points for each agent
    agent_grids = []
    for agent in agents:
        conf_steps = [
            agent.confidence_range[0] + i * (agent.confidence_range[1] - agent.confidence_range[0]) / (steps - 1)
            for i in range(steps)
        ]
        qual_steps = [
            agent.quality_range[0] + i * (agent.quality_range[1] - agent.quality_range[0]) / (steps - 1)
            for i in range(steps)
        ]
        agent_grids.append(list(itertools.product(conf_steps, qual_steps)))

    # Test all combinations
    for combo in itertools.product(*agent_grids):
        votes = [
            (conf, qual, agents[i].weight)
            for i, (conf, qual) in enumerate(combo)
        ]
        score = calculate_weighted_score(votes)
        total_count += 1

        if score >= threshold:
            pass_count += 1
            if len(combinations) < 10:
                combinations.append({
                    'score': score,
                    'votes': [
                        {'agent': agents[i].name, 'conf': conf, 'qual': qual}
                        for i, (conf, qual) in enumerate(combo)
                    ]
                })

    return {
        'threshold': threshold,
        'steps_per_dimension': steps,
        'total_combinations': total_count,
        'passing_combinations': pass_count,
        'pass_rate': pass_count / total_count if total_count > 0 else 0,
        'example_passing': combinations,
    }


# ============================================================================
# VISUALIZATION HELPERS
# ============================================================================

def ascii_histogram(values: List[float], bins: int = 20, width: int = 50) -> str:
    """Create an ASCII histogram"""
    if not values:
        return "No data"

    min_val, max_val = min(values), max(values)
    bin_width = (max_val - min_val) / bins

    if bin_width == 0:
        return f"All values = {min_val:.4f}"

    counts = [0] * bins
    for v in values:
        idx = min(int((v - min_val) / bin_width), bins - 1)
        counts[idx] += 1

    max_count = max(counts)
    scale = width / max_count if max_count > 0 else 1

    lines = []
    for i, count in enumerate(counts):
        bin_start = min_val + i * bin_width
        bar = '#' * int(count * scale)
        lines.append(f"{bin_start:6.3f} |{bar}")

    return '\n'.join(lines)


def ascii_bar_chart(data: Dict[str, float], width: int = 40) -> str:
    """Create an ASCII bar chart"""
    if not data:
        return "No data"

    max_val = max(data.values())
    scale = width / max_val if max_val > 0 else 1

    lines = []
    for label, value in data.items():
        bar = '#' * int(value * scale)
        lines.append(f"{label:25s} |{bar} {value:.3f}")

    return '\n'.join(lines)


# ============================================================================
# INTERACTIVE TESTING
# ============================================================================

def interactive_test():
    """Allow user to input specific agent votes and see results"""
    print("\n" + "="*70)
    print("INTERACTIVE VOTE TESTING")
    print("="*70)
    print("\nEnter agent votes to test threshold achievement.")
    print("Format: confidence,quality for each agent")
    print("Enter 'q' to quit\n")

    total_weight = sum(a.weight for a in AGENTS)

    while True:
        votes = []
        print("-" * 50)

        for agent in AGENTS:
            while True:
                try:
                    user_input = input(f"{agent.name} (conf,qual) [{agent.confidence_range[0]:.2f}-{agent.confidence_range[1]:.2f}, {agent.quality_range[0]:.2f}-{agent.quality_range[1]:.2f}]: ")

                    if user_input.lower() == 'q':
                        return

                    if user_input.strip() == '':
                        # Use midpoint values
                        conf = (agent.confidence_range[0] + agent.confidence_range[1]) / 2
                        qual = (agent.quality_range[0] + agent.quality_range[1]) / 2
                    else:
                        conf, qual = map(float, user_input.split(','))

                    votes.append((conf, qual, agent.weight))
                    break
                except ValueError:
                    print("  Invalid format. Use: 0.5,0.8 or press Enter for defaults")

        score = calculate_weighted_score(votes)

        print(f"\n  RESULT:")
        print(f"  Weighted Score: {score:.4f}")
        print(f"  Breakdown:")
        for i, (conf, qual, weight) in enumerate(votes):
            contrib = conf * qual * weight / total_weight
            print(f"    {AGENTS[i].name}: {conf:.2f} × {qual:.2f} × {weight:.1f} = {contrib:.4f}")

        for threshold in THRESHOLDS_TO_TEST:
            status = "PASS" if score >= threshold else "FAIL"
            print(f"  Threshold {threshold:.2f}: {status}")

        print()


# ============================================================================
# MAIN REPORT
# ============================================================================

def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def main():
    """Run complete analysis and print report"""

    print("\n" + "#"*70)
    print("#" + " "*68 + "#")
    print("#" + "  THRESHOLD MATH ANALYSIS FOR VOTE AGGREGATION SYSTEM".center(68) + "#")
    print("#" + " "*68 + "#")
    print("#"*70)

    # ========================================================================
    # SECTION 1: THEORETICAL BOUNDS
    # ========================================================================
    print_section_header("1. THEORETICAL BOUNDS ANALYSIS")

    bounds = analyze_theoretical_bounds(AGENTS)

    print(f"\nTotal Weight: {bounds['total_weight']:.2f}")
    print(f"Theoretical Score Range: [{bounds['min_score']:.4f}, {bounds['max_score']:.4f}]")

    print("\nPer-Agent Analysis:")
    print("-" * 70)
    print(f"{'Agent':<20} {'Weight':>8} {'W.Frac':>8} {'MinC':>8} {'MaxC':>8} {'TypC':>8}")
    print("-" * 70)

    for agent in bounds['agents']:
        print(f"{agent['name']:<20} {agent['weight']:>8.2f} {agent['weight_fraction']:>8.2%} "
              f"{agent['min_contribution']:>8.4f} {agent['max_contribution']:>8.4f} "
              f"{agent['typical_contribution']:>8.4f}")

    total_typical = sum(a['typical_contribution'] for a in bounds['agents'])
    total_max = sum(a['max_contribution'] for a in bounds['agents'])
    print("-" * 70)
    print(f"{'TOTAL':<20} {bounds['total_weight']:>8.2f} {'100%':>8} "
          f"{bounds['min_score']:>8.4f} {bounds['max_score']:>8.4f} {total_typical:>8.4f}")

    print("\nKey Insight: The typical (midpoint) weighted score is {:.4f}".format(total_typical))

    # ========================================================================
    # SECTION 2: MINIMUM REQUIREMENTS PER THRESHOLD
    # ========================================================================
    print_section_header("2. MINIMUM REQUIREMENTS PER THRESHOLD")

    for threshold in THRESHOLDS_TO_TEST:
        req = find_minimum_requirements(AGENTS, threshold)

        status = "ACHIEVABLE" if req['can_reach_threshold'] else "IMPOSSIBLE"

        print(f"\nThreshold {threshold:.2f}: {status}")
        print(f"  - Max achievable score: {req['max_achievable']:.4f}")
        print(f"  - Typical score: {req['typical_score']:.4f}")
        print(f"  - Shortfall at typical: {req['shortfall_at_typical']:+.4f}")

        if req['shortfall_at_typical'] > 0:
            print(f"  - REQUIRES above-average votes to pass")
        else:
            print(f"  - Can pass with below-average votes")

    # ========================================================================
    # SECTION 3: MONTE CARLO SIMULATION
    # ========================================================================
    print_section_header("3. MONTE CARLO SIMULATION (100,000 trials)")

    mc_results = {}
    for threshold in THRESHOLDS_TO_TEST:
        mc_results[threshold] = monte_carlo_simulation(AGENTS, threshold, 100000)

    print("\nPass Rates by Threshold:")
    print("-" * 60)

    chart_data = {f"T={t:.2f}": mc_results[t]['pass_rate'] for t in THRESHOLDS_TO_TEST}
    print(ascii_bar_chart(chart_data))

    print("\n\nScore Distribution Statistics:")
    print("-" * 70)
    print(f"{'Threshold':>10} {'Pass%':>10} {'Mean':>10} {'P5':>10} {'P50':>10} {'P95':>10}")
    print("-" * 70)

    for threshold in THRESHOLDS_TO_TEST:
        r = mc_results[threshold]
        print(f"{threshold:>10.2f} {r['pass_rate']:>10.2%} {r['mean_score']:>10.4f} "
              f"{r['percentiles']['p5']:>10.4f} {r['percentiles']['p50']:>10.4f} "
              f"{r['percentiles']['p95']:>10.4f}")

    # Show score distribution histogram
    print("\n\nScore Distribution Histogram (threshold=0.50 simulation):")
    print("-" * 60)
    # Collect all scores from baseline simulation
    baseline_sim = monte_carlo_simulation(AGENTS, 0.50, 10000)
    scores_for_hist = []
    for _ in range(5000):
        votes = []
        for agent in AGENTS:
            conf = random.uniform(*agent.confidence_range)
            qual = random.uniform(*agent.quality_range)
            votes.append((conf, qual, agent.weight))
        scores_for_hist.append(calculate_weighted_score(votes))

    print(ascii_histogram(scores_for_hist, bins=15, width=40))

    # ========================================================================
    # SECTION 4: EXAMPLE PASSING/FAILING SCENARIOS
    # ========================================================================
    print_section_header("4. EXAMPLE SCENARIOS")

    print("\n--- PASSING EXAMPLES (threshold=0.50) ---")
    for i, ex in enumerate(mc_results[0.50]['passing_examples'][:3], 1):
        print(f"\nExample {i}: Score = {ex['score']:.4f}")
        for vote in ex['votes']:
            print(f"  {vote['name']}: conf={vote['confidence']:.3f}, qual={vote['quality']:.3f}")

    print("\n--- FAILING EXAMPLES (threshold=0.50) ---")
    for i, ex in enumerate(mc_results[0.50]['failing_examples'][:3], 1):
        print(f"\nExample {i}: Score = {ex['score']:.4f}")
        for vote in ex['votes']:
            print(f"  {vote['name']}: conf={vote['confidence']:.3f}, qual={vote['quality']:.3f}")

    # ========================================================================
    # SECTION 5: GRID SEARCH
    # ========================================================================
    print_section_header("5. EXHAUSTIVE GRID SEARCH (5 steps per dimension)")

    for threshold in [0.40, 0.45, 0.50]:
        grid = grid_search_all_combos(AGENTS, threshold, steps=5)
        print(f"\nThreshold {threshold:.2f}:")
        print(f"  Total combinations tested: {grid['total_combinations']}")
        print(f"  Passing combinations: {grid['passing_combinations']}")
        print(f"  Pass rate: {grid['pass_rate']:.2%}")

    # ========================================================================
    # SECTION 6: OPTIMAL THRESHOLD FINDER
    # ========================================================================
    print_section_header("6. OPTIMAL THRESHOLD RECOMMENDATIONS")

    target_rates = [0.10, 0.20, 0.25, 0.30, 0.40, 0.50]

    print("\nFinding thresholds for various target pass rates:")
    print("-" * 50)
    print(f"{'Target Pass Rate':>20} {'Optimal Threshold':>20}")
    print("-" * 50)

    for target in target_rates:
        result = find_optimal_threshold(AGENTS, target)
        print(f"{target:>20.0%} {result['optimal_threshold']:>20.4f}")

    # Detailed recommendation for 25% pass rate
    rec = find_optimal_threshold(AGENTS, 0.25)
    print(f"\n*** RECOMMENDED THRESHOLD: {rec['optimal_threshold']:.4f} ***")
    print(f"    This gives ~25% of random scenarios passing")
    print(f"    Actual pass rate: {rec['actual_pass_rate']:.2%}")

    # ========================================================================
    # SECTION 7: SENSITIVITY ANALYSIS
    # ========================================================================
    print_section_header("7. SENSITIVITY ANALYSIS")

    sensitivity = sensitivity_analysis(AGENTS, 0.40)  # Use lower threshold for meaningful analysis

    print("\nBaseline (threshold=0.40):")
    print(f"  Pass rate: {sensitivity['baseline']['pass_rate']:.2%}")
    print(f"  Mean score: {sensitivity['baseline']['mean_score']:.4f}")

    print("\nWeight Sensitivity (threshold=0.40):")
    print("-" * 70)
    for item in sensitivity['weight_sensitivity']:
        delta_pct = item['delta'] * 100
        direction = "+" if delta_pct >= 0 else ""
        print(f"  {item['agent']}: weight {item['new_weight']:.2f} (×{item['multiplier']:.2f}) "
              f"-> pass rate {item['pass_rate']:.2%} ({direction}{delta_pct:.1f}%)")

    print("\nConfidence Range Sensitivity (threshold=0.40):")
    print("-" * 70)
    for item in sensitivity['confidence_sensitivity']:
        delta_pct = item['delta'] * 100
        direction = "+" if delta_pct >= 0 else ""
        print(f"  {item['agent']}: shift {item['shift']:+.2f} -> range {item['new_range']} "
              f"-> pass rate {item['pass_rate']:.2%} ({direction}{delta_pct:.1f}%)")

    # ========================================================================
    # SECTION 8: KEY FINDINGS SUMMARY
    # ========================================================================
    print_section_header("8. KEY FINDINGS SUMMARY")

    print("""
MATHEMATICAL ANALYSIS CONCLUSIONS:

1. CURRENT CONFIGURATION ANALYSIS:
   - Total weight: {:.2f}
   - Score range: [{:.4f}, {:.4f}]
   - Typical score: {:.4f}
   - Mean Monte Carlo score: {:.4f}

2. THRESHOLD 0.50 IS VERY RESTRICTIVE:
   - Pass rate: {:.2%} of random scenarios
   - Requires near-maximum votes from all agents
   - Most realistic scenarios will fail

3. RECOMMENDED THRESHOLDS:
   - For 10% pass rate: ~{:.3f}
   - For 25% pass rate: ~{:.3f}  <-- RECOMMENDED
   - For 40% pass rate: ~{:.3f}

4. MATHEMATICAL CONSTRAINTS:
   - FundingRateAgent has low quality range (0.30-0.70), limiting its contribution
   - TimePatternAgent has lowest weight (0.5), reducing its influence
   - OrderBookAgent contributes most due to high weight (0.8) and quality (0.80-1.00)

5. TO INCREASE PASS RATES, CONSIDER:
   - Lowering threshold from 0.50 to 0.35-0.40
   - Increasing FundingRateAgent quality range
   - Increasing agent confidence ranges
   - Adjusting weights to balance contributions
""".format(
        bounds['total_weight'],
        bounds['min_score'],
        bounds['max_score'],
        total_typical,
        mc_results[0.50]['mean_score'],
        mc_results[0.50]['pass_rate'],
        find_optimal_threshold(AGENTS, 0.10)['optimal_threshold'],
        find_optimal_threshold(AGENTS, 0.25)['optimal_threshold'],
        find_optimal_threshold(AGENTS, 0.40)['optimal_threshold'],
    ))

    # ========================================================================
    # SECTION 9: INTERACTIVE MODE
    # ========================================================================
    print_section_header("9. INTERACTIVE TESTING")

    response = input("\nWould you like to test specific vote combinations? (y/n): ")
    if response.lower() == 'y':
        interactive_test()

    print("\n" + "="*70)
    print("Analysis complete.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
