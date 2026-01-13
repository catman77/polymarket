# Claude Code Commands

This directory contains slash commands for common tasks when working with the Polymarket AutoTrader bot.

## Available Commands

### Bot Management

- `/check-bot-status` - Check if bot is running, view recent logs and balance
- `/deploy-to-vps` - Deploy latest changes from GitHub to VPS
- `/emergency-stop` - Immediately stop the trading bot
- `/view-dashboard` - Open live monitoring dashboard

### Performance & Analysis

- `/analyze-performance` - Review win rate, P&L, and trading patterns
- `/check-markets` - See what 15-min markets are currently available

### Position Management

- `/redeem-winners` - Manually redeem winning positions
- `/cleanup-losers` - Remove worthless 0% positions from account

### Troubleshooting

- `/fix-drawdown-halt` - Fix false drawdown halt (reset peak_balance)
- `/adjust-risk-settings` - Modify position sizing or risk limits

## Usage

In Claude Code, type the slash command (e.g., `/check-bot-status`) and Claude will execute the steps defined in the command file.

## Adding New Commands

Create a new `.md` file in this directory with:

```markdown
Brief description of what this command does.

Steps:
1. First step
2. Second step
3. etc.
```

The filename (without `.md`) becomes the slash command name.

## Notes

- Commands that interact with VPS require SSH access
- Commands assume SSH key location: `~/.ssh/polymarket_vultr`
- VPS IP: 216.238.85.11
- Bot location on VPS: `/opt/polymarket-autotrader`
