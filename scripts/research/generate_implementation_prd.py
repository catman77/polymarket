#!/usr/bin/env python3
"""
Generate Implementation PRD from Research Findings

Reads research synthesis documents and auto-generates executable user stories
for Ralph to implement the optimization roadmap.

Author: Prof. Eleanor Nash (Strategic Synthesis)
Date: 2026-01-16
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import json


def read_synthesis_report(reports_dir: Path) -> Dict[str, Any]:
    """Read the main synthesis report."""
    synthesis_path = reports_dir / "RESEARCH_SYNTHESIS.md"
    if not synthesis_path.exists():
        raise FileNotFoundError(f"Synthesis report not found: {synthesis_path}")

    content = synthesis_path.read_text()

    # Extract top 10 priorities section
    priorities = []
    in_priorities = False
    current_priority = None

    for line in content.split('\n'):
        if '## Top 10 Priorities' in line:
            in_priorities = True
            continue
        if in_priorities and line.startswith('###'):
            # New priority
            if current_priority:
                priorities.append(current_priority)
            priority_name = line.replace('###', '').strip()
            current_priority = {'name': priority_name, 'content': []}
        elif in_priorities and line.startswith('##'):
            # End of priorities section
            if current_priority:
                priorities.append(current_priority)
            break
        elif in_priorities and current_priority:
            current_priority['content'].append(line)

    return {
        'priorities': priorities,
        'raw_content': content
    }


def read_deployment_roadmap(reports_dir: Path) -> Dict[str, Any]:
    """Read the deployment roadmap."""
    roadmap_path = reports_dir / "DEPLOYMENT_ROADMAP.md"
    if not roadmap_path.exists():
        raise FileNotFoundError(f"Roadmap not found: {roadmap_path}")

    content = roadmap_path.read_text()

    # Extract milestones
    milestones = []
    in_milestone = False
    current_milestone = None

    for line in content.split('\n'):
        if line.startswith('### Milestone'):
            if current_milestone:
                milestones.append(current_milestone)
            milestone_name = line.replace('###', '').strip()
            current_milestone = {'name': milestone_name, 'content': []}
            in_milestone = True
        elif in_milestone and line.startswith('##'):
            # End of milestones section for this week
            if current_milestone:
                milestones.append(current_milestone)
                current_milestone = None
            in_milestone = False
        elif in_milestone and current_milestone:
            current_milestone['content'].append(line)

    if current_milestone:
        milestones.append(current_milestone)

    return {
        'milestones': milestones,
        'raw_content': content
    }


def extract_files_from_milestone(milestone_content: List[str]) -> List[str]:
    """Extract file paths mentioned in milestone content."""
    files = []
    in_files_section = False

    for line in milestone_content:
        if '**Files Changed:**' in line or '**Files:**' in line:
            in_files_section = True
            continue
        if in_files_section:
            if line.startswith('**'):
                in_files_section = False
            elif line.strip().startswith('-'):
                # Extract file path from bullet point
                file_path = line.strip().lstrip('-').strip()
                # Remove parenthetical notes
                if '(' in file_path:
                    file_path = file_path.split('(')[0].strip()
                if file_path:
                    files.append(file_path)

    return files


def extract_acceptance_criteria(milestone_content: List[str]) -> List[str]:
    """Extract implementation steps from milestone content."""
    criteria = []
    in_implementation = False

    for line in milestone_content:
        if '**Implementation:**' in line:
            in_implementation = True
            continue
        if in_implementation:
            if line.startswith('**'):
                in_implementation = False
            elif line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')):
                step = line.strip()
                criteria.append(step)

    return criteria


def extract_success_metrics(milestone_content: List[str]) -> List[str]:
    """Extract success metrics from milestone content."""
    metrics = []
    in_metrics = False

    for line in milestone_content:
        if '**Success Metrics:**' in line:
            in_metrics = True
            continue
        if in_metrics:
            if line.startswith('**'):
                in_metrics = False
            elif line.strip().startswith('-'):
                metric = line.strip().lstrip('-').strip()
                if metric:
                    metrics.append(metric)

    return metrics


def generate_user_story(
    story_id: str,
    milestone_name: str,
    milestone_content: List[str],
    priority: str
) -> str:
    """Generate a user story from milestone data."""

    # Extract metadata
    files = extract_files_from_milestone(milestone_content)
    criteria = extract_acceptance_criteria(milestone_content)
    metrics = extract_success_metrics(milestone_content)

    # Parse problem and rationale
    problem = ""
    rationale = ""
    for line in milestone_content:
        if '**Problem:**' in line:
            idx = milestone_content.index(line)
            # Collect lines until next section
            for i in range(idx + 1, len(milestone_content)):
                if milestone_content[i].startswith('**'):
                    break
                problem += milestone_content[i] + "\n"

    # Build user story
    story = f"#### {story_id}: {milestone_name}\n"
    story += f"**Priority:** {priority}\n"
    story += f"**Source:** Research Synthesis + Deployment Roadmap\n\n"

    if problem.strip():
        story += "**Problem:**\n"
        story += problem.strip() + "\n\n"

    story += "**Acceptance Criteria:**\n"

    # Add implementation steps as checkboxes
    if criteria:
        for step in criteria:
            story += f"- [ ] {step}\n"
    else:
        # Fallback to generic criteria
        story += "- [ ] Review relevant research reports\n"
        story += "- [ ] Implement changes according to deployment roadmap\n"
        if files:
            for file in files:
                story += f"- [ ] Update {file}\n"
        story += "- [ ] Test changes work correctly\n"

    # Add validation
    story += "- [ ] Typecheck passes\n"

    if metrics:
        story += "- [ ] Verify success metrics:\n"
        for metric in metrics:
            story += f"  - {metric}\n"

    story += "\n"

    if files:
        story += "**Files to Modify:**\n"
        for file in files:
            story += f"- `{file}`\n"
        story += "\n"

    story += "**Testing:**\n"
    story += "- Run typecheck: `mypy scripts/research/`\n"
    story += "- Verify bot starts without errors\n"
    story += "- Monitor for 24-48 hours (shadow testing recommended)\n\n"

    story += "---\n\n"

    return story


def generate_prd(
    synthesis: Dict[str, Any],
    roadmap: Dict[str, Any],
    output_dir: Path
) -> Path:
    """Generate the implementation PRD."""

    prd_path = output_dir / "PRD-research-implementation.md"

    prd_content = """# PRD: Research Implementation - Optimization Roadmap

