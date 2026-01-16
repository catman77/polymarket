# US-BF-017: Multi-Epoch Trend Detection - Quick Summary

**Status:** 🔴 Not Started
**Priority:** P0 - Critical (prevents counter-trend trades)
**Complexity:** Medium (threshold changes + consecutive epoch tracking)

---

## What This Fixes

**Problem:** Bot takes contrarian trades against visible 1-2 hour trends

**Example:** Jan 16 8:00 AM
- Chart shows: Clear downtrend (3-5 red candles, RSI 45-50 falling)
- Bot did: Bought BTC/ETH Up at $0.04 (contrarian fade)
- Result: Both trades losing

**Why it happened:**
- TechAgent abstained (moves too small: -0.15% < 0.30% threshold)
- RegimeAgent abstained (-0.07% mean = "sideways" not "weak bear")
- SentimentAgent dominated (90% confidence contrarian)

---

## Implementation Checklist

### Phase 1: Lower Detection Thresholds (Quick - 10 min)

**Files:** `config/agent_config.py`, `agents/tech_agent.py`, `agents/regime_agent.py`

```python
# config/agent_config.py
TECH_CONFLUENCE_THRESHOLD = 0.002  # Change from 0.003 (0.30% → 0.20%)
REGIME_TREND_THRESHOLD = 0.0005    # Change from 0.001 (0.10% → 0.05%)

# agents/tech_agent.py line 27
CONFLUENCE_THRESHOLD = 0.002  # Keep in sync with config

# agents/regime_agent.py line 21
TREND_THRESHOLD = 0.0005  # Keep in sync with config
```

**Test:** Check logs for more TechAgent signals, fewer abstentions

---

### Phase 2: Add Consecutive Epoch Tracking (Medium - 30 min)

**File:** `agents/tech_agent.py`

**Add to `__init__`:**
```python
from collections import deque

def __init__(self, name: str = "TechAgent", weight: float = 1.0):
    # ... existing code ...
    self.epoch_history: Dict[str, deque] = {}  # Track last 5 epochs per crypto
```

**Add helper method:**
```python
def _update_epoch_history(self, crypto: str, direction: str):
    """Track last 5 epochs of direction for trend detection."""
    if crypto not in self.epoch_history:
        self.epoch_history[crypto] = deque(maxlen=5)

    self.epoch_history[crypto].append(direction)

def _detect_consecutive_trend(self, crypto: str) -> Optional[str]:
    """Detect if last 3+ epochs show same direction."""
    if crypto not in self.epoch_history or len(self.epoch_history[crypto]) < 3:
        return None

    recent = list(self.epoch_history[crypto])[-3:]

    # Check for 3 consecutive same direction
    if all(d == "Up" for d in recent):
        return "Up"
    elif all(d == "Down" for d in recent):
        return "Down"

    return None
```

**Modify `analyze()` before returning vote:**
```python
# Before final return vote
detected_direction = # ... from confluence analysis ...
self._update_epoch_history(crypto, detected_direction)

# Check for trend conflict
consecutive_trend = self._detect_consecutive_trend(crypto)
if consecutive_trend and consecutive_trend != direction:
    # Reduce confidence by 50% when voting against trend
    confidence *= 0.5
    reasoning += f" | ⚠️ Conflicts with 3-epoch {consecutive_trend.lower()}trend"
    log.warning(f"[{self.name}] {crypto}: Voting {direction} against {consecutive_trend} trend")
```

**Test:** Create scenario with 3 consecutive Down epochs, verify confidence reduced for Up vote

---

### Phase 3: Add Regime Strength Classification (Easy - 10 min)

**File:** `agents/regime_agent.py`

**Modify regime detection to return strength:**
```python
def _classify_regime_strength(self, mean_return: float) -> str:
    """Classify regime strength based on mean return."""
    if mean_return > 0.10:
        return "strong_bull"
    elif mean_return > 0.05:
        return "weak_bull"
    elif mean_return < -0.10:
        return "strong_bear"
    elif mean_return < -0.05:
        return "weak_bear"
    else:
        return "sideways"
```

**Add to vote details:**
```python
details = {
    'regime': self.current_regime,
    'regime_strength': self._classify_regime_strength(mean_return),
    'confidence': regime_confidence,
    # ... existing details ...
}
```

**Test:** Check logs show "weak_bear" instead of "sideways" for -0.07% mean

---

### Phase 4: Add Trend Conflict Warnings (Easy - 5 min)

**File:** `coordinator/vote_aggregator.py`

