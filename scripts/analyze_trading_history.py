#!/usr/bin/env python3
"""
Analyze complete trading history from bot logs
Extracts orders, wins, losses, and ML decisions to show time-based patterns
"""

import re
from datetime import datetime
from collections import defaultdict

LOG_FILE = '/opt/polymarket-autotrader/bot.log'

# Parse patterns
order_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*ORDER PLACED.*?(\w+)\s+(Up|Down).*?(\d+)\s+shares.*?\$([\d.]+)'
win_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*WIN.*?(\w+)\s+(Up|Down).*?\$([\d.]+)'
loss_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*LOSS.*?(\w+)\s+(Up|Down)'
ml_trade_pattern = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\].*ML Bot.*TRADE.*?(\w+).*?(Up|Down).*?confidence.*?([\d.]+)'

orders = []
wins = []
losses = []
ml_decisions = []

print("Parsing bot logs...")
with open(LOG_FILE, 'r') as f:
    for line in f:
        # Check for orders
        match = re.search(order_pattern, line)
        if match:
            timestamp, crypto, direction, shares, price = match.groups()
            orders.append({
                'time': timestamp,
                'crypto': crypto.upper(),
                'direction': direction,
                'shares': float(shares),
                'price': float(price)
            })

        # Check for wins
        match = re.search(win_pattern, line)
        if match:
            timestamp, crypto, direction, payout = match.groups()
            wins.append({
                'time': timestamp,
                'crypto': crypto.upper(),
                'direction': direction,
                'payout': float(payout)
            })

        # Check for losses
        match = re.search(loss_pattern, line)
        if match:
            timestamp, crypto, direction = match.groups()
            losses.append({
                'time': timestamp,
                'crypto': crypto.upper(),
                'direction': direction
            })

        # Check for ML decisions
        match = re.search(ml_trade_pattern, line)
        if match:
            timestamp, crypto, direction, confidence = match.groups()
            ml_decisions.append({
                'time': timestamp,
                'crypto': crypto.upper(),
                'direction': direction,
                'confidence': float(confidence)
            })

print(f"\n{'='*80}")
print("COMPLETE TRADING HISTORY")
print(f"{'='*80}")
print(f"Orders Placed: {len(orders)}")
print(f"Resolved Wins: {len(wins)}")
print(f"Resolved Losses: {len(losses)}")
print(f"ML Decisions: {len(ml_decisions)}")

if orders:
    print(f"\n📊 Recent Orders (last 30):")
    for order in orders[-30:]:
        print(f"  {order['time']} | {order['crypto']} {order['direction']} | {order['shares']:.0f} shares @ ${order['price']:.3f}")

if wins or losses:
    total_resolved = len(wins) + len(losses)
    win_rate = (len(wins) / total_resolved * 100) if total_resolved > 0 else 0
    print(f"\n✅ WIN RATE: {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")

    # Total P&L
    total_won = sum(w['payout'] for w in wins)
    total_lost = sum(float(l.get('payout', 0)) for l in losses)
    print(f"💰 Total P&L: ${total_won:.2f} won - Lost positions")

    # Analyze by crypto
    crypto_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for w in wins:
        crypto_stats[w['crypto']]['wins'] += 1
    for l in losses:
        crypto_stats[l['crypto']]['losses'] += 1

    print(f"\n💎 Performance by Crypto:")
    for crypto in sorted(crypto_stats.keys()):
        stats = crypto_stats[crypto]
        total = stats['wins'] + stats['losses']
        wr = (stats['wins'] / total * 100) if total > 0 else 0
        print(f"  {crypto}: {stats['wins']}W/{stats['losses']}L ({wr:.0f}%)")

    # Analyze by hour
    hour_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for w in wins:
        hour = int(w['time'].split()[1].split(':')[0])
        hour_stats[hour]['wins'] += 1
    for l in losses:
        hour = int(l['time'].split()[1].split(':')[0])
        hour_stats[hour]['losses'] += 1

    print(f"\n⏰ Performance by Hour (UTC) - TIME-BASED PATTERN ANALYSIS:")
    print("-" * 80)
    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        total = stats['wins'] + stats['losses']
        wr = (stats['wins'] / total * 100) if total > 0 else 0
        emoji = "🟢" if wr >= 60 else "🟡" if wr >= 50 else "🔴"
        print(f"  {emoji} {hour:02d}:00 | {stats['wins']}W/{stats['losses']}L ({wr:.0f}%) | Total: {total} trades")

if ml_decisions:
    print(f"\n🤖 ML Decisions (last 20):")
    for dec in ml_decisions[-20:]:
        print(f"  {dec['time']} | {dec['crypto']} {dec['direction']} | {dec['confidence']:.1%} conf")

print(f"\n{'='*80}")
print("ANALYSIS COMPLETE")
print(f"{'='*80}")
