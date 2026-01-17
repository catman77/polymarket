#!/usr/bin/env python3
"""
Message Formatter for Telegram Bot

Formats data from trading bot into Telegram messages.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class MessageFormatter:
    """Formats trading data for Telegram messages."""

    def __init__(self):
        # Security: No fallback wallet - must be configured
        self.wallet = os.getenv('POLYMARKET_WALLET')
        if not self.wallet:
            raise ValueError(
                "POLYMARKET_WALLET not configured. "
                "Set it in .env file or environment variable."
            )
        
        # State file path detection: Docker -> VPS -> local
        state_paths = [
            '/app/state/trading_state.json',  # Docker container
            '/opt/polymarket-autotrader/state/trading_state.json',  # VPS
            'state/trading_state.json',  # Local development
        ]
        self.state_file = next((p for p in state_paths if os.path.exists(p)), state_paths[-1])
        
        # Database path detection: Docker -> VPS -> local
        db_paths = [
            '/app/simulation/trade_journal.db',  # Docker container
            '/opt/polymarket-autotrader/simulation/trade_journal.db',  # VPS
            'simulation/trade_journal.db',  # Local development
        ]
        self.db_path = next((p for p in db_paths if os.path.exists(p)), db_paths[-1])

    def get_usdc_balance(self) -> Optional[float]:
        """Get current USDC balance from blockchain."""
        try:
            rpc_url = 'https://polygon-rpc.com'
            usdc_address = '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'
            data = '0x70a08231000000000000000000000000' + self.wallet[2:].lower()

            response = requests.post(rpc_url, json={
                'jsonrpc': '2.0',
                'method': 'eth_call',
                'params': [{'to': usdc_address, 'data': data}, 'latest'],
                'id': 1
            }, timeout=10)

            balance_hex = response.json().get('result', '0x0')
            return int(balance_hex, 16) / 1e6
        except Exception:
            return None

    def get_bot_state(self) -> Optional[Dict]:
        """Read bot trading state."""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None

    def get_current_crypto_price(self, crypto: str) -> Optional[float]:
        """Get current price for a crypto from Binance."""
        try:
            symbol_map = {
                'BTC': 'BTCUSDT',
                'ETH': 'ETHUSDT',
                'SOL': 'SOLUSDT',
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
        except Exception:
            pass

        return None

    def get_epoch_start_price(self, crypto_ticker: str, epoch_timestamp: int) -> Optional[float]:
        """Get crypto price at epoch start from Binance historical data."""
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

            start_time_ms = epoch_timestamp * 1000

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
                    return float(klines[0][1])  # Open price
        except Exception:
            pass

        return None

    def format_balance(self) -> str:
        """Format balance and P&L information."""
        state = self.get_bot_state()
        blockchain_balance = self.get_usdc_balance()

        if not state:
            return "❌ Could not read bot state file"

        current_balance = state.get('current_balance', 0)
        day_start = state.get('day_start_balance', 0)
        peak = state.get('peak_balance', 0)
        daily_pnl = state.get('daily_pnl', 0)

        # Calculate daily P&L percentage
        daily_pnl_pct = (daily_pnl / day_start * 100) if day_start > 0 else 0

        message = "💰 *BALANCE & P&L*\n\n"
        message += f"Current: `${current_balance:.2f}`\n"
        message += f"Day Start: `${day_start:.2f}`\n"
        message += f"Peak: `${peak:.2f}`\n\n"

        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
        message += f"{pnl_emoji} Daily P&L: `${daily_pnl:+.2f}` ({daily_pnl_pct:+.1f}%)\n\n"

        if blockchain_balance is not None:
            match_emoji = "✅" if abs(blockchain_balance - current_balance) < 0.01 else "⚠️"
            message += f"🔗 Blockchain: `${blockchain_balance:.2f}` {match_emoji}"
        else:
            message += "🔗 Blockchain: _Could not fetch_"

        return message

    def format_positions(self) -> str:
        """Format active positions information."""
        try:
            resp = requests.get(
                'https://data-api.polymarket.com/positions',
                params={'user': self.wallet, 'limit': 50},
                timeout=10
            )

            if resp.status_code != 200:
                return "❌ Could not fetch positions from API"

            positions = resp.json()

            # Filter for active positions (non-zero probability)
            active_positions = []
            for pos in positions:
                size = float(pos.get('size', 0))
                cur_price = float(pos.get('curPrice', 0))

                if size > 0 and cur_price > 0.001:  # Active position
                    active_positions.append(pos)

            if not active_positions:
                return "📭 *NO ACTIVE POSITIONS*\n\nNo positions currently held."

            message = f"📈 *ACTIVE POSITIONS* ({len(active_positions)})\n\n"

            total_value = 0
            total_max_payout = 0

            for i, pos in enumerate(active_positions[:10], 1):  # Limit to 10 for message size
                size = float(pos.get('size', 0))
                cur_price = float(pos.get('curPrice', 0))
                outcome = pos.get('outcome', 'Unknown')
                question = pos.get('title', 'Unknown Market')
                slug = pos.get('slug', '')

                current_value = size * cur_price
                max_payout = size * 1.0

                total_value += current_value
                total_max_payout += max_payout

                # Determine status emoji
                if cur_price >= 0.90:
                    status_emoji = "🟢"
                elif cur_price >= 0.50:
                    status_emoji = "🟡"
                elif cur_price >= 0.20:
                    status_emoji = "🟠"
                else:
                    status_emoji = "🔴"

                message += f"{status_emoji} *{outcome}*: {size:.0f} shares @ {cur_price*100:.1f}%\n"

                # Add price comparison if available
                if slug:
                    crypto_ticker = slug.split('-')[0].upper() if slug else None
                    direction = outcome

                    if crypto_ticker and '-' in slug:
                        slug_parts = slug.split('-')
                        if len(slug_parts) >= 4:
                            try:
                                epoch_timestamp = int(slug_parts[-1])
                                start_price = self.get_epoch_start_price(crypto_ticker, epoch_timestamp)
                                current_price = self.get_current_crypto_price(crypto_ticker)

                                if start_price and current_price:
                                    price_diff = current_price - start_price
                                    price_diff_pct = (price_diff / start_price) * 100

                                    is_winning = False
                                    if "Up" in direction and current_price > start_price:
                                        is_winning = True
                                    elif "Down" in direction and current_price < start_price:
                                        is_winning = True

                                    status_text = "✅ WINNING" if is_winning else "❌ LOSING"
                                    arrow = "↑" if price_diff > 0 else "↓"

                                    message += f"   {crypto_ticker}: ${start_price:.2f} → ${current_price:.2f} {arrow} ({price_diff_pct:+.2f}%) {status_text}\n"
                            except Exception:
                                pass

                message += f"   Value: `${current_value:.2f}` | Max: `${max_payout:.2f}`\n\n"

            # Summary
            unrealized_pnl = total_value - (total_max_payout - total_value)
            pnl_pct = (unrealized_pnl / total_value * 100) if total_value > 0 else 0

            message += "💰 *SUMMARY*\n"
            message += f"Total Value: `${total_value:.2f}`\n"
            message += f"If All Win: `${total_max_payout:.2f}`\n"
            message += f"Unrealized P&L: `${unrealized_pnl:+.2f}` ({pnl_pct:+.1f}%)"

            return message

        except Exception as e:
            return f"❌ Error fetching positions: {str(e)}"

    def format_status(self) -> str:
        """Format bot status information."""
        state = self.get_bot_state()

        if not state:
            return "❌ Could not read bot state file"

        mode = state.get('mode', 'unknown').upper()
        consecutive_wins = state.get('consecutive_wins', 0)
        consecutive_losses = state.get('consecutive_losses', 0)

        # Mode emoji
        mode_emoji = {
            'NORMAL': '🟢',
            'CONSERVATIVE': '🟡',
            'DEFENSIVE': '🟠',
            'RECOVERY': '🔴',
            'HALTED': '⛔'
        }.get(mode, '⚪')

        message = "🤖 *BOT STATUS*\n\n"
        message += f"Mode: {mode_emoji} *{mode}*\n\n"

        # Enabled agents (from config)
        enabled_agents = [
            'Tech', 'Sentiment', 'Regime', 'Candlestick',
            'TimePattern', 'OrderBook', 'FundingRate'
        ]
        message += f"Agents: {', '.join(enabled_agents)}\n"
        message += "(+ Risk, Gambler veto)\n\n"

        # Recent activity
        message += "*Recent Activity:*\n"

        # Get 24h trade count from database
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT COUNT(*)
                    FROM outcomes o
                    JOIN trades t ON o.trade_id = t.id
                    WHERE t.is_shadow = 0
                      AND datetime(o.created_at) >= datetime('now', '-1 day')
                ''')

                trades_24h = cursor.fetchone()[0]
                conn.close()

                message += f"• 24h trades: {trades_24h}\n"
        except Exception:
            message += f"• 24h trades: _Unknown_\n"

        message += f"• Streak: {consecutive_wins}W / {consecutive_losses}L\n"

        # Shadow strategies count
        message += f"• Shadow strategies: 30\n\n"

        # Last update time
        message += f"_Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC_"

        return message

    def format_statistics(self) -> str:
        """Format trading statistics."""
        try:
            if not os.path.exists(self.db_path):
                return "❌ Database not found"

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Overall stats - filter by live strategy (ml_live_*)
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN predicted_direction = actual_direction THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN predicted_direction != actual_direction THEN 1 ELSE 0 END) as losses,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as best_trade,
                    MIN(pnl) as worst_trade
                FROM outcomes o
                JOIN trades t ON o.trade_id = t.id
                WHERE t.strategy LIKE 'ml_live%'
            ''')

            row = cursor.fetchone()
            total, wins, losses, total_pnl, avg_pnl, best_trade, worst_trade = row

            if total == 0 or total is None:
                conn.close()
                return "📊 TRADING STATISTICS\n\nNo trades recorded yet."

            win_rate = (wins / total * 100) if total > 0 else 0

            # Plain text formatting (no Markdown)
            message = "📊 TRADING STATISTICS (All-Time)\n\n"
            message += f"Total Trades: {total}\n"
            message += f"Wins: {wins} ({win_rate:.1f}%)\n"
            message += f"Losses: {losses} ({100-win_rate:.1f}%)\n\n"

            message += f"Total P&L: ${total_pnl:.2f}\n"
            message += f"Avg P&L/Trade: ${avg_pnl:.2f}\n\n"

            message += f"Best: ${best_trade:+.2f}\n"
            message += f"Worst: ${worst_trade:+.2f}\n\n"

            # Current streak
            state = self.get_bot_state()
            if state:
                consecutive_wins = state.get('consecutive_wins', 0)
                consecutive_losses = state.get('consecutive_losses', 0)

                if consecutive_wins > 0:
                    message += f"Current Streak: {consecutive_wins}W 🔥"
                elif consecutive_losses > 0:
                    message += f"Current Streak: {consecutive_losses}L ⚠️"
                else:
                    message += "Current Streak: None"

            conn.close()
            return message

        except Exception as e:
            return f"❌ Error fetching statistics: {str(e)}"

    def format_daily_summary(self) -> str:
        """Format daily summary with P&L, trades, and shadow strategy performance."""
        try:
            state = self.get_bot_state()
            if not state:
                return "❌ Could not load bot state"

            # Get today's date range (UTC)
            now = datetime.now()
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            day_start_ts = day_start.timestamp()

            # Calculate daily metrics
            current_balance = state.get('current_balance', 0)
            day_start_balance = state.get('day_start_balance', current_balance)
            daily_pnl = current_balance - day_start_balance
            daily_pnl_pct = (daily_pnl / day_start_balance * 100) if day_start_balance > 0 else 0

            # Get today's trades from database
            trades_today = 0
            wins_today = 0
            losses_today = 0
            best_trade = 0
            worst_trade = 0
            best_trade_desc = ""
            worst_trade_desc = ""

            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get today's trade outcomes
                cursor.execute('''
                    SELECT
                        o.crypto,
                        o.predicted_direction,
                        o.actual_direction,
                        o.pnl
                    FROM outcomes o
                    JOIN trades t ON o.trade_id = t.id
                    WHERE t.strategy LIKE 'ml_live%'
                    AND o.timestamp >= ?
                    ORDER BY o.timestamp DESC
                ''', (day_start_ts,))

                trades = cursor.fetchall()
                trades_today = len(trades)

                for crypto, pred_dir, actual_dir, pnl in trades:
                    if pred_dir == actual_dir:
                        wins_today += 1
                    else:
                        losses_today += 1

                    if pnl > best_trade:
                        best_trade = pnl
                        best_trade_desc = f"{crypto} {pred_dir}"
                    if pnl < worst_trade:
                        worst_trade = pnl
                        worst_trade_desc = f"{crypto} {pred_dir}"

                # Get top 3 shadow strategies by today's performance
                cursor.execute('''
                    SELECT
                        p1.strategy,
                        p1.total_pnl - COALESCE(p2.total_pnl, 0) as daily_pnl
                    FROM performance p1
                    LEFT JOIN (
                        SELECT strategy, total_pnl
                        FROM performance
                        WHERE timestamp <= ?
                        GROUP BY strategy
                        HAVING MAX(timestamp)
                    ) p2 ON p1.strategy = p2.strategy
                    WHERE p1.timestamp >= ?
                    AND p1.strategy NOT LIKE 'ml_live%'
                    GROUP BY p1.strategy
                    HAVING MAX(p1.timestamp)
                    ORDER BY daily_pnl DESC
                    LIMIT 3
                ''', (day_start_ts, day_start_ts))

                shadow_leaders = cursor.fetchall()
                conn.close()
            else:
                shadow_leaders = []

            # Calculate win rate
            win_rate = (wins_today / trades_today * 100) if trades_today > 0 else 0

            # Build summary message
            date_str = now.strftime('%b %d, %Y')
            message = f"📊 DAILY SUMMARY - {date_str}\n\n"

            # Daily P&L
            pnl_sign = "+" if daily_pnl >= 0 else ""
            pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
            message += f"{pnl_emoji} P&L: ${pnl_sign}{daily_pnl:.2f} ({pnl_sign}{daily_pnl_pct:.1f}%)\n"

            # Trades summary
            message += f"Trades: {trades_today}"
            if trades_today > 0:
                message += f" ({wins_today}W / {losses_today}L)\n"
                message += f"Win Rate: {win_rate:.1f}%\n"
            else:
                message += " (No trades today)\n"

            message += "\n"

            # Balance change
            message += f"Balance: ${day_start_balance:.2f} → ${current_balance:.2f}\n\n"

            # Best/worst trades (if any)
            if trades_today > 0:
                message += f"Best: {best_trade_desc} ${best_trade:+.2f}\n"
                message += f"Worst: {worst_trade_desc} ${worst_trade:+.2f}\n\n"

            # Shadow strategy leaders
            if shadow_leaders:
                message += "🎯 Shadow Leaders:\n"
                for i, (strategy, pnl) in enumerate(shadow_leaders, 1):
                    # Clean up strategy name (remove prefixes)
                    clean_name = strategy.replace('shadow_', '').replace('_', ' ').title()
                    message += f"{i}. {clean_name}: ${pnl:+.2f}\n"
                message += "\n"

            # Tomorrow preview
            mode = state.get('mode', 'normal').upper()
            mode_emoji = "🟢" if mode == "NORMAL" else "🟡" if mode in ["CONSERVATIVE", "DEFENSIVE"] else "🔴"

            # Count enabled agents (simplified)
            message += f"Tomorrow: Mode {mode_emoji} {mode}\n"

            return message

        except Exception as e:
            return f"❌ Error generating daily summary: {str(e)}"
