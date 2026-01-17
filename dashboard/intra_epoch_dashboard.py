#!/usr/bin/env python3
"""
Intra-Epoch Momentum Dashboard

Real-time visualization of 1-minute candle patterns within each 15-minute epoch.
Shows momentum buildup and predicted outcome probability for BTC, ETH, SOL, XRP.

Based on data-validated patterns (2,688 epochs, 7 days):
- 4+ of first 5 minutes UP → 79.7% chance epoch ends UP
- 4+ of first 5 minutes DOWN → 74.0% chance epoch ends DOWN
- All first 3 minutes UP → 78.0% chance epoch ends UP
- All first 3 minutes DOWN → 73.9% chance epoch ends DOWN
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Background
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    # Box drawing
    UP_ARROW = "▲"
    DOWN_ARROW = "▼"
    NEUTRAL = "─"
    BLOCK_FULL = "█"
    BLOCK_HALF = "▄"


# Pattern accuracy from validation
PATTERNS = {
    '4_of_5_up': {'direction': 'Up', 'accuracy': 0.797, 'edge': 29.7},
    '4_of_5_down': {'direction': 'Down', 'accuracy': 0.740, 'edge': 24.0},
    'all_3_up': {'direction': 'Up', 'accuracy': 0.780, 'edge': 28.0},
    'all_3_down': {'direction': 'Down', 'accuracy': 0.739, 'edge': 23.9},
    '3_of_5_up': {'direction': 'Up', 'accuracy': 0.65, 'edge': 15.0},
    '3_of_5_down': {'direction': 'Down', 'accuracy': 0.65, 'edge': 15.0},
}


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def get_current_epoch() -> Tuple[int, int]:
    """Get current epoch start and time elapsed."""
    now = int(time.time())
    epoch_start = now // 900 * 900
    time_in_epoch = now - epoch_start
    return epoch_start, time_in_epoch


def fetch_epoch_minutes(crypto: str, epoch_start: int) -> Optional[List[dict]]:
    """
    Fetch 1-minute candles for the current epoch.

    Returns list of dicts with 'direction', 'open', 'close', 'change_pct'
    """
    try:
        symbol = f"{crypto}USDT"
        url = "https://api.binance.com/api/v3/klines"

        params = {
            'symbol': symbol,
            'interval': '1m',
            'startTime': epoch_start * 1000,
            'limit': 15
        }

        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code != 200:
            return None

        klines = resp.json()

        minutes = []
        for k in klines[:-1]:  # Skip last (incomplete)
            open_p = float(k[1])
            close_p = float(k[4])
            high_p = float(k[2])
            low_p = float(k[3])
            change_pct = ((close_p - open_p) / open_p) * 100 if open_p > 0 else 0

            minutes.append({
                'direction': 'Up' if close_p > open_p else 'Down',
                'open': open_p,
                'close': close_p,
                'high': high_p,
                'low': low_p,
                'change_pct': change_pct
            })

        # Add current incomplete candle
        if klines:
            k = klines[-1]
            open_p = float(k[1])
            close_p = float(k[4])
            change_pct = ((close_p - open_p) / open_p) * 100 if open_p > 0 else 0
            minutes.append({
                'direction': 'Up' if close_p > open_p else 'Down',
                'open': open_p,
                'close': close_p,
                'high': float(k[2]),
                'low': float(k[3]),
                'change_pct': change_pct,
                'incomplete': True
            })

        return minutes

    except Exception as e:
        return None


def analyze_pattern(minutes: List[dict]) -> Tuple[Optional[str], float, str, str]:
    """
    Analyze minute patterns and return prediction.

    Returns:
        (direction, probability, pattern_name, description)
    """
    if not minutes:
        return (None, 0.5, 'no_data', 'Waiting for data...')

    completed = [m for m in minutes if not m.get('incomplete', False)]

    if len(completed) < 3:
        return (None, 0.5, 'insufficient', f'Need {3 - len(completed)} more minutes...')

    # Count directions
    ups = sum(1 for m in completed if m['direction'] == 'Up')
    downs = len(completed) - ups

    # Check patterns in order of strength

    # Pattern 1: 4+ of first 5 minutes (strongest signal)
    if len(completed) >= 5:
        first_5 = completed[:5]
        ups_5 = sum(1 for m in first_5 if m['direction'] == 'Up')
        downs_5 = 5 - ups_5

        if ups_5 >= 4:
            return ('Up', 0.797, '4_of_5_up',
                   f'{ups_5}/5 first minutes UP → 79.7% UP')
        elif downs_5 >= 4:
            return ('Down', 0.740, '4_of_5_down',
                   f'{downs_5}/5 first minutes DOWN → 74.0% DOWN')

    # Pattern 2: All first 3 minutes same direction
    first_3 = completed[:3]
    if all(m['direction'] == 'Up' for m in first_3):
        return ('Up', 0.780, 'all_3_up',
               'All 3 first minutes UP → 78.0% UP')
    elif all(m['direction'] == 'Down' for m in first_3):
        return ('Down', 0.739, 'all_3_down',
               'All 3 first minutes DOWN → 73.9% DOWN')

    # Pattern 3: Weaker - 3 of first 5 same direction
    if len(completed) >= 5:
        first_5 = completed[:5]
        ups_5 = sum(1 for m in first_5 if m['direction'] == 'Up')

        if ups_5 >= 3:
            return ('Up', 0.65, '3_of_5_up',
                   f'{ups_5}/5 first minutes UP → ~65% UP (moderate)')
        elif ups_5 <= 2:
            downs_5 = 5 - ups_5
            return ('Down', 0.65, '3_of_5_down',
                   f'{downs_5}/5 first minutes DOWN → ~65% DOWN (moderate)')

    # No clear pattern - show current bias
    if ups > downs:
        bias = ups / len(completed)
        return ('Up', 0.5 + (bias - 0.5) * 0.3, 'no_pattern',
               f'Mixed: {ups}↑ {downs}↓ (slight UP bias)')
    elif downs > ups:
        bias = downs / len(completed)
        return ('Down', 0.5 + (bias - 0.5) * 0.3, 'no_pattern',
               f'Mixed: {ups}↑ {downs}↓ (slight DOWN bias)')
    else:
        return (None, 0.5, 'no_pattern', f'Mixed: {ups}↑ {downs}↓ (no clear pattern)')


def render_minute_bar(minute: dict, index: int, is_current: bool = False) -> str:
    """Render a single minute candle as a colored bar."""
    direction = minute['direction']
    change = minute['change_pct']
    incomplete = minute.get('incomplete', False)

    # Color based on direction
    if direction == 'Up':
        color = Colors.GREEN
        arrow = Colors.UP_ARROW
    else:
        color = Colors.RED
        arrow = Colors.DOWN_ARROW

    # Intensity based on magnitude
    if abs(change) > 0.1:
        block = Colors.BLOCK_FULL
    else:
        block = Colors.BLOCK_HALF

    # Format
    if incomplete:
        return f"{Colors.DIM}{color}[{arrow}]{Colors.RESET}"
    else:
        return f"{color}{arrow}{Colors.RESET}"


def render_probability_bar(probability: float, width: int = 30) -> str:
    """Render a probability bar with UP/DOWN sides."""
    up_pct = probability
    down_pct = 1 - probability

    up_blocks = int(up_pct * width)
    down_blocks = width - up_blocks

    # Color the bar
    up_bar = f"{Colors.GREEN}{'█' * up_blocks}{Colors.RESET}"
    down_bar = f"{Colors.RED}{'█' * down_blocks}{Colors.RESET}"

    return f"DOWN {down_bar}{up_bar} UP"


def render_crypto_panel(crypto: str, minutes: List[dict], epoch_start: int,
                        time_in_epoch: int, panel_width: int = 38) -> List[str]:
    """Render a single crypto panel."""
    lines = []

    # Analyze pattern
    direction, probability, pattern_name, description = analyze_pattern(minutes)

    # Header
    header_color = Colors.CYAN if not direction else (Colors.GREEN if direction == 'Up' else Colors.RED)
    lines.append(f"┌{'─' * (panel_width - 2)}┐")
    lines.append(f"│{header_color}{Colors.BOLD} {crypto:^{panel_width - 4}} {Colors.RESET}│")
    lines.append(f"├{'─' * (panel_width - 2)}┤")

    # Minute candles visualization (3 rows of 5)
    completed = [m for m in minutes if not m.get('incomplete', False)]
    current = [m for m in minutes if m.get('incomplete', False)]

    # Row 1: Minutes 1-5
    row1 = " "
    for i in range(5):
        if i < len(completed):
            row1 += render_minute_bar(completed[i], i) + "  "
        elif i == len(completed) and current:
            row1 += render_minute_bar(current[0], i, is_current=True) + "  "
        else:
            row1 += f"{Colors.DIM}·{Colors.RESET}  "
    lines.append(f"│ Min 1-5:  {row1:^{panel_width - 14}}│")

    # Row 2: Minutes 6-10
    row2 = " "
    for i in range(5, 10):
        if i < len(completed):
            row2 += render_minute_bar(completed[i], i) + "  "
        elif i == len(completed) and current:
            row2 += render_minute_bar(current[0], i, is_current=True) + "  "
        else:
            row2 += f"{Colors.DIM}·{Colors.RESET}  "
    lines.append(f"│ Min 6-10: {row2:^{panel_width - 14}}│")

    # Row 3: Minutes 11-15
    row3 = " "
    for i in range(10, 15):
        if i < len(completed):
            row3 += render_minute_bar(completed[i], i) + "  "
        elif i == len(completed) and current:
            row3 += render_minute_bar(current[0], i, is_current=True) + "  "
        else:
            row3 += f"{Colors.DIM}·{Colors.RESET}  "
    lines.append(f"│ Min 11-15:{row3:^{panel_width - 14}}│")

    lines.append(f"├{'─' * (panel_width - 2)}┤")

    # Count summary
    ups = sum(1 for m in completed if m['direction'] == 'Up')
    downs = len(completed) - ups
    count_str = f"{Colors.GREEN}{ups}↑{Colors.RESET} {Colors.RED}{downs}↓{Colors.RESET}"
    lines.append(f"│ Count: {count_str:^{panel_width + 10}}│")

    # Pattern detection
    if direction:
        prob_color = Colors.GREEN if direction == 'Up' else Colors.RED
        prob_str = f"{prob_color}{probability:.1%} {direction}{Colors.RESET}"
    else:
        prob_str = f"{Colors.YELLOW}50% (no signal){Colors.RESET}"

    lines.append(f"│ Prediction: {prob_str:^{panel_width + 4}}│")

    # Description (wrap if needed)
    desc = description[:panel_width - 4]
    lines.append(f"│ {desc:<{panel_width - 4}} │")

    # Trading window indicator
    if 180 <= time_in_epoch <= 600:
        window_str = f"{Colors.GREEN}● TRADING WINDOW{Colors.RESET}"
    elif time_in_epoch < 180:
        remaining = 180 - time_in_epoch
        window_str = f"{Colors.YELLOW}○ Window in {remaining}s{Colors.RESET}"
    else:
        window_str = f"{Colors.RED}○ Window closed{Colors.RESET}"

    lines.append(f"│ {window_str:^{panel_width + 6}} │")

    lines.append(f"└{'─' * (panel_width - 2)}┘")

    return lines


def render_dashboard(data: Dict[str, List[dict]], epoch_start: int, time_in_epoch: int):
    """Render the full dashboard."""
    clear_screen()

    # Header
    epoch_time = datetime.fromtimestamp(epoch_start, tz=timezone.utc)
    epoch_end = datetime.fromtimestamp(epoch_start + 900, tz=timezone.utc)
    minutes_elapsed = time_in_epoch // 60
    seconds_elapsed = time_in_epoch % 60
    time_remaining = 900 - time_in_epoch

    print(f"\n{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║              INTRA-EPOCH MOMENTUM DASHBOARD - LIVE MONITORING                ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╠══════════════════════════════════════════════════════════════════════════════╣{Colors.RESET}")

    # Epoch info
    print(f"{Colors.CYAN}║{Colors.RESET} Epoch: {epoch_time.strftime('%H:%M')} - {epoch_end.strftime('%H:%M')} UTC                                                   {Colors.CYAN}║{Colors.RESET}")

    # Progress bar
    progress = time_in_epoch / 900
    bar_width = 50
    filled = int(progress * bar_width)
    bar = f"{Colors.GREEN}{'█' * filled}{Colors.RESET}{Colors.DIM}{'░' * (bar_width - filled)}{Colors.RESET}"
    print(f"{Colors.CYAN}║{Colors.RESET} Progress: [{bar}] {minutes_elapsed:02d}:{seconds_elapsed:02d} / 15:00 {Colors.CYAN}║{Colors.RESET}")

    # Trading window status
    if 180 <= time_in_epoch <= 600:
        window_status = f"{Colors.GREEN}● TRADING WINDOW ACTIVE (min 3-10){Colors.RESET}"
    elif time_in_epoch < 180:
        window_status = f"{Colors.YELLOW}○ Waiting for minute 3 ({180 - time_in_epoch}s){Colors.RESET}"
    else:
        window_status = f"{Colors.RED}○ Trading window closed{Colors.RESET}"

    print(f"{Colors.CYAN}║{Colors.RESET} {window_status:<72} {Colors.CYAN}║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}")

    # Render crypto panels side by side
    cryptos = ['BTC', 'ETH', 'SOL', 'XRP']
    panels = []

    for crypto in cryptos:
        minutes = data.get(crypto, [])
        panel = render_crypto_panel(crypto, minutes, epoch_start, time_in_epoch)
        panels.append(panel)

    # Print panels side by side (2x2 grid)
    print()

    # Top row: BTC, ETH
    max_lines = max(len(panels[0]), len(panels[1]))
    for i in range(max_lines):
        line1 = panels[0][i] if i < len(panels[0]) else ' ' * 38
        line2 = panels[1][i] if i < len(panels[1]) else ' ' * 38
        print(f"  {line1}  {line2}")

    print()

    # Bottom row: SOL, XRP
    max_lines = max(len(panels[2]), len(panels[3]))
    for i in range(max_lines):
        line1 = panels[2][i] if i < len(panels[2]) else ' ' * 38
        line2 = panels[3][i] if i < len(panels[3]) else ' ' * 38
        print(f"  {line1}  {line2}")

    # Legend
    print()
    print(f"  {Colors.DIM}Legend: {Colors.GREEN}▲{Colors.RESET}{Colors.DIM}=Up minute  {Colors.RED}▼{Colors.RESET}{Colors.DIM}=Down minute  {Colors.DIM}·{Colors.RESET}{Colors.DIM}=Pending  {Colors.DIM}[▲]{Colors.RESET}{Colors.DIM}=Current (incomplete){Colors.RESET}")
    print(f"  {Colors.DIM}Patterns: 4+/5 same → 74-80% | All 3 same → 74-78% | 3/5 same → ~65%{Colors.RESET}")
    print()
    print(f"  {Colors.DIM}Press Ctrl+C to exit. Refreshing every 5 seconds...{Colors.RESET}")


def main():
    """Main dashboard loop."""
    print(f"\n{Colors.CYAN}Starting Intra-Epoch Momentum Dashboard...{Colors.RESET}")
    print(f"{Colors.DIM}Fetching initial data...{Colors.RESET}\n")

    cryptos = ['BTC', 'ETH', 'SOL', 'XRP']
    refresh_interval = 5  # seconds

    try:
        while True:
            epoch_start, time_in_epoch = get_current_epoch()

            # Fetch data for all cryptos
            data = {}
            for crypto in cryptos:
                minutes = fetch_epoch_minutes(crypto, epoch_start)
                if minutes:
                    data[crypto] = minutes

            # Render dashboard
            render_dashboard(data, epoch_start, time_in_epoch)

            # Wait for next refresh
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}Dashboard stopped.{Colors.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
