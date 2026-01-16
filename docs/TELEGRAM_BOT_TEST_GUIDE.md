# Telegram Bot Testing Guide

**Date:** January 16, 2026
**Status:** Ready for testing
**Bot:** @YourPolymarketBot (replace with actual bot name)

---

## 🧪 Test Checklist

### **Phase 1: Query Commands** (Safe - No Impact on Trading)

Test these commands to verify data retrieval works:

#### 1. `/start` - Welcome message
**Expected:**
```
Welcome to Polymarket AutoTrader Bot!

Available commands:
📊 /stats - Trading statistics
💰 /balance - Current balance
📍 /positions - Open positions
🤖 /status - Bot status
⏸️ /halt - Emergency halt
▶️ /resume - Resume trading
🎚️ /mode - Change mode
```

**Action:** Send `/start` to the bot

---

#### 2. `/stats` - Trading statistics
**Expected:**
```
📊 TRADING STATISTICS (All-Time)

Total Trades: X
Wins: X (XX.X%)
Losses: X (XX.X%)

Total P&L: $X.XX
Avg P&L/Trade: $X.XX

Best: $+X.XX
Worst: $-X.XX

[Breakdown by crypto if available]
```

**Action:** Send `/stats`
**Note:** May show "No trades recorded yet" if database has 0 outcomes

---

#### 3. `/balance` - Current balance
**Expected:**
```
💰 CURRENT BALANCE

Balance: $200.97
Peak: $200.97
Drawdown: 0.0%

Day Start: $6.81
Daily P&L: $+194.16 (+2850%)
```

**Action:** Send `/balance`

---

#### 4. `/positions` - Open positions
**Expected:**
```
📍 OPEN POSITIONS

[If positions exist:]
1. BTC Up @ $0.42
   Entry: $X.XX x X shares
   Current: $X.XX
   P&L: $±X.XX

[If no positions:]
No open positions
```

**Action:** Send `/positions`

---

#### 5. `/status` - Bot status
**Expected:**
```
🤖 BOT STATUS

Mode: normal
Status: RUNNING
Balance: $200.97

Recent Activity:
[Last few log entries or trade summary]
```

**Action:** Send `/status`

---

### **Phase 2: Control Commands** (⚠️ IMPACTS TRADING)

**WARNING:** These commands control the trading bot. Test carefully.

#### 6. `/halt` - Request halt confirmation
**Expected:**
```
⚠️ CONFIRM HALT?

This will stop all trading.
Reply /confirm_halt to proceed.
```

**Action:** Send `/halt`
**Note:** DO NOT send `/confirm_halt` yet - we'll test that separately

---

#### 7. `/mode` - View/change mode
**Expected:**
```
🎚️ TRADING MODE

Current mode: normal

Available modes:
- normal: Standard trading
- conservative: Reduced position sizes
- defensive: Risk-averse trading
- recovery: Post-loss recovery mode
- halted: Trading stopped

To change mode: /mode <mode_name>
Example: /mode conservative
```

**Action:** Send `/mode`

---

### **Phase 3: Advanced Testing** (Only if Phase 1-2 Pass)

#### 8. Test Mode Change
**Action:** Send `/mode conservative`

**Expected:**
```
⚠️ CONFIRM MODE CHANGE?

Change mode from 'normal' to 'conservative'?
Reply /confirm_mode conservative to proceed.
```

**Then send:** `/confirm_mode conservative`

**Expected:**
```
✅ Mode changed to: conservative

New settings applied.
```

**Verify:** Check trading state file
```bash
ssh root@VPS "cat /opt/polymarket-autotrader/v12_state/trading_state.json | grep mode"
```
Should show: `"mode": "conservative"`

**Restore:** Send `/mode normal` then `/confirm_mode normal`

---

#### 9. Test Halt/Resume Cycle
**Action:** Send `/halt`

**Expected:** Confirmation prompt

**Then send:** `/confirm_halt`

**Expected:**
```
🛑 Bot halted

Trading stopped.
Use /resume to continue.
```

**Verify:** Check logs
```bash
ssh root@VPS "tail -10 /opt/polymarket-autotrader/bot.log | grep HALT"
```

**Resume:** Send `/resume`

**Expected:** Confirmation prompt

**Then send:** `/confirm_resume`

**Expected:**
```
▶️ Bot resumed

Trading active.
```

**Verify:** Check logs for normal operation

---

### **Phase 4: Real-time Notifications** (Passive - Wait for Events)

These notifications are sent automatically when events occur:

#### 10. Trade Notification
**Triggers when:** Bot places a new trade

**Expected:**
```
🚀 NEW TRADE

BTC Up @ $0.42
Size: $5.50 (13 shares)
Confidence: 67.5%

Agents: TechAgent, SentimentAgent, RegimeAgent
Strategy: ml_live_ml_random_forest

⏰ 02:50:15 UTC
```

**How to trigger:** Wait for bot to place a trade (may take time depending on market conditions)

---

#### 11. Redemption Notification (Win)
**Triggers when:** Position wins and is redeemed

