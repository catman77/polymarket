#!/usr/bin/env python3
"""
Agent Voting Herding Analysis
Persona: Dr. Amara Johnson - Behavioral Finance Expert

Tests whether agents independently assess markets or exhibit herding behavior
by calculating correlation coefficients between agent vote pairs.

Herding = High correlation (>0.7) suggests redundancy or groupthink
Independence = Low correlation (<0.3) suggests diverse perspectives
"""

import sqlite3
import os
from typing import Dict, List, Tuple
from collections import defaultdict
import math

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '../../simulation/trade_journal.db')
REPORT_DIR = os.path.join(os.path.dirname(__file__), '../../reports/amara_johnson')


def connect_db() -> sqlite3.Connection:
    """Connect to shadow trading database."""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def get_agent_votes(conn: sqlite3.Connection) -> List[Tuple[int, str, str, float]]:
    """
    Query agent votes from database.

    Returns:
        List of (decision_id, agent_name, direction, confidence)
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT decision_id, agent_name, direction, confidence
        FROM agent_votes
        ORDER BY decision_id, agent_name
    """)
    return cursor.fetchall()


def build_agent_vote_matrix(votes: List[Tuple[int, str, str, float]]) -> Dict[str, List[int]]:
    """
    Build vote matrix: agent_name -> [vote_1, vote_2, ..., vote_n]

    Encoding:
    - Up = +1
    - Down = -1
    - No vote = 0 (agent didn't participate in that decision)

    Returns:
        Dict mapping agent name to list of encoded votes per decision
    """
    # Get all unique decision IDs
    decision_ids = sorted(set(row[0] for row in votes))

    # Get all unique agent names
    agent_names = sorted(set(row[1] for row in votes))

    # Initialize matrix: agent -> list of zeros
    matrix: Dict[str, List[int]] = {agent: [0] * len(decision_ids) for agent in agent_names}

    # Map decision_id to index
    decision_index = {decision_id: idx for idx, decision_id in enumerate(decision_ids)}

    # Fill matrix
    for decision_id, agent_name, direction, confidence in votes:
        idx = decision_index[decision_id]
        vote = 1 if direction.lower() == 'up' else -1
        matrix[agent_name][idx] = vote

    return matrix


def calculate_pearson_correlation(x: List[int], y: List[int]) -> Tuple[float, float]:
    """
    Calculate Pearson correlation coefficient between two vote sequences.

    Only considers decisions where BOTH agents voted (non-zero).

    Returns:
        (r, p_value) where:
        - r = correlation coefficient (-1 to +1)
        - p_value = approximate p-value (using t-distribution)
    """
    # Filter to decisions where both agents voted
    pairs = [(xi, yi) for xi, yi in zip(x, y) if xi != 0 and yi != 0]

    if len(pairs) < 3:
        # Insufficient data for correlation
        return (0.0, 1.0)

    n = len(pairs)
    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]

    # Calculate means
    mean_x = sum(x_vals) / n
    mean_y = sum(y_vals) / n

    # Calculate covariance and standard deviations
    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in pairs) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x_vals) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y_vals) / n)

    # Avoid division by zero
    if std_x == 0 or std_y == 0:
        return (0.0, 1.0)

    # Pearson r
    r = cov / (std_x * std_y)

    # Approximate p-value using t-distribution
    # t = r * sqrt(n - 2) / sqrt(1 - r^2)
    # For simplicity: |t| > 2 approximately implies p < 0.05
    if abs(r) < 1.0:
        t = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
        # Very rough approximation (proper calculation needs scipy.stats)
        p_value = 0.01 if abs(t) > 2.576 else 0.05 if abs(t) > 1.96 else 0.10 if abs(t) > 1.645 else 0.20
    else:
        # Perfect correlation (r = ±1)
        p_value = 0.0

    return (r, p_value)


def calculate_correlation_matrix(matrix: Dict[str, List[int]]) -> Dict[Tuple[str, str], Tuple[float, float, int]]:
    """
    Calculate pairwise correlation matrix for all agent pairs.

    Returns:
        Dict mapping (agent1, agent2) -> (r, p_value, n_overlapping_decisions)
    """
    agents = sorted(matrix.keys())
    correlations: Dict[Tuple[str, str], Tuple[float, float, int]] = {}

    for i, agent1 in enumerate(agents):
        for j, agent2 in enumerate(agents):
            if i < j:  # Only calculate upper triangle (avoid duplicates)
                r, p_value = calculate_pearson_correlation(matrix[agent1], matrix[agent2])
                # Count overlapping decisions (both agents voted)
                n_overlap = sum(1 for x1, x2 in zip(matrix[agent1], matrix[agent2]) if x1 != 0 and x2 != 0)
                correlations[(agent1, agent2)] = (r, p_value, n_overlap)

    return correlations


