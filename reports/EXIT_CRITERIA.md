# Exit Criteria and Risk Thresholds

**Version:** 1.0
**Created:** 2026-01-16
**Owner:** Prof. Eleanor Nash (Strategic Synthesis)
**Purpose:** Define quantitative triggers for operational decisions (HALT, PAUSE, SCALE UP)

---

## Philosophy

> "When should we shut down the bot? When should we scale up? Clear quantitative triggers prevent emotional decisions."
> — Prof. Eleanor Nash, Game Theory Economist

**Principle:** Risk management requires **hard rules**, not subjective judgment.

- ✅ **Quantitative:** Measurable thresholds (%, $, counts)
- ✅ **Automated:** Bot enforces triggers without human intervention
- ✅ **Conservative:** Err on the side of caution (protect capital first)
- ❌ **Emotional:** "It feels like a bad streak" → Not acceptable
- ❌ **Subjective:** "The market looks scary" → Not actionable

---

## HALT Criteria (Immediate Shutdown)

**Definition:** Stop all trading immediately. Requires manual restart with investigation.

### Trigger 1: Drawdown Exceeds 30%
**Formula:** `(peak_balance - current_balance) / peak_balance > 0.30`

**Example:**
- Peak balance: $300
- Current balance: $209
- Drawdown: ($300 - $209) / $300 = 30.3% → **HALT**

**Rationale:**
- 30% loss is psychologically difficult to recover from (requires 43% gain)
- Historical data: Jan 16 desync showed 33% drawdown triggered halt (correct behavior)
- Stress tests: 10-loss streak at $200 = 26.3% drawdown (within tolerance)

**Actions:**
1. Log HALT event with timestamp and reason
2. Stop trading loop (no new positions)
3. Send alert: Email/SMS to operator
4. Write halt reason to `state/trading_state.json` → `mode: "halted"`
5. Await manual restart command

**Override:** Can only be reset by manual state file edit + bot restart

---

### Trigger 2: Consecutive Losses ≥ 8
**Formula:** `consecutive_losses >= 8`

**Example:**
- Last 8 trades: L, L, L, L, L, L, L, L → **HALT**

**Rationale:**
- 8 losses in a row is statistically unlikely at 58% WR (p = 0.0003%)
- Indicates either strategy failure or adverse market conditions
- Prevents catastrophic drawdown from continuing bad streak

**Actions:**
1. Log HALT event with loss streak details
2. Stop trading immediately
3. Trigger investigation: Review last 8 trades for common failure pattern
4. Alert operator with trade IDs and entry details

**Recovery:**
- Manual restart required
- Operator must investigate loss pattern before resuming
- Consider strategy adjustment (raise thresholds, disable agent, etc.)

---

### Trigger 3: Daily Loss Exceeds $30 OR 20% of Balance
**Formula:** `daily_pnl < -30 OR (daily_pnl / day_start_balance) < -0.20`

**Example 1 (Absolute loss):**
- Day start balance: $200
- Daily P&L: -$32 → **HALT** (exceeds $30 limit)

**Example 2 (Percentage loss):**
- Day start balance: $100
- Daily P&L: -$22 → **HALT** (22% loss)

**Rationale:**
- Limits maximum daily damage (prevents single-day blowup)
- Percentage-based protects small accounts (20% of $50 = $10 limit)
- Absolute limit protects large accounts ($30 limit regardless of size)

**Actions:**
1. Log HALT event with daily loss details
2. Stop trading for remainder of day (UTC 00:00 reset)
3. Bot automatically restarts next day if conditions clear
4. Alert operator with trade breakdown

**Recovery:**
- Automatic restart at UTC 00:00 (if other conditions OK)
- Manual restart allowed earlier if operator approves
- Reset `day_start_balance` and `daily_pnl` counters

---

### Trigger 4: Balance Drops Below $50
**Formula:** `current_balance < 50`

**Rationale:**
- Insufficient capital for meaningful position sizing
- Min bet = $1.10, at $50 balance → only 2-3% sizing (too small)
- Prevents trading with insufficient edge (fees dominate)

