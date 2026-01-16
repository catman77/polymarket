#!/usr/bin/env python3
"""
Per-Agent Performance Analysis
Author: Victor 'Vic' Ramanujan (Quantitative Strategist)

Analyzes individual agent voting accuracy and contribution to trading outcomes.
Identifies which agents help vs hurt performance.
"""

import sqlite3
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class AgentPerformance:
    """Agent performance metrics"""
    agent_name: str
    total_votes: int
    votes_up: int
    votes_down: int
    correct_votes: int
    incorrect_votes: int
    accuracy: float
    avg_confidence: float
    avg_quality: float
    up_win_rate: float  # Win rate when agent voted Up
    down_win_rate: float  # Win rate when agent voted Down

    @property
    def overall_win_rate(self) -> float:
        """Calculate overall win rate"""
        total = self.correct_votes + self.incorrect_votes
        return (self.correct_votes / total * 100) if total > 0 else 0.0


def analyze_agent_votes(db_path: str) -> Dict[str, AgentPerformance]:
    """
    Query agent_votes and outcomes to calculate per-agent accuracy.

    Logic:
    1. Join agent_votes -> decisions -> outcomes
    2. For each agent vote, check if predicted direction matched actual direction
    3. Calculate win rate separately for Up votes vs Down votes
    4. Identify agents with <50% accuracy (disable candidates)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to join agent votes with outcomes
    query = """
    SELECT
        av.agent_name,
        av.direction as voted_direction,
        av.confidence,
        av.quality,
        o.predicted_direction,
        o.actual_direction,
        CASE
            WHEN av.direction = o.actual_direction THEN 1
            ELSE 0
        END as is_correct
    FROM agent_votes av
    JOIN decisions d ON av.decision_id = d.id
    JOIN outcomes o ON (d.strategy = o.strategy AND d.crypto = o.crypto AND d.epoch = o.epoch)
    WHERE d.should_trade = 1
    """

    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Aggregate by agent
    agent_data = defaultdict(lambda: {
        'total': 0,
        'up_votes': 0,
        'down_votes': 0,
        'correct': 0,
        'incorrect': 0,
        'up_correct': 0,
        'up_total': 0,
        'down_correct': 0,
        'down_total': 0,
        'confidence_sum': 0.0,
        'quality_sum': 0.0
    })

    for row in rows:
        agent_name, voted_direction, confidence, quality, predicted_dir, actual_dir, is_correct = row

        agent = agent_data[agent_name]
        agent['total'] += 1
        agent['confidence_sum'] += confidence
        agent['quality_sum'] += quality

        if voted_direction == 'Up':
            agent['up_votes'] += 1
            agent['up_total'] += 1
            if is_correct:
                agent['up_correct'] += 1
                agent['correct'] += 1
            else:
                agent['incorrect'] += 1
        else:  # Down
            agent['down_votes'] += 1
            agent['down_total'] += 1
            if is_correct:
                agent['down_correct'] += 1
                agent['correct'] += 1
            else:
                agent['incorrect'] += 1

    # Calculate metrics for each agent
    results = {}
    for agent_name, data in agent_data.items():
        total = data['total']
        if total == 0:
            continue

        accuracy = (data['correct'] / total * 100) if total > 0 else 0.0
        avg_confidence = data['confidence_sum'] / total
        avg_quality = data['quality_sum'] / total

        up_wr = (data['up_correct'] / data['up_total'] * 100) if data['up_total'] > 0 else 0.0
        down_wr = (data['down_correct'] / data['down_total'] * 100) if data['down_total'] > 0 else 0.0

        results[agent_name] = AgentPerformance(
            agent_name=agent_name,
            total_votes=total,
            votes_up=data['up_votes'],
            votes_down=data['down_votes'],
            correct_votes=data['correct'],
            incorrect_votes=data['incorrect'],
            accuracy=accuracy,
            avg_confidence=avg_confidence,
            avg_quality=avg_quality,
            up_win_rate=up_wr,
            down_win_rate=down_wr
        )

    return results


def generate_report(agent_performance: Dict[str, AgentPerformance], output_md: str, output_csv: str):
    """Generate markdown report and CSV table"""

    # Sort by accuracy (descending)
    sorted_agents = sorted(
        agent_performance.values(),
        key=lambda x: x.accuracy,
        reverse=True
    )

    # Identify disable candidates (<50% accuracy)
    disable_candidates = [a for a in sorted_agents if a.accuracy < 50.0]

    # Generate markdown report
    with open(output_md, 'w') as f:
        f.write("# Per-Agent Performance Analysis\n\n")
        f.write("**Author:** Victor 'Vic' Ramanujan (Quantitative Strategist)\n")
        f.write("**Date:** 2026-01-16\n")
        f.write("**Data Source:** simulation/trade_journal.db → agent_votes + outcomes\n\n")
        f.write("---\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")

        if not sorted_agents:
            f.write("**Assessment:** INSUFFICIENT DATA\n")
            f.write("**Total Agents Analyzed:** 0\n\n")
            f.write("⚠️ **No agent voting data available** (bot may not be running or database empty)\n\n")
            f.write("---\n\n")
            f.write("## Recommendations\n\n")
            f.write("**Data Collection Phase:**\n")
            f.write("- Shadow trading system not populated yet\n")
            f.write("- Ensure bot is running with shadow strategies enabled\n")
            f.write("- Re-run this analysis after 50+ trades per strategy\n\n")
        else:
            f.write(f"**Total Agents Analyzed:** {len(sorted_agents)}\n")
            f.write(f"**Total Votes:** {sum(a.total_votes for a in sorted_agents)}\n")
            f.write(f"**Average Accuracy:** {sum(a.accuracy for a in sorted_agents) / len(sorted_agents):.1f}%\n\n")

            if disable_candidates:
                f.write(f"⚠️ **{len(disable_candidates)} agents with <50% accuracy** (disable candidates)\n\n")
            else:
                f.write("✅ **All agents performing above 50% accuracy**\n\n")

            f.write("---\n\n")

            # Agent Rankings
            f.write("## Agent Rankings (by Accuracy)\n\n")
            f.write("| Rank | Agent Name | Accuracy | Votes | Up WR | Down WR | Conf | Quality |\n")
            f.write("|------|-----------|----------|-------|-------|---------|------|--------|\n")

            for i, agent in enumerate(sorted_agents, 1):
                rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

                # Flag underperformers
                flag = " ⚠️" if agent.accuracy < 50.0 else ""

                f.write(f"| {rank_emoji} | {agent.agent_name}{flag} | {agent.accuracy:.1f}% | "
                       f"{agent.total_votes} | {agent.up_win_rate:.1f}% | {agent.down_win_rate:.1f}% | "
                       f"{agent.avg_confidence:.2f} | {agent.avg_quality:.2f} |\n")

            f.write("\n---\n\n")

            # Detailed Analysis
            f.write("## Detailed Agent Analysis\n\n")

            for agent in sorted_agents:
                f.write(f"### {agent.agent_name}\n\n")
                f.write(f"**Overall Accuracy:** {agent.accuracy:.1f}%\n")
                f.write(f"**Total Votes:** {agent.total_votes} ({agent.votes_up} Up, {agent.votes_down} Down)\n")
                f.write(f"**Correct:** {agent.correct_votes} | **Incorrect:** {agent.incorrect_votes}\n\n")

                f.write("**Directional Performance:**\n")
                f.write(f"- Up votes: {agent.up_win_rate:.1f}% win rate ({agent.votes_up} votes)\n")
                f.write(f"- Down votes: {agent.down_win_rate:.1f}% win rate ({agent.votes_down} votes)\n\n")

                f.write("**Quality Metrics:**\n")
                f.write(f"- Avg Confidence: {agent.avg_confidence:.2f}\n")
                f.write(f"- Avg Quality Score: {agent.avg_quality:.2f}\n\n")

                # Recommendation
                if agent.accuracy < 50.0:
                    f.write("🔴 **RECOMMENDATION: DISABLE**\n")
                    f.write(f"- Agent is worse than random (50%)\n")
                    f.write(f"- Disabling will likely improve overall system accuracy\n\n")
                elif agent.accuracy < 55.0:
                    f.write("🟡 **RECOMMENDATION: MONITOR**\n")
                    f.write(f"- Agent barely beats random baseline\n")
                    f.write(f"- Monitor performance over next 50 votes\n\n")
                else:
                    f.write("🟢 **RECOMMENDATION: KEEP**\n")
                    f.write(f"- Agent provides positive contribution\n\n")

                f.write("---\n\n")

            # Disable Candidates Section
            if disable_candidates:
                f.write("## ⚠️ Agents with <50% Accuracy (Disable Candidates)\n\n")

                for agent in disable_candidates:
                    f.write(f"### {agent.agent_name}\n")
                    f.write(f"- **Accuracy:** {agent.accuracy:.1f}% (worse than coin flip)\n")
                    f.write(f"- **Total Votes:** {agent.total_votes}\n")
                    f.write(f"- **Action:** Set `ENABLE_{agent.agent_name.upper()}_AGENT = False` in config\n\n")

                f.write("**Expected Impact of Disabling:**\n")
                f.write("- Removing negative contributors should improve system-wide win rate\n")
                f.write("- Test via shadow trading before deploying to production\n\n")
                f.write("---\n\n")

            # Methodology
            f.write("## Methodology\n\n")
            f.write("**Data Source:** SQLite database `trade_journal.db`\n\n")
            f.write("**Query Logic:**\n")
            f.write("1. Join `agent_votes` → `decisions` → `outcomes`\n")
            f.write("2. For each vote, check if agent's direction matched actual outcome\n")
            f.write("3. Calculate accuracy = correct_votes / total_votes\n")
            f.write("4. Separate win rates for Up votes vs Down votes\n\n")
            f.write("**Accuracy Calculation:**\n")
            f.write("- Agent is 'correct' if voted direction matches actual market direction\n")
            f.write("- Baseline: 50% (random coin flip)\n")
            f.write("- <50% = Agent hurts performance\n")
            f.write("- >55% = Agent provides edge\n\n")
            f.write("**Confidence & Quality:**\n")
            f.write("- Confidence: Agent's self-reported certainty (0-1)\n")
            f.write("- Quality: Entry quality score from agent (0-1)\n")
            f.write("- High confidence + low accuracy = overconfident agent\n\n")

    # Generate CSV table
    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Rank', 'Agent Name', 'Accuracy (%)', 'Total Votes',
            'Up Votes', 'Down Votes', 'Up Win Rate (%)', 'Down Win Rate (%)',
            'Avg Confidence', 'Avg Quality', 'Recommendation'
        ])

        for i, agent in enumerate(sorted_agents, 1):
            recommendation = "DISABLE" if agent.accuracy < 50.0 else "MONITOR" if agent.accuracy < 55.0 else "KEEP"

            writer.writerow([
                i,
                agent.agent_name,
                f"{agent.accuracy:.1f}",
                agent.total_votes,
                agent.votes_up,
                agent.votes_down,
                f"{agent.up_win_rate:.1f}",
                f"{agent.down_win_rate:.1f}",
                f"{agent.avg_confidence:.2f}",
                f"{agent.avg_quality:.2f}",
                recommendation
            ])


def main():
    """Main execution"""
    # Paths
    db_path = Path(__file__).parent.parent.parent / "simulation" / "trade_journal.db"
    report_dir = Path(__file__).parent.parent.parent / "reports" / "vic_ramanujan"

    # Create output directory
    report_dir.mkdir(parents=True, exist_ok=True)

    output_md = report_dir / "per_agent_performance.md"
    output_csv = report_dir / "agent_rankings.csv"

    print(f"Per-Agent Performance Analysis")
    print(f"Author: Victor 'Vic' Ramanujan")
    print(f"-" * 60)

    # Check if database exists
    if not db_path.exists():
        print(f"⚠️  Database not found: {db_path}")
        print(f"Creating empty report...")

        # Generate empty report
        generate_report({}, output_md, output_csv)

        print(f"\n✅ Report generated: {output_md}")
        print(f"✅ CSV table generated: {output_csv}")
        print(f"\nRe-run this script after bot has collected voting data.")
        return

    # Analyze agent votes
    print(f"Querying database: {db_path}")
    agent_performance = analyze_agent_votes(str(db_path))

    if not agent_performance:
        print(f"⚠️  No agent voting data found in database")
        print(f"Creating empty report...")
    else:
        print(f"\n✅ Analyzed {len(agent_performance)} agents")

        # Print quick summary
        sorted_agents = sorted(agent_performance.values(), key=lambda x: x.accuracy, reverse=True)

        print(f"\nTop 3 Agents:")
        for i, agent in enumerate(sorted_agents[:3], 1):
            print(f"  {i}. {agent.agent_name}: {agent.accuracy:.1f}% accuracy ({agent.total_votes} votes)")

        disable_candidates = [a for a in sorted_agents if a.accuracy < 50.0]
        if disable_candidates:
            print(f"\n⚠️  {len(disable_candidates)} agents with <50% accuracy (disable candidates)")

    # Generate reports
    print(f"\nGenerating reports...")
    generate_report(agent_performance, output_md, output_csv)

    print(f"\n✅ Report generated: {output_md}")
    print(f"✅ CSV table generated: {output_csv}")


if __name__ == "__main__":
    main()
