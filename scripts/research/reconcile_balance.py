#!/usr/bin/env python3
"""
Balance Reconciliation Script

Persona: Dr. Kenji Nakamoto (Data Forensics Specialist)
Context: "If starting_balance + sum(pnl) ≠ current_balance, there's a data integrity
         issue or hidden transactions."

Purpose: Verify that the balance in trading_state.json matches the sum of all
         deposits, withdrawals, and trade P&L from the logs.

Acceptance Criteria:
- Extract all deposits, withdrawals, trade P&L from logs
- Calculate: starting_balance + deposits - withdrawals + sum(trade_pnl)
- Compare to current_balance in state file
- Report discrepancy (if any) with % error
- Reconciliation within $1 considered acceptable
"""

import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Transaction:
    """Represents a financial transaction."""
    timestamp: datetime
    type: str  # 'deposit', 'withdrawal', 'trade_win', 'trade_loss'
    amount: float
    description: str


@dataclass
class ReconciliationReport:
    """Balance reconciliation results."""
    starting_balance: float
    total_deposits: float
    total_withdrawals: float
    total_trade_pnl: float
    calculated_balance: float
    actual_balance: float
    discrepancy: float
    discrepancy_pct: float
    transactions: List[Transaction]
    status: str  # 'MATCH', 'MINOR_DISCREPANCY', 'MAJOR_DISCREPANCY'


