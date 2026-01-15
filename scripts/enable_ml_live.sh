#!/bin/bash
#
# Enable ML Live Trading on VPS
#
# This script modifies the systemd service to run the bot in ML mode.
# ML Random Forest predictions replace agent consensus for live trading.
#
# WARNING: This is a high-risk configuration.
# Only run this after shadow testing validates ML performance.
#

set -e

echo "================================================================================"
echo "🤖 ENABLE ML LIVE TRADING"
echo "================================================================================"
echo ""
echo "⚠️  WARNING: This will replace agent consensus with ML predictions"
echo "   Current balance at risk: Check v12_state/trading_state.json"
echo ""
read -p "Are you sure you want to enable ML live trading? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Creating ML-enabled service file..."

# Backup original service
sudo cp /etc/systemd/system/polymarket-bot.service /etc/systemd/system/polymarket-bot.service.backup

# Create new service file with ML environment variables
sudo tee /etc/systemd/system/polymarket-bot.service > /dev/null <<'EOF'
[Unit]
Description=Polymarket AutoTrader (ML Mode)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/polymarket-autotrader
Environment="PATH=/opt/polymarket-autotrader/venv/bin"
Environment="USE_ML_BOT=true"
Environment="ML_THRESHOLD=0.55"
ExecStart=/opt/polymarket-autotrader/venv/bin/python3 /opt/polymarket-autotrader/bot/momentum_bot_v12.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/polymarket-autotrader/bot.log
StandardError=append:/opt/polymarket-autotrader/bot.log

[Install]
WantedBy=multi-user.target
EOF

echo "✓ Service file updated"
echo ""
echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "✓ Systemd reloaded"
echo ""
echo "Restarting bot service..."
sudo systemctl restart polymarket-bot

echo "✓ Bot restarted in ML mode"
echo ""
echo "Checking service status..."
sudo systemctl status polymarket-bot --no-pager

echo ""
echo "================================================================================"
echo "✅ ML LIVE TRADING ENABLED"
echo "================================================================================"
echo ""
echo "The bot is now using ML Random Forest predictions for live trading."
echo ""
echo "Monitor logs:"
echo "  tail -f /opt/polymarket-autotrader/bot.log | grep -E 'ML Bot|🤖'"
echo ""
echo "Check balance:"
echo "  cat /opt/polymarket-autotrader/v12_state/trading_state.json | jq '.current_balance'"
echo ""
echo "To REVERT to agent mode:"
echo "  sudo cp /etc/systemd/system/polymarket-bot.service.backup /etc/systemd/system/polymarket-bot.service"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl restart polymarket-bot"
echo ""
echo "================================================================================"