## Introduction

Based on comprehensive research by 9 specialized personas (48 reports, 31 user stories),
this PRD translates findings into executable code changes to achieve 60-65% win rate target.

**Source:** Research Synthesis Report (`reports/RESEARCH_SYNTHESIS.md`)

**Timeline:** 4 weeks (Jan 16 - Feb 13, 2026)

**Strategic Approach:** Simplify first (remove what hurts), then optimize (improve what works).

---

## Goals

1. **Increase win rate** from 56-58% to 60-65%
2. **Reduce system complexity** from 11 agents to 3-5 agents
3. **Lower average entry price** to <$0.20 (from ~$0.24)
4. **Improve agent confidence** calibration
5. **Fix critical bugs** (state tracking, drawdown protection)
6. **Balance directional trades** (40-60% range, not 96.5% UP bias)

---

## System Context

**Current State:**
- Balance: $200.97 (33% drawdown from $300 peak)
- Win Rate: ~58% (validated with statistical significance)
- Architecture: Multi-agent consensus (11 agents voting)
- Critical Issues: State tracking bugs, over-complexity, underperforming agents

**Target State:**
- Balance: Growing steadily with 60-65% WR
- System: 3-5 high-performing agents
- Risk: Robust drawdown protection, balanced directional trades
- Trade Quality: Cheaper entries (<$0.20), better timing (late epoch)

---

## User Stories

"""

    # Generate user stories from milestones
    story_counter = 1
    week_map = {
        'Week 1': 'CRITICAL',
        'Week 2': 'HIGH',
        'Week 3': 'MEDIUM',
        'Week 4': 'LOW'
    }

    current_week = None
    for milestone in roadmap['milestones']:
        milestone_name = milestone['name']
        milestone_content = milestone['content']

        # Determine week from milestone name or content
        week = None
        for week_key in week_map.keys():
            if week_key.lower() in ' '.join(milestone_content[:5]).lower():
                week = week_key
                break

        if week and week != current_week:
            current_week = week
            prd_content += f"\n## {week}: Implementation Tasks\n\n"

        # Generate story ID
        story_id = f"US-RI-{story_counter:03d}"
        priority = week_map.get(week, 'MEDIUM')

        # Generate user story
        user_story = generate_user_story(
            story_id=story_id,
            milestone_name=milestone_name,
            milestone_content=milestone_content,
            priority=priority
        )

        prd_content += user_story
        story_counter += 1

    # Add completion criteria
    prd_content += """
---

## Completion Criteria

**ALL user stories complete** when:
- ✅ All checkboxes marked `[x]`
- ✅ Typecheck passes for all modified files
- ✅ Bot runs without errors in production
- ✅ Win rate improvement validated (100+ trades)
- ✅ No critical bugs or regressions

**Success Validation:**
- Win rate: 60-65% over 100 trades
- System complexity: 5 agents, <1200 lines of code
- Trade quality: <$0.20 avg entry, 60%+ late trades
- Risk: No false halts, balanced directional trades

---

## Rollback Strategy

