#!/bin/bash
#
# Deploy Agent System to VPS
#
# Usage:
#   ./scripts/deploy_agents.sh [log_only|moderate|conservative|aggressive]
#
# Modes:
#   log_only      - Log decisions but don't trade (default)
#   moderate      - Balanced trading (recommended)
#   conservative  - Selective, high confidence trades
#   aggressive    - More trades, lower confidence

set -e

MODE="${1:-log_only}"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           DEPLOYING AGENT SYSTEM TO VPS                     ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Mode: $MODE"
echo "║  Server: 216.238.85.11"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Validate mode
case "$MODE" in
    log_only|moderate|conservative|aggressive)
        echo "✅ Valid mode: $MODE"
        ;;
    *)
        echo "❌ Invalid mode: $MODE"
        echo "Valid modes: log_only, moderate, conservative, aggressive"
        exit 1
        ;;
esac

# Check SSH connection
echo ""
echo "🔍 Checking SSH connection..."
if ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 "echo '✅ Connected'" 2>/dev/null; then
    echo "✅ SSH connection successful"
else
    echo "❌ SSH connection failed"
    exit 1
fi

# Commit and push changes
echo ""
echo "📝 Committing changes..."
git add .
git commit -m "Deploy agent system in $MODE mode" || echo "No changes to commit"

echo ""
echo "🚀 Pushing to GitHub..."
git push origin main

# Deploy to VPS
echo ""
echo "📦 Deploying to VPS..."
ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11 << EOF
    set -e
    cd /opt/polymarket-autotrader

    echo ""
    echo "🔄 Pulling latest changes..."
    git pull origin main

    echo ""
    echo "⚙️  Setting agent mode to: $MODE"

    # Update config file to set mode
    cat > config/agent_mode.txt << MODE_EOF
$MODE
MODE_EOF

    echo ""
    echo "🔧 Installing any new dependencies..."
    source venv/bin/activate
    pip install -q requests web3 || true

    echo ""
    echo "🧪 Testing agent system..."
    python3 -c "from bot.agent_wrapper import AgentSystemWrapper; print('✅ Import successful')"

    echo ""
    echo "🔄 Restarting bot service..."
    systemctl restart polymarket-bot

    echo ""
    echo "✅ Deployment complete!"

    sleep 3

    echo ""
    echo "📊 Bot status:"
    systemctl status polymarket-bot --no-pager | head -20

    echo ""
    echo "📝 Recent logs:"
    tail -20 bot.log
EOF

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                 DEPLOYMENT COMPLETE!                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Mode: $MODE"
echo "║  Status: Bot restarted with agent system"
echo "║  "
echo "║  Next steps:"
echo "║  1. Monitor logs: ssh root@216.238.85.11 'tail -f /opt/polymarket-autotrader/bot.log'"
echo "║  2. Watch for agent decisions in logs"
echo "║  3. Validate consensus working correctly"
echo "╚══════════════════════════════════════════════════════════════╝"
