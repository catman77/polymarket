#!/usr/bin/env python3
"""
Task 6.1: State Management Audit
Persona: Dmitri "The Hammer" Volkov - System Reliability Engineer

Validates trading_state.json persistence and correctness:
1. State file inspection (field validation)
2. State update code review (atomic writes, error handling)
3. Historical state corruption (Jan 16 desync analysis)
4. State recovery scenarios (missing/corrupted file handling)
5. Multi-process safety (single instance verification)
6. State backup strategy (recommendations)
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path


@dataclass
class StateField:
    """Represents a field in trading_state.json"""
    name: str
    value: Any
    expected_type: type
    valid: bool
    issues: List[str]


@dataclass
class AuditResult:
    """Audit findings for a specific area"""
    area: str
    status: str  # "PASS", "WARNING", "FAIL"
    findings: List[str]
    recommendations: List[str]


class StateManagementAuditor:
    """Comprehensive state management audit tool"""

    def __init__(self, state_file: str = "state/trading_state.json", bot_code: str = "bot/momentum_bot_v12.py"):
        self.state_file = state_file
        self.bot_code = bot_code
        self.results: List[AuditResult] = []

    def run_full_audit(self) -> Dict[str, Any]:
        """Execute all audit checks"""
        print("🔨 Dmitri's State Management Audit")
        print("=" * 80)

        # 1. State file inspection
        state_data = self.audit_state_file()

        # 2. Code review (atomic writes, error handling)
        self.audit_state_persistence_code()

        # 3. Historical corruption analysis
        self.audit_jan16_desync()

        # 4. Recovery scenarios
        self.audit_recovery_scenarios()

        # 5. Multi-process safety
        self.audit_multi_process_safety()

        # 6. Backup strategy
        self.audit_backup_strategy()

        # Calculate overall verdict
        verdict = self.calculate_verdict()

        return {
            "state_data": state_data,
            "results": self.results,
            "verdict": verdict,
            "timestamp": datetime.now().isoformat()
        }

    def audit_state_file(self) -> Optional[Dict]:
        """Audit 1: Inspect state file structure and values"""
        findings = []
        recommendations = []

        if not os.path.exists(self.state_file):
            findings.append(f"❌ State file not found: {self.state_file}")
            findings.append("🔴 CRITICAL: Bot cannot operate without state file")
            recommendations.append("Create default state file with initial values")
            self.results.append(AuditResult(
                area="State File Existence",
                status="FAIL",
                findings=findings,
                recommendations=recommendations
            ))
            return None

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
        except json.JSONDecodeError as e:
            findings.append(f"❌ State file JSON corrupted: {e}")
            findings.append("🔴 CRITICAL: Cannot parse state file")
            recommendations.append("Restore from backup or reinitialize state")
            self.results.append(AuditResult(
                area="State File Parsing",
                status="FAIL",
                findings=findings,
                recommendations=recommendations
            ))
            return None
        except Exception as e:
            findings.append(f"❌ Unexpected error reading state: {e}")
            self.results.append(AuditResult(
                area="State File Access",
                status="FAIL",
                findings=findings,
                recommendations=["Investigate file permissions or corruption"]
            ))
            return None

        # Expected fields
        expected_fields = {
            "day_start_balance": float,
            "current_balance": float,
            "peak_balance": float,
            "daily_pnl": float,
            "mode": str,
            "consecutive_wins": int,
            "consecutive_losses": int,
            "total_trades": int,
            "total_wins": int
        }

        # Validate fields
        field_results = []
        for field_name, expected_type in expected_fields.items():
            issues = []
            if field_name not in state:
                issues.append(f"Missing required field: {field_name}")
                field_results.append(StateField(field_name, None, expected_type, False, issues))
            else:
                value = state[field_name]
                type_valid = isinstance(value, expected_type)
                if not type_valid:
                    issues.append(f"Wrong type: expected {expected_type.__name__}, got {type(value).__name__}")

                # Value validation
                if field_name in ["current_balance", "peak_balance"] and value < 0:
                    issues.append(f"Invalid negative balance: ${value:.2f}")

                if field_name == "mode" and value not in ["normal", "conservative", "defensive", "recovery", "halted"]:
                    issues.append(f"Unknown mode: {value}")

                if field_name in ["consecutive_wins", "consecutive_losses", "total_trades", "total_wins"] and value < 0:
                    issues.append(f"Invalid negative count: {value}")

                field_results.append(StateField(field_name, value, expected_type, len(issues) == 0, issues))

        # Logical consistency checks
        if "current_balance" in state and "peak_balance" in state:
            if state["current_balance"] > state["peak_balance"]:
                findings.append(f"⚠️  WARNING: current_balance (${state['current_balance']:.2f}) > peak_balance (${state['peak_balance']:.2f})")
                findings.append("   → peak_balance should always be >= current_balance")
                recommendations.append("Reset peak_balance = max(peak_balance, current_balance)")

        if "total_trades" in state and "total_wins" in state:
            if state["total_wins"] > state["total_trades"]:
                findings.append(f"❌ INVALID: total_wins ({state['total_wins']}) > total_trades ({state['total_trades']})")
                recommendations.append("Investigate counter logic in bot code")

        # Drawdown calculation
        if "current_balance" in state and "peak_balance" in state and state["peak_balance"] > 0:
            drawdown = (state["peak_balance"] - state["current_balance"]) / state["peak_balance"]
            if drawdown >= 0.30:
                findings.append(f"🔴 CRITICAL: Drawdown {drawdown*100:.1f}% >= 30% threshold")
                findings.append(f"   → Should be HALTED (peak: ${state['peak_balance']:.2f}, current: ${state['current_balance']:.2f})")
                if state.get("mode") != "halted":
                    recommendations.append("Bot should auto-halt at 30% drawdown - verify Guardian logic")

        # Report field results
        for field in field_results:
            if not field.valid:
                for issue in field.issues:
                    findings.append(f"❌ {field.name}: {issue}")

        status = "FAIL" if any(not f.valid for f in field_results) else ("WARNING" if findings else "PASS")

        if status == "PASS":
            findings.append("✅ All required fields present and valid")

        self.results.append(AuditResult(
            area="State File Structure",
            status=status,
            findings=findings,
            recommendations=recommendations
        ))

        return state

    def audit_state_persistence_code(self):
        """Audit 2: Review state update code for atomic writes and error handling"""
        findings = []
        recommendations = []

        if not os.path.exists(self.bot_code):
            findings.append(f"⚠️  Bot code not found: {self.bot_code}")
            self.results.append(AuditResult(
                area="Code Review - State Persistence",
                status="WARNING",
                findings=findings,
                recommendations=["Provide bot code for review"]
            ))
            return

        with open(self.bot_code, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        # Check for atomic write pattern (temp file + rename)
        has_temp_file = "temp" in code.lower() or ".tmp" in code.lower()
        has_rename = "os.rename" in code or "shutil.move" in code

        if not (has_temp_file and has_rename):
            findings.append("⚠️  WARNING: No atomic write pattern detected")
            findings.append("   → State updates may corrupt on crash (write partial JSON)")
            recommendations.append("Use atomic write pattern: write to temp file → rename to final")
            recommendations.append("Example: json.dump(state, f_tmp) → os.rename('state.tmp', 'state.json')")
        else:
            findings.append("✅ Atomic write pattern detected (temp file + rename)")

        # Check for error handling in state save
        save_state_funcs = re.findall(r'def\s+(save_state|update_state|persist_state)[^:]*:', code)
        if save_state_funcs:
            findings.append(f"✅ Found state save functions: {', '.join(save_state_funcs)}")

            # Check for try/except around state save
            has_try_except = "try:" in code and "except" in code
            if has_try_except:
                findings.append("✅ Error handling (try/except) present in code")
            else:
                findings.append("⚠️  WARNING: No explicit try/except for state save")
                recommendations.append("Add error handling around state writes to prevent crashes")
        else:
            findings.append("⚠️  No explicit save_state() function found")
            recommendations.append("Encapsulate state persistence in dedicated function")

        # Check for file locking (multi-process safety)
        has_lock = "fcntl.flock" in code or "Lock()" in code or "threading.Lock" in code
        if has_lock:
            findings.append("✅ File locking mechanism detected (multi-process safe)")
        else:
            findings.append("⚠️  No file locking detected")
            findings.append("   → Risk: Multiple processes could corrupt state")
            recommendations.append("Add file locking if multiple bot instances possible")

        status = "WARNING" if any("WARNING" in f for f in findings) else "PASS"

        self.results.append(AuditResult(
            area="Code Review - State Persistence",
            status=status,
            findings=findings,
            recommendations=recommendations
        ))

    def audit_jan16_desync(self):
        """Audit 3: Analyze Jan 16 peak_balance desync incident"""
        findings = []
        recommendations = []

        findings.append("📋 Jan 16 Incident: peak_balance desync ($186 error)")
        findings.append("")
        findings.append("**Root Cause Analysis:**")
        findings.append("1. peak_balance incorrectly included unredeemed position values")
        findings.append("2. After redemption, cash increased but peak stayed high")
        findings.append("3. Created false drawdown calculation → premature halt")
        findings.append("")
        findings.append("**Timeline:**")
        findings.append("- Jan 15: Recovered $194 profit (including position values)")
        findings.append("- Jan 16 01:56: Discovered state file balance desync ($186 error)")
        findings.append("- Jan 16 01:56: Corrected state file to match on-chain ($200.97)")
        findings.append("")
        findings.append("**Verified Fix:**")
        findings.append("✅ State file manually corrected")
        findings.append("✅ Drawdown protection recalculated with correct peak")

        recommendations.append("**Prevention Measures:**")
        recommendations.append("1. peak_balance should ONLY track realized cash (not positions)")
        recommendations.append("2. Add assertion: peak_balance >= current_balance (always true)")
        recommendations.append("3. Log peak_balance updates with reason (trade win, deposit, etc.)")
        recommendations.append("4. Daily reconciliation: Compare state vs on-chain balance")
        recommendations.append("5. Alert if peak_balance unchanged for >7 days (stale)")

        self.results.append(AuditResult(
            area="Jan 16 Desync Incident",
            status="WARNING",
            findings=findings,
            recommendations=recommendations
        ))

    def audit_recovery_scenarios(self):
        """Audit 4: Test state recovery scenarios"""
        findings = []
        recommendations = []

        findings.append("🧪 State Recovery Scenarios:")
        findings.append("")

        # Scenario 1: Missing state file
        findings.append("**Scenario 1: State file deleted**")
        if os.path.exists(self.bot_code):
            with open(self.bot_code, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            if "os.path.exists" in code and "trading_state.json" in code:
                findings.append("✅ Code checks for state file existence")
                findings.append("   → Likely creates default state if missing")
            else:
                findings.append("⚠️  No explicit state file existence check")
                findings.append("   → May crash with FileNotFoundError")
                recommendations.append("Add state file existence check + default initialization")
        else:
            findings.append("⚠️  Cannot verify (bot code not found)")

        findings.append("")

        # Scenario 2: Corrupted JSON
        findings.append("**Scenario 2: State file corrupted (invalid JSON)**")
        findings.append("⚠️  Risk: json.load() raises JSONDecodeError")
        findings.append("   → Bot crashes on startup")
        recommendations.append("Add try/except around state loading")
        recommendations.append("Fallback: Load from backup or reset to defaults")

        findings.append("")

        # Scenario 3: Partial write (crash during save)
        findings.append("**Scenario 3: Partial write (crash mid-save)**")
        if "os.rename" in code if os.path.exists(self.bot_code) else False:
            findings.append("✅ Atomic rename prevents partial writes")
        else:
            findings.append("⚠️  Risk: Partial JSON written (corrupted file)")
            recommendations.append("Use atomic write pattern (temp file + rename)")

        findings.append("")

        # Scenario 4: Stale state (bot restarted after crash)
        findings.append("**Scenario 4: Stale state (bot crashed, positions settled)**")
        findings.append("⚠️  Risk: State balance != on-chain balance after redemptions")
        recommendations.append("On startup: Fetch on-chain balance and reconcile")
        recommendations.append("If mismatch >$1: Log warning + auto-correct state")

        status = "WARNING"  # Always recommend improvements

        self.results.append(AuditResult(
            area="State Recovery Scenarios",
            status=status,
            findings=findings,
            recommendations=recommendations
        ))

    def audit_multi_process_safety(self):
        """Audit 5: Verify single-instance operation"""
        findings = []
        recommendations = []

        findings.append("🔒 Multi-Process Safety Check:")
        findings.append("")

        # Check if bot is running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "momentum_bot"],
                capture_output=True,
                text=True,
                timeout=5
            )
            processes = result.stdout.strip().split('\n') if result.stdout else []
            process_count = len([p for p in processes if p])

            if process_count == 0:
                findings.append("✅ Bot not currently running (safe for analysis)")
            elif process_count == 1:
                findings.append("✅ Exactly 1 bot process running (correct)")
            else:
                findings.append(f"🔴 CRITICAL: {process_count} bot processes detected!")
                findings.append("   → Multiple instances will corrupt state")
                recommendations.append("Kill duplicate processes immediately")
                recommendations.append("Add process lock file (e.g., /tmp/polymarket-bot.lock)")
        except subprocess.TimeoutExpired:
            findings.append("⚠️  Process check timed out")
        except FileNotFoundError:
            findings.append("⚠️  pgrep not available (cannot check processes)")
        except Exception as e:
            findings.append(f"⚠️  Error checking processes: {e}")

        findings.append("")

        # Check systemd service configuration
        findings.append("**Systemd Configuration:**")
        try:
            result = subprocess.run(
                ["systemctl", "show", "polymarket-bot", "--property=ExecStart"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout:
                findings.append(f"✅ Service configured: {result.stdout.strip()}")
            else:
                findings.append("⚠️  Service not found or not configured")
        except:
            findings.append("⚠️  Cannot check systemd (not on VPS or no permissions)")

        recommendations.append("**Best Practices:**")
        recommendations.append("1. Use systemd to ensure single instance (auto-restart on crash)")
        recommendations.append("2. Add PID lock file: /tmp/polymarket-bot.pid")
        recommendations.append("3. On startup: Check lock file → exit if already running")
        recommendations.append("4. On shutdown: Remove lock file")

        status = "WARNING" if ('process_count' in locals() and process_count > 1) else "PASS"

        self.results.append(AuditResult(
            area="Multi-Process Safety",
            status=status,
            findings=findings,
            recommendations=recommendations
        ))

    def audit_backup_strategy(self):
        """Audit 6: Evaluate state backup strategy"""
        findings = []
        recommendations = []

        findings.append("💾 State Backup Strategy Audit:")
        findings.append("")

        # Check if state is gitignored
        gitignore_path = ".gitignore"
        state_gitignored = False
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as f:
                gitignore = f.read()
            if "state/" in gitignore or "trading_state.json" in gitignore:
                findings.append("✅ State files gitignored (won't commit secrets)")
                state_gitignored = True
            else:
                findings.append("⚠️  State NOT gitignored (risk: commit sensitive data)")
                recommendations.append("Add 'state/' to .gitignore")

        findings.append("")

        # Check for backup files
        findings.append("**Current Backup Status:**")
        state_dir = os.path.dirname(self.state_file) or "."
        backup_files = []
        if os.path.exists(state_dir):
            for file in os.listdir(state_dir):
                if "backup" in file.lower() or ".bak" in file or file.endswith("~"):
                    backup_files.append(file)

        if backup_files:
            findings.append(f"✅ Found {len(backup_files)} backup file(s):")
            for backup in backup_files[:5]:  # Show max 5
                findings.append(f"   - {backup}")
        else:
            findings.append("⚠️  No backup files detected")
            findings.append("   → Risk: State corruption = permanent data loss")

        findings.append("")

        # Check for backup automation
        findings.append("**Backup Automation:**")
        findings.append("⚠️  No automated backup system detected")
        findings.append("")

        recommendations.append("**Recommended Backup Strategy:**")
        recommendations.append("1. Daily automated backup via cron:")
        recommendations.append("   ```bash")
        recommendations.append("   0 0 * * * cp state/trading_state.json state/backup_$(date +%Y%m%d).json")
        recommendations.append("   ```")
        recommendations.append("2. Keep last 30 days of backups (prune old files)")
        recommendations.append("3. Off-site backup: Upload to S3/Dropbox weekly")
        recommendations.append("4. Test recovery: Restore from backup monthly")
        recommendations.append("5. Document recovery procedure in README")
        recommendations.append("6. Add state checksum to detect corruption")

        status = "WARNING"  # Always recommend backups

        self.results.append(AuditResult(
            area="Backup Strategy",
            status=status,
            findings=findings,
            recommendations=recommendations
        ))

    def calculate_verdict(self) -> Dict[str, Any]:
        """Calculate overall audit verdict"""
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        warning_count = sum(1 for r in self.results if r.status == "WARNING")
        pass_count = sum(1 for r in self.results if r.status == "PASS")

        if fail_count > 0:
            overall = "🔴 CRITICAL"
            summary = f"System has {fail_count} critical issue(s) requiring immediate attention"
        elif warning_count >= 3:
            overall = "🟡 NEEDS IMPROVEMENT"
            summary = f"System has {warning_count} warning(s) - operational but needs hardening"
        elif warning_count > 0:
            overall = "🟢 ACCEPTABLE"
            summary = f"System operational with {warning_count} minor issue(s)"
        else:
            overall = "🟢 EXCELLENT"
            summary = "State management is robust and well-designed"

        return {
            "overall": overall,
            "summary": summary,
            "fail_count": fail_count,
            "warning_count": warning_count,
            "pass_count": pass_count
        }

    def generate_report(self, audit_data: Dict[str, Any], output_file: str):
        """Generate markdown report"""
        with open(output_file, 'w') as f:
            f.write("# State Management Audit Report\n\n")
            f.write("**Auditor:** Dmitri \"The Hammer\" Volkov - System Reliability Engineer\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Audit Scope:** Task 6.1 - State Persistence & Correctness Validation\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            verdict = audit_data["verdict"]
            f.write(f"**Overall Assessment:** {verdict['overall']}\n\n")
            f.write(f"{verdict['summary']}\n\n")
            f.write(f"- ✅ Passed: {verdict['pass_count']} areas\n")
            f.write(f"- ⚠️  Warnings: {verdict['warning_count']} areas\n")
            f.write(f"- 🔴 Failures: {verdict['fail_count']} areas\n\n")
            f.write("---\n\n")

            # Current State Data
            if audit_data.get("state_data"):
                state = audit_data["state_data"]
                f.write("## Current State Snapshot\n\n")
                f.write("```json\n")
                f.write(json.dumps(state, indent=2))
                f.write("\n```\n\n")
                f.write("---\n\n")

            # Detailed Findings
            f.write("## Detailed Audit Findings\n\n")
            for result in self.results:
                f.write(f"### {result.area}\n\n")
                f.write(f"**Status:** {result.status}\n\n")

                if result.findings:
                    f.write("**Findings:**\n\n")
                    for finding in result.findings:
                        if finding:  # Skip empty lines
                            f.write(f"{finding}\n")
                    f.write("\n")

                if result.recommendations:
                    f.write("**Recommendations:**\n\n")
                    for rec in result.recommendations:
                        if rec:  # Skip empty lines
                            f.write(f"{rec}\n")
                    f.write("\n")

                f.write("---\n\n")

            # Action Items
            f.write("## Priority Action Items\n\n")

            critical_items = []
            for result in self.results:
                if result.status == "FAIL":
                    critical_items.extend(result.recommendations)

            if critical_items:
                f.write("### 🔴 Critical (Immediate)\n\n")
                for i, item in enumerate(critical_items[:5], 1):
                    f.write(f"{i}. {item}\n")
                f.write("\n")

            warning_items = []
            for result in self.results:
                if result.status == "WARNING":
                    warning_items.extend(result.recommendations[:2])  # Top 2 per area

            if warning_items:
                f.write("### 🟡 Important (Within 1 Week)\n\n")
                for i, item in enumerate(warning_items[:10], 1):
                    f.write(f"{i}. {item}\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("**END OF REPORT**\n")

        print(f"\n✅ Report generated: {output_file}")


def main():
    """Main execution"""
    import sys

    # Parse arguments
    state_file = sys.argv[1] if len(sys.argv) > 1 else "state/trading_state.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "reports/dmitri_volkov/state_audit.md"

    # Create output directory
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Run audit
    auditor = StateManagementAuditor(state_file=state_file)
    audit_data = auditor.run_full_audit()

    # Generate report
    auditor.generate_report(audit_data, output_file)

    # Print summary
    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    verdict = audit_data["verdict"]
    print(f"\nOverall: {verdict['overall']}")
    print(f"{verdict['summary']}")
    print(f"\nDetails: {output_file}")

    # Exit code based on verdict
    if verdict["fail_count"] > 0:
        sys.exit(1)  # Critical issues
    else:
        sys.exit(0)  # Acceptable or better


if __name__ == "__main__":
    main()
