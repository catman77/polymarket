Open the live dashboard to monitor bot activity in real-time.

The dashboard shows:
- Current balance and daily P&L
- Open positions with unrealized P&L
- Win/loss streaks
- Recent trades
- Market opportunities

Steps:
1. Provide the SSH command to run dashboard:
   ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 'cd /opt/polymarket-autotrader && venv/bin/python3 dashboard/live_dashboard.py'

2. Explain dashboard controls:
   - Auto-refreshes every 10 seconds
   - Ctrl+C to exit
   - Shows real-time position values

3. Alternative: Show how to run in persistent screen session:
   screen -S dashboard
   venv/bin/python3 dashboard/live_dashboard.py
   Detach: Ctrl+A then D
   Reattach: screen -r dashboard
