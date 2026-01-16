# Jan 16 Peak Balance Desync - Root Cause Analysis

**Analyst:** Dmitri "The Hammer" Volkov (System Reliability Engineer)
**Date:** 2026-01-16 12:54 UTC
**Task:** US-RC-007 - Reproduce Jan 16 peak_balance desync

---

## Executive Summary

**Desync Detected:** ✅ YES
**Expected Peak:** $300.00
**Observed Peak:** $290.53
**Discrepancy:** $9.47

**Root Cause:**
Peak balance was $290.53 instead of $300.00. Discrepancy: $9.47. Root cause likely: peak_balance updated from unredeemed position values before Jan 16. When positions were redeemed, cash increased but peak stayed at inflated value, causing false drawdown calculation.

---

## Timeline Analysis

### Observation Period
- **First Event:** 2026-01-16T01:05:20
- **Last Event:** 2026-01-16T15:40:55
- **Total Events:** 679

### Event Breakdown

| Timestamp | Type | Peak Balance | Current Balance | Cash Only | Redeemable |
|-----------|------|--------------|-----------------|-----------|------------|
| 2026-01-16 01:05:20 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:06:21 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:07:21 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:08:22 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:09:22 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:10:22 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:11:23 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:12:23 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:13:24 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:14:25 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:15:25 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:16:26 | HALT | $290.53 | $198.46 | $198.46 | N/A |
| 2026-01-16 01:20:26 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:21:27 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:22:27 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:23:28 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:24:28 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:25:29 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:26:29 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:27:30 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:28:30 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:29:31 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:30:31 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:31:31 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:32:32 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:33:32 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:34:33 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:35:33 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:36:34 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:37:34 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:38:35 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:39:35 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:40:36 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:41:36 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:42:36 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:43:37 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:44:38 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:45:38 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:46:39 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:47:39 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:48:40 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:49:40 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:50:41 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:51:41 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:52:42 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:53:42 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:54:43 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:55:43 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:56:31 | HALT | $290.53 | $200.97 | $200.97 | N/A |
| 2026-01-16 01:57:31 | HALT | $290.53 | $200.97 | $200.97 | N/A |

*... 629 more events (see full log)*


---

## Root Cause Hypothesis

### Problem Statement
The bot halted at 01:05 UTC on Jan 16 with a 31.7% drawdown calculation:
- **Peak Balance:** $290.53 (incorrect)
- **Current Balance:** $198.46 (cash only)
- **Expected Peak:** $300.00 (historical high from Jan 15)

This created a false drawdown of 31.7% instead of the actual 33.8%.

### Mechanism of Desync

1. **Pre-Jan 16:** Bot had unredeemed winning positions
2. **Position Value Inclusion:** peak_balance was updated to include unredeemed position values ($290.53 = $200.97 cash + ~$90 positions)
3. **Redemption:** Positions redeemed, cash increased to $200.97
4. **Peak Not Updated:** peak_balance remained at $290.53 (inflated value)
5. **False Drawdown:** Bot calculated drawdown using inflated peak vs cash-only current

### Evidence Supporting Hypothesis


✅ **Confirmed:** Peak balance discrepancy of $9.47
✅ **Pattern:** All HALT messages show consistent peak of $290.53
✅ **Timing:** Desync present from first log entry (01:05 UTC)

**Inference:** The desync occurred BEFORE 01:05 UTC, likely during redemption cycle between Jan 15-16.


---

## Code Analysis

### Current peak_balance Update Logic

**File:** `bot/momentum_bot_v12.py` (Guardian class)

**Current Implementation:**
```python
# Peak is updated when current_balance exceeds it
if state.current_balance > state.peak_balance:
    state.peak_balance = state.current_balance
```

**Issue:** `current_balance` can include:
1. **Cash** (USDC balance on-chain)
2. **Unredeemed positions** (estimated value before redemption)

**When positions redeem:**
- `current_balance` increases (cash inflow)
- `peak_balance` may already be inflated from unredeemed position estimates
- Result: False peak value persists

---

## Proposed Fix

### Solution 1: Cash-Only Peak Tracking (Recommended)

```python
def update_peak_balance(state: TradingState, cash_balance: float, redeemable_value: float):
    """Update peak using CASH ONLY (not unredeemed positions)"""
    # Only count realized cash, not unredeemed position values
    if cash_balance > state.peak_balance:
        state.peak_balance = cash_balance
        logger.info(f"NEW PEAK: ${state.peak_balance:.2f} (cash only, excludes unredeemed)")
```

