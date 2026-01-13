Deploy the latest changes from GitHub to the VPS.

Steps:
1. Verify current local branch is main and pushed to GitHub
2. SSH to VPS: root@216.238.85.11
3. Navigate to /opt/polymarket-autotrader
4. Run ./scripts/deploy.sh
5. Verify bot restarted successfully
6. Show recent logs to confirm bot is trading
7. Report any errors or issues