class BalanceReconciler:
    """Reconciles balance from trade history and state file."""

    def __init__(self, log_file: str, state_file: str):
        self.log_file = log_file
        self.state_file = state_file
        self.transactions: List[Transaction] = []

    def parse_logs(self) -> None:
        """Parse bot.log for all financial transactions."""
        if not os.path.exists(self.log_file):
            print(f"⚠️  Log file not found: {self.log_file}")
            return

        # Patterns to match financial transactions
        trade_win_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?WIN.*?(BTC|ETH|SOL|XRP).*?(Up|Down).*?'
            r'P&L:\s*\$?([+-]?\d+\.?\d*)',
            re.IGNORECASE
        )
        trade_loss_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?LOSS.*?(BTC|ETH|SOL|XRP).*?(Up|Down).*?'
            r'P&L:\s*\$?([+-]?\d+\.?\d*)',
            re.IGNORECASE
        )
        deposit_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?DEPOSIT.*?\$?(\d+\.?\d*)',
            re.IGNORECASE
        )
        withdrawal_pattern = re.compile(
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?WITHDRAWAL.*?\$?(\d+\.?\d*)',
            re.IGNORECASE
        )

        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Check for wins
                    match = trade_win_pattern.search(line)
                    if match:
                        timestamp_str, crypto, direction, pnl_str = match.groups()
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            pnl = float(pnl_str)
                            self.transactions.append(Transaction(
                                timestamp=timestamp,
                                type='trade_win',
                                amount=pnl,
                                description=f"WIN: {crypto} {direction} (${pnl:.2f})"
                            ))
                        except (ValueError, AttributeError):
                            continue

                    # Check for losses
                    match = trade_loss_pattern.search(line)
                    if match:
                        timestamp_str, crypto, direction, pnl_str = match.groups()
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            pnl = float(pnl_str)
                            # Losses are negative
                            if pnl > 0:
                                pnl = -pnl
                            self.transactions.append(Transaction(
                                timestamp=timestamp,
                                type='trade_loss',
                                amount=pnl,
                                description=f"LOSS: {crypto} {direction} (${pnl:.2f})"
                            ))
                        except (ValueError, AttributeError):
                            continue

                    # Check for deposits
                    match = deposit_pattern.search(line)
                    if match:
                        timestamp_str, amount_str = match.groups()
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            amount = float(amount_str)
                            self.transactions.append(Transaction(
                                timestamp=timestamp,
                                type='deposit',
                                amount=amount,
                                description=f"DEPOSIT: ${amount:.2f}"
                            ))
                        except (ValueError, AttributeError):
                            continue

                    # Check for withdrawals
                    match = withdrawal_pattern.search(line)
                    if match:
                        timestamp_str, amount_str = match.groups()
                        try:
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            amount = float(amount_str)
                            self.transactions.append(Transaction(
                                timestamp=timestamp,
                                type='withdrawal',
                                amount=amount,
                                description=f"WITHDRAWAL: ${amount:.2f}"
                            ))
                        except (ValueError, AttributeError):
                            continue

        except Exception as e:
            print(f"⚠️  Error parsing log file: {e}")

        # Sort transactions by timestamp
        self.transactions.sort(key=lambda t: t.timestamp)

    def get_state_balance(self) -> Optional[float]:
        """Get current balance from trading_state.json."""
        if not os.path.exists(self.state_file):
            print(f"⚠️  State file not found: {self.state_file}")
            return None

        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return float(state.get('current_balance', 0.0))
        except Exception as e:
            print(f"⚠️  Error reading state file: {e}")
            return None

    def get_starting_balance(self) -> float:
        """
        Determine starting balance.

        If state file has day_start_balance or initial balance fields, use those.
        Otherwise, assume the first deposit is the starting balance.
        If no deposits found, use a default (will be noted in report).
        """
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                # Try to get day_start_balance or peak_balance as proxy
                day_start = state.get('day_start_balance')
                if day_start is not None:
                    return float(day_start)
        except Exception:
            pass

        # Check for first deposit in transactions
        deposits = [t for t in self.transactions if t.type == 'deposit']
        if deposits:
            return deposits[0].amount

        # Default: assume $0 starting (will show full discrepancy)
        return 0.0

    def reconcile(self) -> ReconciliationReport:
        """Perform balance reconciliation."""
        self.parse_logs()

        starting_balance = self.get_starting_balance()
        actual_balance = self.get_state_balance() or 0.0

        # Calculate totals
        total_deposits = sum(t.amount for t in self.transactions if t.type == 'deposit')
        total_withdrawals = sum(t.amount for t in self.transactions if t.type == 'withdrawal')
        total_trade_pnl = sum(
            t.amount for t in self.transactions
            if t.type in ('trade_win', 'trade_loss')
        )

        # Calculate expected balance
        calculated_balance = starting_balance + total_deposits - total_withdrawals + total_trade_pnl

        # Calculate discrepancy
        discrepancy = actual_balance - calculated_balance
        discrepancy_pct = (abs(discrepancy) / max(actual_balance, 1.0)) * 100 if actual_balance != 0 else 0.0

        # Determine status
        if abs(discrepancy) <= 1.0:
            status = 'MATCH'
        elif abs(discrepancy) <= 10.0:
            status = 'MINOR_DISCREPANCY'
        else:
            status = 'MAJOR_DISCREPANCY'

        return ReconciliationReport(
            starting_balance=starting_balance,
            total_deposits=total_deposits,
            total_withdrawals=total_withdrawals,
            total_trade_pnl=total_trade_pnl,
            calculated_balance=calculated_balance,
            actual_balance=actual_balance,
            discrepancy=discrepancy,
            discrepancy_pct=discrepancy_pct,
            transactions=self.transactions,
            status=status
        )

    def generate_report(self, report: ReconciliationReport, output_file: str) -> None:
        """Generate markdown report."""
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w') as f:
            f.write("# Balance Reconciliation Report\n\n")
            f.write("**Persona:** Dr. Kenji Nakamoto (Data Forensics Specialist)\n\n")
            f.write("**Generated:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n\n")
            f.write("---\n\n")

            # Executive Summary
            f.write("## Executive Summary\n\n")
            if report.status == 'MATCH':
                icon = "✅"
                verdict = "EXCELLENT - Balance reconciles within $1"
            elif report.status == 'MINOR_DISCREPANCY':
                icon = "⚠️"
                verdict = "ACCEPTABLE - Minor discrepancy <$10"
            else:
                icon = "🔴"
                verdict = "CRITICAL - Major discrepancy detected"

            f.write(f"{icon} **Status:** {verdict}\n\n")
            f.write(f"**Discrepancy:** ${report.discrepancy:+.2f} ({report.discrepancy_pct:.2f}% error)\n\n")

            # Balance Calculation
            f.write("## Balance Calculation\n\n")
            f.write("```\n")
            f.write(f"Starting Balance:    ${report.starting_balance:>10.2f}\n")
            f.write(f"+ Deposits:          ${report.total_deposits:>10.2f}\n")
            f.write(f"- Withdrawals:       ${report.total_withdrawals:>10.2f}\n")
            f.write(f"+ Trade P&L:         ${report.total_trade_pnl:>10.2f}\n")
            f.write(f"                     {'=' * 25}\n")
            f.write(f"Calculated Balance:  ${report.calculated_balance:>10.2f}\n")
            f.write(f"Actual Balance:      ${report.actual_balance:>10.2f}\n")
            f.write(f"                     {'=' * 25}\n")
            f.write(f"Discrepancy:         ${report.discrepancy:>10.2f}\n")
            f.write("```\n\n")

            # Transaction Summary
            f.write("## Transaction Summary\n\n")
            f.write(f"- **Total Transactions:** {len(report.transactions)}\n")

            trade_wins = [t for t in report.transactions if t.type == 'trade_win']
            trade_losses = [t for t in report.transactions if t.type == 'trade_loss']
            deposits = [t for t in report.transactions if t.type == 'deposit']
            withdrawals = [t for t in report.transactions if t.type == 'withdrawal']

            f.write(f"- **Trade Wins:** {len(trade_wins)} (${sum(t.amount for t in trade_wins):.2f})\n")
            f.write(f"- **Trade Losses:** {len(trade_losses)} (${sum(t.amount for t in trade_losses):.2f})\n")
            f.write(f"- **Deposits:** {len(deposits)} (${sum(t.amount for t in deposits):.2f})\n")
            f.write(f"- **Withdrawals:** {len(withdrawals)} (${sum(t.amount for t in withdrawals):.2f})\n\n")

            # Discrepancy Analysis
            f.write("## Discrepancy Analysis\n\n")
            if report.status == 'MATCH':
                f.write("**Verdict:** Balance reconciliation SUCCESSFUL ✅\n\n")
                f.write("The calculated balance matches the actual balance within acceptable tolerance ($1). ")
                f.write("This indicates:\n\n")
                f.write("- ✅ All trades are properly logged\n")
                f.write("- ✅ No hidden transactions\n")
                f.write("- ✅ State file is accurate\n")
                f.write("- ✅ Data integrity is intact\n\n")
            elif report.status == 'MINOR_DISCREPANCY':
                f.write("**Verdict:** Minor discrepancy detected ⚠️\n\n")
                f.write(f"Discrepancy of ${abs(report.discrepancy):.2f} is within acceptable range (<$10). ")
                f.write("This could be due to:\n\n")
                f.write("- Rounding errors in fee calculations\n")
                f.write("- Redemption timing differences\n")
                f.write("- Gas fees not logged\n")
                f.write("- Unredeemed position values\n\n")
                f.write("**Recommendation:** Monitor for growth. If discrepancy >$10, investigate further.\n\n")
            else:
                f.write("**Verdict:** CRITICAL discrepancy detected 🔴\n\n")
                f.write(f"Discrepancy of ${abs(report.discrepancy):.2f} ({report.discrepancy_pct:.2f}%) ")
                f.write("indicates a serious data integrity issue. Possible causes:\n\n")
                f.write("- 🔴 Missing trade entries in logs\n")
                f.write("- 🔴 Unreported deposits or withdrawals\n")
                f.write("- 🔴 State file corruption\n")
                f.write("- 🔴 Manual balance adjustments\n")
                f.write("- 🔴 Redemption tracking failures\n\n")
                f.write("**Recommendation:** URGENT - Investigate root cause before proceeding.\n\n")

            # Recent Transactions (last 20)
            f.write("## Recent Transactions (Last 20)\n\n")
            f.write("| Timestamp | Type | Amount | Description |\n")
            f.write("|-----------|------|--------|-------------|\n")

            recent_txns = report.transactions[-20:] if len(report.transactions) > 20 else report.transactions
            for txn in reversed(recent_txns):
                timestamp_str = txn.timestamp.strftime('%Y-%m-%d %H:%M')
                f.write(f"| {timestamp_str} | {txn.type} | ${txn.amount:+.2f} | {txn.description} |\n")

            f.write("\n")

            # Recommendations
            f.write("## Recommendations\n\n")
            if report.status == 'MATCH':
                f.write("1. ✅ **Data Integrity:** Continue current logging practices\n")
                f.write("2. ✅ **Monitoring:** Run reconciliation weekly to catch issues early\n")
                f.write("3. ✅ **Backup:** Ensure state file is backed up regularly\n")
            elif report.status == 'MINOR_DISCREPANCY':
                f.write("1. ⚠️  **Investigation:** Review recent redemptions and gas fees\n")
                f.write("2. ⚠️  **Logging:** Add more detailed transaction logging\n")
                f.write("3. ⚠️  **Monitoring:** Check if discrepancy grows over time\n")
                f.write("4. ⚠️  **State File:** Consider resetting peak_balance to current_balance\n")
            else:
                f.write("1. 🔴 **URGENT:** Stop trading until discrepancy is resolved\n")
                f.write("2. 🔴 **Audit:** Review all transactions on-chain (Polygon)\n")
                f.write("3. 🔴 **State File:** Check for corruption or manual edits\n")
                f.write("4. 🔴 **Logs:** Search for missing WIN/LOSS entries\n")
                f.write("5. 🔴 **Redemption:** Check for unredeemed winning positions\n")

            f.write("\n---\n\n")
            f.write("**Data Sources:**\n")
            f.write(f"- Log File: `{self.log_file}`\n")
            f.write(f"- State File: `{self.state_file}`\n")
            f.write(f"- Transactions Parsed: {len(report.transactions)}\n")