**Actions:**
1. Log HALT event
2. Stop trading permanently (requires deposit)
3. Alert operator: "Insufficient funds, deposit required"

**Recovery:**
- Operator deposits additional funds (≥$100 recommended)
- Manual restart after balance ≥$100
- Reset `peak_balance` to new starting balance

---

### Trigger 5: Critical System Error (Exception Loop)
**Formula:** `errors_in_last_60s >= 10`

**Example:**
- Bot logs 10 exceptions in 60 seconds (API timeouts, RPC failures, etc.)

**Rationale:**
- Indicates infrastructure failure (not strategy failure)
- Prevents bot from burning CPU in error loop
- Avoids placing erroneous trades during system malfunction

**Actions:**
1. Log HALT event with error stack trace
2. Stop trading immediately
3. Exit gracefully (save state, close connections)
4. Alert operator: "Critical system error, manual intervention required"

**Recovery:**
- Operator investigates root cause (API down, network issue, etc.)
- Fix infrastructure problem before restart
- Manual restart after issue resolved

---

## PAUSE Criteria (Temporary Suspension)

**Definition:** Stop trading temporarily. Automatically resumes when conditions improve.

### Trigger 1: Win Rate Drops Below 53% (Over Last 50 Trades)
**Formula:** `win_rate_50_trades < 0.53`

**Example:**
- Last 50 trades: 26 wins, 24 losses
- Win rate: 26/50 = 52% → **PAUSE**

**Rationale:**
- 53% is breakeven after fees (6.3% round-trip at 50% probability)
- Below 53% = negative edge (losing money over time)
- 50-trade window = ~1 week of data (statistically meaningful)

**Actions:**
1. Log PAUSE event
2. Stop placing new trades (finish open positions)
3. Alert operator: "Win rate below breakeven, paused for analysis"
4. Trigger analysis:
   - Check if regime changed (bull → bear, etc.)
   - Review agent performance (did specific agent degrade?)
   - Validate entry prices (are we buying too expensive?)

**Resume Conditions:**
- Win rate recovers to ≥55% over 20 trades
- OR operator manually overrides after investigation
- OR strategy adjustment deployed (raise thresholds, disable agent, etc.)

**Auto-Resume:** Yes (if win rate improves organically)

---

### Trigger 2: Regime Shift Detected (Volatile → Extreme Volatile)
**Formula:** `regime_volatility_percentile > 95`

**Example:**
- RegimeAgent detects volatility exceeds 95th percentile (extreme market conditions)
- Crypto markets enter "flash crash" or "melt-up" phase

**Rationale:**
- Extreme volatility = unpredictable outcomes
- 15-minute binary outcomes become coin flips in high volatility
- Risk of rapid, large losses in unstable markets

**Actions:**
1. Log PAUSE event with regime details
2. Stop placing new trades
3. Monitor regime every 15 minutes
4. Alert operator: "Extreme volatility detected, paused"

**Resume Conditions:**
- Volatility drops below 85th percentile for 1 hour
- OR operator manually overrides (if confident in strategy)

**Auto-Resume:** Yes (after volatility stabilizes)

---

### Trigger 3: Position Limit Saturated (4/4 Positions Open)
**Formula:** `open_positions >= MAX_POSITIONS (4)`

**Example:**
- Bot has open positions: BTC Up, ETH Down, SOL Up, XRP Down
- Cannot open new positions until one resolves

**Rationale:**
- Risk management: Max 4 positions prevents overexposure
- Correlation protection: Avoids excessive same-direction exposure
- Liquidity protection: Ensures capital available for redemption

**Actions:**
1. Log PAUSE event (temporary)
2. Wait for next epoch resolution (~15 minutes)
3. Resume scanning after position closes

**Resume Conditions:**
- Any position resolves (win or loss)
- Open positions < 4

**Auto-Resume:** Yes (immediately after position closes)

---

