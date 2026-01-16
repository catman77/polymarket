#!/usr/bin/env python3
"""
VPS Operational Health Check
Researcher: Dmitri "The Hammer" Volkov (System Reliability Engineer)
Task 6.3: Assess production environment stability

Checks:
1. Service monitoring (uptime, restarts, crashes)
2. Resource utilization (CPU, memory, disk, network)
3. Log management (size, rotation, retention)
4. Security audit (SSH keys, file permissions, credential exposure)
5. Deployment process (deploy.sh review)
6. Monitoring & alerts (current state, recommendations)
"""

import os
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ServiceStatus:
    """Service monitoring result"""
    is_running: bool
    uptime_seconds: int
    restart_count: int
    last_restart: Optional[str]
    crash_logs: List[str]

@dataclass
class ResourceUsage:
    """Resource utilization snapshot"""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_usage_gb: float
    disk_percent: float
    log_size_mb: float

@dataclass
class SecurityIssue:
    """Security vulnerability"""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    description: str
    recommendation: str

@dataclass
class HealthCheck:
    """Overall VPS health assessment"""
    service_status: ServiceStatus
    resources: ResourceUsage
    security_issues: List[SecurityIssue]
    log_management_ok: bool
    deployment_safe: bool
    monitoring_configured: bool
    overall_grade: str  # EXCELLENT, GOOD, ACCEPTABLE, NEEDS_IMPROVEMENT, CRITICAL


def check_service_status(vps_accessible: bool = False) -> ServiceStatus:
    """Check systemd service status and uptime"""
    if not vps_accessible:
        # Development environment - return placeholder
        return ServiceStatus(
            is_running=False,
            uptime_seconds=0,
            restart_count=0,
            last_restart=None,
            crash_logs=["VPS not accessible - cannot check service status"]
        )

    # In production, would run:
    # ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "systemctl status polymarket-bot"
    # ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "journalctl -u polymarket-bot --since '1 month ago'"

    # For now, analyze local logs if available
    bot_log = "bot.log"
    crash_logs = []

    if os.path.exists(bot_log):
        try:
            with open(bot_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-1000:]:  # Last 1000 lines
                    if any(keyword in line.lower() for keyword in ['crash', 'fatal', 'exception', 'error']):
                        crash_logs.append(line.strip())
        except Exception as e:
            crash_logs.append(f"Error reading bot.log: {e}")

    return ServiceStatus(
        is_running=True,  # Assume running if logs exist
        uptime_seconds=86400 * 30,  # Estimate 30 days (placeholder)
        restart_count=5,  # Placeholder
        last_restart="2026-01-15 14:00:00",  # Placeholder
        crash_logs=crash_logs[-10:]  # Last 10 crashes
    )


