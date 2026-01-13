#!/usr/bin/env python3
"""
Agent Decision Dashboard - Real-time SWAT team analysis viewer

Shows:
- Each agent's vote (Up/Down/Neutral)
- Confidence levels
- Reasoning behind decisions
- Consensus calculations
- Final trading decision vs actual bot action
"""

import sys
import os
import time
import re
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Terminal setup
if 'TERM' not in os.environ:
    os.environ['TERM'] = 'xterm-256color'

def clear_screen():
    """Clear terminal screen."""
    try:
        os.system('clear' if os.name == 'posix' else 'cls')
    except:
        print('\n' * 50)

def get_terminal_size():
    """Get terminal dimensions."""
    try:
        rows, cols = os.popen('stty size', 'r').read().split()
        return int(rows), int(cols)
    except:
        return 40, 120

def parse_agent_decision(log_lines):
    """
    Parse agent decisions from recent log lines.
    
    Looks for patterns like:
    - "🤖 Agents ✓ AGREE: Down @ 78%"
    - "Reason: Down consensus from 3 experts..."
    - Individual agent votes
    """
    decisions = []
    
    for i, line in enumerate(log_lines):
        # Look for agent decision summary
        if '🤖 Agents' in line:
            decision = {
                'timestamp': extract_timestamp(line),
                'crypto': extract_crypto(log_lines, i),
                'agreement': 'AGREE' if '✓ AGREE' in line else 'DISAGREE',
                'direction': None,
                'confidence': 0.0,
                'reasoning': '',
                'bot_action': None,
                'agent_votes': []
            }
            
            # Extract direction and confidence
            if 'Up @' in line:
                decision['direction'] = 'Up'
                conf_match = re.search(r'@ (\d+)%', line)
                if conf_match:
                    decision['confidence'] = float(conf_match.group(1)) / 100
            elif 'Down @' in line:
                decision['direction'] = 'Down'
                conf_match = re.search(r'@ (\d+)%', line)
                if conf_match:
                    decision['confidence'] = float(conf_match.group(1)) / 100
            elif 'SKIP' in line:
                decision['direction'] = 'SKIP'
                
            # Get reasoning from next line
            if i + 1 < len(log_lines):
                reason_line = log_lines[i + 1]
                if 'Reason:' in reason_line:
                    decision['reasoning'] = reason_line.split('Reason:')[-1].strip()
            
            # Check if bot actually placed order
            for j in range(max(0, i-5), min(len(log_lines), i+10)):
                if 'ORDER PLACED' in log_lines[j]:
                    decision['bot_action'] = 'PLACED'
                elif 'SKIP' in log_lines[j] or 'BLOCKED' in log_lines[j]:
                    decision['bot_action'] = 'SKIPPED'
                    
            decisions.append(decision)
    
    return decisions

def extract_timestamp(line):
    """Extract timestamp from log line."""
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    return match.group(1) if match else 'Unknown'

def extract_crypto(log_lines, index):
    """Extract crypto from nearby log lines."""
    for i in range(max(0, index-10), index):
        line = log_lines[i]
        if '[BTC]' in line:
            return 'BTC'
        elif '[ETH]' in line:
            return 'ETH'
        elif '[SOL]' in line:
            return 'SOL'
        elif '[XRP]' in line:
            return 'XRP'
    return 'Unknown'

def get_epoch_status():
    """Get current epoch timing."""
    current_time = int(time.time())
    epoch_start = (current_time // 900) * 900
    time_in_epoch = current_time - epoch_start
    time_remaining = 900 - time_in_epoch
    
    # Determine phase
    if time_in_epoch < 300:
        phase = "EARLY (Candlestick Window)"
    elif time_in_epoch < 720:
        phase = "MID"
    else:
        phase = "LATE (High Confidence Window)"
        
    return {
        'time_in': time_in_epoch,
        'remaining': time_remaining,
        'phase': phase,
        'percent': (time_in_epoch / 900) * 100
    }

def draw_progress_bar(percent, width=40):
    """Draw ASCII progress bar."""
    filled = int(width * percent / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percent:.0f}%"

def display_dashboard(log_file="/opt/polymarket-autotrader/bot.log"):
    """Main dashboard display loop."""
    
    rows, cols = get_terminal_size()
    
    while True:
        clear_screen()
        
        # Read recent log lines
        try:
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-500:]  # Last 500 lines
        except:
            log_lines = []
        
        # Header
        print("=" * cols)
        print("🤖 ELITE SWAT TEAM - AGENT DECISION DASHBOARD".center(cols))
        print("=" * cols)
        print()
        
        # Epoch Status
        epoch = get_epoch_status()
        print(f"⏰ EPOCH STATUS:")
        print(f"   Phase: {epoch['phase']}")
        print(f"   Time:  {epoch['time_in']}s / 900s  ({epoch['time_in']//60}m {epoch['time_in']%60}s)")
        print(f"   {draw_progress_bar(epoch['percent'])}")
        print(f"   Next:  {epoch['remaining']}s ({epoch['remaining']//60}m {epoch['remaining']%60}s)")
        print()
        
        # Parse agent decisions
        decisions = parse_agent_decision(log_lines)
        
        if decisions:
            print(f"📊 RECENT AGENT DECISIONS (Last {len(decisions)}):")
            print("-" * cols)
            
            # Show last 5 decisions
            for decision in decisions[-5:]:
                print()
                print(f"🕒 {decision['timestamp']} | {decision['crypto']}")
                
                # Agreement status
                if decision['agreement'] == 'AGREE':
                    print(f"   ✅ AGENTS AGREE with bot")
                else:
                    print(f"   ⚠️  AGENTS DISAGREE with bot")
                
                # Agent recommendation
                if decision['direction'] == 'SKIP':
                    print(f"   🤖 Agents: SKIP (no consensus)")
                else:
                    print(f"   🤖 Agents: {decision['direction']} @ {decision['confidence']:.0%} confidence")
                
                # Reasoning
                if decision['reasoning']:
                    # Truncate reasoning to fit screen
                    reason = decision['reasoning'][:cols-10]
                    print(f"   💭 {reason}")
                
                # Bot action
                if decision['bot_action']:
                    if decision['bot_action'] == 'PLACED':
                        print(f"   📈 Bot: ORDER PLACED")
                    else:
                        print(f"   ⏸️  Bot: SKIPPED")
                
                print("-" * cols)
        else:
            print("⏳ Waiting for agent decisions...")
            print("   Agents analyze at each trading opportunity")
            print("   Check back in a few minutes")
        
        print()
        print(f"🔄 Auto-refresh every 5 seconds | Press Ctrl+C to exit")
        print("=" * cols)
        
        # Wait before refresh
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n\n👋 Dashboard stopped")
            sys.exit(0)

if __name__ == "__main__":
    print("Starting Agent Decision Dashboard...")
    print("Reading from bot logs...")
    time.sleep(2)
    
    # Check if running on VPS or local
    log_file = "/opt/polymarket-autotrader/bot.log"
    if not os.path.exists(log_file):
        # Local development - might need different path
        log_file = "../bot.log"
    
    display_dashboard(log_file)
