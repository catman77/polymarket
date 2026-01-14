# Deploy Shadow Trading System to VPS

## Quick Deploy (Copy-Paste Commands)

SSH into your VPS and run these commands:

```bash
# 1. Navigate to bot directory
cd /opt/polymarket-autotrader

# 2. Pull latest code (includes shadow trading system)
git pull origin main

# 3. Restart the bot to load new code
systemctl restart polymarket-bot

# 4. Wait for initialization
sleep 10

# 5. Check that shadow trading is enabled
journalctl -u polymarket-bot -n 50 --no-pager | grep -E "Shadow Trading|strategies running"
```

You should see output like:
```
📊 Shadow Trading: 5 strategies running
  • conservative
  • aggressive
  • contrarian_focused
  • momentum_focused
  • no_regime_adjustment
```

## Verify It's Working

After the bot has been running for a bit:

```bash
# Check if database exists
ls -lh simulation/trade_journal.db

# View live dashboard
python3 simulation/dashboard.py

# Quick performance check
python3 simulation/analyze.py compare
```

## Monitor Shadow Trading

### Live Dashboard (Auto-refresh)
```bash
python3 simulation/dashboard.py
# Refreshes every 5 seconds
# Press Ctrl+C to exit
```

### CLI Analysis
```bash
# Compare all strategies
python3 simulation/analyze.py compare

# View specific strategy
python3 simulation/analyze.py details --strategy contrarian_focused

# Recent decisions
python3 simulation/analyze.py decisions --limit 50
```

### Export Data
```bash
# Export performance to CSV
python3 simulation/export.py performance -o results.csv

# Export all trades
python3 simulation/export.py trades -o trades.csv
```

### Check Bot Logs
```bash
# Live logs
journalctl -u polymarket-bot -f

# Last 100 lines
journalctl -u polymarket-bot -n 100

# Filter for shadow trading
journalctl -u polymarket-bot -n 200 | grep -E "Shadow|TRADE|WIN|LOSS"
```

## Disable Shadow Trading (If Needed)

Edit the config file:
```bash
nano /opt/polymarket-autotrader/config/agent_config.py
```

Change:
```python
ENABLE_SHADOW_TRADING = False  # Was True
```

Then restart:
```bash
systemctl restart polymarket-bot
```

## Database Location

Shadow trading database: `/opt/polymarket-autotrader/simulation/trade_journal.db`

You can query it directly:
```bash
sqlite3 simulation/trade_journal.db

# Example queries:
SELECT strategy, total_trades, win_rate, total_pnl FROM performance ORDER BY total_pnl DESC;
SELECT * FROM strategies;
SELECT COUNT(*) FROM decisions;
```

## Expected Performance

After 20-30 trades, you should be able to see:
- Which strategy has the best ROI
- Which strategy has the best win rate
- How your current strategy compares to alternatives
- Whether higher/lower thresholds perform better

## Troubleshooting

**Database doesn't exist:**
- Bot needs to be restarted with new code
- Check that git pull worked: `git log -1 --oneline` should show "Add shadow trading system"

**No shadow trading logs:**
- Check config: `grep ENABLE_SHADOW_TRADING config/agent_config.py`
- Should show: `ENABLE_SHADOW_TRADING = True`

**Bot not starting:**
- Check logs: `journalctl -u polymarket-bot -n 50`
- Check status: `systemctl status polymarket-bot`

## What Shadow Trading Does

- Runs 5 alternative strategies in parallel with your live bot
- Each strategy starts with virtual $100 balance
- All strategies see the same market data at the same time
- Makes virtual trades (no real money at risk)
- Tracks wins/losses and calculates performance metrics
- Logs everything to SQLite database for analysis
- Zero impact on live trading (< 5% CPU overhead)

After enough trades, you can identify the best-performing strategy and switch your live bot to use those parameters!
