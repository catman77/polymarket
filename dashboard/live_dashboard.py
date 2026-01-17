#!/usr/bin/env python3
"""
Live Polymarket Trading Dashboard - Real-time monitoring with auto-refresh
"""

import requests
import time
import os
import json
import sys
from datetime import datetime, timezone

WALLET = "0x52dF6Dc5DE31DD844d9E432A0821BC86924C2237"
REFRESH_INTERVAL = 10  # seconds

# Set TERM immediately to prevent errors
if 'TERM' not in os.environ:
    os.environ['TERM'] = 'xterm-256color'

def clear_screen():
    """Clear terminal screen."""
    try:
        os.system('clear' if os.name == 'posix' else 'cls')
    except:
        print('\n' * 50)

def get_usdc_balance():
    """Get current USDC balance from blockchain."""
    try:
        rpc_url = 'https://polygon-rpc.com'
        usdc_address = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
        data = '0x70a08231000000000000000000000000' + WALLET[2:].lower()

        response = requests.post(rpc_url, json={
            'jsonrpc': '2.0',
            'method': 'eth_call',
            'params': [{'to': usdc_address, 'data': data}, 'latest'],
            'id': 1
        }, timeout=10)

        balance_hex = response.json().get('result', '0x0')
        return int(balance_hex, 16) / 1e6
    except:
        return None

