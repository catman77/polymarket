Adjust risk management settings in the bot configuration.

Common adjustments:
- Position sizing (MAX_POSITION_USD, POSITION_TIERS)
- Risk limits (MAX_DRAWDOWN_PCT, DAILY_LOSS_LIMIT_USD)
- Strategy thresholds (EARLY_MAX_ENTRY, CONTRARIAN_MAX_ENTRY)
- Correlation limits (MAX_SAME_DIRECTION_POSITIONS)

Steps:
1. Ask user what setting they want to adjust
2. Show current value from bot/momentum_bot_v12.py
3. Explain impact of the change
4. Make the adjustment using Edit tool
5. Commit the change with descriptive message
6. Push to GitHub
7. Provide deploy command to update VPS
8. Warn user to monitor bot closely after risk changes
