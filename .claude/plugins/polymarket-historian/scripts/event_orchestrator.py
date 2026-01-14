#!/usr/bin/env python3
"""
EVENT-DRIVEN AGENT ORCHESTRATOR

Automatically spawns specialized agents when specific events occur:
- Bot halted → Deploy recovery agent
- Win rate drops → Deploy diagnostic agent
- Profitable pattern detected → Deploy optimization agent
- Market regime shifts → Deploy adaptation agent
- Large loss → Deploy risk analysis agent
- Redemption pile-up → Deploy redemption agent

This is the "uber command" that manages the entire system autonomously.
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Plugin directories
PLUGIN_DIR = Path(__file__).parent.parent
DATA_DIR = PLUGIN_DIR / "data"
EVENT_LOG_FILE = DATA_DIR / "events.json"
AGENT_SPAWNS_FILE = DATA_DIR / "agent_spawns.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)


class EventType(Enum):
    """All possible event types that trigger agent actions."""
    BOT_HALTED = "bot_halted"
    WIN_RATE_DROP = "win_rate_drop"
    LOSING_STREAK = "losing_streak"
    PROFITABLE_PATTERN = "profitable_pattern"
    REGIME_SHIFT = "regime_shift"
    LARGE_LOSS = "large_loss"
    REDEMPTION_PENDING = "redemption_pending"
    BALANCE_LOW = "balance_low"
    POSITION_STUCK = "position_stuck"
    AGENT_DISAGREEMENT = "agent_disagreement"
    UNKNOWN_MARKET = "unknown_market"


class AgentType(Enum):
    """All available agent types that can be spawned."""
    RECOVERY_AGENT = "recovery"
    DIAGNOSTIC_AGENT = "diagnostic"
    OPTIMIZATION_AGENT = "optimization"
    ADAPTATION_AGENT = "adaptation"
    RISK_ANALYSIS_AGENT = "risk_analysis"
    REDEMPTION_AGENT = "redemption"
    BALANCE_MANAGER = "balance_manager"
    POSITION_RESOLVER = "position_resolver"
    CONSENSUS_BUILDER = "consensus_builder"
    MARKET_RESEARCHER = "market_researcher"


# Event → Agent Mapping
EVENT_HANDLERS = {
    EventType.BOT_HALTED: [
        (AgentType.RECOVERY_AGENT, "Analyze halt reason and restore trading"),
        (AgentType.DIAGNOSTIC_AGENT, "Identify root cause of halt")
    ],
    EventType.WIN_RATE_DROP: [
        (AgentType.DIAGNOSTIC_AGENT, "Analyze why win rate is dropping"),
        (AgentType.RISK_ANALYSIS_AGENT, "Review recent trades for patterns")
    ],
    EventType.LOSING_STREAK: [
        (AgentType.RISK_ANALYSIS_AGENT, "Analyze losing streak causes"),
        (AgentType.ADAPTATION_AGENT, "Adjust strategy to current conditions")
    ],
    EventType.PROFITABLE_PATTERN: [
        (AgentType.OPTIMIZATION_AGENT, "Exploit profitable pattern discovered")
    ],
    EventType.REGIME_SHIFT: [
        (AgentType.ADAPTATION_AGENT, "Adapt strategy to new market regime"),
        (AgentType.OPTIMIZATION_AGENT, "Optimize for new conditions")
    ],
    EventType.LARGE_LOSS: [
        (AgentType.RISK_ANALYSIS_AGENT, "Investigate large loss cause"),
        (AgentType.DIAGNOSTIC_AGENT, "Prevent future large losses")
    ],
    EventType.REDEMPTION_PENDING: [
        (AgentType.REDEMPTION_AGENT, "Redeem all pending winners")
    ],
    EventType.BALANCE_LOW: [
        (AgentType.BALANCE_MANAGER, "Manage low balance situation"),
        (AgentType.REDEMPTION_AGENT, "Redeem winners to restore balance")
    ],
    EventType.POSITION_STUCK: [
        (AgentType.POSITION_RESOLVER, "Resolve stuck positions")
    ],
    EventType.AGENT_DISAGREEMENT: [
        (AgentType.CONSENSUS_BUILDER, "Resolve agent disagreement"),
        (AgentType.DIAGNOSTIC_AGENT, "Analyze why agents disagree")
    ],
    EventType.UNKNOWN_MARKET: [
        (AgentType.MARKET_RESEARCHER, "Research unknown market conditions")
    ]
}


class Event:
    """Represents a detected event."""

    def __init__(self, event_type: EventType, severity: str, data: Dict):
        self.event_type = event_type
        self.severity = severity  # low, medium, high, critical
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.id = f"{event_type.value}_{int(time.time())}"

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.event_type.value,
            'severity': self.severity,
            'data': self.data,
            'timestamp': self.timestamp
        }


class EventOrchestrator:
    """
    Monitors for events and automatically spawns agents to handle them.
    """

    def __init__(self):
        self.events_log = self.load_events_log()
        self.agent_spawns = self.load_agent_spawns()

    def load_events_log(self) -> List[Dict]:
        """Load event log from disk."""
        if EVENT_LOG_FILE.exists():
            with open(EVENT_LOG_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_events_log(self):
        """Save event log to disk."""
        with open(EVENT_LOG_FILE, 'w') as f:
            json.dump(self.events_log, f, indent=2)

    def load_agent_spawns(self) -> List[Dict]:
        """Load agent spawn history."""
        if AGENT_SPAWNS_FILE.exists():
            with open(AGENT_SPAWNS_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_agent_spawns(self):
        """Save agent spawn history."""
        with open(AGENT_SPAWNS_FILE, 'w') as f:
            json.dump(self.agent_spawns, f, indent=2)

    def detect_events(self) -> List[Event]:
        """
        Scan current state and detect events that require agent action.
        """
        events = []

        # Check bot state
        bot_halted = self.check_bot_halted()
        if bot_halted:
            events.append(Event(
                EventType.BOT_HALTED,
                "critical",
                {"reason": bot_halted['reason'], "balance": bot_halted['balance']}
            ))

        # Check win rate
        win_rate_drop = self.check_win_rate_drop()
        if win_rate_drop:
            events.append(Event(
                EventType.WIN_RATE_DROP,
                "high",
                {"current_wr": win_rate_drop['current'], "previous_wr": win_rate_drop['previous']}
            ))

        # Check losing streak
        losing_streak = self.check_losing_streak()
        if losing_streak:
            events.append(Event(
                EventType.LOSING_STREAK,
                "high",
                {"consecutive_losses": losing_streak['count']}
            ))

        # Check profitable patterns
        profitable_pattern = self.check_profitable_patterns()
        if profitable_pattern:
            events.append(Event(
                EventType.PROFITABLE_PATTERN,
                "medium",
                {"pattern": profitable_pattern['pattern'], "win_rate": profitable_pattern['win_rate']}
            ))

        # Check regime shift
        regime_shift = self.check_regime_shift()
        if regime_shift:
            events.append(Event(
                EventType.REGIME_SHIFT,
                "medium",
                {"old_regime": regime_shift['old'], "new_regime": regime_shift['new']}
            ))

        # Check redemptions pending
        redemptions = self.check_redemptions_pending()
        if redemptions:
            events.append(Event(
                EventType.REDEMPTION_PENDING,
                "medium",
                {"total_value": redemptions['total'], "count": redemptions['count']}
            ))

        # Check balance low
        balance_low = self.check_balance_low()
        if balance_low:
            events.append(Event(
                EventType.BALANCE_LOW,
                "high",
                {"balance": balance_low['balance'], "threshold": balance_low['threshold']}
            ))

        return events

    def check_bot_halted(self) -> Optional[Dict]:
        """Check if bot is halted."""
        try:
            # Read bot state
            state_file = Path("/opt/polymarket-autotrader/v12_state/trading_state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                halt_reason = state.get('halt_reason')
                if halt_reason:
                    return {
                        'reason': halt_reason,
                        'balance': state.get('current_balance', 0)
                    }
        except:
            pass
        return None

    def check_win_rate_drop(self) -> Optional[Dict]:
        """Check if win rate has dropped significantly."""
        # Load recent patterns
        patterns_file = DATA_DIR / "patterns" / "latest_analysis.json"
        if not patterns_file.exists():
            return None

        try:
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)

            # Compare current WR to historical
            # TODO: Implement actual WR tracking
            return None
        except:
            return None

    def check_losing_streak(self) -> Optional[Dict]:
        """Check for consecutive losses."""
        try:
            state_file = Path("/opt/polymarket-autotrader/v12_state/trading_state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                consecutive_losses = state.get('consecutive_losses', 0)
                if consecutive_losses >= 3:
                    return {'count': consecutive_losses}
        except:
            pass
        return None

    def check_profitable_patterns(self) -> Optional[Dict]:
        """Check for highly profitable patterns worth exploiting."""
        patterns_file = DATA_DIR / "patterns" / "latest_analysis.json"
        if not patterns_file.exists():
            return None

        try:
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)

            # Look for patterns with >75% WR and >20 trades
            for strategy, stats in patterns.get('by_strategy', {}).items():
                if stats.get('win_rate', 0) > 75 and stats.get('total_trades', 0) > 20:
                    return {
                        'pattern': strategy,
                        'win_rate': stats['win_rate'],
                        'trades': stats['total_trades']
                    }
        except:
            pass
        return None

    def check_regime_shift(self) -> Optional[Dict]:
        """Check if market regime has changed."""
        # TODO: Implement regime tracking
        return None

    def check_redemptions_pending(self) -> Optional[Dict]:
        """Check for pending redemptions."""
        # Check latest snapshot for redeemable positions
        snapshots_dir = DATA_DIR / "snapshots"
        if not snapshots_dir.exists():
            return None

        try:
            snapshots = sorted(snapshots_dir.glob("*.json"), reverse=True)
            if snapshots:
                with open(snapshots[0], 'r') as f:
                    snapshot = json.load(f)

                positions = snapshot.get('positions', {})
                redeemable = positions.get('redeemable', [])

                if len(redeemable) >= 2:  # 2+ positions ready to redeem
                    total_value = sum(p.get('current_value', 0) for p in redeemable)
                    if total_value >= 10:  # $10+ pending
                        return {
                            'count': len(redeemable),
                            'total': total_value
                        }
        except:
            pass
        return None

    def check_balance_low(self) -> Optional[Dict]:
        """Check if balance is critically low."""
        try:
            state_file = Path("/opt/polymarket-autotrader/v12_state/trading_state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                balance = state.get('current_balance', 0)
                threshold = 15.0  # Critical if below $15

                if balance < threshold:
                    return {
                        'balance': balance,
                        'threshold': threshold
                    }
        except:
            pass
        return None

    def spawn_agent(self, agent_type: AgentType, task: str, event_data: Dict) -> Dict:
        """
        Spawn a specialized agent to handle an event.

        This would integrate with Claude Code's Task API or subprocess management.
        """

        print(f"🤖 Spawning {agent_type.value} agent...")
        print(f"   Task: {task}")
        print(f"   Event Data: {event_data}")

        # For now, log the spawn
        # In production, this would use Claude Code CLI to spawn actual agents

        spawn_record = {
            'id': f"agent_{int(time.time())}",
            'agent_type': agent_type.value,
            'task': task,
            'event_data': event_data,
            'spawned_at': datetime.now().isoformat(),
            'status': 'spawned'
        }

        self.agent_spawns.append(spawn_record)
        self.save_agent_spawns()

        return spawn_record

    def handle_event(self, event: Event):
        """
        Handle a detected event by spawning appropriate agents.
        """

        print(f"\n🚨 EVENT DETECTED: {event.event_type.value}")
        print(f"   Severity: {event.severity.upper()}")
        print(f"   Data: {event.data}")

        # Get handlers for this event type
        handlers = EVENT_HANDLERS.get(event.event_type, [])

        if not handlers:
            print(f"   ⚠️  No handlers configured for {event.event_type.value}")
            return

        # Spawn all appropriate agents
        for agent_type, task in handlers:
            spawn_record = self.spawn_agent(agent_type, task, event.data)
            print(f"   ✅ Spawned {agent_type.value}: {spawn_record['id']}")

        # Log event
        self.events_log.append(event.to_dict())
        self.save_events_log()

    def run_cycle(self):
        """Run one orchestration cycle."""

        print("\n" + "=" * 70)
        print(f"EVENT ORCHESTRATOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

        # Detect events
        print("\n🔍 Scanning for events...")
        events = self.detect_events()

        if not events:
            print("   ✅ No events detected - system healthy")
        else:
            print(f"   ⚠️  Detected {len(events)} event(s)")

            # Handle each event
            for event in events:
                self.handle_event(event)

        # Print status
        print("\n📊 ORCHESTRATOR STATUS:")
        print(f"   Total events logged: {len(self.events_log)}")
        print(f"   Total agents spawned: {len(self.agent_spawns)}")

        print("\n" + "=" * 70)

    def run_forever(self):
        """Run the orchestrator forever."""

        print("\n🚀 STARTING EVENT-DRIVEN ORCHESTRATOR\n")
        print("Monitoring for events and auto-spawning agents...")
        print("Press Ctrl+C to stop.\n")

        try:
            while True:
                self.run_cycle()

                # Check every 5 minutes
                print("\n💤 Sleeping for 5 minutes...\n")
                time.sleep(300)

        except KeyboardInterrupt:
            print("\n\n👋 Orchestrator stopped")


def main():
    """Main entry point."""

    orchestrator = EventOrchestrator()

    if len(sys.argv) > 1:
        if sys.argv[1] == '--once':
            orchestrator.run_cycle()
        elif sys.argv[1] == '--status':
            print("EVENT ORCHESTRATOR STATUS")
            print(f"Total events: {len(orchestrator.events_log)}")
            print(f"Total agent spawns: {len(orchestrator.agent_spawns)}")
        else:
            print("Usage: event_orchestrator.py [--once|--status]")
    else:
        orchestrator.run_forever()


if __name__ == "__main__":
    main()
