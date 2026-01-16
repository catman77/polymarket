#!/usr/bin/env python3
"""
Standalone test for DirectionalBalanceTracker (no dependencies).

Tests the class logic directly without importing the full coordinator module.
"""

from dataclasses import dataclass
from typing import Dict
from collections import deque
from datetime import datetime


@dataclass
class DirectionalDecision:
    """Records a single decision with direction and timestamp."""
    direction: str
    timestamp: float


class DirectionalBalanceTracker:
    """
    Monitors directional balance over rolling windows to detect cascading bias.
    """

    def __init__(self, window_size: int = 20, bias_threshold: float = 0.70):
        self.window_size = window_size
        self.bias_threshold = bias_threshold
        self.decisions: deque = deque(maxlen=window_size)

    def record(self, direction: str):
        """Record a new decision (Up or Down only)."""
        if direction not in ["Up", "Down"]:
            return

        decision = DirectionalDecision(
            direction=direction,
            timestamp=datetime.now().timestamp()
        )
        self.decisions.append(decision)

    def get_balance(self) -> Dict[str, float]:
        """Calculate directional percentages."""
        if not self.decisions:
            return {
                'up_pct': 0.0,
                'down_pct': 0.0,
                'total_decisions': 0
            }

        up_count = sum(1 for d in self.decisions if d.direction == "Up")
        down_count = sum(1 for d in self.decisions if d.direction == "Down")
        total = len(self.decisions)

        return {
            'up_pct': up_count / total if total > 0 else 0.0,
            'down_pct': down_count / total if total > 0 else 0.0,
            'total_decisions': total
        }

    def has_bias(self) -> bool:
        """Check if directional bias exceeds threshold."""
        balance = self.get_balance()

        if balance['total_decisions'] < self.window_size:
            return False

        return (balance['up_pct'] >= self.bias_threshold or
                balance['down_pct'] >= self.bias_threshold)

    def get_balance_summary(self) -> str:
        """Get human-readable balance summary."""
        balance = self.get_balance()

        if balance['total_decisions'] == 0:
            return "No decisions tracked yet"

        summary = (
            f"Directional Balance ({balance['total_decisions']} decisions): "
            f"Up {balance['up_pct']:.1%} | Down {balance['down_pct']:.1%}"
        )

        if self.has_bias():
            dominant = "Up" if balance['up_pct'] > balance['down_pct'] else "Down"
            dominant_pct = max(balance['up_pct'], balance['down_pct'])
            summary += f" ⚠️ BIAS DETECTED: {dominant} {dominant_pct:.1%}"

        return summary


def test_bias_detected():
    """Test: 15 Up / 5 Down → 75% Up bias with alert"""
    tracker = DirectionalBalanceTracker(window_size=20, bias_threshold=0.70)

    for _ in range(15):
        tracker.record("Up")
    for _ in range(5):
        tracker.record("Down")

    balance = tracker.get_balance()
    assert balance['up_pct'] == 0.75, f"Expected 75% Up, got {balance['up_pct']:.2%}"
    assert balance['down_pct'] == 0.25
    assert balance['total_decisions'] == 20
    assert tracker.has_bias() is True

    summary = tracker.get_balance_summary()
    assert "BIAS DETECTED" in summary

    print("✅ Test 1: 15 Up / 5 Down → 75% Up bias detected")


def test_balanced_no_alert():
    """Test: 10 Up / 10 Down → 50% balanced, no alert"""
    tracker = DirectionalBalanceTracker(window_size=20, bias_threshold=0.70)

    for _ in range(10):
        tracker.record("Up")
    for _ in range(10):
        tracker.record("Down")

    balance = tracker.get_balance()
    assert balance['up_pct'] == 0.50
    assert balance['down_pct'] == 0.50
    assert tracker.has_bias() is False

    summary = tracker.get_balance_summary()
    assert "BIAS DETECTED" not in summary

    print("✅ Test 2: 10 Up / 10 Down → balanced, no alert")


def test_empty_tracker():
    """Test: Empty tracker → no bias"""
    tracker = DirectionalBalanceTracker()

    balance = tracker.get_balance()
    assert balance['total_decisions'] == 0
    assert tracker.has_bias() is False

    print("✅ Test 3: Empty tracker → no bias")


def test_insufficient_decisions():
    """Test: Less than window_size → no bias alert"""
    tracker = DirectionalBalanceTracker(window_size=20)

    for _ in range(10):
        tracker.record("Up")

    assert tracker.has_bias() is False

    print("✅ Test 4: Insufficient decisions → no alert")


def test_extreme_bias():
    """Test: All Up → 100% bias"""
    tracker = DirectionalBalanceTracker(window_size=20)

    for _ in range(20):
        tracker.record("Up")

    balance = tracker.get_balance()
    assert balance['up_pct'] == 1.0
    assert tracker.has_bias() is True

    print("✅ Test 5: All Up → 100% bias detected")


def test_rolling_window():
    """Test: Rolling window keeps only last N decisions"""
    tracker = DirectionalBalanceTracker(window_size=5)

    for _ in range(10):
        tracker.record("Up")

    balance = tracker.get_balance()
    assert balance['total_decisions'] == 5

    for _ in range(3):
        tracker.record("Down")

    balance = tracker.get_balance()
    assert balance['total_decisions'] == 5
    assert balance['up_pct'] == 0.4
    assert balance['down_pct'] == 0.6

    print("✅ Test 6: Rolling window works correctly")


if __name__ == "__main__":
    print("Testing DirectionalBalanceTracker (standalone)...\n")

    test_bias_detected()
    test_balanced_no_alert()
    test_empty_tracker()
    test_insufficient_decisions()
    test_extreme_bias()
    test_rolling_window()

    print("\n✅ All tests passed!")
