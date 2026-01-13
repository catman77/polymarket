# Agent System Integration Guide

## Quick Start

### 1. Deploy in Log-Only Mode (Safe - No Trading Changes)

```bash
# From your local machine
cd /Volumes/TerraTitan/Development/polymarket-autotrader
./scripts/deploy_agents.sh log_only
```

This will:
- Deploy agent system to VPS
- Run in LOG-ONLY mode (agents log decisions but don't execute)
- Keep existing bot logic unchanged
- Monitor logs to see what agents would decide

### 2. Monitor Agent Decisions

```bash
# SSH to VPS
ssh -i ~/.ssh/polymarket_vultr root@216.238.85.11

# Watch logs for agent decisions
tail -f /opt/polymarket-autotrader/bot.log | grep -E "Agent|VOTE|DECISION"
```

Look for patterns like:
```
[BTC] Agent Decision:
  Should Trade: True
  Direction: Down
  Confidence: 79.00%
  Weighted Score: 0.786
  Vote Breakdown: Up=0 Down=2 Neutral=1
  Reason: Down consensus from 3 experts...
```

### 3. Enable Live Trading (After Validation)

**Option A: Conservative Mode** (Recommended First)
```bash
./scripts/deploy_agents.sh conservative
```
- High consensus threshold (0.75)
- Only trades with strong agreement
- Fewer trades, higher confidence

**Option B: Moderate Mode** (Recommended Long-Term)
```bash
./scripts/deploy_agents.sh moderate
```
- Balanced consensus threshold (0.65)
- Good mix of trade frequency and confidence
- Best overall performance

**Option C: Aggressive Mode** (Higher Risk)
```bash
./scripts/deploy_agents.sh aggressive
```
- Lower consensus threshold (0.55)
- More trades with lower confidence
- Higher volume, higher risk

---

## Manual Integration

If you want to manually integrate into `momentum_bot_v12.py`:

### Step 1: Import Agent System

Add at top of `momentum_bot_v12.py`:

```python
from bot.agent_wrapper import AgentSystemWrapper
from config import agent_config
```

### Step 2: Initialize Agents

In the `main()` function, after initializing other components:

```python
# Initialize agent system
agent_system = AgentSystemWrapper()  # Uses config/agent_config.py settings

log.info(f"Agent System: {'ENABLED' if agent_system.enabled else 'LOG-ONLY'}")
```

### Step 3: Replace Trading Logic

Find the section where trading decisions are made (around line 1700-1800).

**Before (Old Logic):**
```python
# Check for contrarian opportunity
if (CONTRARIAN_ENABLED and
    CONTRARIAN_MIN_TIME <= time_in_epoch <= CONTRARIAN_MAX_TIME):

    if (up_price >= CONTRARIAN_PRICE_THRESHOLD and
        down_price <= CONTRARIAN_MAX_ENTRY):
        direction = "Down"
        entry_price = down_price
        # ... etc
```

**After (Agent Logic):**
```python
# Get decision from agent system
should_trade, direction, confidence, reason = agent_system.make_decision(
    crypto=crypto,
    epoch=epoch,
    prices={
        'btc': btc_price,
        'eth': eth_price,
        'sol': sol_price,
        'xrp': xrp_price
    },
    orderbook={
        'yes': {'price': up_price, 'ask': up_price},
        'no': {'price': down_price, 'ask': down_price}
    },
    positions=guardian.open_positions,
    balance=get_usdc_balance(),
    time_in_epoch=time_in_epoch,
    rsi=rsi_calc.get_rsi(crypto),
    regime=current_regime if 'current_regime' in locals() else 'unknown',
    mode=recovery.state.mode
)

if not should_trade:
    log.info(f"  [{crypto.upper()}] AGENTS SKIP: {reason}")
    continue

# Get position size from risk agent
position_size = agent_system.get_position_size(
    confidence=confidence,
    balance=get_usdc_balance(),
    consecutive_losses=recovery.state.consecutive_losses
)

log.info(f"  [{crypto.upper()}] AGENTS APPROVE: {direction} @ {confidence:.0%} (${position_size:.2f})")
```

### Step 4: Keep Fallback Logic

For safety, keep the old logic as a fallback:

```python
try:
    # Try agent system first
    should_trade, direction, confidence, reason = agent_system.make_decision(...)

    if should_trade:
        # Use agent decision
        pass
    else:
        # Fall back to old logic
        # ... existing code ...

except Exception as e:
    log.error(f"Agent system error: {e}")
    # Fall back to old logic
    # ... existing code ...
```

---

## Configuration

Edit `config/agent_config.py` to customize behavior:

### Change Mode Programmatically

```python
from config import agent_config

# Switch to conservative mode
agent_config.apply_mode('conservative')

# Or set individual settings
agent_config.CONSENSUS_THRESHOLD = 0.70
agent_config.MIN_CONFIDENCE = 0.55
```

### Adjust Agent Weights

```python
# Boost TechAgent, reduce SentimentAgent
agent_config.AGENT_WEIGHTS = {
    'TechAgent': 1.2,
    'SentimentAgent': 0.8,
    'RegimeAgent': 1.0,
    'RiskAgent': 1.0,
}
```

### Tune Risk Settings

```python
# More conservative position sizing
agent_config.RISK_POSITION_TIERS = [
    (30, 0.10),   # Reduce from 15% to 10%
    (75, 0.07),   # Reduce from 10% to 7%
    (150, 0.05),  # Reduce from 7% to 5%
    (float('inf'), 0.03),  # Reduce from 5% to 3%
]
```

---

## Monitoring & Validation

### Check Agent Performance

```python
# Get performance report
report = agent_system.get_performance_report()

for agent_name, metrics in report['agents'].items():
    print(f"{agent_name}:")
    print(f"  Accuracy: {metrics['accuracy']:.1%}")
    print(f"  Total Votes: {metrics['total_votes']}")
```

### Watch Live Logs

```bash
# On VPS
tail -f /opt/polymarket-autotrader/bot.log | grep -A 10 "Agent Decision"
```

### Compare Agent vs Old Bot

In log-only mode, you'll see both:
- Agent decision (what agents would do)
- Old bot decision (what actually happens)

Compare to validate agents are making good decisions before going live.

---

## Rollback Plan

If agents underperform:

### Immediate Rollback (Same Config)

```bash
# Disable agents without code changes
ssh root@216.238.85.11
cd /opt/polymarket-autotrader

# Edit config
nano config/agent_config.py
# Change: CURRENT_MODE = 'log_only'

# Restart
systemctl restart polymarket-bot
```

### Full Rollback (Git)

```bash
# Revert to previous version
git checkout HEAD~1 bot/momentum_bot_v12.py
git push origin main --force

# Redeploy
./scripts/deploy.sh
```

### Adjust Threshold

If too many trades:
```python
agent_config.CONSENSUS_THRESHOLD = 0.75  # More selective
```

If too few trades:
```python
agent_config.CONSENSUS_THRESHOLD = 0.55  # More aggressive
```

---

## Testing Checklist

Before enabling live trading:

- [ ] Deployed in log-only mode
- [ ] Monitored for 24 hours
- [ ] Agent decisions make sense
- [ ] No errors in logs
- [ ] Consensus threshold appropriate
- [ ] Position sizing reasonable
- [ ] Vetoes working (blocking unsafe trades)
- [ ] Performance tracking functional
- [ ] Fallback logic tested

---

## Common Issues

### "No module named 'agents'"

**Solution:**
```bash
cd /opt/polymarket-autotrader
pip install -e .
# Or add to PYTHONPATH
export PYTHONPATH=/opt/polymarket-autotrader:$PYTHONPATH
```

### Agents always vote Neutral

**Cause:** Insufficient data (price history, orderbook)

**Solution:** Wait 5-10 minutes for price data to accumulate

### Consensus never met

**Cause:** Threshold too high or agents disagree

**Solution:** Lower threshold or check agent configurations:
```python
agent_config.CONSENSUS_THRESHOLD = 0.60  # Lower from 0.65
```

### Import errors on VPS

**Solution:**
```bash
cd /opt/polymarket-autotrader
pip install requests web3 python-dotenv
```

---

## Performance Expectations

### Log-Only Mode (Week 1)
- No performance impact
- Validate decisions match expectations
- ~70% of decisions should align with profitable trades

### Conservative Mode (Week 2)
- 10-15 trades per day
- 75-80% win rate (selective)
- +15-20% daily profit increase

### Moderate Mode (Week 3+)
- 50-70 trades per day
- 70-75% win rate
- +100-150% daily profit increase

---

## Support

If issues occur:

1. Check logs: `/opt/polymarket-autotrader/bot.log`
2. Check config: `config/agent_config.py`
3. Test wrapper: `python3 bot/agent_wrapper.py`
4. Run tests: `python3 tests/test_4_agent_system.py`
5. Review documentation: `docs/PHASE2_4_AGENTS_COMPLETE.md`

**Emergency Disable:**
```bash
ssh root@216.238.85.11
cd /opt/polymarket-autotrader
echo "log_only" > config/agent_mode.txt
systemctl restart polymarket-bot
```

This immediately reverts to log-only mode without code changes.