def main():
    """Main execution function."""
    # Default paths
    log_file = os.getenv('BOT_LOG', 'bot.log')
    state_file = os.getenv('STATE_FILE', 'state/trading_state.json')
    output_file = 'reports/kenji_nakamoto/balance_reconciliation.md'

    # Override with command line args if provided
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    if len(sys.argv) > 2:
        state_file = sys.argv[2]

    print("=" * 80)
    print("BALANCE RECONCILIATION ANALYSIS")
    print("=" * 80)
    print(f"📂 Log File: {log_file}")
    print(f"📂 State File: {state_file}")
    print(f"📊 Output: {output_file}")
    print()

    reconciler = BalanceReconciler(log_file, state_file)
    report = reconciler.reconcile()

    print(f"Starting Balance:    ${report.starting_balance:.2f}")
    print(f"Deposits:            ${report.total_deposits:.2f}")
    print(f"Withdrawals:         ${report.total_withdrawals:.2f}")
    print(f"Trade P&L:           ${report.total_trade_pnl:.2f}")
    print(f"Calculated Balance:  ${report.calculated_balance:.2f}")
    print(f"Actual Balance:      ${report.actual_balance:.2f}")
    print(f"Discrepancy:         ${report.discrepancy:+.2f} ({report.discrepancy_pct:.2f}%)")
    print()
    print(f"Status: {report.status}")
    print()

    reconciler.generate_report(report, output_file)
    print(f"✅ Report generated: {output_file}")

    # Exit code based on status
    if report.status == 'MAJOR_DISCREPANCY':
        print("\n🔴 CRITICAL: Major discrepancy detected. Please investigate.")
        sys.exit(1)
    elif report.status == 'MINOR_DISCREPANCY':
        print("\n⚠️  WARNING: Minor discrepancy detected. Monitor for growth.")
        sys.exit(0)
    else:
        print("\n✅ SUCCESS: Balance reconciliation complete.")
        sys.exit(0)


if __name__ == '__main__':
    main()