def generate_csv_matrix(matrix: Dict[str, List[int]], correlations: Dict[Tuple[str, str], Tuple[float, float, int]]) -> str:
    """Generate CSV correlation matrix with agents as rows and columns."""
    agents = sorted(matrix.keys())

    # Header
    csv_lines = ['Agent,' + ','.join(agents)]

    # Rows
    for agent1 in agents:
        row = [agent1]
        for agent2 in agents:
            if agent1 == agent2:
                row.append('1.00')  # Self-correlation is 1.0
            elif (agent1, agent2) in correlations:
                r, _, _ = correlations[(agent1, agent2)]
                row.append(f'{r:.2f}')
            elif (agent2, agent1) in correlations:
                r, _, _ = correlations[(agent2, agent1)]
                row.append(f'{r:.2f}')
            else:
                row.append('N/A')
        csv_lines.append(','.join(row))

    return '\n'.join(csv_lines)


def generate_ascii_heatmap(matrix: Dict[str, List[int]], correlations: Dict[Tuple[str, str], Tuple[float, float, int]]) -> str:
    """Generate ASCII heatmap of correlation coefficients."""
    agents = sorted(matrix.keys())

    # Color codes for correlation strength
    def get_color(r: float) -> str:
        if abs(r) >= 0.7:
            return '🔴'  # High correlation (herding)
        elif abs(r) >= 0.5:
            return '🟠'  # Moderate correlation
        elif abs(r) >= 0.3:
            return '🟡'  # Weak correlation
        else:
            return '🟢'  # Low correlation (independence)

    # Build heatmap
    lines = []
    lines.append('Correlation Heatmap (🔴 High ≥0.7, 🟠 Moderate ≥0.5, 🟡 Weak ≥0.3, 🟢 Low <0.3)')
    lines.append('')

    # Header with agent names (truncated)
    header = '        ' + ' '.join(f'{agent[:6]:>6}' for agent in agents)
    lines.append(header)
    lines.append('        ' + '------' * len(agents))

    # Rows
    for agent1 in agents:
        row_chars = [f'{agent1[:6]:>6}']
        for agent2 in agents:
            if agent1 == agent2:
                row_chars.append('  ■   ')  # Self-correlation
            elif (agent1, agent2) in correlations:
                r, _, _ = correlations[(agent1, agent2)]
                color = get_color(r)
                row_chars.append(f'{color}{r:>5.2f}')
            elif (agent2, agent1) in correlations:
                r, _, _ = correlations[(agent2, agent1)]
                color = get_color(r)
                row_chars.append(f'{color}{r:>5.2f}')
            else:
                row_chars.append('  N/A ')
        lines.append('  '.join(row_chars))

    return '\n'.join(lines)


