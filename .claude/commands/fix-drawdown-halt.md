Fix the bot when it's HALTED due to false drawdown calculation.

This happens when peak_balance includes old unredeemed position values.

Steps:
1. SSH to VPS and check bot.log for "HALTED: Drawdown" message
2. Read current state from state/trading_state.json
3. Show current_balance vs peak_balance
4. Reset peak_balance to match current_balance using Python script
5. Restart the bot with systemctl restart polymarket-bot
6. Verify bot resumes trading by checking logs
7. Confirm no more HALTED messages
