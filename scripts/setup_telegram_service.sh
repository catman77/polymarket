#!/bin/bash
# Setup Telegram Bot as systemd service

set -e

echo "========================================="
echo "Setting up Telegram Bot Service"
echo "========================================="

# Stop existing service if running
if systemctl is-active --quiet telegram-bot; then
    echo "Stopping existing telegram-bot service..."
    systemctl stop telegram-bot
fi

# Copy service file
echo "Installing service file..."
cp /opt/polymarket-autotrader/scripts/telegram-bot.service /etc/systemd/system/

# Create logs directory if it doesn't exist
mkdir -p /opt/polymarket-autotrader/logs

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "Enabling telegram-bot service..."
systemctl enable telegram-bot

# Start service
echo "Starting telegram-bot service..."
systemctl start telegram-bot

# Check status
echo ""
echo "Service status:"
systemctl status telegram-bot --no-pager

echo ""
echo "========================================="
echo "Telegram Bot Service Setup Complete!"
echo "========================================="
echo ""
echo "Useful commands:"
echo "  systemctl status telegram-bot    - Check status"
echo "  systemctl restart telegram-bot   - Restart bot"
echo "  systemctl stop telegram-bot      - Stop bot"
echo "  tail -f logs/telegram_bot.log    - View logs"
echo ""
