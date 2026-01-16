"""
Performance Monitor - Automated Performance Degradation Detection

Tracks rolling metrics and sends alerts when performance degrades below thresholds.
Designed to catch issues early before significant losses occur.

Usage:
    from utils.performance_monitor import PerformanceMonitor

    monitor = PerformanceMonitor()
    monitor.record_trade(outcome='WIN', entry_price=0.15, direction='Up')
    alerts = monitor.check_alerts()
    for alert in alerts:
        print(f"🚨 {alert['level']}: {alert['message']}")
"""

import json
import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Single trade record for performance tracking"""
    timestamp: str
    outcome: Literal['WIN', 'LOSS']
    entry_price: float
    direction: Literal['Up', 'Down']
    confidence: Optional[float] = None


@dataclass
class Alert:
    """Performance degradation alert"""
    level: Literal['WARNING', 'CRITICAL']
    metric: str
    message: str
    current_value: float
    threshold: float
    timestamp: str


class PerformanceMonitor:
    """
    Monitors trading performance and generates alerts on degradation.

    Tracks:
    - Rolling win rate (last 50 trades)
    - Directional balance (avoid >70% same direction)
    - Average entry price (target <$0.20)
    - Recent losses (consecutive loss streaks)

    Alert Thresholds:
    - Win rate <55%: WARNING
    - Win rate <52%: CRITICAL (below breakeven)
    - Directional bias >70%: WARNING
    - Directional bias >80%: CRITICAL
    - Consecutive losses ≥5: WARNING
    - Consecutive losses ≥8: CRITICAL
    """

    def __init__(self, window_size: int = 50, state_file: str = "state/performance_metrics.json"):
        self.window_size = window_size
        self.state_file = state_file
        self.trades: deque = deque(maxlen=window_size)
        self.consecutive_losses = 0
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(hours=1)  # Don't spam same alert

        # Load existing state if available
        self._load_state()

    def _load_state(self):
        """Load previous trade history from state file"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                self.trades = deque([Trade(**t) for t in state.get('trades', [])], maxlen=self.window_size)
                self.consecutive_losses = state.get('consecutive_losses', 0)
                logger.info(f"Loaded {len(self.trades)} trades from state file")
        except FileNotFoundError:
            logger.info("No previous performance state found, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load performance state: {e}")

    def _save_state(self):
        """Save current trade history to state file"""
        try:
            state = {
                'trades': [asdict(t) for t in self.trades],
                'consecutive_losses': self.consecutive_losses,
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save performance state: {e}")

    def record_trade(self, outcome: Literal['WIN', 'LOSS'], entry_price: float,
                     direction: Literal['Up', 'Down'], confidence: Optional[float] = None):
        """
        Record a completed trade for performance tracking.

        Args:
            outcome: 'WIN' or 'LOSS'
            entry_price: Entry price paid (e.g., 0.15 = $0.15)
            direction: 'Up' or 'Down'
            confidence: Optional confidence score (0-1)
        """
        trade = Trade(
            timestamp=datetime.utcnow().isoformat(),
            outcome=outcome,
            entry_price=entry_price,
            direction=direction,
            confidence=confidence
        )
        self.trades.append(trade)

        # Track consecutive losses
        if outcome == 'LOSS':
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self._save_state()
        logger.debug(f"Recorded {outcome} trade at ${entry_price:.2f} ({direction})")

    def get_win_rate(self) -> Optional[float]:
        """Calculate rolling win rate (last N trades)"""
        if len(self.trades) == 0:
            return None
        wins = sum(1 for t in self.trades if t.outcome == 'WIN')
        return wins / len(self.trades)

    def get_directional_balance(self) -> Optional[Dict[str, float]]:
        """Calculate directional balance (Up vs Down %)"""
        if len(self.trades) == 0:
            return None
        up_count = sum(1 for t in self.trades if t.direction == 'Up')
        down_count = len(self.trades) - up_count
        return {
            'up_pct': up_count / len(self.trades),
            'down_pct': down_count / len(self.trades),
            'up_count': up_count,
            'down_count': down_count
        }

    def get_avg_entry_price(self) -> Optional[float]:
        """Calculate average entry price"""
        if len(self.trades) == 0:
            return None
        return sum(t.entry_price for t in self.trades) / len(self.trades)

    def check_alerts(self) -> List[Alert]:
        """
        Check all metrics and generate alerts for degraded performance.

        Returns:
            List of Alert objects (empty if no issues detected)
        """
        alerts = []
        now = datetime.utcnow()

        # Need minimum trades for statistical significance
        if len(self.trades) < 20:
            return alerts

        # Check win rate
        win_rate = self.get_win_rate()
        if win_rate is not None:
            if win_rate < 0.52 and self._should_alert('win_rate_critical', now):
                alerts.append(Alert(
                    level='CRITICAL',
                    metric='win_rate',
                    message=f'Win rate dropped to {win_rate:.1%} (below breakeven at 53%)',
                    current_value=win_rate,
                    threshold=0.52,
                    timestamp=now.isoformat()
                ))
            elif win_rate < 0.55 and self._should_alert('win_rate_warning', now):
                alerts.append(Alert(
                    level='WARNING',
                    metric='win_rate',
                    message=f'Win rate dropped to {win_rate:.1%} (target: 60-65%)',
                    current_value=win_rate,
                    threshold=0.55,
                    timestamp=now.isoformat()
                ))

        # Check directional balance
        balance = self.get_directional_balance()
        if balance is not None:
            max_pct = max(balance['up_pct'], balance['down_pct'])
            if max_pct > 0.80 and self._should_alert('bias_critical', now):
                direction = 'UP' if balance['up_pct'] > 0.5 else 'DOWN'
                alerts.append(Alert(
                    level='CRITICAL',
                    metric='directional_bias',
                    message=f'Severe directional bias: {max_pct:.1%} {direction} (target: 40-60%)',
                    current_value=max_pct,
                    threshold=0.80,
                    timestamp=now.isoformat()
                ))
            elif max_pct > 0.70 and self._should_alert('bias_warning', now):
                direction = 'UP' if balance['up_pct'] > 0.5 else 'DOWN'
                alerts.append(Alert(
                    level='WARNING',
                    metric='directional_bias',
                    message=f'Directional bias detected: {max_pct:.1%} {direction} (target: 40-60%)',
                    current_value=max_pct,
                    threshold=0.70,
                    timestamp=now.isoformat()
                ))

        # Check consecutive losses
        if self.consecutive_losses >= 8 and self._should_alert('losses_critical', now):
            alerts.append(Alert(
                level='CRITICAL',
                metric='consecutive_losses',
                message=f'{self.consecutive_losses} consecutive losses - possible regime shift or broken strategy',
                current_value=float(self.consecutive_losses),
                threshold=8.0,
                timestamp=now.isoformat()
            ))
        elif self.consecutive_losses >= 5 and self._should_alert('losses_warning', now):
            alerts.append(Alert(
                level='WARNING',
                metric='consecutive_losses',
                message=f'{self.consecutive_losses} consecutive losses - monitor closely',
                current_value=float(self.consecutive_losses),
                threshold=5.0,
                timestamp=now.isoformat()
            ))

        # Check average entry price
        avg_entry = self.get_avg_entry_price()
        if avg_entry is not None and avg_entry > 0.25 and self._should_alert('entry_price_warning', now):
            alerts.append(Alert(
                level='WARNING',
                metric='avg_entry_price',
                message=f'Average entry price ${avg_entry:.2f} too high (target: <$0.20)',
                current_value=avg_entry,
                threshold=0.25,
                timestamp=now.isoformat()
            ))

        return alerts

    def _should_alert(self, alert_key: str, now: datetime) -> bool:
        """Check if enough time has passed since last alert (avoid spam)"""
        last_alert = self.last_alert_time.get(alert_key)
        if last_alert is None or now - last_alert > self.alert_cooldown:
            self.last_alert_time[alert_key] = now
            return True
        return False

    def get_summary(self) -> Dict:
        """Get current performance summary"""
        return {
            'trade_count': len(self.trades),
            'win_rate': self.get_win_rate(),
            'directional_balance': self.get_directional_balance(),
            'avg_entry_price': self.get_avg_entry_price(),
            'consecutive_losses': self.consecutive_losses,
            'recent_trades': [asdict(t) for t in list(self.trades)[-10:]]
        }


if __name__ == '__main__':
    # Example usage
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    monitor = PerformanceMonitor()

    # Simulate some trades
    print("Simulating trades...")
    trades = [
        ('WIN', 0.15, 'Up'),
        ('WIN', 0.18, 'Down'),
        ('LOSS', 0.22, 'Up'),
        ('WIN', 0.12, 'Down'),
        ('LOSS', 0.28, 'Up'),
    ]

    for outcome, price, direction in trades:
        monitor.record_trade(outcome, price, direction)

    # Check for alerts
    alerts = monitor.check_alerts()
    if alerts:
        print(f"\n🚨 {len(alerts)} alerts detected:")
        for alert in alerts:
            print(f"  [{alert.level}] {alert.message}")
    else:
        print("\n✅ No performance issues detected")

    # Show summary
    summary = monitor.get_summary()
    print(f"\n📊 Performance Summary:")
    print(f"  Trades: {summary['trade_count']}")
    if summary['win_rate']:
        print(f"  Win Rate: {summary['win_rate']:.1%}")
    if summary['avg_entry_price']:
        print(f"  Avg Entry: ${summary['avg_entry_price']:.2f}")
    if summary['directional_balance']:
        bal = summary['directional_balance']
        print(f"  Direction: {bal['up_pct']:.1%} UP / {bal['down_pct']:.1%} DOWN")
