#!/usr/bin/env python3
"""
Component Elimination Audit

PERSONA: Alex "Occam" Rousseau (First Principles Engineer)
MINDSET: "Complexity is a liability. What's the simplest thing that could possibly work?"

Audits every component in the trading system to identify elimination candidates.
Every line of code is a liability—prove it earns its keep.

Key Questions:
- Can we delete this entire agent and improve results?
- Are we solving the right problem, or optimizing the wrong solution?
- What would this system look like if we rebuilt it with only what we know works?
"""

import os
import sys
import re
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@dataclass
class Component:
    """Represents a system component with cost and benefit metrics"""
    name: str
    type: str  # 'agent', 'feature', 'config', 'module'
    file_path: str = ""
    lines_of_code: int = 0
    execution_time_ms: float = 0.0  # Estimated
    decision_frequency: float = 0.0  # % of trades influenced (0.0-1.0)
    win_rate_contribution: float = 0.0  # Expected WR delta if removed (-0.05 to +0.05)
    description: str = ""
    dependencies: List[str] = field(default_factory=list)
    config_params: List[str] = field(default_factory=list)

    @property
    def maintenance_burden(self) -> str:
        """Qualitative assessment of maintenance cost"""
        if self.lines_of_code == 0:
            return "ZERO"
        elif self.lines_of_code < 50:
            return "LOW"
        elif self.lines_of_code < 200:
            return "MODERATE"
        else:
            return "HIGH"

    @property
    def elimination_score(self) -> float:
        """
        Higher score = better candidate for elimination

        Score formula:
        - Negative WR contribution: +10 (actively hurts)
        - Zero WR contribution: +5 (dead weight)
        - Low decision frequency (<10%): +3 (rarely used)
        - High LOC (>200): +2 (high maintenance)
        - Positive WR contribution: -10 (keep!)
        """
        score = 0.0

        # Win rate impact (most important)
        if self.win_rate_contribution < -0.01:  # Hurts WR by >1%
            score += 10
        elif abs(self.win_rate_contribution) < 0.01:  # Zero impact
            score += 5
        elif self.win_rate_contribution > 0.02:  # Helps WR by >2%
            score -= 10

        # Decision frequency
        if self.decision_frequency < 0.10:  # Used <10% of time
            score += 3

        # Maintenance burden
        if self.lines_of_code > 200:
            score += 2
        elif self.lines_of_code > 500:
            score += 3

        # Execution cost (if significant)
        if self.execution_time_ms > 100:  # >100ms per call
            score += 1

        return score

    @property
    def recommendation(self) -> str:
        """Elimination recommendation based on score"""
        score = self.elimination_score
        if score >= 10:
            return "🔴 DELETE (high confidence)"
        elif score >= 7:
            return "🟠 DISABLE (test removal)"
        elif score >= 4:
            return "🟡 REVIEW (low value)"
        elif score >= 0:
            return "🟢 KEEP (marginal value)"
        else:
            return "✅ ESSENTIAL (proven value)"