### Trigger 4: Directional Exposure Exceeds 8%
**Formula:** `sum(same_direction_positions) / balance > 0.08`

**Example:**
- Balance: $200
- Open positions: BTC Up ($8), ETH Up ($6), SOL Up ($4)
- Total Up exposure: $18 / $200 = 9% → **PAUSE** (no more Up trades)

**Rationale:**
- Prevents directional bias (all Up or all Down)
- Protects against correlated losses (all cryptos move together)
- Ensures portfolio balance

**Actions:**
1. Log PAUSE event (directional limit)
2. Block new trades in over-exposed direction (Up or Down)
3. Allow trades in opposite direction

**Resume Conditions:**
- Directional exposure drops below 7%
- OR opposite direction positions balance out total exposure

**Auto-Resume:** Yes (after exposure rebalances)

---

## SCALE UP Criteria (Increase Position Sizing)

**Definition:** Increase position sizing after proven performance. Conservative increments only.

### Trigger 1: Consistent Win Rate > 60% (Over Last 100 Trades)
**Formula:** `win_rate_100_trades > 0.60`

**Example:**
- Last 100 trades: 62 wins, 38 losses
- Win rate: 62% → **SCALE UP ELIGIBLE**

**Rationale:**
- 60% WR = strong edge (10% above breakeven)
- 100 trades = ~2 weeks of data (high confidence)
- Statistical significance: p < 0.05 (not luck)

**Actions:**
1. Log SCALE UP eligibility
2. Increase max position size:
   - Current: 5-15% tiered sizing
   - New: 7-20% tiered sizing (+2% across all tiers)
3. Monitor for 50 trades at new sizing
4. If WR drops <58%, revert to original sizing

**Increment:** +2% per tier (gradual increase)

**Max Cap:** 20% per trade (never risk more than 20% on single position)

---

### Trigger 2: Balance Exceeds $500 (Profitable Growth)
**Formula:** `current_balance > 500 AND balance > day_start_balance * 2.5`

**Example:**
- Starting balance: $200
- Current balance: $520
- Growth: 2.6x → **SCALE UP ELIGIBLE**

**Rationale:**
- Balance growth indicates sustainable profitability
- $500+ provides sufficient capital for larger positions
- 2.5x multiplier ensures growth is not from deposit (must be earned)

**Actions:**
1. Log SCALE UP eligibility
2. Increase max position size:
   - Current: $15 max bet
   - New: $25 max bet (+$10)
3. Apply tiered sizing (still use 5-15% tiers based on balance)

**Increment:** +$10 max bet per milestone ($500, $1000, $2000, etc.)

**Max Cap:** $100 per trade (protect against single large loss)

---

### Trigger 3: 50 Consecutive Trades Without HALT/PAUSE
**Formula:** `trades_since_last_halt >= 50 AND no_pause_events_in_last_week`

**Rationale:**
- System stability = confidence in strategy
- 50 trades without incident = 1 week of clean operation
- Indicates risk controls are working correctly

**Actions:**
1. Log SCALE UP eligibility (stability bonus)
2. Unlock additional features:
   - Enable shadow strategy auto-promotion (if disabled)
   - Consider re-enabling contrarian trades (if disabled)
   - Explore new cryptos (XRP, DOGE) or timeframes (30-min)

**Increment:** Feature unlock (not position sizing)

**Rollback:** If any HALT/PAUSE triggered, reset counter to 0

---

## Decision Tree: Operational Response