def get_current_epoch_time():
    """Get time into current 15-minute epoch."""
    current_time = int(time.time())
    epoch_start = (current_time // 900) * 900
    time_in_epoch = current_time - epoch_start
    time_remaining = 900 - time_in_epoch
    return time_in_epoch, time_remaining

def get_bot_state():
    """Read bot trading state (tries intra_epoch first, then trading_state)."""
    # Try intra-epoch bot state first (new bot)
    try:
        with open('/opt/polymarket-autotrader/state/intra_epoch_state.json', 'r') as f:
            state = json.load(f)
            state['bot_type'] = 'intra_epoch'
            return state
    except:
        pass

    # Fallback to old trading_state.json
    try:
        with open('/opt/polymarket-autotrader/state/trading_state.json', 'r') as f:
            state = json.load(f)
            state['bot_type'] = 'ml_bot'
            return state
    except:
        return None


def get_intra_epoch_patterns():
    """Fetch current intra-epoch momentum patterns for all cryptos."""
    patterns = {}
    epoch_start = (int(time.time()) // 900) * 900
    time_in_epoch = int(time.time()) - epoch_start

    for crypto in ['BTC', 'ETH', 'SOL', 'XRP']:
        try:
            # Fetch 1-minute candles
            symbol = f"{crypto}USDT"
            resp = requests.get(
                'https://api.binance.com/api/v3/klines',
                params={
                    'symbol': symbol,
                    'interval': '1m',
                    'startTime': epoch_start * 1000,
                    'limit': 15
                },
                timeout=5
            )

            if resp.status_code != 200:
                continue

            klines = resp.json()
            minutes = []
            for k in klines[:-1]:  # Skip incomplete
                open_p = float(k[1])
                close_p = float(k[4])
                minutes.append('Up' if close_p > open_p else 'Down')

            if len(minutes) < 3:
                patterns[crypto] = {'signal': None, 'reason': 'Waiting...'}
                continue

            # Check patterns
            ups = sum(1 for m in minutes if m == 'Up')
            downs = len(minutes) - ups

            # 4+ of first 5
            if len(minutes) >= 5:
                first_5 = minutes[:5]
                ups_5 = sum(1 for m in first_5 if m == 'Up')
                if ups_5 >= 4:
                    patterns[crypto] = {
                        'signal': 'Up',
                        'accuracy': 79.7,
                        'reason': f'{ups_5}/5 UP',
                        'ups': ups,
                        'downs': downs
                    }
                    continue
                elif ups_5 <= 1:
                    patterns[crypto] = {
                        'signal': 'Down',
                        'accuracy': 74.0,
                        'reason': f'{5-ups_5}/5 DOWN',
                        'ups': ups,
                        'downs': downs
                    }
                    continue

            # All 3 same
            first_3 = minutes[:3]
            if all(m == 'Up' for m in first_3):
                patterns[crypto] = {
                    'signal': 'Up',
                    'accuracy': 78.0,
                    'reason': '3/3 UP',
                    'ups': ups,
                    'downs': downs
                }
            elif all(m == 'Down' for m in first_3):
                patterns[crypto] = {
                    'signal': 'Down',
                    'accuracy': 73.9,
                    'reason': '3/3 DOWN',
                    'ups': ups,
                    'downs': downs
                }
            else:
                patterns[crypto] = {
                    'signal': None,
                    'reason': 'Mixed',
                    'ups': ups,
                    'downs': downs
                }

        except:
            patterns[crypto] = {'signal': None, 'reason': 'Error'}

    return patterns, epoch_start, time_in_epoch

def get_market_details(market_id):
    """Fetch market details from Gamma API."""
    try:
        resp = requests.get(
            f'https://gamma-api.polymarket.com/markets/{market_id}',
            timeout=5
        )
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def get_price_to_beat(slug, outcome):
    """
    Get the price to beat (epoch start price) for a position.

    For Up: Need crypto to end ABOVE start price
    For Down: Need crypto to end BELOW start price

    Returns: (price_to_beat, current_crypto_price, direction_needed)
    """
    try:
        # Fetch market by slug
        resp = requests.get(
            f'https://gamma-api.polymarket.com/markets?slug={slug}',
            timeout=5
        )
        if resp.status_code != 200:
            return None, None, None

        markets = resp.json()
        if not markets:
            return None, None, None

        market = markets[0] if isinstance(markets, list) else markets

        # Extract crypto and direction from outcome (e.g., "BTC Up" or "SOL Down")
        parts = outcome.split()
        if len(parts) < 2:
            return None, None, None

        crypto = parts[0]  # BTC, ETH, SOL, XRP
        direction = parts[1]  # Up or Down

        # Get epoch start price from market metadata
        # The market should have start_price or we can infer from question
        question = market.get('question', '')

        # Try to extract start price from question
        # Example: "Will BTC be higher than $43,521.50 at 9:15 PM?"
        import re
        price_match = re.search(r'\$([0-9,]+\.?\d*)', question)
        if price_match:
            start_price = float(price_match.group(1).replace(',', ''))

            # Get current crypto price
            current_price = get_current_crypto_price(crypto)

            return start_price, current_price, direction

    except Exception as e:
        pass

    return None, None, None

def get_current_crypto_price(crypto):
    """Get current price for a crypto from Binance."""
    try:
        symbol_map = {
            'BTC': 'BTCUSDT',
            'Bitcoin': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'Ethereum': 'ETHUSDT',
            'SOL': 'SOLUSDT',
            'Solana': 'SOLUSDT',
            'XRP': 'XRPUSDT'
        }

        symbol = symbol_map.get(crypto)
        if not symbol:
            return None

        resp = requests.get(
            f'https://api.binance.com/api/v3/ticker/price',
            params={'symbol': symbol},
            timeout=3
        )

        if resp.status_code == 200:
            return float(resp.json()['price'])
    except:
        pass

    return None

def get_epoch_start_price(crypto_ticker, epoch_timestamp):
    """
    Get the crypto price at epoch start time from Binance historical data.

    Args:
        crypto_ticker: Ticker symbol (e.g., 'SOL', 'BTC', 'ETH', 'XRP')
        epoch_timestamp: Unix timestamp of epoch start (seconds)

    Returns:
        Float price at epoch start, or None if unavailable
    """
    try:
        symbol_map = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'SOL': 'SOLUSDT',
            'XRP': 'XRPUSDT'
        }

        symbol = symbol_map.get(crypto_ticker)
        if not symbol:
            return None

        # Binance klines API requires milliseconds
        start_time_ms = epoch_timestamp * 1000

        # Fetch 1-minute kline at epoch start
        resp = requests.get(
            'https://api.binance.com/api/v3/klines',
            params={
                'symbol': symbol,
                'interval': '1m',
                'startTime': start_time_ms,
                'limit': 1
            },
            timeout=5
        )

        if resp.status_code == 200:
            klines = resp.json()
            if klines and len(klines) > 0:
                # Kline format: [open_time, open, high, low, close, volume, ...]
                # We want the open price (index 1)
                open_price = float(klines[0][1])
                return open_price
    except:
        pass

    return None

def get_positions():
    """Get all positions categorized by status."""
    try:
        resp = requests.get(
            'https://data-api.polymarket.com/positions',
            params={'user': WALLET, 'limit': 50},
            timeout=10
        )

        if resp.status_code != 200:
            return None

        positions = resp.json()
        
        open_positions = []
        resolved_winners = []
        resolved_losers = []
        awaiting_resolution = []
        
        for pos in positions:
            size = float(pos.get('size', 0))
            if size < 0.01:
                continue

            outcome = pos.get('outcome', 'Unknown')
            cur_price = float(pos.get('curPrice', 0))

            # Get title directly from position (more reliable than market object)
            question = pos.get('title', 'Unknown Market')

            # Get redeemable status
            redeemable = pos.get('redeemable', False)

            # Check market resolution status (if market object exists)
            market = pos.get('market', {})
            resolved = market.get('resolved', False) if market else False
            closed = market.get('closed', False) if market else False

            current_value = size * cur_price
            max_payout = size * 1.0
            win_prob = cur_price

            position_data = {
                'outcome': outcome,
                'question': question[:70],
                'size': size,
                'cur_price': cur_price,
                'current_value': current_value,
                'max_payout': max_payout,
                'win_prob': win_prob,
                'resolved': resolved,
                'closed': closed,
                'redeemable': redeemable,
                'slug': pos.get('slug')
            }

            if resolved:
                winning_outcome = market.get('winning_outcome', '')
                if outcome == winning_outcome:
                    resolved_winners.append(position_data)
                else:
                    resolved_losers.append(position_data)
            elif closed:
                awaiting_resolution.append(position_data)
            else:
                # Filter out worthless positions (0% win prob or < $0.10 value)
                if win_prob <= 0.01 or current_value < 0.10:
                    continue  # Skip displaying worthless positions

                # Check redeemable status AND has value (only show winners worth $1+)
                if (redeemable or win_prob >= 0.99) and current_value >= 1.0:
                    position_data['status'] = 'READY_REDEEM'
                    open_positions.append(position_data)
                elif win_prob <= 0.01 or current_value < 1.0:
                    position_data['status'] = 'LIKELY_LOSS'
                    open_positions.append(position_data)
                else:
                    position_data['status'] = 'ACTIVE'
                    open_positions.append(position_data)
        
        return {
            'open': open_positions,
            'resolved_winners': resolved_winners,
            'resolved_losers': resolved_losers,
            'awaiting': awaiting_resolution
        }
    except Exception as e:
        return None

def render_dashboard():
    """Render the complete dashboard."""
    clear_screen()
    
    # Header
    print("=" * 80)
    print(" " * 20 + "🤖 POLYMARKET LIVE TRADING DASHBOARD")
    print("=" * 80)
    print(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | 🔄 Refreshing every {REFRESH_INTERVAL}s")
    print()
    
    # System Status
    print("🖥️  SYSTEM STATUS")
    print("-" * 80)
    
    # Bot State
    bot_state = get_bot_state()
    if bot_state:
        bot_type = bot_state.get('bot_type', 'unknown')
        halted = bot_state.get('halted', False)
        mode_emoji = "🔴" if halted else "🟢"

        current_balance = bot_state.get('current_balance', 0)
        daily_pnl = bot_state.get('daily_pnl', 0)
        total_trades = bot_state.get('total_trades', 0)
        total_wins = bot_state.get('total_wins', 0)
        total_losses = bot_state.get('total_losses', 0)
        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

        bot_name = "INTRA-EPOCH MOMENTUM" if bot_type == 'intra_epoch' else "ML BOT"
        print(f"{mode_emoji} Bot: {bot_name} {'(HALTED)' if halted else '(ACTIVE)'}")
        print(f"💰 Balance: ${current_balance:.2f}")
        print(f"📊 Daily P&L: ${daily_pnl:+.2f}")
        print(f"📈 Record: {total_wins}W/{total_losses}L ({win_rate:.1f}% win rate)")

        if bot_state.get('halt_reason'):
            print(f"⚠️  Halt Reason: {bot_state['halt_reason']}")

        # Show active positions from bot state
        positions = bot_state.get('positions', {})
        if positions:
            print(f"🎯 Bot Positions: {', '.join(positions.keys())}")
    else:
        print("⚠️  Could not read bot state")

    # Intra-Epoch Momentum Patterns
    patterns, epoch_start, time_in_epoch = get_intra_epoch_patterns()
    window_active = 180 <= time_in_epoch <= 600

    print()
    print("📊 INTRA-EPOCH MOMENTUM (74-80% accuracy patterns)")
    print("-" * 80)

    pattern_line = ""
    for crypto in ['BTC', 'ETH', 'SOL', 'XRP']:
        p = patterns.get(crypto, {})
        signal = p.get('signal')
        reason = p.get('reason', '?')
        accuracy = p.get('accuracy', 0)

        if signal == 'Up':
            emoji = "🟢"
            pattern_line += f"{emoji} {crypto}:UP({reason}) "
        elif signal == 'Down':
            emoji = "🔴"
            pattern_line += f"{emoji} {crypto}:DN({reason}) "
        else:
            emoji = "⚪"
            ups = p.get('ups', 0)
            downs = p.get('downs', 0)
            pattern_line += f"{emoji} {crypto}:{ups}↑{downs}↓ "

    print(f"  {pattern_line}")
    window_status = "🟢 TRADING WINDOW ACTIVE" if window_active else "⏳ Window: min 3-10"
    print(f"  {window_status} | Epoch min {time_in_epoch // 60}:{time_in_epoch % 60:02d}")
    
    # Blockchain Balance
    blockchain_balance = get_usdc_balance()
    if blockchain_balance is not None:
        print(f"🔗 Blockchain Balance: ${blockchain_balance:.2f}")
    
    # Epoch Timer
    time_in, time_remaining = get_current_epoch_time()
    mins_remaining = time_remaining // 60
    secs_remaining = time_remaining % 60
    progress = int((time_in / 900) * 40)
    bar = "█" * progress + "░" * (40 - progress)
    print(f"⏱️  Epoch Timer: [{bar}] {mins_remaining}m {secs_remaining}s remaining")
    
    print()
    
    # Positions
    positions = get_positions()
    if not positions:
        print("⚠️  Could not fetch positions")
        return
    
    open_pos = positions['open']
    resolved_wins = positions['resolved_winners']
    resolved_losses = positions['resolved_losers']
    awaiting = positions['awaiting']
    
    # Separate ready-to-redeem positions
    ready_redeem = [p for p in open_pos if p.get('status') == 'READY_REDEEM']
    active_pos = [p for p in open_pos if p.get('status') != 'READY_REDEEM']
    
    # Ready to Redeem (100% winners)
    if ready_redeem:
        total_redeem = sum(p['current_value'] for p in ready_redeem)
        print("💰 READY TO REDEEM (AUTO-REDEEMER RUNS EVERY 5 MIN)")
        print("-" * 80)
        for i, pos in enumerate(ready_redeem, 1):
            redeem_status = "✓ Redeemable" if pos.get('redeemable') else "⏳ Pending"
            print(f"🟢 [{i}] {pos['outcome']}: {pos['size']:.0f} shares @ {pos['cur_price']*100:.1f}%")
            print(f"    {pos['question']}")
            print(f"    💵 Will Redeem: ${pos['current_value']:.2f} | {redeem_status}")
        print(f"\n✅ Total Pending Redemption: ${total_redeem:.2f}")
        print()
    
    # Active Open Positions
    if active_pos:
        print("📈 ACTIVE POSITIONS")
        print("-" * 80)

        # Calculate totals
        total_current_value = sum(p['current_value'] for p in active_pos)
        total_max_payout = sum(p['max_payout'] for p in active_pos)

        # Estimate amount invested (shares bought at their initial price)
        # We approximate by assuming entry price ≈ max(0.50, current_price)
        # This is an estimate since we don't track actual entry prices
        total_invested = sum(p['size'] * max(0.50, p['cur_price']) for p in active_pos)

        # Calculate unrealized P&L (current value vs estimated investment)
        unrealized_pnl = total_current_value - total_invested
        pnl_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0

        for i, pos in enumerate(active_pos, 1):
            status_emoji = "🔴" if pos.get('status') == 'LIKELY_LOSS' else "🟡"

            prob_pct = pos['win_prob'] * 100
            bar_length = int(prob_pct / 2.5)
            bar = "█" * bar_length + "░" * (40 - bar_length)

            # Estimate entry price for this position
            est_entry = max(0.50, pos['cur_price'])
            est_invested = pos['size'] * est_entry

            print(f"\n{status_emoji} [{i}] {pos['outcome']}: {pos['size']:.0f} shares @ {pos['cur_price']*100:.1f}%")
            print(f"    {pos['question']}")
            print(f"    Win Prob: [{bar}] {prob_pct:.1f}%")

            # Show current crypto price and position status
            # Extract crypto from slug (format: "btc-updown-15m-...", "sol-updown-15m-...", etc)
            slug = pos.get('slug', '')
            direction = pos['outcome']  # "Up" or "Down"

            if slug and direction:
                # Get crypto ticker from slug (first part before hyphen)
                crypto_ticker = slug.split('-')[0].upper() if slug else None

                if crypto_ticker:
                    current_price = get_current_crypto_price(crypto_ticker)

                    # Extract epoch timestamp from slug (last part)
                    # Format: "sol-updown-15m-1768516200"
                    slug_parts = slug.split('-')
                    if len(slug_parts) >= 4:
                        try:
                            epoch_timestamp = int(slug_parts[-1])
                            start_price = get_epoch_start_price(crypto_ticker, epoch_timestamp)

                            if current_price and start_price:
                                # Calculate price change
                                price_diff = current_price - start_price
                                price_diff_pct = (price_diff / start_price) * 100

                                # Determine if winning
                                is_winning = False
                                if direction == "Up" and current_price > start_price:
                                    is_winning = True
                                elif direction == "Down" and current_price < start_price:
                                    is_winning = True

                                status_emoji = "✅" if is_winning else "❌"
                                status_text = "WINNING" if is_winning else "LOSING"
                                arrow = "↑" if price_diff > 0 else "↓" if price_diff < 0 else "→"

                                print(f"    📊 {crypto_ticker}: Start ${start_price:,.2f} | Current ${current_price:,.2f} {arrow} | {price_diff:+.2f} ({price_diff_pct:+.2f}%) {status_emoji} {status_text}")
                            elif current_price:
                                # Fallback if epoch start price unavailable
                                arrow = "↑" if direction == "Up" else "↓" if direction == "Down" else ""
                                print(f"    📊 {crypto_ticker} Current Price: ${current_price:,.2f} {arrow} | Market Prob: {pos['cur_price']*100:.1f}%")
                        except (ValueError, IndexError):
                            # If timestamp parsing fails, show current price only
                            if current_price:
                                arrow = "↑" if direction == "Up" else "↓" if direction == "Down" else ""
                                print(f"    📊 {crypto_ticker} Current Price: ${current_price:,.2f} {arrow} | Market Prob: {pos['cur_price']*100:.1f}%")

            print(f"    Current Value: ${pos['current_value']:.2f} | If Win: ${pos['max_payout']:.2f} | Est. Invested: ${est_invested:.2f}")

        print(f"\n💰 SUMMARY:")
        print(f"   Current Value: ${total_current_value:.2f} (what your shares are worth now)")
        print(f"   If All Win: ${total_max_payout:.2f} (max payout if everything wins)")
        print(f"   Est. Invested: ${total_invested:.2f} (approx capital tied up)")
        print(f"   Unrealized P&L: ${unrealized_pnl:+.2f} ({pnl_pct:+.1f}%)")
        print()
    
    if not ready_redeem and not active_pos:
        print("📈 OPEN POSITIONS: None")
        print()
    
    # Awaiting Resolution
    if awaiting:
        print(f"⏳ AWAITING RESOLUTION ({len(awaiting)})")
        print("-" * 80)
        for pos in awaiting:
            print(f"  • {pos['outcome']}: {pos['size']:.0f} shares - {pos['question']}")
        print()
    
    # Resolved Winners
    if resolved_wins:
        total_won = sum(p['max_payout'] for p in resolved_wins)
        print(f"✅ RESOLVED WINNERS ({len(resolved_wins)}) - Total: ${total_won:.2f}")
        print("-" * 80)
        for pos in resolved_wins[:5]:
            print(f"  ✅ {pos['outcome']}: {pos['size']:.0f} shares = ${pos['max_payout']:.2f}")
        if len(resolved_wins) > 5:
            print(f"  ... and {len(resolved_wins) - 5} more")
        print()
    
    # Resolved Losers
    if resolved_losses:
        total_lost = sum(p['current_value'] for p in resolved_losses)
        print(f"❌ RESOLVED LOSSES ({len(resolved_losses)}) - Lost: ${total_lost:.2f}")
        print("-" * 80)
        for pos in resolved_losses[:3]:
            print(f"  ❌ {pos['outcome']}: {pos['size']:.0f} shares - ${pos['current_value']:.2f} lost")
        if len(resolved_losses) > 3:
            print(f"  ... and {len(resolved_losses) - 3} more")
        print()
    
    print("=" * 80)
    print("💡 Press Ctrl+C to exit | Dashboard updates every 10 seconds")
    print("=" * 80)
    
    sys.stdout.flush()

def main():
    """Main loop."""
    print("Starting live dashboard...")
    time.sleep(1)
    
    try:
        while True:
            render_dashboard()
            time.sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        clear_screen()
        print("\n👋 Dashboard stopped. Goodbye!")
        print()

if __name__ == "__main__":
    main()
