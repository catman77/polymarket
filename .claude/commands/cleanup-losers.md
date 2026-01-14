Clean up worthless losing positions (0% probability) from the account.

These positions clutter the dashboard and can't be redeemed for value.

Steps:
1. SSH to VPS
2. Navigate to /opt/polymarket-autotrader
3. Run: venv/bin/python3 utils/cleanup_losers.py (use venv Python)
4. Show list of worthless positions (curPrice near 0%)
5. Estimate gas cost for cleanup (~$0.10-0.30)
6. Ask user for confirmation before proceeding
7. Execute cleanup if approved
8. Report positions removed and gas spent