```
┌─────────────────────────────────────────────────────┐
│          New Trade Opportunity Detected             │
└─────────────────────────────┬───────────────────────┘
                              │
                  ┌───────────▼──────────┐
                  │  Check HALT Criteria │
                  └───────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
         │ Balance │    │Drawdown │    │  Loss   │
         │  < $50  │    │  > 30%  │    │Streak≥8│
         └────┬────┘    └────┬────┘    └────┬────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                         ┌────▼────┐
                         │  HALT?  │
                         └────┬────┘
                              │
                  ┌───────────┼───────────┐
                  │YES                   │NO
            ┌─────▼─────┐         ┌─────▼─────┐
            │   HALT    │         │Check PAUSE│
            │  Trading  │         │ Criteria  │
            │  Alert!   │         └─────┬─────┘
            └───────────┘               │
                                   ┌────┼────┐
                                   │         │
                            ┌──────▼───┐ ┌──▼─────┐
                            │ WR<53%   │ │Volatile│
                            │(50 trd)  │ │Regime  │
                            └──────┬───┘ └──┬─────┘
                                   │        │
                                   └────┬───┘
                                        │
                                   ┌────▼────┐
                                   │ PAUSE?  │
                                   └────┬────┘
                                        │
                            ┌───────────┼──────────┐
                            │YES               │NO
                     ┌──────▼──────┐    ┌─────▼─────┐
                     │   PAUSE     │    │   TRADE   │
                     │   Trading   │    │  ALLOWED  │
                     │Wait Resume  │    └─────┬─────┘
                     └─────────────┘          │
                                        ┌─────▼─────┐
                                        │Check Scale│
                                        │   Up      │
                                        └─────┬─────┘
                                              │
                                   ┌──────────┼─────────┐
                                   │                    │
                            ┌──────▼───┐        ┌──────▼────┐
                            │ WR>60%   │        │Balance>$500│
                            │(100 trd) │        │ (2.5x)     │
                            └──────┬───┘        └──────┬─────┘
                                   │                   │
                                   └─────────┬─────────┘
                                             │
                                        ┌────▼────┐
                                        │Scale Up?│
                                        └────┬────┘
                                             │
                                 ┌───────────┼──────────┐
                                 │YES               │NO
                          ┌──────▼──────┐    ┌─────▼─────┐
                          │  Increase   │    │  Normal   │
                          │  Position   │    │  Trading  │
                          │   Sizing    │    │           │
                          └─────────────┘    └───────────┘
```

---

## Escalation Procedures

### Level 1: Automated Response (No Human Required)
**Triggers:** PAUSE (WR drop, volatility, position limits)
- **Action:** Bot handles automatically (pause → resume when clear)
- **Alert:** Log entry only (no notification)
- **Human Involvement:** None (unless PAUSE persists >24 hours)

### Level 2: Notification (Human Awareness)
**Triggers:** HALT (drawdown, loss streak, daily loss)
- **Action:** Bot stops trading immediately
- **Alert:** Email/SMS to operator within 5 minutes
- **Human Involvement:** Investigate cause, decide restart timing
- **Timeline:** Respond within 4 hours

### Level 3: Investigation (Root Cause Analysis)
**Triggers:** Repeated HALT (3+ times in 7 days)
- **Action:** Bot remains halted pending investigation
- **Alert:** Email with detailed trade log analysis
- **Human Involvement:** Full investigation required
  - Review last 100 trades for pattern
  - Check if market conditions changed
  - Validate strategy assumptions
  - Consider strategy overhaul or retirement
- **Timeline:** Respond within 24 hours

### Level 4: Critical (System Failure)
**Triggers:** Critical system error, infrastructure failure
- **Action:** Bot shuts down completely
- **Alert:** Immediate SMS + email + Slack ping
- **Human Involvement:** Emergency response required
  - Check VPS health (CPU, memory, disk)
  - Verify API endpoints operational
  - Review error logs for stack trace
  - Restart infrastructure if needed
- **Timeline:** Respond within 1 hour

---

## Monitoring & Alerts

### Real-Time Dashboards
1. **Live Balance Tracker**
   - Current balance, peak balance, drawdown %
   - Update every 60 seconds
   - Red alert if drawdown >25%

2. **Win Rate Tracker (50-trade window)**
   - Rolling win rate, last 50 trades
   - Update after each trade resolution
   - Yellow alert if WR <55%, red if WR <53%

3. **Position Monitor**
   - Open positions (count, direction, exposure)
   - Update every 15 seconds
   - Alert if directional exposure >7%

