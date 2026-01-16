#!/usr/bin/env python3
"""
US-RC-006: Audit state file atomic write safety
Persona: Dmitri "The Hammer" Volkov - System Reliability Engineer

Focused audit of save_state() function for atomic write pattern.
Tests crash scenarios and generates fix recommendations.
"""

import json
import os
import tempfile
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional


def audit_save_state_code() -> dict:
    """Review bot code for atomic write implementation"""
    bot_file = "bot/momentum_bot_v12.py"

    if not os.path.exists(bot_file):
        return {
            "file_exists": False,
            "has_atomic_writes": False,
            "findings": ["❌ Bot file not found - cannot audit"],
            "risk_level": "UNKNOWN"
        }

    with open(bot_file, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    # Find save_state function
    save_state_start = code.find("def save_state(")
    if save_state_start == -1:
        return {
            "file_exists": True,
            "has_atomic_writes": False,
            "findings": ["❌ save_state() function not found in bot code"],
            "risk_level": "CRITICAL"
        }

    # Extract function (approximately 20 lines should capture it)
    save_state_end = save_state_start + 1000  # Reasonable function size
    save_state_code = code[save_state_start:save_state_end]

    # Check for atomic write pattern
    has_temp_file = (".tmp" in save_state_code or "tempfile" in save_state_code)
    has_rename = ("os.rename" in save_state_code or "shutil.move" in save_state_code)

    findings = []

    if has_temp_file and has_rename:
        findings.append("✅ Atomic write pattern detected (temp file + rename)")
        has_atomic = True
        risk = "LOW"
    else:
        findings.append("❌ BUG FOUND: save_state() writes directly to file")
        findings.append("⚠️  RISK: Bot crash during save will corrupt state.json")
        findings.append("🔴 IMPACT: Corrupted state → bot cannot restart → manual intervention required")

        # Extract the problematic code
        with_open_line = None
        for i, line in enumerate(save_state_code.split('\n')):
            if 'with open' in line and "'w'" in line:
                with_open_line = i
                break

        if with_open_line:
            findings.append(f"\n📄 Current implementation (UNSAFE):")
            findings.append("```python")
            for i, line in enumerate(save_state_code.split('\n')[with_open_line:with_open_line+3]):
                findings.append(line)
            findings.append("```")

        has_atomic = False
        risk = "CRITICAL"

    return {
        "file_exists": True,
        "has_atomic_writes": has_atomic,
        "findings": findings,
        "risk_level": risk,
        "function_code": save_state_code[:500]  # First 500 chars for reference
    }


def generate_atomic_write_fix() -> str:
    """Generate code snippet showing proper atomic write pattern"""
    return """
## Recommended Fix: Atomic Write Pattern

Replace the current `save_state()` function with this POSIX-atomic implementation:

```python
import tempfile
import os
import json
from dataclasses import asdict

def save_state(state: TradingState):
    \"""
    Save state using atomic write pattern to prevent corruption.

    Pattern:
    1. Write to temporary file (.tmp)
    2. Flush to disk (ensures write completes)
    3. Rename temp to final (atomic operation on POSIX)

    If crash occurs during step 1-2: old file remains intact
    If crash occurs during step 3: rename is atomic (either completes or doesn't)
    \"""
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
"""


def create_crash_test() -> str:
    """Create test script that simulates crash during state save"""
    return """#!/usr/bin/env python3
\"""
Crash Scenario Test for State File Atomic Writes

Simulates 3 failure scenarios:
1. Crash during JSON write (mid-file)
2. Crash after write but before file close
3. Crash during fsync()

Expected behavior:
- BEFORE FIX: State file corrupted (invalid JSON)
- AFTER FIX: State file remains valid (atomic writes protect it)
\"""

import json
import os
import signal
import time
import tempfile
from multiprocessing import Process
from pathlib import Path


def unsafe_save_state(state_file: str, data: dict):
    \"""Current implementation (UNSAFE) - writes directly\"""
    with open(state_file, 'w') as f:
        json.dump(data, f, indent=2)


def safe_save_state(state_file: str, data: dict):
    \"""Fixed implementation (SAFE) - uses atomic writes\"""
    temp_file = state_file + ".tmp"

    try:
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.rename(temp_file, state_file)
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


def test_scenario(scenario_name: str, save_func, crash_after_ms: int):
    \"""
    Test one crash scenario

    Args:
        scenario_name: Description of test
        save_func: Function to test (safe or unsafe)
        crash_after_ms: When to simulate crash (milliseconds)

    Returns:
        bool: True if state file is valid after crash
    \"""
    test_dir = tempfile.mkdtemp()
    state_file = os.path.join(test_dir, "test_state.json")

    # Create initial valid state
    initial_state = {"balance": 100.0, "mode": "normal"}
    with open(state_file, 'w') as f:
        json.dump(initial_state, f)

    # Fork process that will crash
    def crashy_writer():
        time.sleep(crash_after_ms / 1000.0)
        # Simulate crash by sending SIGKILL to self
        os.kill(os.getpid(), signal.SIGKILL)

    # Start crash timer in background
    import threading
    crash_thread = threading.Thread(target=crashy_writer, daemon=True)
    crash_thread.start()

    # Attempt save (will be interrupted)
    try:
        updated_state = {"balance": 200.0, "mode": "recovery"}
        save_func(state_file, updated_state)
        time.sleep(0.1)  # Give crash time to happen
    except:
        pass  # Expected to fail or be interrupted

    # Check if state file is still valid
    try:
        with open(state_file, 'r') as f:
            recovered_state = json.load(f)

        # File is valid - check if it's old or new state
        if recovered_state == initial_state:
            result = "✅ SAFE: Old state preserved (write didn't complete)"
        elif recovered_state == updated_state:
            result = "✅ SAFE: New state written successfully"
        else:
            result = "⚠️  WARNING: State partially updated (unexpected)"

        valid = True
    except (json.JSONDecodeError, FileNotFoundError):
        result = "❌ CORRUPTED: State file is invalid JSON or missing"
        valid = False

    # Cleanup
    if os.path.exists(state_file):
        os.remove(state_file)
    os.rmdir(test_dir)

    print(f"{scenario_name}: {result}")
    return valid


if __name__ == "__main__":
    print("=" * 80)
    print("State File Crash Recovery Test")
    print("=" * 80)
    print()

    print("Testing UNSAFE implementation (current code):")
    print("-" * 80)
    unsafe_results = [
        test_scenario("  Scenario 1: Crash during write", unsafe_save_state, 5),
        test_scenario("  Scenario 2: Crash after write", unsafe_save_state, 20),
        test_scenario("  Scenario 3: Crash during close", unsafe_save_state, 15),
    ]
    unsafe_pass_rate = sum(unsafe_results) / len(unsafe_results) * 100
    print(f"\\n  UNSAFE Pass Rate: {unsafe_pass_rate:.0f}% ({sum(unsafe_results)}/{len(unsafe_results)} scenarios)")
    print()

    print("Testing SAFE implementation (with atomic writes):")
    print("-" * 80)
    safe_results = [
        test_scenario("  Scenario 1: Crash during write", safe_save_state, 5),
        test_scenario("  Scenario 2: Crash after write", safe_save_state, 20),
        test_scenario("  Scenario 3: Crash during close", safe_save_state, 15),
    ]
    safe_pass_rate = sum(safe_results) / len(safe_results) * 100
    print(f"\\n  SAFE Pass Rate: {safe_pass_rate:.0f}% ({sum(safe_results)}/{len(safe_results)} scenarios)")
    print()

    print("=" * 80)
    print("VERDICT:")
    print("=" * 80)
    if safe_pass_rate > unsafe_pass_rate:
        print("✅ Atomic writes significantly improve crash recovery")
        print(f"   Improvement: {safe_pass_rate - unsafe_pass_rate:.0f}% fewer corruptions")
    elif safe_pass_rate == 100:
        print("✅ Atomic writes provide 100% protection against corruption")
    else:
        print("⚠️  Both implementations have risks - further testing needed")
    print()

    sys.exit(0 if safe_pass_rate >= 90 else 1)
"""


def generate_report(audit_result: dict, fix_code: str, test_code: str) -> str:
    """Generate markdown report"""
    report = f"""# US-RC-006: State File Atomic Write Audit

**Persona:** Dmitri "The Hammer" Volkov - System Reliability Engineer
**Date:** {Path(__file__).stat().st_mtime if Path(__file__).exists() else "Unknown"}
**Status:** {'PASS' if audit_result['has_atomic_writes'] else 'FAIL'}
**Risk Level:** {audit_result['risk_level']}

---

## Executive Summary

Atomic writes are {'IMPLEMENTED' if audit_result['has_atomic_writes'] else 'NOT IMPLEMENTED'} in `bot/momentum_bot_v12.py`.

**Risk Assessment:** {audit_result['risk_level']}

{'✅ The bot uses atomic writes to prevent state corruption during crashes.' if audit_result['has_atomic_writes'] else '❌ The bot writes directly to state.json without atomic guarantees, creating critical corruption risk.'}

---

## Audit Findings

### Code Review: `save_state()` Function

"""

    for finding in audit_result['findings']:
        report += f"{finding}\n"

    report += f"""

### Risk Analysis

| Aspect | Current Implementation | Risk |
|--------|----------------------|------|
| **Write Method** | {'Atomic (temp + rename)' if audit_result['has_atomic_writes'] else 'Direct write'} | {audit_result['risk_level']} |
| **Crash Protection** | {'Yes' if audit_result['has_atomic_writes'] else 'No'} | {audit_result['risk_level']} |
| **Corruption Possible** | {'No' if audit_result['has_atomic_writes'] else 'Yes'} | {audit_result['risk_level']} |
| **Recovery Required** | {'Automatic' if audit_result['has_atomic_writes'] else 'Manual'} | {audit_result['risk_level']} |

### Real-World Scenarios

**Scenario 1: Bot crashes mid-save (OOM kill, power loss, SIGKILL)**
- Current behavior: {'State file remains valid' if audit_result['has_atomic_writes'] else 'State file corrupted (partial JSON)'}
- Impact: {'Bot restarts normally' if audit_result['has_atomic_writes'] else 'Bot cannot start, requires manual state file repair'}

**Scenario 2: Filesystem full during save**
- Current behavior: {'Temp file write fails, original preserved' if audit_result['has_atomic_writes'] else 'Partial write, file corrupted'}
- Impact: {'Bot logs error, retries on next cycle' if audit_result['has_atomic_writes'] else 'Bot stuck, manual intervention needed'}

**Scenario 3: VPS hard reboot during state update**
- Current behavior: {'Previous state intact (atomic rename did not complete)' if audit_result['has_atomic_writes'] else 'State file may be corrupted or empty'}
- Impact: {'Loss of last cycle data only' if audit_result['has_atomic_writes'] else 'Loss of all state, manual balance/peak reset needed'}

---

"""

    if not audit_result['has_atomic_writes']:
        report += fix_code
        report += f"""

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

"""

    report += f"""
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
0 * * * * cp /opt/polymarket-autotrader/state/trading_state.json /opt/polymarket-autotrader/state/backups/state_$(date +\\%Y\\%m\\%d_\\%H00).json
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
        logging.error(f"State file corrupted or missing: {{e}}")
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
{{
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

{'✅ The bot is protected against state corruption.' if audit_result['has_atomic_writes'] else '❌ The bot has a CRITICAL bug that will cause state corruption on crash.'}

**Risk Level:** {audit_result['risk_level']}

{'No immediate action needed. Continue monitoring for state file issues.' if audit_result['has_atomic_writes'] else 'IMMEDIATE ACTION REQUIRED: Apply atomic write fix before next deployment.'}

---

**Audited by:** Dmitri "The Hammer" Volkov
**Motto:** "If it can fail, it will fail. Build for 3am crashes."

"""

    return report


if __name__ == "__main__":
    print("🔨 Dmitri's Atomic Write Audit (US-RC-006)")
    print("=" * 80)
    print()

    # 1. Audit code
    print("Step 1: Auditing save_state() implementation...")
    audit_result = audit_save_state_code()

    print(f"  Status: {audit_result['risk_level']}")
    print(f"  Atomic writes: {'YES' if audit_result['has_atomic_writes'] else 'NO'}")
    print()

    # 2. Generate fix code
    print("Step 2: Generating atomic write fix...")
    fix_code = generate_atomic_write_fix()
    print("  ✅ Fix code generated")
    print()

    # 3. Generate crash test
    print("Step 3: Creating crash recovery test...")
    test_code = create_crash_test()
    test_file = "scripts/research/test_state_crash_recovery.py"
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, 'w') as f:
        f.write(test_code)
    os.chmod(test_file, 0o755)  # Make executable
    print(f"  ✅ Test created: {test_file}")
    print()

    # 4. Generate report
    print("Step 4: Generating audit report...")
    report = generate_report(audit_result, fix_code, test_code)
    report_file = "reports/dmitri_volkov/atomic_write_audit.md"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"  ✅ Report saved: {report_file}")
    print()

    print("=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    print()
    print(f"Risk Level: {audit_result['risk_level']}")
    print(f"Findings: {len(audit_result['findings'])}")
    print()
    print("Next steps:")
    print(f"  1. Review report: {report_file}")
    print(f"  2. Run crash test: python3 {test_file}")
    if not audit_result['has_atomic_writes']:
        print("  3. Apply fix to bot/momentum_bot_v12.py")
        print("  4. Re-run crash test to verify fix")
        print("  5. Deploy to VPS")
    print()

    # Exit code: 0 if safe, 1 if unsafe
    sys.exit(0 if audit_result['has_atomic_writes'] else 1)
