# `/auto-manage` - Autonomous Event-Driven Management

**The "Uber Command" - Set it and forget it**

## Purpose

Automatically detects critical events and spawns specialized agents to handle them **without any human intervention**.

## How It Works

```
┌────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN AUTO-MANAGEMENT                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  1. CONTINUOUS MONITORING (Every 5 minutes)                │
│     • Bot status (halted?)                                 │
│     • Win rate (dropping?)                                 │
│     • Balance (too low?)                                   │
│     • Redemptions (pending?)                               │
│     • Patterns (profitable opportunities?)                 │
│                                                            │
│  2. EVENT DETECTION                                        │
│     • Bot halted → CRITICAL                                │
│     • Win rate drop >10% → HIGH                            │
│     • Losing streak ≥3 → HIGH                              │
│     • Redemptions $10+ → MEDIUM                            │
│     • Profitable pattern 75%+ WR → MEDIUM                  │
│                                                            │
│  3. AUTOMATIC AGENT SPAWNING                               │
│     ┌──────────────────────────────────────────┐          │
│     │ EVENT: Bot Halted                         │          │
│     │ → Spawn Recovery Agent                    │          │
│     │   Task: "Analyze halt, restore trading"  │          │
│     │ → Spawn Diagnostic Agent                  │          │
│     │   Task: "Identify root cause"             │          │
│     └──────────────────────────────────────────┘          │
│                                                            │
│  4. AUTONOMOUS RESOLUTION                                  │
│     • Agents execute without approval                      │
│     • Changes logged for transparency                      │
│     • Results monitored and validated                      │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Event → Agent Mapping

| Event | Severity | Agents Spawned | Action |
|-------|----------|----------------|--------|
| **Bot Halted** | CRITICAL | Recovery Agent<br>Diagnostic Agent | Restore trading ASAP<br>Prevent recurrence |
| **Win Rate Drop** | HIGH | Diagnostic Agent<br>Risk Analysis Agent | Find why WR dropped<br>Analyze recent trades |
| **Losing Streak** | HIGH | Risk Analysis Agent<br>Adaptation Agent | Investigate cause<br>Adapt strategy |
| **Profitable Pattern** | MEDIUM | Optimization Agent | Exploit discovered pattern |
| **Regime Shift** | MEDIUM | Adaptation Agent<br>Optimization Agent | Adapt to new regime<br>Optimize for conditions |
| **Large Loss** | HIGH | Risk Analysis Agent<br>Diagnostic Agent | Investigate root cause<br>Prevent future losses |
| **Redemptions Pending** | MEDIUM | Redemption Agent | Auto-redeem all winners |
| **Balance Low** | HIGH | Balance Manager<br>Redemption Agent | Manage low balance<br>Redeem to restore funds |
| **Position Stuck** | MEDIUM | Position Resolver | Resolve stuck positions |
| **Agent Disagreement** | MEDIUM | Consensus Builder<br>Diagnostic Agent | Resolve disagreement<br>Analyze why it occurred |

## Available Agents

### 1. **Recovery Agent**
**When:** Bot halted
**Task:** Analyze halt reason (drawdown, daily loss, consecutive losses) and restore trading
**Actions:**
- Reset peak balance if false drawdown
- Clear consecutive loss counter if justified
- Adjust risk parameters to prevent re-halt
- Restart bot service

### 2. **Diagnostic Agent**
**When:** Any abnormal behavior
**Task:** Deep-dive analysis of root causes
**Actions:**
- Analyze recent logs for errors
- Check agent vote patterns
- Review market conditions
- Generate diagnostic report

### 3. **Optimization Agent**
**When:** Profitable pattern detected
**Task:** Maximize exploitation of winning strategies
**Actions:**
- Increase position sizing for pattern
- Adjust entry/exit thresholds
- Enable pattern-specific filters
- Track ROI of optimizations

### 4. **Adaptation Agent**
**When:** Regime shift or losing streak
**Task:** Adjust strategy to current conditions
**Actions:**
- Detect new market regime (bull/bear/choppy)
- Switch strategy focus (momentum/contrarian/late)
- Adjust agent weights for regime
- Update risk parameters

### 5. **Risk Analysis Agent**
**When:** Large loss or losing streak
**Task:** Prevent future losses
**Actions:**
- Analyze losing trades for patterns
- Identify which strategies are failing
- Recommend disabling/reducing losing strategies
- Tighten risk limits if needed

### 6. **Redemption Agent**
**When:** $10+ in pending redemptions
**Task:** Auto-redeem all winning positions
**Actions:**
- Fetch all redeemable positions
- Execute Web3 redemption transactions
- Verify redemptions succeeded
- Update balance tracking

### 7. **Balance Manager**
**When:** Balance below $15
**Task:** Manage low balance crisis
**Actions:**
- Trigger redemption of all winners
- Reduce position sizing temporarily
- Switch to ultra-conservative mode
- Alert if critical

### 8. **Position Resolver**
**When:** Positions stuck (not resolving)
**Task:** Resolve stuck positions
**Actions:**
- Check if epoch has ended
- Force redemption if applicable
- Contact Polymarket API if issue
- Log for manual review if unresolvable

### 9. **Consensus Builder**
**When:** Agents disagree significantly
**Task:** Resolve agent conflicts
**Actions:**
- Analyze why agents disagree
- Check data quality for each agent
- Temporarily increase consensus threshold
- Flag for strategy review

### 10. **Market Researcher**
**When:** Unknown market conditions
**Task:** Research unfamiliar patterns
**Actions:**
- Fetch market data from multiple sources
- Compare to historical patterns
- Generate market analysis report
- Recommend strategy adjustments

## Usage

### Start Auto-Management

```bash
# Run continuously (production)
nohup python3 .claude/plugins/polymarket-historian/scripts/event_orchestrator.py > orchestrator.log 2>&1 &
echo $! > orchestrator.pid
```

### Check for Events (Manual)

```bash
# Run single scan
python3 .claude/plugins/polymarket-historian/scripts/event_orchestrator.py --once
```

### View Status

```bash
# Check orchestrator status
python3 .claude/plugins/polymarket-historian/scripts/event_orchestrator.py --status