Each user story includes:
- Clear acceptance criteria (testable)
- File paths (easy to revert with git)
- Success metrics (objective go/no-go)
- Testing requirements (shadow testing recommended)

**Rollback Procedure:**
1. Identify failing user story (WR drop, errors, etc.)
2. Revert git commits for that story only
3. Restore config files from backup
4. Monitor for 24 hours to confirm stability
5. Investigate root cause before re-attempting

**Escalation:**
- WR drop <1%: Monitor for 24h (may be noise)
- WR drop 1-2%: Rollback single story
- WR drop >2%: Rollback entire week
- Critical error: HALT bot, full audit

---

## Execution Instructions

Run Ralph to execute this PRD autonomously:

```bash
./ralph.sh PRD-research-implementation.md 50 2
```

Ralph will:
1. Read each user story sequentially
2. Implement changes according to acceptance criteria
3. Run tests and typecheck
4. Mark story complete `[x]` if tests pass
5. Commit changes with descriptive message
6. Continue to next story

**Manual Oversight:**
- Review each commit before deploying to production VPS
- Shadow test major changes (Week 3 agent reduction)
- Monitor win rate after each milestone
- Rollback immediately if WR drops >1%

---

## Progress Tracking

Progress logged in `progress-research-implementation.txt`:

```
## Iteration [N] - US-RI-XXX: [Task Name]
**Priority:** CRITICAL/HIGH/MEDIUM/LOW
**Completed:** YYYY-MM-DD HH:MM
**Files Changed:**
- path/to/file1.py
- path/to/file2.md

**Learnings:**
- Pattern discovered: [useful context]
- Gotcha: [edge case handled]

---
```

---

## Next Steps After Completion

1. **Validate performance** (100+ trades at 60-65% WR)
2. **Update documentation** (CLAUDE.md, STRATEGY.md)
3. **Archive old configs** (`config/archived/`)
4. **Tag release** (`v13.0 - Research Implementation`)
5. **Monitor for 1 month** (ensure stability across regimes)
6. **Scale up** (if 65%+ WR sustained, increase position sizing)

---

**Document Version:** 1.0 (Auto-generated)
**Last Updated:** 2026-01-16
**Status:** READY FOR EXECUTION
**Total User Stories:** {story_counter - 1}

---
"""

    # Write PRD
    prd_path.write_text(prd_content)
    print(f"✅ Generated: {prd_path}")
    print(f"   Total user stories: {story_counter - 1}")

    return prd_path


def generate_progress_file(output_dir: Path) -> Path:
    """Generate empty progress tracking file."""
    progress_path = output_dir / "progress-research-implementation.txt"

    content = """# Progress Tracking: Research Implementation

This file tracks Ralph's progress executing PRD-research-implementation.md.

Format:
```
## Iteration [N] - US-RI-XXX: [Task Name]
**Priority:** CRITICAL/HIGH/MEDIUM/LOW
**Completed:** YYYY-MM-DD HH:MM
**Files Changed:**
- path/to/file.py

**Learnings:**
- Pattern: [reusable knowledge]
- Gotcha: [edge case to remember]

---
```

## Learnings for Future Iterations

(Ralph will append learnings here as patterns emerge)

---

"""

    progress_path.write_text(content)
    print(f"✅ Generated: {progress_path}")

    return progress_path


def main():
    """Main execution function."""
    # Setup paths
    repo_root = Path(__file__).resolve().parents[2]
    reports_dir = repo_root / "reports"
    output_dir = repo_root

    print("=" * 80)
    print("Auto-Generating Implementation PRD")
    print("=" * 80)
    print()

    # Read research documents
    print("📖 Reading research synthesis...")
    synthesis = read_synthesis_report(reports_dir)
    print(f"   Found {len(synthesis['priorities'])} priorities")

    print("📖 Reading deployment roadmap...")
    roadmap = read_deployment_roadmap(reports_dir)
    print(f"   Found {len(roadmap['milestones'])} milestones")
    print()

    # Generate PRD
    print("🔨 Generating implementation PRD...")
    prd_path = generate_prd(synthesis, roadmap, output_dir)
    print()

    # Generate progress file
    print("📝 Generating progress tracking file...")
    progress_path = generate_progress_file(output_dir)
    print()

    # Output instructions
    print("=" * 80)
    print("✅ Implementation PRD Generated Successfully!")
    print("=" * 80)
    print()
    print(f"📄 PRD Location: {prd_path}")
    print(f"📄 Progress Tracking: {progress_path}")
    print()
    print("🚀 Ready to execute optimizations. Run:")
    print()
    print("   ./ralph.sh PRD-research-implementation.md 50 2")
    print()
    print("This will execute all user stories autonomously.")
    print("Review commits before deploying to production VPS.")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
