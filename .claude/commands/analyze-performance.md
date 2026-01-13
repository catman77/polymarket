Analyze the bot's recent trading performance.

Steps:
1. SSH to VPS and read state/trading_state.json
2. Calculate key metrics:
   - Current balance vs day_start_balance (daily P&L)
   - Win rate (total_wins / total_trades)
   - Current mode and consecutive wins/losses
   - Peak balance vs current (drawdown check)
3. Search bot.log for recent ORDER PLACED events
4. Count wins vs losses from recent trades
5. Identify best performing strategy (contrarian, early, late)
6. Report any concerning patterns (loss streaks, mode downgrades)
7. Provide recommendations if performance is poor
