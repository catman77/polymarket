Emergency stop the trading bot immediately.

Use when:
- Bot is making bad trades repeatedly
- Market conditions have changed dramatically
- Need to review strategy before continuing
- Wallet security concern

Steps:
1. SSH to VPS: root@216.238.85.11
2. Stop the bot service: systemctl stop polymarket-bot
3. Verify bot stopped: systemctl status polymarket-bot
4. Check for any pending orders in bot.log
5. Show current balance and open positions
6. Create HALT file as backup: touch /opt/polymarket-autotrader/HALT
7. Explain that bot won't restart until HALT file is removed
8. Provide restart instructions when ready:
   - Remove HALT file: rm /opt/polymarket-autotrader/HALT
   - Start bot: systemctl start polymarket-bot