class ComponentAuditor:
    """Audits all system components for elimination candidates"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.components: List[Component] = []
        self.agent_performance: Dict[str, float] = {}
        self.shadow_performance: Dict[str, Dict[str, Any]] = {}

    def run_audit(self) -> List[Component]:
        """Execute full component audit"""
        print("🔍 Starting Component Elimination Audit...")
        print("   Persona: Alex 'Occam' Rousseau")
        print("   Philosophy: Complexity is a liability. Prove every component earns its keep.\n")

        # Load performance data
        self._load_agent_performance()
        self._load_shadow_performance()

        # Audit each component type
        self._audit_agents()
        self._audit_features()
        self._audit_config_parameters()

        # Sort by elimination score (highest first)
        self.components.sort(key=lambda c: c.elimination_score, reverse=True)

        print(f"\n✅ Audit complete: {len(self.components)} components analyzed\n")
        return self.components

    def _load_agent_performance(self):
        """Load per-agent win rate from research reports"""
        report_path = self.project_root / "reports" / "vic_ramanujan" / "per_agent_performance.md"

        if not report_path.exists():
            print("⚠️  Agent performance report not found (will use estimates)")
            return

        try:
            with open(report_path, 'r') as f:
                content = f.read()

            # Parse agent accuracy from markdown table
            # Format: | AgentName | 48.5% | ...
            pattern = r'\|\s*(\w+Agent)\s*\|\s*(\d+\.?\d*)%'
            matches = re.findall(pattern, content)

            for agent_name, accuracy_str in matches:
                accuracy = float(accuracy_str) / 100.0
                # Convert accuracy to WR contribution (vs 50% baseline)
                self.agent_performance[agent_name] = accuracy - 0.50

            print(f"📊 Loaded performance data for {len(self.agent_performance)} agents")

        except Exception as e:
            print(f"⚠️  Error loading agent performance: {e}")

    def _load_shadow_performance(self):
        """Load shadow strategy performance from database"""
        db_path = self.project_root / "simulation" / "trade_journal.db"

        if not db_path.exists():
            print("⚠️  Shadow trading database not found (will use estimates)")
            return

        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT strategy_name, win_rate, total_pnl, total_trades
                FROM performance
                WHERE total_trades >= 5
            """)

            for row in cursor.fetchall():
                strategy_name, win_rate, total_pnl, total_trades = row
                self.shadow_performance[strategy_name] = {
                    'win_rate': win_rate,
                    'total_pnl': total_pnl,
                    'total_trades': total_trades
                }

            conn.close()
            print(f"📊 Loaded performance data for {len(self.shadow_performance)} shadow strategies")

        except Exception as e:
            print(f"⚠️  Error loading shadow performance: {e}")

    def _audit_agents(self):
        """Audit all agent components"""
        print("🤖 Auditing Agents...")

        agents_dir = self.project_root / "agents"
        agent_files = list(agents_dir.glob("*.py")) + list(agents_dir.glob("voting/*.py"))

        for agent_file in agent_files:
            if agent_file.name == "__init__.py" or agent_file.name == "base_agent.py":
                continue

            # Extract agent name from filename
            agent_name = self._extract_agent_name(agent_file.name)
            if not agent_name:
                continue

            # Count lines of code
            loc = self._count_lines(agent_file)

            # Get performance data
            wr_contribution = self.agent_performance.get(agent_name, 0.0)

            # Estimate decision frequency (from config weights)
            decision_freq = self._estimate_decision_frequency(agent_name)

            component = Component(
                name=agent_name,
                type='agent',
                file_path=str(agent_file.relative_to(self.project_root)),
                lines_of_code=loc,
                win_rate_contribution=wr_contribution,
                decision_frequency=decision_freq,
                description=f"Agent voting on market direction",
                config_params=self._extract_agent_config_params(agent_name)
            )

            self.components.append(component)
            print(f"  ✓ {agent_name}: {loc} LOC, WR impact={wr_contribution:+.2%}, freq={decision_freq:.0%}")

    def _audit_features(self):
        """Audit feature components (RSI, confluence, regime detection, etc.)"""
        print("\n🔧 Auditing Features...")

        # Define features manually (extracted from bot logic)
        features = [
            {
                'name': 'RSI Indicator',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 80,
                'description': '14-period RSI calculation across all cryptos',
                'decision_freq': 0.80,  # Used in TechAgent
                'wr_contribution': 0.0,  # Unknown, needs ablation test
            },
            {
                'name': 'Exchange Confluence',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 120,
                'description': 'Multi-exchange price agreement detection',
                'decision_freq': 0.90,
                'wr_contribution': 0.0,  # Unknown
            },
            {
                'name': 'Regime Detection',
                'file': 'bot/ralph_regime_adapter.py',
                'loc_estimate': 200,
                'description': 'Market classification (bull/bear/sideways/volatile)',
                'decision_freq': 1.0,  # Always runs
                'wr_contribution': 0.0,  # From RegimeAgent performance
            },
            {
                'name': 'Trend Filter',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 60,
                'description': 'Directional bias filter (blocks trades against trend)',
                'decision_freq': 0.40,  # When strong trend detected
                'wr_contribution': -0.03,  # Caused Jan 14 96.5% UP bias disaster
            },
            {
                'name': 'Recovery Mode Controller',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 150,
                'description': 'Adjusts position sizing based on recent losses',
                'decision_freq': 0.20,  # Only in losing streaks
                'wr_contribution': 0.0,  # Unknown (from Amara's analysis)
            },
            {
                'name': 'Auto-Redemption',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 100,
                'description': 'Automatic winning position redemption',
                'decision_freq': 1.0,  # After every epoch
                'wr_contribution': 0.0,  # Infrastructure, not strategy
            },
            {
                'name': 'Position Correlation Limits',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 80,
                'description': 'Max 4 positions, max 3 same direction',
                'decision_freq': 0.30,  # When approaching limits
                'wr_contribution': 0.02,  # Risk management benefit
            },
            {
                'name': 'Tiered Position Sizing',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 50,
                'description': 'Dynamic position sizing based on balance',
                'decision_freq': 1.0,  # Every trade
                'wr_contribution': 0.03,  # Risk management benefit
            },
            {
                'name': 'Drawdown Protection',
                'file': 'bot/momentum_bot_v12.py',
                'loc_estimate': 40,
                'description': '30% drawdown halt mechanism',
                'decision_freq': 1.0,  # Checked every trade
                'wr_contribution': 0.05,  # Critical safety feature
            },
            {
                'name': 'Candlestick Pattern Recognition',
                'file': 'agents/candle_agent.py',
                'loc_estimate': 200,
                'description': 'Detects bullish/bearish candlestick patterns',
                'decision_freq': 0.70,
                'wr_contribution': 0.0,  # From CandlestickAgent performance
            },
            {
                'name': 'Time Pattern Analysis',
                'file': 'agents/time_pattern_agent.py',
                'loc_estimate': 150,
                'description': 'Historical hourly performance patterns',
                'decision_freq': 0.50,
                'wr_contribution': 0.0,  # From TimePatternAgent performance
            },
            {
                'name': 'Orderbook Microstructure',
                'file': 'agents/voting/orderbook_agent.py',
                'loc_estimate': 180,
                'description': 'Bid-ask spread and depth analysis',
                'decision_freq': 0.60,
                'wr_contribution': 0.0,  # Unknown, recently added
            },
            {
                'name': 'Funding Rate Analysis',
                'file': 'agents/voting/funding_rate_agent.py',
                'loc_estimate': 120,
                'description': 'Derivatives funding rate signals',
                'decision_freq': 0.50,
                'wr_contribution': 0.0,  # Unknown, recently added
            },
        ]

        for feature in features:
            component = Component(
                name=feature['name'],
                type='feature',
                file_path=feature['file'],
                lines_of_code=feature['loc_estimate'],
                decision_frequency=feature['decision_freq'],
                win_rate_contribution=feature['wr_contribution'],
                description=feature['description']
            )
            self.components.append(component)
            print(f"  ✓ {feature['name']}: {feature['loc_estimate']} LOC (est), freq={feature['decision_freq']:.0%}")

    def _audit_config_parameters(self):
        """Audit configuration parameters"""
        print("\n⚙️  Auditing Config Parameters...")

        config_file = self.project_root / "config" / "agent_config.py"
        if not config_file.exists():
            print("  ⚠️  Config file not found")
            return

        with open(config_file, 'r') as f:
            content = f.read()

        # Count total config parameters (uppercase variables)
        params = re.findall(r'^([A-Z_]+)\s*=', content, re.MULTILINE)

        print(f"  ✓ Found {len(params)} configuration parameters")

        # Create a component for config complexity
        component = Component(
            name="Configuration Complexity",
            type="config",
            file_path="config/agent_config.py",
            lines_of_code=len(params),  # Use param count as "LOC"
            decision_frequency=1.0,  # Config affects all decisions
            win_rate_contribution=0.0,  # Indirect impact
            description=f"{len(params)} tunable parameters creating configuration space explosion"
        )
        self.components.append(component)

        # High param count = complexity liability
        if len(params) > 30:
            print(f"  ⚠️  WARNING: {len(params)} parameters is excessive (target: <15)")

    def _extract_agent_name(self, filename: str) -> str:
        """Extract agent class name from filename"""
        # tech_agent.py -> TechAgent
        # funding_rate_agent.py -> FundingRateAgent
        name = filename.replace('.py', '').replace('_', ' ').title().replace(' ', '')
        if not name.endswith('Agent'):
            name += 'Agent'
        return name

    def _count_lines(self, file_path: Path) -> int:
        """Count non-comment, non-blank lines of code"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            count = 0
            in_docstring = False
            for line in lines:
                stripped = line.strip()

                # Skip empty lines
                if not stripped:
                    continue

                # Handle docstrings
                if '"""' in stripped or "'''" in stripped:
                    in_docstring = not in_docstring
                    continue

                if in_docstring:
                    continue

                # Skip comments
                if stripped.startswith('#'):
                    continue

                count += 1

            return count

        except Exception as e:
            print(f"  ⚠️  Error counting lines in {file_path.name}: {e}")
            return 0

    def _estimate_decision_frequency(self, agent_name: str) -> float:
        """Estimate how often agent influences decisions"""
        # Load config to check if agent is enabled
        config_file = self.project_root / "config" / "agent_config.py"
        if not config_file.exists():
            return 0.5  # Default guess

        try:
            with open(config_file, 'r') as f:
                content = f.read()

            # Check AGENT_ENABLED dict
            enabled_pattern = rf"'{agent_name}':\s*(True|False)"
            match = re.search(enabled_pattern, content)
            if match:
                enabled = match.group(1) == 'True'
                if not enabled:
                    return 0.0  # Disabled agents have 0% frequency

            # Check agent weight
            weight_pattern = rf"'{agent_name}':\s*([0-9.]+)"
            match = re.search(weight_pattern, content)
            if match:
                weight = float(match.group(1))
                if weight == 0.0:
                    return 0.0
                # Weight roughly correlates with influence
                # Normalize to 0-1 range (assume max weight is 2.0)
                return min(weight / 2.0, 1.0)

            return 0.5  # Default if not found

        except Exception as e:
            return 0.5

    def _extract_agent_config_params(self, agent_name: str) -> List[str]:
        """Extract config parameters related to an agent"""
        config_file = self.project_root / "config" / "agent_config.py"
        if not config_file.exists():
            return []

        try:
            with open(config_file, 'r') as f:
                content = f.read()

            # Find params matching agent name pattern
            # e.g., TECH_* for TechAgent, SENTIMENT_* for SentimentAgent
            agent_prefix = agent_name.replace('Agent', '').upper()
            pattern = rf'^({agent_prefix}_[A-Z_]+)\s*='
            params = re.findall(pattern, content, re.MULTILINE)
            return params

        except Exception:
            return []

    def generate_report(self, output_path: str):
        """Generate markdown report with elimination candidates"""
        print(f"\n📝 Generating report: {output_path}")

        with open(output_path, 'w') as f:
            f.write("# Component Elimination Audit\n\n")
            f.write("**Analyst:** Alex 'Occam' Rousseau (First Principles Engineer)\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n")
            f.write("**Philosophy:** *Complexity is a liability. Every component must earn its keep.*\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            f.write(f"**Total Components Analyzed:** {len(self.components)}\n\n")

            # Count by recommendation
            delete = sum(1 for c in self.components if '🔴 DELETE' in c.recommendation)
            disable = sum(1 for c in self.components if '🟠 DISABLE' in c.recommendation)
            review = sum(1 for c in self.components if '🟡 REVIEW' in c.recommendation)
            keep = sum(1 for c in self.components if '🟢 KEEP' in c.recommendation)
            essential = sum(1 for c in self.components if '✅ ESSENTIAL' in c.recommendation)

            f.write(f"- 🔴 **DELETE (high confidence):** {delete} components\n")
            f.write(f"- 🟠 **DISABLE (test removal):** {disable} components\n")
            f.write(f"- 🟡 **REVIEW (low value):** {review} components\n")
            f.write(f"- 🟢 **KEEP (marginal value):** {keep} components\n")
            f.write(f"- ✅ **ESSENTIAL (proven value):** {essential} components\n\n")

            # Key Findings
            f.write("### Key Findings\n\n")
            f.write("1. **Negative ROI Components:** Components that actively hurt win rate\n")
            f.write("2. **Dead Weight:** Components with zero measurable impact\n")
            f.write("3. **Redundancy:** Multiple components doing similar work\n")
            f.write("4. **Complexity Tax:** High LOC without corresponding value\n\n")

            total_loc = sum(c.lines_of_code for c in self.components if c.type != 'config')
            f.write(f"**Total Lines of Code:** {total_loc:,} lines (maintenance burden)\n\n")

            # Elimination Candidates (sorted by score)
            f.write("---\n\n")
            f.write("## Ranked Elimination Candidates\n\n")
            f.write("*Higher elimination score = stronger candidate for removal*\n\n")

            # Table header
            f.write("| Rank | Component | Type | Score | Recommendation | LOC | WR Impact | Freq | Burden |\n")
            f.write("|------|-----------|------|-------|----------------|-----|-----------|------|--------|\n")

            for rank, component in enumerate(self.components, 1):
                f.write(f"| {rank} | {component.name} | {component.type} | ")
                f.write(f"{component.elimination_score:.1f} | {component.recommendation} | ")
                f.write(f"{component.lines_of_code} | ")
                f.write(f"{component.win_rate_contribution:+.1%} | ")
                f.write(f"{component.decision_frequency:.0%} | ")
                f.write(f"{component.maintenance_burden} |\n")

            # Detailed Analysis
            f.write("\n---\n\n")
            f.write("## Detailed Component Analysis\n\n")

            for component in self.components:
                if component.elimination_score >= 4:  # Only detail candidates for removal
                    f.write(f"### {component.recommendation} {component.name}\n\n")
                    f.write(f"**Type:** {component.type}\n")
                    f.write(f"**File:** `{component.file_path}`\n")
                    f.write(f"**Elimination Score:** {component.elimination_score:.1f}\n\n")
                    f.write(f"**Metrics:**\n")
                    f.write(f"- Lines of Code: {component.lines_of_code}\n")
                    f.write(f"- Maintenance Burden: {component.maintenance_burden}\n")
                    f.write(f"- Decision Frequency: {component.decision_frequency:.0%}\n")
                    f.write(f"- Win Rate Contribution: {component.win_rate_contribution:+.2%}\n\n")
                    f.write(f"**Description:** {component.description}\n\n")

                    if component.config_params:
                        f.write(f"**Config Parameters ({len(component.config_params)}):**\n")
                        for param in component.config_params[:5]:  # Show first 5
                            f.write(f"- `{param}`\n")
                        if len(component.config_params) > 5:
                            f.write(f"- *...and {len(component.config_params) - 5} more*\n")
                        f.write("\n")

                    # Reasoning
                    f.write("**Elimination Rationale:**\n")
                    if component.win_rate_contribution < -0.01:
                        f.write("- ⚠️  **Negative ROI:** Actively hurts performance\n")
                    if abs(component.win_rate_contribution) < 0.01:
                        f.write("- ⚠️  **Zero Impact:** No measurable effect on outcomes\n")
                    if component.decision_frequency < 0.10:
                        f.write("- ⚠️  **Low Utilization:** Used in <10% of decisions\n")
                    if component.lines_of_code > 200:
                        f.write(f"- ⚠️  **High Maintenance:** {component.lines_of_code} LOC to maintain\n")
                    f.write("\n")

            # Recommendations
            f.write("---\n\n")
            f.write("## Implementation Recommendations\n\n")
            f.write("### Phase 1: Delete Negative ROI Components (Week 1)\n\n")

            negative_roi = [c for c in self.components if c.win_rate_contribution < -0.01]
            if negative_roi:
                for comp in negative_roi:
                    f.write(f"- [ ] **DELETE {comp.name}** ({comp.win_rate_contribution:+.2%} WR impact)\n")
                    f.write(f"  - File: `{comp.file_path}`\n")
                    f.write(f"  - Expected improvement: +{abs(comp.win_rate_contribution):.1%} win rate\n")
            else:
                f.write("✅ No components with proven negative ROI identified\n")

            f.write("\n### Phase 2: Disable Dead Weight (Week 2)\n\n")
            dead_weight = [c for c in self.components if abs(c.win_rate_contribution) < 0.01 and c.elimination_score >= 7]
            if dead_weight:
                for comp in dead_weight:
                    f.write(f"- [ ] **DISABLE {comp.name}** (zero impact, {comp.lines_of_code} LOC)\n")
                    f.write(f"  - Set `ENABLE_{comp.name.replace('Agent', '').upper()}_AGENT = False`\n")
                    f.write(f"  - Monitor: Should see no WR change\n")
            else:
                f.write("✅ No clear dead weight components identified (need ablation tests)\n")

            f.write("\n### Phase 3: Config Simplification (Week 3)\n\n")
            config_comp = [c for c in self.components if c.type == 'config']
            if config_comp:
                comp = config_comp[0]
                f.write(f"- [ ] **REDUCE config parameters from {comp.lines_of_code} to <15**\n")
                f.write(f"  - Remove: Per-agent thresholds (use global)\n")
                f.write(f"  - Remove: Unused regime adjustment parameters\n")
                f.write(f"  - Remove: Feature flags for disabled components\n")

            f.write("\n### Testing Protocol\n\n")
            f.write("For each component removal:\n\n")
            f.write("1. **Shadow test:** Add strategy with component disabled to shadow trading\n")
            f.write("2. **Run 50 trades:** Accumulate statistical significance\n")
            f.write("3. **Compare WR:** If WR ≥ baseline, remove permanently\n")
            f.write("4. **Measure complexity reduction:** LOC removed, params removed\n")
            f.write("5. **Rollback plan:** Keep component in git history for 30 days\n\n")

            # First Principles Question
            f.write("---\n\n")
            f.write("## First Principles Question\n\n")
            f.write('**"If we started from scratch, what would we build?"**\n\n')
            f.write("Based on this audit, the simplest viable system might be:\n\n")
            f.write("1. **Single best agent** (from Vic's performance ranking)\n")
            f.write("2. **Entry price filter** (<$0.25 for fee advantage)\n")
            f.write("3. **Position sizing** (tiered based on balance)\n")
            f.write("4. **Drawdown protection** (30% halt)\n\n")
            f.write("**Total LOC estimate:** <500 lines (vs current 3300+ lines)\n\n")
            f.write("**Next step:** Implement Minimal Viable Strategy (US-RC-031D) to test this hypothesis\n\n")

        print(f"✅ Report generated: {output_path}")


def main():
    """Main execution"""
    project_root = Path(__file__).parent.parent.parent

    # Create output directory
    output_dir = project_root / "reports" / "alex_rousseau"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run audit
    auditor = ComponentAuditor(str(project_root))
    components = auditor.run_audit()

    # Generate report
    output_path = output_dir / "elimination_candidates.md"
    auditor.generate_report(str(output_path))

    # Summary
    print("\n" + "="*80)
    print("AUDIT COMPLETE")
    print("="*80)
    print(f"Total components analyzed: {len(components)}")
    print(f"Elimination candidates: {sum(1 for c in components if c.elimination_score >= 7)}")
    print(f"\nReport: {output_path}")
    print("\nKey Finding: Complexity is a liability. Start deleting.")
    print("="*80)


if __name__ == "__main__":
    main()
