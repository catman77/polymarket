#!/bin/bash
# Restart bot with shadow trading system enabled

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "========================================"
echo "Restarting Bot with Shadow Trading"
echo "========================================"
echo ""

# Stop existing bot
echo "1. Stopping existing bot process..."
if pgrep -f "momentum_bot_v12.py" > /dev/null; then
    pkill -f "momentum_bot_v12.py"
    echo "   ✅ Old bot stopped"
    sleep 2
else
    echo "   ℹ️  No existing bot process found"
fi

# Verify virtual environment exists
echo ""
echo "2. Checking virtual environment..."
if [ ! -d "venv" ]; then
    echo "   ❌ Virtual environment not found!"
    echo "   Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "   ✅ Virtual environment found"
    source venv/bin/activate
fi

# Verify shadow trading config
echo ""
echo "3. Verifying shadow trading configuration..."
if python3 -c "from config import agent_config; exit(0 if agent_config.ENABLE_SHADOW_TRADING else 1)" 2>/dev/null; then
    echo "   ✅ Shadow trading is ENABLED"
    python3 -c "from config import agent_config; print(f'   📊 Running {len(agent_config.SHADOW_STRATEGIES)} strategies: {', '.join(agent_config.SHADOW_STRATEGIES)}')"
else
    echo "   ⚠️  Shadow trading is DISABLED"
    echo "   Edit config/agent_config.py to enable"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start bot in background
echo ""
echo "4. Starting bot with shadow trading..."
nohup python3 bot/momentum_bot_v12.py > logs/bot.log 2>&1 &
BOT_PID=$!

echo "   ✅ Bot started (PID: $BOT_PID)"

# Wait for initialization
echo ""
echo "5. Waiting for initialization..."
sleep 3

# Check if bot is still running
if ps -p $BOT_PID > /dev/null; then
    echo "   ✅ Bot is running"
else
    echo "   ❌ Bot failed to start!"
    echo ""
    echo "Last 20 lines of log:"
    tail -20 logs/bot.log
    exit 1
fi

# Show initialization output
echo ""
echo "6. Checking initialization output..."
echo "----------------------------------------"
tail -30 logs/bot.log | grep -E "Agent System|Shadow Trading|strategies running|ENABLED" || echo "   (Waiting for full initialization...)"
echo "----------------------------------------"

echo ""
echo "========================================"
echo "✅ Bot Successfully Restarted!"
echo "========================================"
echo ""
echo "Monitor with:"
echo "  tail -f logs/bot.log                    # Live logs"
echo "  python3 simulation/dashboard.py         # Shadow trading dashboard"
echo "  python3 simulation/analyze.py compare   # Performance comparison"
echo ""
echo "Stop with:"
echo "  pkill -f momentum_bot_v12.py"
echo ""