### Daily Reports (Email @ 00:00 UTC)
- Daily P&L, trade count, win rate
- Peak balance, current drawdown
- Mode status (normal, conservative, defensive, recovery, halted)
- Next milestone progress (if scaling up)

### Weekly Reports (Email @ Monday 00:00 UTC)
- 7-day performance summary
- Comparison to previous week
- Agent performance (if multi-agent enabled)
- Recommendations (scale up, pause, adjust strategy)

---

## Configuration Integration

### In `config/agent_config.py`:
```python
# Exit Criteria Configuration
EXIT_CRITERIA = {
    # HALT triggers
    "MAX_DRAWDOWN_PCT": 0.30,              # 30% max drawdown
    "MAX_CONSECUTIVE_LOSSES": 8,           # 8 loss streak
    "MAX_DAILY_LOSS_USD": 30,              # $30 daily loss limit
    "MAX_DAILY_LOSS_PCT": 0.20,            # 20% daily loss limit
    "MIN_BALANCE_USD": 50,                 # Min balance to trade

    # PAUSE triggers
    "MIN_WIN_RATE_50_TRADES": 0.53,        # 53% breakeven WR
    "REGIME_VOLATILITY_HALT_PERCENTILE": 95,  # Extreme volatility
    "MAX_POSITIONS": 4,                    # Position limit
    "MAX_DIRECTIONAL_EXPOSURE_PCT": 0.08,  # 8% max one direction

    # SCALE UP triggers
    "SCALE_UP_WIN_RATE_100_TRADES": 0.60,  # 60% WR for scaling
    "SCALE_UP_BALANCE_USD": 500,           # $500 milestone
    "SCALE_UP_BALANCE_MULTIPLIER": 2.5,    # 2.5x earned growth
    "SCALE_UP_STABILITY_TRADES": 50,       # 50 clean trades

    # Alerts
    "ALERT_EMAIL": "operator@example.com",
    "ALERT_SMS": "+1234567890",
    "ALERT_SLACK_WEBHOOK": "https://hooks.slack.com/...",
}
```

### In `bot/momentum_bot_v12.py`:
```python
# Example HALT check (every scan cycle)
def check_exit_criteria(self):
    """Check HALT, PAUSE, and SCALE UP triggers."""
    # HALT: Drawdown
    drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
    if drawdown > EXIT_CRITERIA["MAX_DRAWDOWN_PCT"]:
        self.trigger_halt(f"Drawdown {drawdown:.1%} exceeds {EXIT_CRITERIA['MAX_DRAWDOWN_PCT']:.0%}")
        return "HALT"

    # HALT: Loss streak
    if self.consecutive_losses >= EXIT_CRITERIA["MAX_CONSECUTIVE_LOSSES"]:
        self.trigger_halt(f"Loss streak {self.consecutive_losses} exceeds {EXIT_CRITERIA['MAX_CONSECUTIVE_LOSSES']}")
        return "HALT"

    # HALT: Daily loss
    if self.daily_pnl < -EXIT_CRITERIA["MAX_DAILY_LOSS_USD"]:
        self.trigger_halt(f"Daily loss ${abs(self.daily_pnl):.2f} exceeds ${EXIT_CRITERIA['MAX_DAILY_LOSS_USD']}")
        return "HALT"

    # PAUSE: Win rate
    if len(self.last_50_trades) >= 50:
        wr_50 = sum(self.last_50_trades) / 50
        if wr_50 < EXIT_CRITERIA["MIN_WIN_RATE_50_TRADES"]:
            self.trigger_pause(f"Win rate {wr_50:.1%} below breakeven {EXIT_CRITERIA['MIN_WIN_RATE_50_TRADES']:.0%}")
            return "PAUSE"

    # SCALE UP: Win rate + balance
    if len(self.last_100_trades) >= 100:
        wr_100 = sum(self.last_100_trades) / 100
        if wr_100 > EXIT_CRITERIA["SCALE_UP_WIN_RATE_100_TRADES"] and \
           self.current_balance > EXIT_CRITERIA["SCALE_UP_BALANCE_USD"]:
            self.trigger_scale_up("Win rate and balance milestones reached")
            return "SCALE_UP"

    return "NORMAL"
```

