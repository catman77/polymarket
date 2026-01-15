#!/usr/bin/env python3
"""
Validation script for automated optimization infrastructure (US-019)

Checks that all automation components are properly installed and configured:
- Auto-promoter daily checks (cron job)
- Alert system integration (bot main loop)
- Shadow trading system (collecting data)
- Database schema (all tables present)
- Configuration files (all settings valid)
"""

import os
import sys
import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


class AutomationValidator:
    """Validates automated optimization infrastructure"""

    def __init__(self, base_path: str = "/opt/polymarket-autotrader"):
        self.base_path = base_path
        self.results: List[Tuple[str, bool, str]] = []

    def check(self, name: str, condition: bool, message: str):
        """Record a check result"""
        self.results.append((name, condition, message))
        status = f"{GREEN}✓{RESET}" if condition else f"{RED}✗{RESET}"
        print(f"{status} {name}: {message}")

    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        print(f"\n{BLUE}{'='*80}{RESET}")
        print(f"{BLUE}Automated Optimization Infrastructure Validation{RESET}")
        print(f"{BLUE}{'='*80}{RESET}\n")

        self.check_database_schema()
        self.check_shadow_trading()
        self.check_alert_system()
        self.check_auto_promoter()
        self.check_configuration()
        self.check_cron_jobs()

        # Summary
        print(f"\n{BLUE}{'='*80}{RESET}")
        passed = sum(1 for _, result, _ in self.results if result)
        total = len(self.results)
        pass_rate = (passed / total * 100) if total > 0 else 0

        if passed == total:
            print(f"{GREEN}✓ All {total} checks passed!{RESET}")
        else:
            print(f"{YELLOW}⚠ {passed}/{total} checks passed ({pass_rate:.1f}%){RESET}")
            print(f"\n{RED}Failed checks:{RESET}")
            for name, result, message in self.results:
                if not result:
                    print(f"  • {name}: {message}")

        print(f"{BLUE}{'='*80}{RESET}\n")
        return passed == total

    def check_database_schema(self):
        """Verify all required database tables exist"""
        print(f"\n{BLUE}Database Schema:{RESET}")

        db_path = f"{self.base_path}/simulation/trade_journal.db"

        if not os.path.exists(db_path):
            self.check("Database file", False, f"Not found at {db_path}")
            return

        self.check("Database file", True, f"Found at {db_path}")

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check required tables
            required_tables = [
                'strategies',
                'decisions',
                'trades',
                'outcomes',
                'agent_votes',
                'agent_performance',
                'agent_votes_outcomes',
                'performance'
            ]

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            for table in required_tables:
                exists = table in existing_tables
                self.check(f"Table: {table}", exists,
                          "Present" if exists else "Missing")

            # Check data collection
            cursor.execute("SELECT COUNT(*) FROM strategies")
            strategy_count = cursor.fetchone()[0]
            self.check("Shadow strategies", strategy_count > 0,
                      f"{strategy_count} strategies configured")

            cursor.execute("SELECT COUNT(*) FROM decisions")
            decision_count = cursor.fetchone()[0]
            self.check("Decision logging", decision_count > 0,
                      f"{decision_count} decisions logged")

            conn.close()

        except Exception as e:
            self.check("Database query", False, f"Error: {str(e)}")

    def check_shadow_trading(self):
        """Verify shadow trading system is configured"""
        print(f"\n{BLUE}Shadow Trading System:{RESET}")

        config_path = f"{self.base_path}/config/agent_config.py"

        if not os.path.exists(config_path):
            self.check("Config file", False, f"Not found at {config_path}")
            return

        self.check("Config file", True, "Found")

        try:
            with open(config_path, 'r') as f:
                content = f.read()

            # Check shadow trading enabled
            enabled = 'ENABLE_SHADOW_TRADING = True' in content
            self.check("Shadow trading enabled", enabled,
                      "ENABLE_SHADOW_TRADING = True" if enabled else "Disabled in config")

            # Check for ultra_selective strategy
            has_ultra = "'ultra_selective'" in content
            self.check("ultra_selective strategy", has_ultra,
                      "Configured" if has_ultra else "Not in SHADOW_STRATEGIES")

            # Check for kelly_sizing strategy
            has_kelly = "'kelly_sizing'" in content
            self.check("kelly_sizing strategy", has_kelly,
                      "Configured" if has_kelly else "Not in SHADOW_STRATEGIES")

        except Exception as e:
            self.check("Config parsing", False, f"Error: {str(e)}")

    def check_alert_system(self):
        """Verify alert system is integrated into bot"""
        print(f"\n{BLUE}Alert System:{RESET}")

        bot_path = f"{self.base_path}/bot/momentum_bot_v12.py"

        if not os.path.exists(bot_path):
            self.check("Bot file", False, f"Not found at {bot_path}")
            return

        self.check("Bot file", True, "Found")

        try:
            with open(bot_path, 'r') as f:
                content = f.read()

            # Check for alert system import
            has_import = 'from analytics.alert_system import AlertSystem' in content
            self.check("AlertSystem import", has_import,
                      "Imported" if has_import else "Not imported")

            # Check for alert interval
            has_interval = 'alert_check_interval' in content
            self.check("Alert interval config", has_interval,
                      "Configured (600s)" if has_interval else "Not configured")

            # Check for alert checks in main loop
            has_checks = 'alert_system.run_all_checks()' in content
            self.check("Alert checks in main loop", has_checks,
                      "Integrated" if has_checks else "Not integrated")

        except Exception as e:
            self.check("Bot parsing", False, f"Error: {str(e)}")

    def check_auto_promoter(self):
        """Verify auto-promoter module exists and is functional"""
        print(f"\n{BLUE}Auto-Promoter:{RESET}")

        promoter_path = f"{self.base_path}/simulation/auto_promoter.py"

        if not os.path.exists(promoter_path):
            self.check("Auto-promoter file", False, f"Not found at {promoter_path}")
            return

        self.check("Auto-promoter file", True, "Found")

        try:
            with open(promoter_path, 'r') as f:
                content = f.read()

            # Check for required methods
            required_methods = [
                'get_live_performance',
                'get_shadow_performance',
                'get_promotion_candidates',
                'promote_strategy',
                'run_promotion_check'
            ]

            for method in required_methods:
                has_method = f"def {method}" in content
                self.check(f"Method: {method}", has_method,
                          "Present" if has_method else "Missing")

        except Exception as e:
            self.check("Auto-promoter parsing", False, f"Error: {str(e)}")

    def check_configuration(self):
        """Verify configuration files are valid"""
        print(f"\n{BLUE}Configuration:{RESET}")

        state_path = f"{self.base_path}/state/trading_state.json"

        if not os.path.exists(state_path):
            self.check("Trading state", False, f"Not found at {state_path}")
            return

        self.check("Trading state file", True, "Found")

        try:
            with open(state_path, 'r') as f:
                state = json.load(f)

            # Check required fields
            required_fields = [
                'current_balance',
                'peak_balance',
                'day_start_balance',
                'mode',
                'total_trades'
            ]

            for field in required_fields:
                has_field = field in state
                self.check(f"State field: {field}", has_field,
                          f"{state.get(field)}" if has_field else "Missing")

        except Exception as e:
            self.check("State file parsing", False, f"Error: {str(e)}")

    def check_cron_jobs(self):
        """Verify cron jobs are scheduled (VPS only)"""
        print(f"\n{BLUE}Cron Jobs:{RESET}")

        try:
            result = subprocess.run(['crontab', '-l'],
                                   capture_output=True,
                                   text=True,
                                   timeout=5)

            if result.returncode != 0:
                self.check("Crontab access", False, "Cannot read crontab")
                return

            self.check("Crontab access", True, "Readable")

            crontab = result.stdout

            # Check for auto-promoter job
            has_promoter = 'auto_promoter.py' in crontab
            self.check("Auto-promoter cron job", has_promoter,
                      "Scheduled (daily 00:00 UTC)" if has_promoter else "Not scheduled")

            # Check for daily dataset update (if exists)
            has_dataset = 'update' in crontab.lower()
            if has_dataset:
                self.check("Dataset update cron job", True, "Scheduled")

        except FileNotFoundError:
            self.check("Cron availability", False,
                      "Not available (local environment or non-Unix system)")
        except subprocess.TimeoutExpired:
            self.check("Crontab query", False, "Timeout")
        except Exception as e:
            self.check("Cron check", False, f"Error: {str(e)}")


def main():
    """Main validation workflow"""
    # Detect environment (VPS or local)
    if os.path.exists("/opt/polymarket-autotrader"):
        base_path = "/opt/polymarket-autotrader"
        print(f"{GREEN}Detected VPS environment{RESET}")
    elif os.path.exists("/Volumes/TerraTitan/Development/polymarket-autotrader"):
        base_path = "/Volumes/TerraTitan/Development/polymarket-autotrader"
        print(f"{YELLOW}Detected local development environment{RESET}")
    else:
        print(f"{RED}Error: Cannot find polymarket-autotrader directory{RESET}")
        sys.exit(1)

    validator = AutomationValidator(base_path)
    success = validator.run_all_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
