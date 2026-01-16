# US-RC-006: State File Atomic Write Audit

**Persona:** Dmitri "The Hammer" Volkov - System Reliability Engineer
**Date:** 1768579854.5545547
**Status:** FAIL
**Risk Level:** CRITICAL

---

## Executive Summary

Atomic writes are NOT IMPLEMENTED in `bot/momentum_bot_v12.py`.

**Risk Assessment:** CRITICAL

❌ The bot writes directly to state.json without atomic guarantees, creating critical corruption risk.

---

## Audit Findings

### Code Review: `save_state()` Function

❌ BUG FOUND: save_state() writes directly to file
⚠️  RISK: Bot crash during save will corrupt state.json
🔴 IMPACT: Corrupted state → bot cannot restart → manual intervention required

📄 Current implementation (UNSAFE):
```python
    with open(state_file, 'w') as f:
        json.dump(asdict(state), f, indent=2)

```


### Risk Analysis

| Aspect | Current Implementation | Risk |
|--------|----------------------|------|
| **Write Method** | Direct write | CRITICAL |
| **Crash Protection** | No | CRITICAL |
| **Corruption Possible** | Yes | CRITICAL |
| **Recovery Required** | Manual | CRITICAL |

### Real-World Scenarios

**Scenario 1: Bot crashes mid-save (OOM kill, power loss, SIGKILL)**
- Current behavior: State file corrupted (partial JSON)
- Impact: Bot cannot start, requires manual state file repair

**Scenario 2: Filesystem full during save**
- Current behavior: Partial write, file corrupted
- Impact: Bot stuck, manual intervention needed

**Scenario 3: VPS hard reboot during state update**
- Current behavior: State file may be corrupted or empty
- Impact: Loss of all state, manual balance/peak reset needed

---


## Recommended Fix: Atomic Write Pattern

Replace the current `save_state()` function with this POSIX-atomic implementation:

```python
import tempfile
import os
import json
from dataclasses import asdict

def save_state(state: TradingState):
    """
    Save state using atomic write pattern to prevent corruption.

    Pattern:
    1. Write to temporary file (.tmp)
    2. Flush to disk (ensures write completes)
    3. Rename temp to final (atomic operation on POSIX)

    If crash occurs during step 1-2: old file remains intact
    If crash occurs during step 3: rename is atomic (either completes or doesn't)
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    state_file = os.path.join(STATE_DIR, "trading_state.json")
    temp_file = state_file + ".tmp"

    try:
        # Write to temporary file
        with open(temp_file, 'w') as f:
            json.dump(asdict(state), f, indent=2)
            f.flush()  # Ensure data written to OS buffer
            os.fsync(f.fileno())  # Force write to disk (prevents buffer loss on crash)

        # Atomic rename (POSIX guarantees this is atomic)
        os.rename(temp_file, state_file)

    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        logging.error(f"Failed to save state: {e}")
        raise
```

### Why This Works:

1. **Temporary file isolation:** Write happens to `.tmp` file, not the live state file
2. **fsync() guarantee:** Forces data to physical disk (not just OS buffer)
3. **Atomic rename:** `os.rename()` is atomic on POSIX filesystems (Linux, macOS)
   - Either the file is renamed completely, or it's not renamed at all
   - No possibility of partial rename or corrupted destination file
4. **Error handling:** If anything fails, temp file is cleaned up, original remains intact

### Testing:

Run `test_state_crash_recovery.py` to verify fix works:
```bash
python3 scripts/research/test_state_crash_recovery.py
```

Expected result: All 3 crash scenarios should leave state.json intact.


---

## Crash Recovery Test

A test script has been generated to validate the fix: `scripts/research/test_state_crash_recovery.py`

Run the test:
```bash
python3 scripts/research/test_state_crash_recovery.py
```

The test simulates 3 crash scenarios and compares unsafe vs safe implementations.

**Expected Results:**
- UNSAFE (current): 0-33% pass rate (frequent corruption)
- SAFE (with fix): 100% pass rate (no corruption)

---


## Recommendations

### Priority 1: CRITICAL - Implement Atomic Writes

**Action:** Apply the fix shown above to `bot/momentum_bot_v12.py`

**Timeline:** ASAP (before next deployment)

**Validation:**
1. Apply fix to `save_state()` function
2. Run crash test: `python3 scripts/research/test_state_crash_recovery.py`
3. Verify 100% pass rate
4. Deploy to VPS with confidence

### Priority 2: Add State File Backup

**Action:** Implement hourly backups of `state/trading_state.json`

**Example cron job:**
```bash
# Add to VPS crontab
0 * * * * cp /opt/polymarket-autotrader/state/trading_state.json /opt/polymarket-autotrader/state/backups/state_$(date +\%Y\%m\%d_\%H00).json
```

### Priority 3: Add State Validation on Load

**Action:** Validate loaded state for logical consistency

**Example:**
```python
def load_state() -> TradingState:
    state = TradingState()

    try:
        with open(state_file, 'r') as f:
            data = json.load(f)

        # Validate fields
        if data.get('current_balance', 0) < 0:
            logging.error("Invalid state: negative balance")
            return TradingState()  # Reset to defaults

        if data.get('peak_balance', 0) < data.get('current_balance', 0):
            logging.warning("Invalid state: peak < current (fixing)")
            data['peak_balance'] = data['current_balance']

        return TradingState(**data)

    except (json.JSONDecodeError, FileNotFoundError, TypeError) as e:
        logging.error(f"State file corrupted or missing: {e}")
        return TradingState()  # Start fresh with defaults
```

---

## Appendix: Technical Details

### What is Atomic Write?

An **atomic operation** is one that either completes fully or not at all—no partial states possible.

On POSIX systems (Linux, macOS), `os.rename()` is guaranteed atomic when:
- Source and destination are on same filesystem
- Destination filename is being replaced (not created in new location)

### Why Direct Writes Are Unsafe

```python
# Current code (UNSAFE):
with open("state.json", "w") as f:
    json.dump(data, f)  # <-- If crash happens here, file is partial JSON
```

If the bot is killed (OOM, power loss, manual kill) during `json.dump()`, the file will contain incomplete JSON like:

```json
{
  "balance": 200
```

This breaks `json.load()` on next startup → bot cannot recover.

### Why Atomic Writes Are Safe

```python
# Fixed code (SAFE):
with open("state.json.tmp", "w") as f:
    json.dump(data, f)
    os.fsync(f.fileno())  # Force disk write

os.rename("state.json.tmp", "state.json")  # <-- Atomic
```

If crash happens:
- **Before rename:** Temp file may be partial, but `state.json` is untouched (old data intact)
- **During rename:** POSIX guarantees rename is atomic (either completes or doesn't, no partial)
- **After rename:** New data successfully written

In all cases, `state.json` is always valid JSON.

---

## Conclusion

❌ The bot has a CRITICAL bug that will cause state corruption on crash.

**Risk Level:** CRITICAL

IMMEDIATE ACTION REQUIRED: Apply atomic write fix before next deployment.

---

**Audited by:** Dmitri "The Hammer" Volkov
**Motto:** "If it can fail, it will fail. Build for 3am crashes."

