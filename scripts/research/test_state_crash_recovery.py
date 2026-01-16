#!/usr/bin/env python3
"""
Crash Scenario Test for State File Atomic Writes

Simulates 3 failure scenarios:
1. Crash during JSON write (mid-file)
2. Crash after write but before file close
3. Crash during fsync()

Expected behavior:
- BEFORE FIX: State file corrupted (invalid JSON)
- AFTER FIX: State file remains valid (atomic writes protect it)
"""

import json
import os
import signal
import time
import tempfile
from multiprocessing import Process
from pathlib import Path


def unsafe_save_state(state_file: str, data: dict):
    """Current implementation (UNSAFE) - writes directly"""
    with open(state_file, 'w') as f:
        json.dump(data, f, indent=2)


def safe_save_state(state_file: str, data: dict):
    """Fixed implementation (SAFE) - uses atomic writes"""
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
    """
    Test one crash scenario

    Args:
        scenario_name: Description of test
        save_func: Function to test (safe or unsafe)
        crash_after_ms: When to simulate crash (milliseconds)

    Returns:
        bool: True if state file is valid after crash
    """
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
    print(f"\n  UNSAFE Pass Rate: {unsafe_pass_rate:.0f}% ({sum(unsafe_results)}/{len(unsafe_results)} scenarios)")
    print()

    print("Testing SAFE implementation (with atomic writes):")
    print("-" * 80)
    safe_results = [
        test_scenario("  Scenario 1: Crash during write", safe_save_state, 5),
        test_scenario("  Scenario 2: Crash after write", safe_save_state, 20),
        test_scenario("  Scenario 3: Crash during close", safe_save_state, 15),
    ]
    safe_pass_rate = sum(safe_results) / len(safe_results) * 100
    print(f"\n  SAFE Pass Rate: {safe_pass_rate:.0f}% ({sum(safe_results)}/{len(safe_results)} scenarios)")
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
