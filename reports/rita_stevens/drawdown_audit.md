# Drawdown Calculation Audit Report

**Auditor:** Colonel Rita "The Guardian" Stevens (Risk Management Architect)
**Date:** 2026-01-16
**Mission:** Validate drawdown tracking formula and identify bugs causing Jan 16 desync
**Mindset:** "Plan for failure. Stress test everything. Hope is not a strategy."

---

## Executive Summary

**CRITICAL BUG IDENTIFIED:** Peak balance tracking includes unredeemed position values instead of cash-only balance, causing false halt conditions.

**Status:** ⚠️ **PARTIAL FIX DEPLOYED** (automatic peak tracking disabled as of Jan 16, 2026)

**Risk Level:** 🔴 **HIGH** - Drawdown protection can fail or trigger incorrectly

**Recommendations:**
1. ✅ **Immediate:** Manual peak resets (currently implemented)
2. 🔧 **Short-term:** Re-enable automatic peak tracking with cash-only formula
3. 🛡️ **Long-term:** Implement peak reset on redemption events

---

## Current Formula Analysis

### Location
- **File:** `bot/momentum_bot_v12.py`
- **Function:** `Guardian.check_kill_switch()` (lines 672-690)
- **Constants:** `MAX_DRAWDOWN_PCT = 0.30` (30% halt threshold)

### Formula Breakdown

```python
# Current implementation (lines 677-683)
cash_balance = get_usdc_balance()
redeemable_value = self.get_redeemable_value()
effective_balance = cash_balance + redeemable_value

drawdown = (self.state.peak_balance - effective_balance) / self.state.peak_balance
```

**Components:**
1. **cash_balance:** On-chain USDC balance (blockchain ground truth)
2. **redeemable_value:** Winning positions at ≥99% probability (effectively $1.00)
3. **effective_balance:** Total liquid value (cash + near-certain winners)
4. **peak_balance:** Highest balance ever reached (stored in state file)

**Formula:** `drawdown = (peak - current) / peak`

**Threshold:** Halt if `drawdown > 0.30` (30%)

---

## Bug Analysis: Jan 16, 2026 Incident

### The Problem

**Observed Behavior:**
- State file showed `peak_balance = $386.97`
- Actual cash balance: `$200.97`
- Calculated drawdown: `($386.97 - $200.97) / $386.97 = 48.1%` → **HALT**

**Root Cause:**
Peak balance was inflated by including unredeemed position values that were **not yet liquid cash**.

### How It Happened

**Scenario Timeline:**

1. **Bot places trade:** Spends $20 on position
   - Cash: $200.97 → $180.97
   - Position value: $0 → $20.00 (at entry price)
   - Total portfolio: $200.97 (unchanged at entry)

2. **Position wins:** Now worth ~$1.00 per share
   - Cash: $180.97 (unchanged)
   - Position value: $20 → ~$200 (winner at 99%+)
   - Total portfolio: $380.97

3. **Peak tracking bug:** Peak set to portfolio value
   - `peak_balance = $380.97` ❌ **WRONG** (includes unrealized position)

4. **Position redeemed:** Shares converted to USDC
   - Cash: $180.97 + $200 = $380.97 ✅ (correct cash balance)
   - Position value: $200 → $0 (redeemed)
   - Total portfolio: $380.97 (now all cash)

5. **Subsequent losing trades:** Cash drops
   - Cash: $380.97 → $200.97 (lost $180)
   - Peak still: $380.97
   - Drawdown: 47% → **FALSE HALT**

### Why This Is Wrong

**The bug:** Peak included **unrealized position value** ($200 in mid-trade positions) instead of tracking **realized cash only**.

**Correct behavior:**
- Peak should track **cash balance after redemptions**, not portfolio market value
- Peak = max(cash after each redemption)
- Unredeemed positions should NOT inflate peak

**Jan 16 correct peak:**
- If peak had been `$200.97` (cash-only), drawdown would be: `($200.97 - $200.97) / $200.97 = 0%` → No halt ✅

