Check what 15-minute Up/Down markets are currently available for trading.

Shows which crypto markets are active and when they resolve.

Steps:
1. Run the market discovery utility:
   python3 utils/check_15min_markets.py

2. Display results showing:
   - Active markets for BTC, ETH, SOL, XRP
   - Current epoch and time remaining
   - Next epoch times
   - Market availability

3. If run from VPS, SSH first:
   ssh root@216.238.85.11
   cd /opt/polymarket-autotrader
   python3 utils/check_15min_markets.py

4. Report if markets are active or if there's a schedule gap