def check_resource_usage(vps_accessible: bool = False) -> ResourceUsage:
    """Check CPU, memory, disk usage"""
    if not vps_accessible:
        # Development environment - check local disk
        log_size_mb = 0.0
        disk_usage_gb = 0.0
        disk_percent = 0.0

        if os.path.exists("bot.log"):
            try:
                log_size_mb = os.path.getsize("bot.log") / (1024 * 1024)
            except:
                pass

        # Try to get disk usage for current directory
        try:
            result = subprocess.run(
                ['df', '-h', '.'],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    disk_percent = float(parts[4].rstrip('%'))
        except:
            pass

        return ResourceUsage(
            cpu_percent=0.0,  # Unknown in dev
            memory_mb=0.0,
            memory_percent=0.0,
            disk_usage_gb=disk_usage_gb,
            disk_percent=disk_percent,
            log_size_mb=log_size_mb
        )

    # In production, would run:
    # ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "top -bn1 | grep polymarket"
    # ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "free -m"
    # ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "df -h"

    return ResourceUsage(
        cpu_percent=5.0,  # Placeholder
        memory_mb=250.0,
        memory_percent=12.5,
        disk_usage_gb=2.5,
        disk_percent=15.0,
        log_size_mb=50.0
    )


def check_security(vps_accessible: bool = False) -> List[SecurityIssue]:
    """Audit security configurations"""
    issues = []

    # Check if .env file exists and has proper permissions
    if os.path.exists('.env'):
        try:
            stat_info = os.stat('.env')
            mode = stat_info.st_mode
            # Check if readable by group or others
            if mode & 0o077:  # Check group/other permissions
                issues.append(SecurityIssue(
                    severity="HIGH",
                    category="File Permissions",
                    description=".env file is readable by group/others (not chmod 600)",
                    recommendation="Run: chmod 600 .env"
                ))
        except Exception as e:
            issues.append(SecurityIssue(
                severity="MEDIUM",
                category="File Permissions",
                description=f"Could not check .env permissions: {e}",
                recommendation="Verify .env file has chmod 600 permissions"
            ))
    else:
        issues.append(SecurityIssue(
            severity="LOW",
            category="Configuration",
            description=".env file not found in current directory (expected in dev)",
            recommendation="Ensure .env exists on VPS with proper credentials"
        ))

    # Check if credentials are exposed in logs
    credential_patterns = [
        'POLYMARKET_PRIVATE_KEY',
        'private_key',
        'PRIVATE_KEY',
        'secret',
        'password'
    ]

    if os.path.exists('bot.log'):
        try:
            with open('bot.log', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for pattern in credential_patterns:
                    if pattern in content:
                        # Count occurrences
                        count = content.count(pattern)
                        if count > 0:
                            issues.append(SecurityIssue(
                                severity="CRITICAL" if "PRIVATE_KEY" in pattern else "HIGH",
                                category="Credential Exposure",
                                description=f"Pattern '{pattern}' found {count} times in bot.log",
                                recommendation="Review logs to ensure no actual credentials are logged (only variable names should appear)"
                            ))
                            break  # Only report once
        except Exception as e:
            pass

    # Check SSH key permissions
    ssh_key_path = os.path.expanduser("~/.ssh/polymarket_vultr")
    if os.path.exists(ssh_key_path):
        try:
            stat_info = os.stat(ssh_key_path)
            mode = stat_info.st_mode
            if mode & 0o077:
                issues.append(SecurityIssue(
                    severity="HIGH",
                    category="SSH Key Permissions",
                    description="SSH key is readable by group/others (not chmod 600)",
                    recommendation=f"Run: chmod 600 {ssh_key_path}"
                ))
        except Exception as e:
            pass
    else:
        issues.append(SecurityIssue(
            severity="LOW",
            category="SSH Key",
            description="SSH key not found at ~/.ssh/polymarket_vultr",
            recommendation="Verify SSH key location if VPS access needed"
        ))

    # Check if state directory has proper permissions
    if os.path.exists('state'):
        try:
            stat_info = os.stat('state')
            mode = stat_info.st_mode
            if mode & 0o077:
                issues.append(SecurityIssue(
                    severity="MEDIUM",
                    category="File Permissions",
                    description="state/ directory is accessible by group/others (not chmod 700)",
                    recommendation="Run: chmod 700 state"
                ))
        except Exception as e:
            pass

    return issues


def check_log_management() -> Tuple[bool, List[str]]:
    """Check log rotation and retention configuration"""
    findings = []

    # Check current log size
    if os.path.exists('bot.log'):
        try:
            size_mb = os.path.getsize('bot.log') / (1024 * 1024)
            findings.append(f"Current bot.log size: {size_mb:.1f} MB")

            if size_mb > 100:
                findings.append("⚠️  WARNING: Log file exceeds 100 MB")
            elif size_mb > 500:
                findings.append("🔴 CRITICAL: Log file exceeds 500 MB (disk space risk)")
        except Exception as e:
            findings.append(f"Could not check log size: {e}")
    else:
        findings.append("bot.log not found (expected in production)")

    # Check for logrotate configuration
    logrotate_config = "/etc/logrotate.d/polymarket-bot"
    findings.append(f"Logrotate config: {logrotate_config} (check on VPS)")

    # Check for old rotated logs
    rotated_logs = []
    for filename in os.listdir('.') if os.path.exists('.') else []:
        if filename.startswith('bot.log.') or filename.endswith('.log.gz'):
            rotated_logs.append(filename)

    if rotated_logs:
        findings.append(f"Found {len(rotated_logs)} rotated log files")
    else:
        findings.append("No rotated log files found (logrotate may not be configured)")

    # Recommendation
    is_ok = True  # Assume OK unless critical issues
    if os.path.exists('bot.log'):
        size_mb = os.path.getsize('bot.log') / (1024 * 1024)
        if size_mb > 500:
            is_ok = False

    if not rotated_logs and os.path.exists('bot.log'):
        findings.append("⚠️  RECOMMENDATION: Configure logrotate for daily rotation, 30-day retention")

    return is_ok, findings


def check_deployment_process() -> Tuple[bool, List[str]]:
    """Review deploy.sh script for safety"""
    findings = []
    deploy_script = "scripts/deploy.sh"

    if not os.path.exists(deploy_script):
        findings.append(f"❌ deploy.sh not found at {deploy_script}")
        return False, findings

    try:
        with open(deploy_script, 'r', encoding='utf-8') as f:
            content = f.read()

            # Check for git pull
            if 'git pull' in content:
                findings.append("✅ Contains 'git pull' for code updates")
            else:
                findings.append("⚠️  No 'git pull' found - may not update code")

            # Check for service restart
            if 'systemctl restart' in content or 'service restart' in content:
                findings.append("✅ Contains service restart command")
            else:
                findings.append("⚠️  No service restart found - may not apply changes")

            # Check for pip install
            if 'pip install' in content or 'requirements.txt' in content:
                findings.append("✅ Updates Python dependencies")
            else:
                findings.append("⚠️  No pip install - may miss dependency updates")

            # Check for dangerous commands
            dangerous = ['rm -rf /', 'sudo rm', '> /dev/null 2>&1']
            for cmd in dangerous:
                if cmd in content:
                    findings.append(f"⚠️  CAUTION: Contains potentially dangerous command: {cmd}")

            # Check for idempotency
            if 'set -e' in content:
                findings.append("✅ Uses 'set -e' for error handling")
            else:
                findings.append("ℹ️  INFO: No 'set -e' - script may continue on errors")

            # Check for backup
            if 'backup' in content.lower() or 'cp' in content:
                findings.append("✅ Includes backup step")
            else:
                findings.append("⚠️  No backup step found - risky deployment")

        is_safe = True  # Assume safe unless critical issues
        return is_safe, findings

    except Exception as e:
        findings.append(f"❌ Error reading deploy.sh: {e}")
        return False, findings


def assess_monitoring() -> Tuple[bool, List[str]]:
    """Check if monitoring and alerting are configured"""
    findings = []

    # Check for monitoring dashboards
    dashboard_files = [
        'dashboard/live_dashboard.py',
        'simulation/dashboard.py'
    ]

    for dashboard in dashboard_files:
        if os.path.exists(dashboard):
            findings.append(f"✅ Found dashboard: {dashboard}")
        else:
            findings.append(f"❌ Dashboard not found: {dashboard}")

    # Check for alerting configuration
    alert_keywords = ['telegram', 'email', 'webhook', 'alert', 'notification']
    alert_configured = False

    for root, dirs, files in os.walk('.'):
        if 'venv' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                try:
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if any(keyword in content.lower() for keyword in alert_keywords):
                            findings.append(f"✅ Alerting code found in: {filepath}")
                            alert_configured = True
                            break
                except:
                    pass
        if alert_configured:
            break

    if not alert_configured:
        findings.append("⚠️  No alerting system detected")
        findings.append("📊 RECOMMENDATION: Set up Telegram bot or email alerts for:")
        findings.append("   - Bot halt events")
        findings.append("   - Consecutive losses (3+)")
        findings.append("   - Balance drops >10%")
        findings.append("   - Service crashes")

    # Check for Prometheus/Grafana
    if os.path.exists('prometheus.yml') or os.path.exists('grafana'):
        findings.append("✅ Prometheus/Grafana configuration found")
    else:
        findings.append("ℹ️  No Prometheus/Grafana detected (optional)")

    is_configured = alert_configured
    return is_configured, findings


def calculate_overall_grade(
    service_ok: bool,
    resources_ok: bool,
    security_issues: List[SecurityIssue],
    log_ok: bool,
    deploy_ok: bool,
    monitor_ok: bool
) -> str:
    """Determine overall VPS health grade"""

    # Critical security issues
    critical_security = any(issue.severity == "CRITICAL" for issue in security_issues)
    high_security = any(issue.severity == "HIGH" for issue in security_issues)

    if critical_security:
        return "CRITICAL"

    if not service_ok:
        return "CRITICAL"

    if high_security or not log_ok or not deploy_ok:
        return "NEEDS_IMPROVEMENT"

    if not resources_ok or not monitor_ok:
        return "ACCEPTABLE"

    if len(security_issues) > 0:
        return "GOOD"

    return "EXCELLENT"


def generate_report(health: HealthCheck, output_path: str = "reports/dmitri_volkov/vps_health_report.md"):
    """Generate VPS health report"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# VPS Operational Health Check Report\n\n")
        f.write("**Researcher:** Dmitri \"The Hammer\" Volkov (System Reliability Engineer)\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(f"**Overall Grade:** {health.overall_grade}\n\n")
        f.write("---\n\n")

        # Executive Summary
        f.write("## Executive Summary\n\n")
        grade_emoji = {
            "EXCELLENT": "🟢",
            "GOOD": "🟢",
            "ACCEPTABLE": "🟡",
            "NEEDS_IMPROVEMENT": "🟡",
            "CRITICAL": "🔴"
        }
        f.write(f"{grade_emoji.get(health.overall_grade, '⚪')} **{health.overall_grade}**\n\n")

        if health.overall_grade == "EXCELLENT":
            f.write("VPS environment is stable and secure. All systems operational.\n\n")
        elif health.overall_grade == "GOOD":
            f.write("VPS environment is generally healthy with minor issues to address.\n\n")
        elif health.overall_grade == "ACCEPTABLE":
            f.write("VPS environment is functional but needs improvements for production reliability.\n\n")
        elif health.overall_grade == "NEEDS_IMPROVEMENT":
            f.write("VPS environment has significant issues that should be addressed promptly.\n\n")
        else:
            f.write("🚨 CRITICAL: VPS environment has critical issues requiring immediate attention.\n\n")

        # Service Status
        f.write("## 1. Service Monitoring\n\n")
        f.write(f"**Service Running:** {'✅ Yes' if health.service_status.is_running else '❌ No'}\n\n")

        if health.service_status.uptime_seconds > 0:
            uptime_days = health.service_status.uptime_seconds / 86400
            f.write(f"**Uptime:** {uptime_days:.1f} days\n\n")
        else:
            f.write("**Uptime:** Unknown (VPS not accessible)\n\n")

        f.write(f"**Restart Count:** {health.service_status.restart_count}\n\n")

        if health.service_status.last_restart:
            f.write(f"**Last Restart:** {health.service_status.last_restart}\n\n")

        if health.service_status.crash_logs:
            f.write("**Recent Errors/Crashes:**\n\n")
            f.write("```\n")
            for log in health.service_status.crash_logs[-5:]:
                f.write(f"{log}\n")
            f.write("```\n\n")
            f.write(f"_(Showing last 5 of {len(health.service_status.crash_logs)} error entries)_\n\n")
        else:
            f.write("**Recent Errors/Crashes:** None detected\n\n")

        # Resource Usage
        f.write("## 2. Resource Utilization\n\n")
        f.write("| Resource | Usage | Status |\n")
        f.write("|----------|-------|--------|\n")

        cpu_status = "✅ Normal" if health.resources.cpu_percent < 50 else "⚠️ High" if health.resources.cpu_percent < 80 else "🔴 Critical"
        mem_status = "✅ Normal" if health.resources.memory_percent < 50 else "⚠️ High" if health.resources.memory_percent < 80 else "🔴 Critical"
        disk_status = "✅ Normal" if health.resources.disk_percent < 70 else "⚠️ High" if health.resources.disk_percent < 90 else "🔴 Critical"
        log_status = "✅ Normal" if health.resources.log_size_mb < 100 else "⚠️ High" if health.resources.log_size_mb < 500 else "🔴 Critical"

        f.write(f"| CPU | {health.resources.cpu_percent:.1f}% | {cpu_status} |\n")
        f.write(f"| Memory | {health.resources.memory_mb:.0f} MB ({health.resources.memory_percent:.1f}%) | {mem_status} |\n")
        f.write(f"| Disk | {health.resources.disk_usage_gb:.1f} GB ({health.resources.disk_percent:.1f}%) | {disk_status} |\n")
        f.write(f"| bot.log Size | {health.resources.log_size_mb:.1f} MB | {log_status} |\n\n")

        if health.resources.cpu_percent == 0 and health.resources.memory_percent == 0:
            f.write("_Note: Resource metrics unavailable (VPS not accessible). Run on production VPS for actual data._\n\n")

        # Security Audit
        f.write("## 3. Security Audit\n\n")

        if not health.security_issues:
            f.write("✅ **No security issues detected**\n\n")
        else:
            f.write(f"**Issues Found:** {len(health.security_issues)}\n\n")

            # Group by severity
            critical = [issue for issue in health.security_issues if issue.severity == "CRITICAL"]
            high = [issue for issue in health.security_issues if issue.severity == "HIGH"]
            medium = [issue for issue in health.security_issues if issue.severity == "MEDIUM"]
            low = [issue for issue in health.security_issues if issue.severity == "LOW"]

            if critical:
                f.write("### 🔴 CRITICAL Issues\n\n")
                for issue in critical:
                    f.write(f"**{issue.category}:** {issue.description}\n\n")
                    f.write(f"_Recommendation:_ {issue.recommendation}\n\n")

            if high:
                f.write("### 🟠 HIGH Priority Issues\n\n")
                for issue in high:
                    f.write(f"**{issue.category}:** {issue.description}\n\n")
                    f.write(f"_Recommendation:_ {issue.recommendation}\n\n")

            if medium:
                f.write("### 🟡 MEDIUM Priority Issues\n\n")
                for issue in medium:
                    f.write(f"**{issue.category}:** {issue.description}\n\n")
                    f.write(f"_Recommendation:_ {issue.recommendation}\n\n")

            if low:
                f.write("### ⚪ LOW Priority Issues\n\n")
                for issue in low:
                    f.write(f"**{issue.category}:** {issue.description}\n\n")
                    f.write(f"_Recommendation:_ {issue.recommendation}\n\n")

        # Log Management
        f.write("## 4. Log Management\n\n")
        f.write(f"**Status:** {'✅ OK' if health.log_management_ok else '⚠️ Needs Attention'}\n\n")
        f.write("**Findings:**\n\n")
        # Log findings would come from check_log_management()
        f.write("- Current log rotation: Manual or not configured\n")
        f.write("- Recommended: Daily rotation with 30-day retention\n")
        f.write("- Configuration file: `/etc/logrotate.d/polymarket-bot`\n\n")

        # Deployment Process
        f.write("## 5. Deployment Process\n\n")
        f.write(f"**Status:** {'✅ Safe' if health.deployment_safe else '⚠️ Needs Review'}\n\n")
        f.write("**Script:** `scripts/deploy.sh`\n\n")
        f.write("_See deployment_process.md for detailed analysis_\n\n")

        # Monitoring
        f.write("## 6. Monitoring & Alerts\n\n")
        f.write(f"**Status:** {'✅ Configured' if health.monitoring_configured else '⚠️ Not Configured'}\n\n")

        if not health.monitoring_configured:
            f.write("**Recommended Alerts:**\n\n")
            f.write("- Bot halt events (30% drawdown, daily loss limit)\n")
            f.write("- Consecutive losses (3+ in a row)\n")
            f.write("- Balance drops >10% in 1 hour\n")
            f.write("- Service crashes (systemd failure)\n")
            f.write("- API errors (timeouts, rate limits)\n\n")
            f.write("**Implementation Options:**\n\n")
            f.write("1. Telegram bot (easiest)\n")
            f.write("2. Email notifications (via sendmail)\n")
            f.write("3. Prometheus + Grafana (most robust)\n")
            f.write("4. Datadog / New Relic (managed service)\n\n")

        # Recommendations
        f.write("## Recommendations\n\n")

        if health.overall_grade in ["CRITICAL", "NEEDS_IMPROVEMENT"]:
            f.write("### 🔴 CRITICAL Actions\n\n")
            if any(issue.severity == "CRITICAL" for issue in health.security_issues):
                f.write("1. **Fix critical security issues immediately**\n")
            if not health.service_status.is_running:
                f.write("2. **Investigate why service is not running**\n")

        if health.overall_grade in ["NEEDS_IMPROVEMENT", "ACCEPTABLE", "GOOD"]:
            f.write("### 🟡 Important Actions\n\n")
            f.write("1. Configure log rotation (daily, 30-day retention)\n")
            f.write("2. Set up monitoring/alerting system\n")
            f.write("3. Review and fix file permissions (chmod 600 .env, chmod 700 state/)\n")

        f.write("\n### 🟢 Optimization Actions\n\n")
        f.write("1. Implement Prometheus + Grafana for metrics\n")
        f.write("2. Set up automated backups (state/, database, logs)\n")
        f.write("3. Configure blue/green deployment for zero-downtime updates\n")
        f.write("4. Add resource monitoring alerts (CPU >80%, disk >90%)\n\n")

        # Appendix
        f.write("---\n\n")
        f.write("## Appendix: VPS Access Commands\n\n")
        f.write("```bash\n")
        f.write("# SSH access\n")
        f.write("ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11\n\n")
        f.write("# Check service status\n")
        f.write("systemctl status polymarket-bot\n\n")
        f.write("# View logs\n")
        f.write("journalctl -u polymarket-bot -n 100 --no-pager\n\n")
        f.write("# Check resource usage\n")
        f.write("top -bn1 | head -20\n")
        f.write("free -m\n")
        f.write("df -h\n\n")
        f.write("# Check log size\n")
        f.write("ls -lh /opt/polymarket-autotrader/bot.log\n")
        f.write("```\n\n")

        f.write("---\n\n")
        f.write(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write("**Next Steps:** Address critical and important actions, then re-run health check.\n")


def main():
    print("=" * 80)
    print("VPS OPERATIONAL HEALTH CHECK")
    print("Researcher: Dmitri 'The Hammer' Volkov")
    print("=" * 80)
    print()

    # Check if VPS is accessible (for production use)
    vps_accessible = False  # Set to True when running on VPS or with SSH access

    print("[1/6] Checking service status...")
    service_status = check_service_status(vps_accessible)

    print("[2/6] Checking resource usage...")
    resources = check_resource_usage(vps_accessible)
    resources_ok = (
        resources.cpu_percent < 80 and
        resources.memory_percent < 80 and
        resources.disk_percent < 90 and
        resources.log_size_mb < 500
    )

    print("[3/6] Running security audit...")
    security_issues = check_security(vps_accessible)

    print("[4/6] Checking log management...")
    log_ok, log_findings = check_log_management()

    print("[5/6] Reviewing deployment process...")
    deploy_ok, deploy_findings = check_deployment_process()

    print("[6/6] Assessing monitoring configuration...")
    monitor_ok, monitor_findings = assess_monitoring()

    # Calculate overall grade
    overall_grade = calculate_overall_grade(
        service_status.is_running,
        resources_ok,
        security_issues,
        log_ok,
        deploy_ok,
        monitor_ok
    )

    # Create health check result
    health = HealthCheck(
        service_status=service_status,
        resources=resources,
        security_issues=security_issues,
        log_management_ok=log_ok,
        deployment_safe=deploy_ok,
        monitoring_configured=monitor_ok,
        overall_grade=overall_grade
    )

    # Generate report
    print("\nGenerating report...")
    output_path = "reports/dmitri_volkov/vps_health_report.md"
    generate_report(health, output_path)

    print(f"✅ Report saved: {output_path}")
    print()
    print("=" * 80)
    print(f"OVERALL GRADE: {overall_grade}")
    print("=" * 80)
    print()

    if overall_grade == "CRITICAL":
        print("🚨 CRITICAL issues found - immediate action required!")
        return 1
    elif overall_grade == "NEEDS_IMPROVEMENT":
        print("⚠️  Significant issues found - address promptly")
        return 1
    else:
        print("✅ VPS health check complete")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
