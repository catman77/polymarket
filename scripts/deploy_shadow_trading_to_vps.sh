#!/bin/bash
# Deploy shadow trading system to VPS and restart bot

set -e

VPS_IP="216.238.85.11"
VPS_USER="root"
VPS_PATH="/opt/polymarket-autotrader"

echo "========================================"
echo "Deploying Shadow Trading to VPS"
echo "========================================"
echo ""

# 1. Commit and push changes
echo "1. Committing and pushing changes..."
git add -A
git commit -m "Add shadow trading system for strategy comparison" || echo "   ℹ️  Nothing to commit"
git push origin main
echo "   ✅ Changes pushed to GitHub"

# 2. SSH to VPS and update
echo ""
echo "2. Connecting to VPS and updating..."
ssh -o ConnectTimeout=10 "$VPS_USER@$VPS_IP" << 'ENDSSH'
set -e

cd /opt/polymarket-autotrader

echo "   📥 Pulling latest code from GitHub..."
git pull origin main

echo "   🔄 Restarting bot service..."
systemctl restart polymarket-bot

echo "   ⏳ Waiting for initialization (10 seconds)..."
sleep 10

echo ""
echo "   📊 Checking bot status..."
systemctl status polymarket-bot --no-pager | head -15

echo ""
echo "   📋 Last 30 lines of log:"
echo "   ----------------------------------------"
journalctl -u polymarket-bot -n 30 --no-pager | grep -E "Agent System|Shadow Trading|strategies running|ENABLED" || journalctl -u polymarket-bot -n 30 --no-pager
echo "   ----------------------------------------"

ENDSSH

echo ""
echo "========================================"
echo "✅ Deployment Complete!"
echo "========================================"
echo ""
echo "Monitor shadow trading with:"
echo "  ssh root@$VPS_IP"
echo "  cd /opt/polymarket-autotrader"
echo "  python3 simulation/dashboard.py"
echo ""
echo "Or view logs:"
echo "  ssh root@$VPS_IP 'journalctl -u polymarket-bot -f'"
echo ""