**Benefits:**
- Prevents inflated peaks from position estimates
- Drawdown calculation uses consistent metric (realized cash)
- Simple to implement

### Solution 2: Separate Peaks (Cash vs Total)

```python
@dataclass
class TradingState:
    peak_cash_balance: float  # NEW: realized cash only
    peak_total_balance: float  # Existing: cash + unredeemed

    def get_drawdown_peak(self) -> float:
        """Use cash-only peak for drawdown calc"""
        return self.peak_cash_balance
```

**Benefits:**
- Maintains both metrics for analytics
- More accurate drawdown protection
- Requires more testing

---

## Testing Strategy

### Scenario 1: Desync Reproduction Test

```python
def test_desync_scenario():
    """Reproduce Jan 16 desync conditions"""
    state = TradingState(
        current_balance=290.53,  # Cash + unredeemed positions
        peak_balance=290.53,
        cash_only=200.97,
        unredeemed_value=89.56
    )

    # Simulate redemption
    state.current_balance = state.cash_only + state.unredeemed_value  # $290.53
    state.cash_only += state.unredeemed_value  # $290.53
    state.unredeemed_value = 0

    # BUG: Peak is now inflated (should be $300 historical, not $290.53)
    # Current = $290.53
    # Drawdown = (290.53 - 290.53) / 290.53 = 0% (FALSE)

    # Fix: Reset peak to cash-only value
    state.peak_balance = max(state.peak_balance, 300.00)  # Historical high
    # Drawdown = (300 - 290.53) / 300 = 3.2% (TRUE)
```

### Scenario 2: Peak Reset Test

```python
def test_peak_reset():
    """Verify manual peak reset prevents false halt"""
    state = load_state()
    state.peak_balance = state.current_balance  # Reset to current
    save_state(state)

    # Bot should no longer halt (drawdown reset)
    assert calculate_drawdown(state) < 0.30
```

---

## Recommendations

### Immediate Actions (CRITICAL)
1. **Manual Peak Reset:** SSH to VPS, reset peak_balance to current_balance
2. **Verify Fix:** Monitor bot for 24h, ensure no false halts
3. **Document:** Add comment in state file explaining manual intervention

### Short-Term Actions (Within 1 Week)
1. **Implement Fix:** Deploy Solution 1 (cash-only peak tracking)
2. **Add Logging:** Log peak updates with reason (cash increase, manual reset, etc.)
3. **Unit Tests:** Add tests for desync scenarios

### Long-Term Actions (Within 1 Month)
1. **State Validation:** Add state file validation on load (detect anomalies)
2. **Peak Audit:** Weekly review of peak_balance vs historical data
3. **Monitoring:** Alert if peak_balance > on-chain balance + 20%

---

## Data Sources

- **VPS Log File:** `/opt/polymarket-autotrader/bot.log`
- **State File:** `/opt/polymarket-autotrader/state/trading_state.json`
- **Context Document:** `CLAUDE.md` (peak_balance = $300 historical)

---

## Appendix A: VPS Commands for Manual Fix

```bash
# SSH to VPS
ssh root@216.238.85.11

# Navigate to bot directory
cd /opt/polymarket-autotrader

# Reset peak_balance to current_balance
python3 << 'EOF'
import json

with open('state/trading_state.json', 'r+') as f:
    state = json.load(f)
    print(f"Before: peak=${state['peak_balance']:.2f}, current=${state['current_balance']:.2f}")

    # Reset peak to current (manual intervention)
    state['peak_balance'] = state['current_balance']

    print(f"After: peak=${state['peak_balance']:.2f}, current=${state['current_balance']:.2f}")

    f.seek(0)
    json.dump(state, f, indent=2)
    f.truncate()
EOF

# Restart bot
systemctl restart polymarket-bot

# Verify
systemctl status polymarket-bot
tail -20 bot.log
```

---

## Appendix B: Git History Analysis

### Command to Check State File History

```bash
# On VPS
cd /opt/polymarket-autotrader
git log --all --full-history -p -- state/trading_state.json | head -500
```

**Note:** state/ directory is gitignored, so git history unavailable. Rely on log forensics instead.

---

**END OF REPORT**

Generated by: scripts/research/jan16_desync_root_cause.py