# View event log
cat .claude/plugins/polymarket-historian/data/events.json

# View agent spawns
cat .claude/plugins/polymarket-historian/data/agent_spawns.json
```

### Stop Auto-Management

```bash
# Kill orchestrator
kill $(cat orchestrator.pid)
```

## Example Event Flow

**Scenario:** Bot halts due to false drawdown

```
┌────────────────────────────────────────────────────────────┐
│ T+0:00 - Bot halts (drawdown 35% > 30% limit)              │
│ T+0:05 - Orchestrator detects halt event                   │
│ T+0:05 - Spawns Recovery Agent                             │
│          Task: "Analyze halt and restore trading"          │
│ T+0:06 - Recovery Agent analyzes state                     │
│          - Finds: peak $58, balance $39 + $15 redeemable   │
│          - Diagnosis: False drawdown (unredeemed winners)  │
│ T+0:07 - Recovery Agent spawns Redemption Agent            │
│          Task: "Redeem $15 in winners"                     │
│ T+0:08 - Redemption Agent redeems positions                │
│          New balance: $54                                  │
│ T+0:09 - Recovery Agent resets peak to $54                 │
│ T+0:10 - Recovery Agent restarts bot                       │
│          Bot resumes trading (drawdown now 0%)             │
│ T+0:15 - Bot places first trade post-recovery              │
│                                                            │
│ RESULT: 15-minute autonomous recovery from halt            │
│         No human intervention required                     │
└────────────────────────────────────────────────────────────┘
```

## Integration with Profitability Loop

The event orchestrator **complements** the profitability loop:

```
┌─────────────────────────────────────────────────┐
│         AUTONOMOUS MANAGEMENT STACK             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Layer 1: EXECUTION (Bot)                       │
│    • Places trades                              │
│    • Follows strategy                           │
│                                                 │
│  Layer 2: LEARNING (Profitability Loop)         │
│    • Collects data                              │
│    • Identifies patterns                        │
│    • Optimizes strategy                         │
│                                                 │
│  Layer 3: EMERGENCY RESPONSE (Orchestrator)     │
│    • Detects critical events                    │
│    • Spawns specialized agents                  │
│    • Resolves issues autonomously               │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Profitability Loop:** Long-term optimization (hours/days)
**Event Orchestrator:** Immediate crisis response (minutes)

Together, they create a **fully autonomous trading system** that:
- Optimizes itself over time
- Recovers from failures instantly
- Adapts to changing conditions
- Requires zero human intervention

## Safety

**What the Orchestrator Can Do:**
✅ Reset peak balance (if false drawdown)
✅ Redeem winning positions
✅ Adjust risk parameters temporarily
✅ Restart bot service
✅ Switch to conservative mode

**What It Cannot Do:**
❌ Change core bot code
❌ Withdraw funds from wallet
❌ Disable all safety limits
❌ Make unauthorized API calls

**All agent actions are logged** in `data/agent_spawns.json` for transparency.

## Benefits

**Without Auto-Management:**
- Bot halts → Wait for human to notice (hours/days)
- Win rate drops → Manual investigation required
- Redemptions pile up → Manual redemption needed
- Low balance → Bot stops trading, opportunity lost

**With Auto-Management:**
- Bot halts → Auto-recovery in <15 minutes
- Win rate drops → Diagnostic agent investigates immediately
- Redemptions pile up → Auto-redeemed every cycle
- Low balance → Emergency redemption + conservative mode

**Average recovery time: <15 minutes vs hours/days**

## When to Use

**Always on in production.**

The orchestrator is designed to run 24/7 alongside the bot and profitability loop.

**Disable only if:**
- Testing new strategies manually
- Need full control for debugging
- Running on limited resources

Otherwise, let it run and forget about it.

## Monitoring

View what the orchestrator is doing:

```bash
# Recent events
tail .claude/plugins/polymarket-historian/data/events.json

# Recent agent spawns
tail .claude/plugins/polymarket-historian/data/agent_spawns.json

# Live log
tail -f orchestrator.log
```

---

**The Uber Command - Set it once, runs forever, handles everything.**