def generate_report(matrix: Dict[str, List[int]], correlations: Dict[Tuple[str, str], Tuple[float, float, int]]) -> str:
    """Generate comprehensive herding analysis report."""
    agents = sorted(matrix.keys())

    # Identify herding pairs (r > 0.7)
    herding_pairs = [(a1, a2, r, p, n) for (a1, a2), (r, p, n) in correlations.items() if r > 0.7]
    herding_pairs.sort(key=lambda x: x[2], reverse=True)  # Sort by r descending

    # Identify independent pairs (r < 0.3)
    independent_pairs = [(a1, a2, r, p, n) for (a1, a2), (r, p, n) in correlations.items() if abs(r) < 0.3]

    # Identify negative correlations (contrarian agents)
    contrarian_pairs = [(a1, a2, r, p, n) for (a1, a2), (r, p, n) in correlations.items() if r < -0.5]
    contrarian_pairs.sort(key=lambda x: x[2])  # Sort by r ascending (most negative first)

    # Build report
    lines = []
    lines.append('# Agent Voting Herding Analysis')
    lines.append('')
    lines.append('**Persona:** Dr. Amara Johnson - Behavioral Finance Expert')
    lines.append('**Analysis Date:** 2026-01-16')
    lines.append('')
    lines.append('---')
    lines.append('')
    lines.append('## Executive Summary')
    lines.append('')
    lines.append(f'**Agents Analyzed:** {len(agents)}')
    lines.append(f'**Total Agent Pairs:** {len(correlations)}')
    lines.append(f'**Herding Pairs (r > 0.7):** {len(herding_pairs)}')
    lines.append(f'**Independent Pairs (|r| < 0.3):** {len(independent_pairs)}')
    lines.append(f'**Contrarian Pairs (r < -0.5):** {len(contrarian_pairs)}')
    lines.append('')

    # Verdict
    if len(herding_pairs) > len(agents) * 0.3:  # >30% of pairs show herding
        verdict = '⚠️ **HERDING DETECTED** - Multiple agents exhibit redundant behavior'
    elif len(herding_pairs) > 0:
        verdict = '⚠️ **MODERATE HERDING** - Some agent pairs show high correlation'
    else:
        verdict = '✅ **INDEPENDENT** - Agents exhibit diverse perspectives'
    lines.append(verdict)
    lines.append('')
    lines.append('---')
    lines.append('')

    # Methodology
    lines.append('## Methodology')
    lines.append('')
    lines.append('### Herding Definition')
    lines.append('')
    lines.append('**Herding** occurs when multiple agents make similar predictions without independent')
    lines.append('reasoning. In trading systems, herding reduces diversity and increases systemic risk.')
    lines.append('')
    lines.append('### Correlation Analysis')
    lines.append('')
    lines.append('- **Vote Encoding:** Up = +1, Down = -1, No Vote = 0')
    lines.append('- **Metric:** Pearson correlation coefficient (r)')
    lines.append('- **Interpretation:**')
    lines.append('  - **r > 0.7:** High correlation (herding - redundancy)')
    lines.append('  - **0.3 < r < 0.7:** Moderate correlation (some overlap)')
    lines.append('  - **|r| < 0.3:** Low correlation (independent)')
    lines.append('  - **r < -0.5:** Negative correlation (contrarian behavior)')
    lines.append('')
    lines.append('Only decisions where BOTH agents voted are included in correlation calculation.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Herding pairs
    lines.append('## Herding Pairs (r > 0.7)')
    lines.append('')
    if herding_pairs:
        lines.append('These agent pairs vote together too consistently. Consider disabling one agent')
        lines.append('from each pair to reduce redundancy and improve decision diversity.')
        lines.append('')
        lines.append('| Agent 1 | Agent 2 | Correlation (r) | P-Value | Overlapping Decisions |')
        lines.append('|---------|---------|-----------------|---------|------------------------|')
        for a1, a2, r, p, n in herding_pairs:
            lines.append(f'| {a1} | {a2} | {r:.3f} | {p:.3f} | {n} |')
    else:
        lines.append('✅ **No herding detected.** All agent pairs show r ≤ 0.7.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Independent pairs
    lines.append('## Independent Pairs (|r| < 0.3)')
    lines.append('')
    lines.append(f'**Count:** {len(independent_pairs)} pairs')
    lines.append('')
    lines.append('These agent pairs provide diverse perspectives. This is the ideal state for')
    lines.append('multi-agent consensus systems.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Contrarian pairs
    lines.append('## Contrarian Pairs (r < -0.5)')
    lines.append('')
    if contrarian_pairs:
        lines.append('These agent pairs vote in opposite directions. This can indicate:')
        lines.append('1. Genuine contrarian strategies (intentional)')
        lines.append('2. Conflicting methodologies (need investigation)')
        lines.append('')
        lines.append('| Agent 1 | Agent 2 | Correlation (r) | P-Value | Overlapping Decisions |')
        lines.append('|---------|---------|-----------------|---------|------------------------|')
        for a1, a2, r, p, n in contrarian_pairs:
            lines.append(f'| {a1} | {a2} | {r:.3f} | {p:.3f} | {n} |')
    else:
        lines.append('No strongly contrarian agent pairs detected.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Correlation matrix
    lines.append('## Correlation Matrix')
    lines.append('')
    lines.append('```')
    lines.append(generate_ascii_heatmap(matrix, correlations))
    lines.append('```')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Recommendations
    lines.append('## Recommendations')
    lines.append('')
    if herding_pairs:
        lines.append('### 🔴 HIGH PRIORITY: Reduce Redundancy')
        lines.append('')
        lines.append('**Action:** Disable one agent from each herding pair.')
        lines.append('')
        for a1, a2, r, p, n in herding_pairs[:3]:  # Top 3 worst offenders
            lines.append(f'- **{a1} ↔ {a2}** (r = {r:.3f}): Disable lower-performing agent')
        lines.append('')
        lines.append('**Rationale:** Herding reduces decision diversity without adding value.')
        lines.append('Two agents voting identically provide no more information than one.')
        lines.append('')

    if len(independent_pairs) > 0:
        lines.append('### ✅ MAINTAIN: Independent Agents')
        lines.append('')
        lines.append(f'**Count:** {len(independent_pairs)} pairs show healthy independence (|r| < 0.3).')
        lines.append('')
        lines.append('**Action:** Keep these agents active. They provide diverse perspectives.')
        lines.append('')

    if contrarian_pairs:
        lines.append('### ⚠️ INVESTIGATE: Contrarian Behavior')
        lines.append('')
        lines.append('**Action:** Review contrarian agent pairs to ensure behavior is intentional,')
        lines.append('not a bug or data issue.')
        lines.append('')

    lines.append('### General Recommendations')
    lines.append('')
    lines.append('1. **Reduce Agent Count:** If herding is widespread, the system may have too many')
    lines.append('   agents. Consider consolidating to 3-5 truly independent agents.')
    lines.append('2. **Agent Diversity:** Ensure agents use different data sources and methodologies.')
    lines.append('3. **Regular Audits:** Re-run this analysis quarterly to detect emerging herding.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Dr. Johnson's assessment
    lines.append('## Behavioral Finance Perspective')
    lines.append('')
    lines.append('> *"Do agents independently assess the market? Or do they copy each other (herding)?"*')
    lines.append('> — Dr. Amara Johnson')
    lines.append('')
    lines.append('**Herding in Financial Markets:**')
    lines.append('')
    lines.append('Herding behavior occurs when decision-makers imitate others rather than making')
    lines.append('independent judgments. In multi-agent systems, herding manifests as high vote')
    lines.append('correlation between agents.')
    lines.append('')
    lines.append('**Risks of Herding:**')
    lines.append('- **Reduced diversity:** All agents fail in the same way')
    lines.append('- **Systemic risk:** Correlated errors compound losses')
    lines.append('- **False confidence:** Consensus appears strong but is redundant')
    lines.append('')
    lines.append('**Benefits of Independence:**')
    lines.append('- **Diverse perspectives:** Agents disagree productively')
    lines.append('- **Error averaging:** Uncorrelated errors cancel out')
    lines.append('- **Robust decisions:** Consensus emerges from genuine disagreement')
    lines.append('')
    lines.append('**Assessment:**')
    lines.append('')
    if len(herding_pairs) > len(agents) * 0.3:
        lines.append('The current system exhibits **significant herding**. Multiple agents are')
        lines.append('redundant and should be disabled to improve decision quality.')
    elif len(herding_pairs) > 0:
        lines.append('The system shows **moderate herding** in a few agent pairs. Selective agent')
        lines.append('removal can improve diversity without losing valuable perspectives.')
    else:
        lines.append('The system exhibits **healthy independence**. Agents provide diverse perspectives')
        lines.append('and genuine consensus. This is the ideal state for multi-agent decision-making.')
    lines.append('')
    lines.append('---')
    lines.append('')

    # Appendix
    lines.append('## Appendix: Full Correlation Matrix (CSV)')
    lines.append('')
    lines.append('```csv')
    lines.append(generate_csv_matrix(matrix, correlations))
    lines.append('```')
    lines.append('')

    return '\n'.join(lines)


def main():
    """Main execution."""
    print("Agent Voting Herding Analysis")
    print("=" * 60)
    print()

    # Connect to database
    try:
        conn = connect_db()
        print(f"✓ Connected to database: {DB_PATH}")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print()
        print("Note: Shadow trading database not found.")
        print("This script requires the bot to have recorded agent votes.")
        return

    # Get agent votes
    votes = get_agent_votes(conn)
    print(f"✓ Retrieved {len(votes)} agent votes")

    if len(votes) == 0:
        print("✗ No agent votes found in database.")
        print()
        print("This may be a dev environment with no trading history.")
        conn.close()
        return

    # Build vote matrix
    matrix = build_agent_vote_matrix(votes)
    agent_count = len(matrix)
    print(f"✓ Built vote matrix for {agent_count} agents")

    if agent_count < 2:
        print("✗ Need at least 2 agents to calculate correlations.")
        conn.close()
        return

    # Calculate correlation matrix
    correlations = calculate_correlation_matrix(matrix)
    print(f"✓ Calculated {len(correlations)} pairwise correlations")

    # Identify herding pairs
    herding_pairs = [(a1, a2, r) for (a1, a2), (r, p, n) in correlations.items() if r > 0.7]
    print(f"✓ Herding pairs (r > 0.7): {len(herding_pairs)}")

    # Generate CSV matrix
    os.makedirs(REPORT_DIR, exist_ok=True)
    csv_path = os.path.join(REPORT_DIR, 'agent_correlation_matrix.csv')
    csv_content = generate_csv_matrix(matrix, correlations)
    with open(csv_path, 'w') as f:
        f.write(csv_content)
    print(f"✓ Generated CSV: {csv_path}")

    # Generate report
    report_path = os.path.join(REPORT_DIR, 'agent_herding_analysis.md')
    report = generate_report(matrix, correlations)
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"✓ Generated report: {report_path}")

    # Summary
    print()
    print("Summary:")
    print(f"  Agents analyzed: {agent_count}")
    print(f"  Total pairs: {len(correlations)}")
    print(f"  Herding pairs (r > 0.7): {len(herding_pairs)}")
    if len(herding_pairs) > 0:
        print()
        print("  ⚠️  HERDING DETECTED - Review report for recommendations")
    else:
        print()
        print("  ✅ No herding detected - Agents are independent")

    conn.close()


if __name__ == '__main__':
    main()