**After aggregation, check for conflicts:**
```python
# After aggregating votes
if 'TechAgent' in votes_by_agent:
    tech_details = votes_by_agent['TechAgent'].details
    if 'consecutive_trend' in tech_details and tech_details['consecutive_trend']:
        # Check if any high-confidence vote conflicts
        conflicting_agents = []
        for agent_name, vote in votes_by_agent.items():
            if vote.direction != tech_details['consecutive_trend'] and vote.confidence > 0.7:
                conflicting_agents.append(f"{agent_name}({vote.confidence:.0%})")

        if conflicting_agents:
            log.warning(
                f"⚠️ Trend conflict: {', '.join(conflicting_agents)} voting "
                f"against {tech_details['consecutive_trend']} trend"
            )
```

**Test:** Verify warning logged when SentimentAgent Up vote conflicts with Down trend

---

## Testing Strategy

### Unit Tests

Create `tests/test_trend_detection.py`:

```python
def test_tech_agent_consecutive_trend_detection():
    """Test TechAgent detects 3 consecutive Down epochs."""
    agent = TechAgent()

    # Simulate 3 consecutive Down epochs
    for _ in range(3):
        agent._update_epoch_history('btc', 'Down')

    trend = agent._detect_consecutive_trend('btc')
    assert trend == 'Down'

def test_regime_agent_weak_bear_classification():
    """Test RegimeAgent classifies -0.07% as weak_bear."""
    agent = RegimeAgent()

    # Simulate -0.07% mean return
    strength = agent._classify_regime_strength(-0.0007)
    assert strength == 'weak_bear'

def test_confidence_reduction_on_trend_conflict():
    """Test TechAgent reduces confidence when voting against trend."""
    agent = TechAgent()

    # Set up 3 consecutive Down epochs
    for _ in range(3):
        agent._update_epoch_history('btc', 'Down')

    # Mock vote for Up
    vote = agent.analyze('btc', epoch=123, data={})

    # Should reduce confidence if voting Up against Down trend
    # (actual implementation depends on logic)
```

### Integration Test

Run bot in shadow mode with US-BF-017 fixes:
- Monitor for 4 hours (16 epochs)
- Check TechAgent abstain rate drops
- Verify no Up trades during 3+ Down epoch streaks
- Confirm RegimeAgent classifies weak trends correctly

---

## Success Metrics

**Before US-BF-017:**
- TechAgent abstain rate: ~70% (threshold too high)
- RegimeAgent "sideways" classification: Incorrectly used for weak trends
- Counter-trend trades: Occurred (Jan 16 8am example)

**After US-BF-017:**
- TechAgent abstain rate: Target 40-50% (more signals detected)
- RegimeAgent weak trend detection: -0.05 to -0.09% classified correctly
- Counter-trend trades: Confidence reduced by 50% when conflicting
- Trade alignment: Visible chart trends match bot decisions

---

## Rollout Plan

1. **Local Testing (30 min)**
   - Implement all 4 phases
   - Run unit tests
   - Check typechecks pass

2. **Shadow Testing (4-8 hours)**
   - Deploy to VPS with shadow strategy
   - Monitor trend detection logs
   - Compare against live strategy

3. **Live Deployment (if shadow validates)**
   - Replace live strategy config
   - Monitor for 24 hours
   - Verify no counter-trend trades occur

4. **Monitoring (ongoing)**
   - Track TechAgent abstain rate
   - Log all trend conflicts
   - Measure trade alignment with TradingView charts

---

## Risk Assessment

**Low Risk Changes:**
- Threshold adjustments (easily reversible)
- Logging additions (no behavior change)
- Regime strength classification (informational only)

**Medium Risk Changes:**
- Consecutive epoch tracking (new state management)
- Confidence reduction on conflict (changes trade decisions)

**Mitigation:**
- Shadow test before going live
- Start with 50% confidence reduction (not 100% block)
- Can revert by raising thresholds back to 0.003/0.001

---

## Related Issues

- **US-BF-001 to US-BF-016:** Previous bias fixes (completed)
- **ML Feature Leakage:** Separate issue, documented but not fixing yet
- **Single Agent Dominance:** Related to this (SentimentAgent overrode trend signals)

---

## Next Steps

1. Review this summary
2. Start implementation (Phase 1 is quick - 10 min)
3. Test locally
4. Shadow test on VPS
5. Monitor and validate

**Estimated Total Time:** 1-2 hours implementation + 4-8 hours validation