**Expected:**
```
✅ POSITION REDEEMED

BTC Up WINNER!
Entry: $0.42 x 13 shares
Redeemed: 13 shares = $13.00

P&L: $+7.54
New Balance: $208.51

⏰ 03:05:20 UTC
```

**How to trigger:** Wait for existing position to resolve as winner (~15 min per epoch)

---

#### 12. Critical Alert Notification
**Triggers when:** Drawdown approaching limit, consecutive losses, etc.

**Expected:**
```
⚠️ CRITICAL ALERT

[Alert message - e.g., "Drawdown 25% approaching 30% limit"]

Action recommended: Review bot performance
```

**How to trigger:** Unlikely unless trading goes poorly (which we don't want!)

---

#### 13. Daily Summary Notification
**Triggers when:** Daily at 23:59 UTC

**Expected:**
```
📊 DAILY SUMMARY

Date: January 16, 2026

💰 P&L: $+X.XX
📊 Trades: X (X wins, X losses)
📈 Win Rate: XX.X%

Best Trade: $+X.XX
Worst Trade: $-X.XX

🏆 Top Shadow Strategy: [strategy_name] (+X.XX%)

Balance: $XXX.XX
```

**How to trigger:** Wait until 23:59 UTC or manually trigger (see below)

---

## 🔧 Manual Testing Tools

### Force a Test Notification

If you want to test notifications without waiting for real events, you can trigger them manually from the VPS:

```bash
ssh root@VPS
cd /opt/polymarket-autotrader
source venv/bin/activate
python3

# In Python interpreter:
from telegram_bot.telegram_notifier import notify_trade, notify_redemption

# Test trade notification
notify_trade(
    crypto="BTC",
    direction="Up",
    entry_price=0.42,
    size=5.50,
    shares=13,
    confidence=0.675,
    agents_voted=["TechAgent", "SentimentAgent", "RegimeAgent"],
    strategy="ml_live_ml_random_forest"
)

# Test redemption notification
notify_redemption(
    crypto="BTC",
    direction="Up",
    outcome="win",
    pnl=7.54,
    shares_redeemed=13,
    entry_price=0.42,
    new_balance=208.51
)
```

---

## 📝 Testing Checklist

Use this checklist to track your testing progress:

- [ ] `/start` - Welcome message received
- [ ] `/stats` - Statistics displayed (or "no trades" message)
- [ ] `/balance` - Balance and P&L shown correctly
- [ ] `/positions` - Open positions listed (or "no positions")
- [ ] `/status` - Bot status shown
- [ ] `/halt` - Confirmation prompt received
- [ ] `/mode` - Mode info displayed
- [ ] `/mode conservative` + `/confirm_mode` - Mode changed successfully
- [ ] `/mode normal` - Restored to normal
- [ ] `/halt` + `/confirm_halt` - Bot halted
- [ ] `/resume` + `/confirm_resume` - Bot resumed
- [ ] Trade notification received (when bot trades)
- [ ] Redemption notification received (when position resolves)

---

## 🐛 Troubleshooting

### Bot doesn't respond to commands

**Check 1:** Is Telegram bot running?
```bash
ssh root@VPS "systemctl status telegram-bot"
```

**Check 2:** Are you the authorized user?
```bash
ssh root@VPS "grep TELEGRAM_AUTHORIZED_USER_ID /opt/polymarket-autotrader/.env"
```
Compare this to your Telegram user ID

**Check 3:** Check Telegram bot logs
```bash
ssh root@VPS "tail -50 /opt/polymarket-autotrader/logs/telegram_bot.log"
```

---

### Commands return errors

**Check database:**
```bash
ssh root@VPS "ls -lh /opt/polymarket-autotrader/simulation/trade_journal.db"
```

**Check state file:**
```bash
ssh root@VPS "cat /opt/polymarket-autotrader/v12_state/trading_state.json"
```

---

### Notifications not arriving

**Check if notifications are enabled:**
```bash
ssh root@VPS "grep TELEGRAM_NOTIFICATIONS_ENABLED /opt/polymarket-autotrader/telegram_bot/telegram_notifier.py"
```

**Restart Telegram bot:**
```bash
ssh root@VPS "systemctl restart telegram-bot"
```

---

## ✅ Success Criteria

Your Telegram bot is working correctly if:

1. ✅ All query commands return data (or appropriate "no data" messages)
2. ✅ Control commands show confirmation prompts
3. ✅ Mode changes are reflected in state file
4. ✅ Halt/resume cycle works without errors
5. ✅ Notifications arrive when events occur
6. ✅ No errors in telegram_bot.log

---

## 📞 Getting Your Telegram User ID

If you need to verify your authorized user ID:

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID
3. Compare to `TELEGRAM_AUTHORIZED_USER_ID` in `.env`

---

## 🎯 Next Steps After Testing

Once all tests pass:

1. **Document any issues** found during testing
2. **Verify notifications** arrive in real trading scenarios
3. **Set up alerts** for critical events
4. **Monitor daily summaries** for performance tracking

---

**Happy Testing! 🚀**