---

## Success Metrics

**Criteria are effective if:**
- ✅ No false positives: HALT only triggers on legitimate failures (not noise)
- ✅ No false negatives: HALT triggers before catastrophic loss (drawdown <40%)
- ✅ PAUSE prevents bleed: Win rate recovers after pause (not ignored)
- ✅ SCALE UP is earned: Only scales after proven performance (not premature)

**Failure indicators:**
- ❌ HALT triggered >5 times in 30 days (strategy is unstable)
- ❌ PAUSE ignored: Win rate continues dropping after pause (no recovery)
- ❌ SCALE UP backfires: Win rate drops after increasing sizing
- ❌ Emotional override: Operator disables criteria (defeats purpose)

---

## Review Schedule

**Monthly:** Review exit criteria effectiveness
- Count HALT/PAUSE/SCALE UP events
- Validate thresholds are appropriate (not too loose/tight)
- Adjust based on new data (market volatility changes, etc.)

**Quarterly:** Comprehensive audit
- Compare exit criteria to industry best practices
- Validate against stress tests (Monte Carlo simulations)
- Update thresholds based on 3 months of performance data

**Annually:** Strategic review
- Evaluate if criteria align with long-term goals
- Consider new criteria (e.g., Sharpe ratio, max profit taking)
- Document lessons learned for next generation system

---

## Appendix: Historical Events

### Jan 14, 2026: Trend Filter Bias
**Event:** Lost 95% ($157 → $7) in 12 hours due to directional bias
**Criteria Triggered:** Should have triggered HALT at 30% drawdown (~$110 balance)
**Actual:** Continued trading until near-zero (drawdown protection failed)
**Root Cause:** Peak balance included unredeemed positions (state tracking bug)
**Fix Applied:** Cash-only peak tracking (Milestone 1.1)
**Lesson:** Exit criteria only work if state tracking is accurate

### Jan 16, 2026: State Desync
**Event:** Peak balance was $386.97, actual balance $200.97 ($186 error)
**Criteria Triggered:** False HALT at 33% drawdown (should have been 0%)
**Actual:** Bot halted correctly based on corrupt state data
**Root Cause:** Peak balance incremented on order placement (should be cash only)
**Fix Applied:** Cash-only peak tracking (Milestone 1.1)
**Lesson:** State integrity is prerequisite for risk management

### Jan 16, 2026: Recovery from $6.81
**Event:** Recovered from $6.81 to $200.97 (+$194 profit)
**Criteria Triggered:** Should have HALTED at <$50 balance
**Actual:** Continued trading (recovery mode enabled)
**Root Cause:** MIN_BALANCE_USD not implemented yet
**Fix Applied:** Add MIN_BALANCE_USD = $50 check (this PRD)
**Lesson:** Recoveries are lucky, not strategic. HALT at low balance prevents ruin.

---

## Conclusion

Exit criteria are the **last line of defense** against catastrophic loss. They must be:

1. **Quantitative:** No ambiguity (30% drawdown = HALT, period)
2. **Automated:** Bot enforces rules without human emotion
3. **Conservative:** Better to stop early than lose everything
4. **Tested:** Validate criteria with historical data and stress tests
5. **Reviewed:** Update criteria as system evolves

**Remember:** Hope is not a strategy. Risk management is survival.

---

**Next Steps:**
1. Implement exit criteria checks in `bot/momentum_bot_v12.py` (Deployment Roadmap)
2. Add configuration to `config/agent_config.py`
3. Set up alert integrations (email, SMS, Slack)
4. Test HALT/PAUSE/SCALE UP triggers with unit tests
5. Monitor effectiveness over 30 days of live trading
6. Adjust thresholds based on real-world performance

---

**Document Version:** 1.0
**Last Updated:** 2026-01-16
**Status:** Ready for Implementation