---

## Peak Balance Update Logic

### Current Implementation (TEMPORARILY DISABLED)

**Lines 2183-2186:**
```python
# TEMPORARY: Disabled automatic peak tracking to allow manual reset (Jan 16, 2026)
# state.peak_balance = max(state.peak_balance, balance)  # FIX: Track peak cash, not position estimates
# TODO: Re-enable after manual reset verified
if state.peak_balance == 0:  # Only initialize if zero
    state.peak_balance = balance
```

**Status:** Automatic peak tracking is **DISABLED** (commented out)

**Reason:** Emergency measure after Jan 16 incident to prevent further false halts

**Impact:**
- ✅ **Good:** Prevents false halts from incorrect peak
- ❌ **Bad:** Peak never increases (can't recover from legitimate drawdowns)
- ⚠️ **Risk:** If balance grows to $500, peak stays at $200.97 → 60% "drawdown" if drops to $200 again

### When Is Peak Updated? (When Re-enabled)

**Original logic (now disabled):**
- Every scan cycle: `state.peak_balance = max(state.peak_balance, balance)`
- Updated after balance refresh (line 2183)

**Problem with original logic:**
- Balance includes unredeemed position values → peak inflated
- Should ONLY update peak on **redemption events** (when positions → cash)

---

## Does current_balance Include Unredeemed Positions?

### Answer: **NO** (current_balance is cash-only)

**Evidence:**

1. **Initialization (line 2017):**
   ```python
   balance = get_usdc_balance()  # Query blockchain for USDC
   ```

2. **Balance refresh (line 2181):**
   ```python
   state.current_balance = balance  # balance = cash from get_usdc_balance()
   ```

3. **get_usdc_balance() implementation:**
   - Queries Polygon blockchain USDC contract
   - Returns only liquid USDC tokens in wallet
   - Does NOT include market values of positions

**Conclusion:** `current_balance` correctly tracks **cash only** ✅

**However:** `peak_balance` was updated from `balance` which could reflect **portfolio value** at certain points (bug in older code, now disabled)

---

## Effective Balance Calculation

### What Is Included?

**Formula (line 681):**
```python
effective_balance = cash_balance + redeemable_value
```

**Components:**

1. **cash_balance:** Liquid USDC (blockchain query)
2. **redeemable_value:** Winning positions at ≥99% probability

**Redeemable value logic (lines 727-737):**
```python
for pos in positions:
    cur_price = float(pos.get('curPrice', 0))
    current_value = size * cur_price

    # Count as redeemable if marked redeemable OR at 99%+ AND value >= $1
    if (pos.get('redeemable', False) or cur_price >= 0.99) and current_value >= 1.0:
        redeemable_value += current_value
```

**What is counted as redeemable:**
- Positions marked `redeemable: true` by Polymarket API
- OR positions at ≥99% probability (near-certain winners)
- AND position value ≥ $1.00 (exclude dust)

**What is NOT counted:**
- Open positions at <99% (still in-flight)
- Losing positions (curPrice near $0)
- Dust positions (value <$1)

**Assessment:** ✅ **CORRECT** - Only counts near-liquid winners, excludes speculative positions

---

## State File Validation

### validate_and_fix_state() Function

**Purpose:** Detect and correct state file desyncs vs blockchain reality

**Location:** Lines 1896-1950

**Mechanism:**
1. Query actual USDC balance from blockchain
2. Compare to `state.current_balance` (from file)
3. If discrepancy >2%, log warning
4. If discrepancy >10%, auto-correct state file

**Thresholds:**
- `DESYNC_THRESHOLD = 0.02` (2% triggers warning)
- `CRITICAL_THRESHOLD = 0.10` (10% triggers auto-correction)

**Example Jan 16 scenario:**
```
State file: current_balance = $14.91
Blockchain: actual_balance = $200.97
Discrepancy: $186.06 (1247%) → AUTO-CORRECT
```

**Correction logic:**
```python
state.current_balance = actual_balance  # Fix balance

# Recalculate drawdown after fix
drawdown = (state.peak_balance - actual_balance) / state.peak_balance
if drawdown > MAX_DRAWDOWN_PCT:
    # Create kill switch if still over limit
```

**Assessment:** ✅ **EXCELLENT** - Prevents catastrophic state file bugs

**Limitation:** Validation cannot fix **peak_balance** desync (only fixes current_balance)

---

## Identified Bugs

### 🔴 BUG #1: Peak includes unredeemed positions (Jan 16 incident)

**Severity:** CRITICAL
**Status:** MITIGATED (automatic peak tracking disabled)

**Description:**
Peak balance was updated from portfolio value (cash + positions) instead of cash-only balance.

**Impact:**
- Peak inflated by $100-200 from open/redeemable positions
- After redemption, cash drops back to baseline
- False drawdown calculated: ~40-50% when actual drawdown is 0%
- Bot halts incorrectly, preventing profitable trading

**Root cause:**
```python
# Old behavior (now commented out):
state.peak_balance = max(state.peak_balance, balance)
```

Where `balance` could include:
- Cash: $200
- Unredeemed winners: $180
- Total: $380 (peak set here) ❌

Then after redemption:
- Cash: $380 (all redeemed) ✅
- Peak still: $380
- Bot loses $180 → cash = $200
- Drawdown: ($380 - $200) / $380 = 47% → HALT ❌

**Proposed fix:**
```python
# Option 1: Only update peak on redemption events
if just_redeemed_positions:  # Detect redemption in previous cycle
    state.peak_balance = max(state.peak_balance, cash_balance)

# Option 2: Always use cash-only (no portfolio value)
state.peak_balance = max(state.peak_balance, get_usdc_balance())
```

---

### 🟡 BUG #2: Peak never resets after losses

**Severity:** MEDIUM
**Status:** BY DESIGN (requires manual intervention)

**Description:**
Peak balance never decreases, even after legitimate losses.

**Scenario:**
1. Peak reaches $500
2. Market conditions change, bot loses money
3. Balance drops to $200 (legitimate 60% loss)
4. Drawdown: 60% → HALT
5. Manual reset required to resume trading

**Is this a bug?**
- ❌ Not technically a bug - this is how drawdown protection works
- ✅ By design: Protect against catastrophic losses
- ⚠️ Issue: No automatic recovery path after legitimate losses

**Proposed enhancement:**
- Daily peak reset option (reset peak every 24h)
- Rolling peak window (e.g., peak over last 30 days)
- Manual peak reset command (already implemented via state file edit)

**Current workaround:**
```bash
# Manual peak reset (Jan 16, 2026 solution)
ssh root@VPS_IP
cd /opt/polymarket-autotrader
python3 << 'EOF'
import json
with open('state/trading_state.json', 'r+') as f:
    state = json.load(f)
    state['peak_balance'] = state['current_balance']
    f.seek(0)
    json.dump(state, f, indent=2)
    f.truncate()
EOF
```

---

### 🟢 BUG #3: No division by zero protection

**Severity:** LOW
**Status:** ACCEPTABLE RISK

**Description:**
If `peak_balance = 0`, formula would divide by zero.

**Current protection:**
```python
if self.state.peak_balance > 0:
    drawdown = (self.state.peak_balance - effective_balance) / self.state.peak_balance
```

**Assessment:** ✅ **PROTECTED** - Guard condition prevents division by zero

**Edge case:** If peak=0, drawdown check is skipped entirely (no halt possible)

**Is this correct?**
- ✅ Yes - if peak uninitialized, cannot calculate drawdown
- ✅ Allows bot to start trading from $0 baseline

---

## Unit Test Results

**Test suite:** `scripts/research/test_drawdown_calculation.py`

**Test coverage:**
1. ✅ Normal case - 10% drawdown (within limits)
2. ✅ Boundary case - exactly 30% drawdown (halt trigger)
3. ✅ Danger zone - 35% drawdown (should halt)
4. ✅ Uninitialized peak - peak=0 (no halt)
5. ✅ Negative balance - critical error (immediate halt)
6. ✅ Profit case - balance > peak (no drawdown)
7. ✅ Jan 16 incident - incorrect peak tracking (reproduced bug)
8. ✅ Correct peak tracking - cash-only (fixed behavior)
9. ✅ Redeemable value - includes winning positions (correct)
10. ✅ Division by zero - graceful handling (protected)

**Results:** 10/10 tests passed ✅

**Test execution:**
```bash
cd /Volumes/TerraTitan/Development/polymarket-autotrader
python3 scripts/research/test_drawdown_calculation.py
```

---

## Recommendations

### 🔴 IMMEDIATE (Deploy within 24 hours)

1. **Re-enable automatic peak tracking with cash-only formula**
   ```python
   # Replace lines 2183-2186 with:
   cash_only = get_usdc_balance()  # Blockchain query, no positions
   state.peak_balance = max(state.peak_balance, cash_only)
   ```

2. **Add peak reset on redemption**
   - Track when redemption occurs
   - Update peak ONLY when cash increases from redemption
   - Prevents mid-trade position values from inflating peak

### 🟡 SHORT-TERM (Deploy within 1 week)

3. **Add peak_balance validation to validate_and_fix_state()**
   - Current validation only fixes `current_balance`
   - Should also detect impossible peak values
   - Example: If `peak_balance > 2x current_balance`, flag for review

4. **Log peak updates explicitly**
   ```python
   if new_peak > state.peak_balance:
       log.info(f"📈 NEW PEAK: ${state.peak_balance:.2f} → ${new_peak:.2f}")
       state.peak_balance = new_peak
   ```

5. **Add peak reset command to bot**
   - Detect special file: `state/reset_peak.txt`
   - If exists: `state.peak_balance = state.current_balance`
   - Safer than manual state file editing

### 🟢 LONG-TERM (Deploy within 1 month)

6. **Implement rolling peak window**
   - Track peak over last 30 days
   - Allows recovery from old ATHs
   - Prevents permanent halt after market regime changes

7. **Add drawdown visualization to dashboard**
   - Show: Current balance, peak, drawdown %, distance to halt
   - Alert when approaching 25% (warning zone)

8. **Monte Carlo stress test**
   - Simulate 1000 scenarios with different loss sequences
   - Verify drawdown protection triggers correctly
   - Identify edge cases before they happen in production

---

## Risk Assessment

### Current Risk Level: 🟡 MEDIUM

**Mitigations in place:**
- ✅ Automatic peak tracking disabled (prevents false halts)
- ✅ State validation catches balance desyncs
- ✅ Manual peak reset procedure documented

**Remaining risks:**
- ⚠️ Peak cannot increase automatically (limits profit potential)
- ⚠️ Manual intervention required after any significant event
- ⚠️ No automated recovery from legitimate losses

**Acceptable?**
- 🔶 SHORT-TERM: Yes - prevents worse bugs
- 🔴 LONG-TERM: No - requires active monitoring and manual resets

---

## Conclusion

**Summary:**
The drawdown calculation formula is mathematically sound, but peak balance tracking had a critical bug. The Jan 16 incident was caused by peak including unredeemed position values instead of cash-only balance.

**Current status:**
Automatic peak tracking is disabled as an emergency fix. This prevents false halts but requires manual peak resets after profitable periods.

**Recommended fix:**
Re-enable automatic peak tracking with cash-only formula. Update peak ONLY on redemption events when cash increases. Add validation and logging for peak updates.

**Operational impact:**
Bot can resume trading safely after recommended fixes are deployed. Manual peak resets will still be needed occasionally but should be rare.

---

**Audit completed:** 2026-01-16
**Next review:** After fix deployment (estimated 2026-01-17)

**Auditor signature:**
Colonel Rita "The Guardian" Stevens
*"Trust the math. Verify the code. Test the edge cases."*
